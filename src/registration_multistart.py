
import numpy as np

from registration import register_scan
from features import measure_horizontal_hole


def validate_hole_features(registered_scan, config):
    """Check both expected holes without using ground truth."""

    points = np.asarray(registered_scan.points)

    details = {}

    for hole_name in ["hole_1", "hole_2"]:
        cfg = config["features"][hole_name]

        result = measure_horizontal_hole(
            points,
            approx_y=cfg["approx_center_y_mm"],
            approx_x=cfg["approx_center_x_mm"]
        )

        details[hole_name] = result

    acceptable = all(
        result["status"] == "MEASURED"
        for result in details.values()
    )

    return acceptable, details


def register_scan_multistart(
    nominal_mesh,
    raw_scan,
    config,
    num_attempts=3
):
    """
    Try registration multiple times and retain
    the best candidate passing basic and feature checks.

    Does not use synthetic ground truth.
    """

    candidates = []
    attempts = []

    minimum_fitness = config["quality"][
        "minimum_registration_fitness"
    ]

    for attempt in range(num_attempts):

        registered_scan, diagnostics = register_scan(
            nominal_mesh,
            raw_scan,
            config
        )

        fitness = diagnostics["final_fitness"]
        rmse = diagnostics["final_rmse_mm"]

        basic_ok = (
            np.isfinite(fitness)
            and np.isfinite(rmse)
            and fitness >= minimum_fitness
            and diagnostics["stable_source_points"] >= 100
        )

        if basic_ok:
            feature_ok, feature_details = validate_hole_features(
                registered_scan,
                config
            )
        else:
            feature_ok = False
            feature_details = {}

        attempt_info = {
            "attempt": attempt + 1,
            "fitness": float(fitness),
            "rmse_mm": float(rmse),
            "basic_acceptable": bool(basic_ok),
            "feature_acceptable": bool(feature_ok)
        }

        attempts.append(attempt_info)

        if basic_ok and feature_ok:
            candidates.append({
                "scan": registered_scan,
                "diagnostics": diagnostics,
                "attempt": attempt + 1
            })

    if not candidates:
        return None, {
            "status": "REVIEW",
            "reason": "No acceptable registration candidate",
            "attempts": attempts
        }

    # Rank accepted candidates by final full-scan RMSE.
    # This is a provisional ranking rule.
    best = min(
        candidates,
        key=lambda c: c["diagnostics"]["final_rmse_mm"]
    )

    return best["scan"], {
        "status": "ACCEPTABLE",
        "selected_attempt": best["attempt"],
        "attempts": attempts,
        "registration": best["diagnostics"]
    }
