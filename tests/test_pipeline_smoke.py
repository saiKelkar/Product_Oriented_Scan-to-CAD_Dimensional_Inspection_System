
from pathlib import Path
import json
import sys

import pytest
import open3d as o3d

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from run_pipeline import run_pipeline


@pytest.mark.slow
def test_end_to_end_pipeline(tmp_path):

    cad_path = PROJECT_ROOT / "data/nominal/bracket.stl"
    scan_path = PROJECT_ROOT / "data/synthetic/raw_scan.ply"
    config_path = PROJECT_ROOT / "configs/inspection_config.json"

    output_dir = tmp_path / "inspection"

    report = run_pipeline(
        cad_path=cad_path,
        scan_path=scan_path,
        config_path=config_path,
        output_dir=output_dir
    )

    report_path = output_dir / "inspection_report.json"
    ply_path = output_dir / "deviation_cloud.ply"

    # Every completed attempt must produce a JSON report
    assert report_path.exists()

    with open(report_path, "r") as f:
        saved_report = json.load(f)

    assert saved_report["inspection"]["overall_status"] in {
        "PASS", "FAIL", "REVIEW"
    }

    assert "registration" in saved_report

    if saved_report["inspection"]["overall_status"] == "REVIEW":
        # Registration may be rejected conservatively
        assert saved_report["inspection"]["checks"] == []
        return

    # Successful inspection must produce all outputs
    assert len(saved_report["inspection"]["checks"]) == 7

    assert "defect_detection" in saved_report
    assert "deviation_summary" in saved_report

    assert ply_path.exists()

    cloud = o3d.io.read_point_cloud(str(ply_path))

    assert len(cloud.points) > 0
    assert cloud.has_colors()
