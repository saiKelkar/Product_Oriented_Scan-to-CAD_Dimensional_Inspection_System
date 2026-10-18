
import json
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.slow
def test_cli_inspection(tmp_path):

    output_dir = tmp_path / "cli_inspection"

    command = [
        sys.executable,
        str(PROJECT_ROOT / "main.py"),
        "--cad",
        str(PROJECT_ROOT / "data/nominal/bracket.stl"),
        "--scan",
        str(PROJECT_ROOT / "data/synthetic/raw_scan.ply"),
        "--config",
        str(PROJECT_ROOT / "configs/inspection_config.json"),
        "--output",
        str(output_dir)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180
    )

    assert result.returncode in {0, 1, 2}, (
        result.stdout + "\n" + result.stderr
    )

    report_path = output_dir / "inspection_report.json"

    assert report_path.exists()

    with open(report_path, "r") as f:
        report = json.load(f)

    status = report["inspection"]["overall_status"]

    expected_codes = {
        "PASS": 0,
        "FAIL": 1,
        "REVIEW": 2
    }

    assert result.returncode == expected_codes[status]

    assert "registration" in report

    if status != "REVIEW":
        assert len(report["inspection"]["checks"]) == 7
        assert "defect_detection" in report
        assert (output_dir / "deviation_cloud.ply").exists()
