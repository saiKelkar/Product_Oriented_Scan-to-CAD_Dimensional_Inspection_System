
import json
from pathlib import Path
import numpy as np

from geometry import load_cad, load_scan
from defects import cluster_flange_defects
from registration_multistart import register_scan_multistart
from registration import register_scan
from features import measure_features
from inspection import evaluate_inspection
from reporting import (
    save_report,
    create_deviation_cloud,
    save_colored_cloud
)


def check_registration(diagnostics, config):
    """Basic registration quality gate."""

    minimum_fitness = config["quality"][
        "minimum_registration_fitness"
    ]

    fitness = diagnostics["final_fitness"]
    rmse = diagnostics["final_rmse_mm"]

    if not np.isfinite(fitness) or fitness < minimum_fitness:
        return "REVIEW"

    if not np.isfinite(rmse):
        return "REVIEW"

    if diagnostics["stable_source_points"] < 100:
        return "REVIEW"

    T = np.asarray(diagnostics["transformation"])

    if T.shape != (4, 4) or not np.all(np.isfinite(T)):
        return "REVIEW"

    return "ACCEPTABLE"



def check_registration_features(registered_scan, config):
    """
    Check whether expected hole features are observable.

    Point count is a preliminary coverage proxy,
    not a physical surface coverage percentage.
    """
    import numpy as np
    from features import measure_horizontal_hole

    points = np.asarray(registered_scan.points)
    diagnostics = {}
    all_acceptable = True

    for hole_name in ["hole_1", "hole_2"]:
        hole_cfg = config["features"][hole_name]

        result = measure_horizontal_hole(
            points,
            approx_y=hole_cfg["approx_center_y_mm"],
            approx_x=hole_cfg["approx_center_x_mm"]
        )

        if result["status"] == "MEASURED":
            diagnostics[hole_name] = {
                "status": "ACCEPTABLE",
                "points_observed": result["num_points"],
                "fit_rmse_mm": result["fit_rmse_mm"]
            }
        else:
            all_acceptable = False

            diagnostics[hole_name] = {
                "status": "REVIEW",
                "points_observed": result.get("num_points", 0),
                "reason": result.get(
                    "reason",
                    "Feature measurement unavailable"
                )
            }

    status = "ACCEPTABLE" if all_acceptable else "REVIEW"

    return status, diagnostics


def run_pipeline(cad_path, scan_path, config_path, output_dir):
    """
    Run the complete scan-to-CAD inspection.

    The inspection never reads synthetic ground truth.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load configuration
    with open(config_path, "r") as f:
        config = json.load(f)

    # 2. Load inputs
    nominal_mesh = load_cad(cad_path)
    raw_scan = load_scan(scan_path)

    # 3. Registration
    # 3. Registration strategy
    strategy = config["registration"].get(
        "strategy", "single_start"
    )

    if strategy == "multi_start":

        registered_scan, multi_info = register_scan_multistart(
            nominal_mesh,
            raw_scan,
            config,
            num_attempts=config["registration"].get(
                "num_attempts", 3
            )
        )

        if multi_info["status"] == "ACCEPTABLE":
            diagnostics = multi_info["registration"].copy()

            diagnostics["multi_start"] = {
                "status": multi_info["status"],
                "selected_attempt": multi_info["selected_attempt"],
                "attempts": multi_info["attempts"]
            }

        else:
            diagnostics = {
                "multi_start": multi_info,
                "final_fitness": 0.0,
                "final_rmse_mm": None,
                "stable_source_points": 0,
                "transformation": None
            }

    elif strategy == "single_start":

        registered_scan, diagnostics = register_scan(
            nominal_mesh,
            raw_scan,
            config
        )

    else:
        raise ValueError(
            f"Unknown registration strategy: {strategy}"
        )

    # 4. Registration quality
    registration_status = check_registration(
        diagnostics,
        config
    )

    # Validate expected hole geometry
    if registration_status == "ACCEPTABLE":

        feature_status, feature_diagnostics = (
            check_registration_features(
                registered_scan,
                config
            )
        )

        diagnostics["feature_validation"] = {
            "status": feature_status,
            "holes": feature_diagnostics
        }

        if feature_status != "ACCEPTABLE":
            registration_status = "REVIEW"

    # 5. Stop inspection if registration is unreliable
    if registration_status != "ACCEPTABLE":
        results = {
            "overall_status": "REVIEW",
            "reason": "Registration quality insufficient",
            "checks": [],
            "summary": {
                "passed": 0,
                "failed": 0,
                "review": 1
            }
        }

        measurements = {}

        report = save_report(
            results,
            diagnostics,
            measurements,
            output_dir / "inspection_report.json"
        )

        return report

    # 6. Feature measurements
    measurements = measure_features(
        nominal_mesh,
        registered_scan,
        config
    )

    # 7. Tolerance evaluation
    results = evaluate_inspection(
        measurements,
        config,
        registration_status
    )

    # 8. Detect localized flange defects
    defect_results = cluster_flange_defects(
        nominal_mesh,
        registered_scan,
        config
    )

    # 8. Save JSON
    report = save_report(
        results,
        diagnostics,
        measurements,
        output_dir / "inspection_report.json"
    )

    # 9. Generate and save colored point cloud
    colored_cloud, deviation_summary = create_deviation_cloud(
        nominal_mesh,
        registered_scan,
        tolerance_mm=config["tolerances"][
            "flange_plane_deviation_mm"
        ]
    )

    save_colored_cloud(
        colored_cloud,
        output_dir / "deviation_cloud.ply"
    )

    # 10. Save point-level deviation summary
    report["deviation_summary"] = deviation_summary
    report["defect_detection"] = defect_results

    with open(output_dir / "inspection_report.json", "w") as f:
        json.dump(report, f, indent=2, allow_nan=False)

    return report
