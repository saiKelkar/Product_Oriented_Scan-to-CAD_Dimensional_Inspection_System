
from pathlib import Path
import sys
import math
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from inspection import evaluate_tolerance


def test_pass_within_tolerance():
    assert evaluate_tolerance(0.10, 0.25) == "PASS"


def test_fail_outside_tolerance():
    assert evaluate_tolerance(0.40, 0.25) == "FAIL"


def test_negative_error():
    assert evaluate_tolerance(-0.40, 0.25) == "FAIL"


def test_exact_tolerance_boundary():
    assert evaluate_tolerance(0.25, 0.25) == "PASS"


def test_missing_measurement():
    assert evaluate_tolerance(None, 0.25) == "REVIEW"


def test_invalid_measurement():
    assert evaluate_tolerance(math.nan, 0.25) == "REVIEW"


def test_negative_tolerance():
    assert evaluate_tolerance(0.10, -0.25) == "REVIEW"


def test_uncertainty_safe_pass():
    assert evaluate_tolerance(
        error=0.10,
        tolerance=0.25,
        uncertainty=0.05
    ) == "PASS"


def test_uncertainty_clear_fail():
    assert evaluate_tolerance(
        error=0.40,
        tolerance=0.25,
        uncertainty=0.05
    ) == "FAIL"


def test_uncertainty_boundary_review():
    assert evaluate_tolerance(
        error=0.23,
        tolerance=0.25,
        uncertainty=0.05
    ) == "REVIEW"


def test_invalid_uncertainty():
    assert evaluate_tolerance(
        error=0.10,
        tolerance=0.25,
        uncertainty=-0.05
    ) == "REVIEW"
