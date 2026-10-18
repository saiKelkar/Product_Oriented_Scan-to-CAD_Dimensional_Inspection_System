
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from run_pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Automated 3D Scan-to-CAD Inspection"
    )

    parser.add_argument(
        "--cad",
        type=Path,
        required=True,
        help="Path to nominal CAD mesh (STL)"
    )

    parser.add_argument(
        "--scan",
        type=Path,
        required=True,
        help="Path to raw point cloud (PLY)"
    )

    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Inspection configuration JSON"
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory for inspection outputs"
    )

    args = parser.parse_args()

    for name, path in [
        ("CAD", args.cad),
        ("Scan", args.scan),
        ("Configuration", args.config)
    ]:
        if not path.is_file():
            parser.error(f"{name} file not found: {path}")

    print("\nStarting Scan-to-CAD Inspection")
    print("CAD:", args.cad)
    print("Scan:", args.scan)

    report = run_pipeline(
        cad_path=args.cad,
        scan_path=args.scan,
        config_path=args.config,
        output_dir=args.output
    )

    status = report["inspection"]["overall_status"]

    print("\nInspection completed!")
    print("Overall status:", status)

    print(
        "Tolerance checks:",
        len(report["inspection"]["checks"])
    )

    print(
        "JSON report:",
        args.output / "inspection_report.json"
    )

    if status != "REVIEW":
        print(
            "Colored point cloud:",
            args.output / "deviation_cloud.ply"
        )

    # Exit codes:
    # 0 = inspection passed
    # 1 = part failed inspection
    # 2 = inspection requires review
    if status == "PASS":
        return 0
    elif status == "FAIL":
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
