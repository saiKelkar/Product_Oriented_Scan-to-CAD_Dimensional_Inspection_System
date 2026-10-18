
from pathlib import Path
import sys
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from run_pipeline import check_registration


CONFIG = {
    "quality": {
        "minimum_registration_fitness": 0.80
    }
}


def valid_diagnostics():
    return {
        "final_fitness": 0.98,
        "final_rmse_mm": 0.30,
        "stable_source_points": 5000,
        "transformation": np.eye(4).tolist()
    }


def test_good_registration():
    result = check_registration(
        valid_diagnostics(),
        CONFIG
    )

    assert result == "ACCEPTABLE"


def test_low_fitness():
    diagnostics = valid_diagnostics()
    diagnostics["final_fitness"] = 0.30

    assert check_registration(
        diagnostics, CONFIG
    ) == "REVIEW"


def test_invalid_rmse():
    diagnostics = valid_diagnostics()
    diagnostics["final_rmse_mm"] = np.nan

    assert check_registration(
        diagnostics, CONFIG
    ) == "REVIEW"


def test_insufficient_stable_points():
    diagnostics = valid_diagnostics()
    diagnostics["stable_source_points"] = 10

    assert check_registration(
        diagnostics, CONFIG
    ) == "REVIEW"


def test_missing_transformation():
    diagnostics = valid_diagnostics()
    diagnostics["transformation"] = None

    assert check_registration(
        diagnostics, CONFIG
    ) == "REVIEW"
