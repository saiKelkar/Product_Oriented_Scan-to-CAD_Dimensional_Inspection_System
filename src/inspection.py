
import math


def evaluate_tolerance(error, tolerance, uncertainty=None):
    """
    Evaluate a symmetric tolerance.

    uncertainty=None means no validated uncertainty
    was supplied, so only a provisional decision
    can be made.
    """

    if error is None or not math.isfinite(error):
        return "REVIEW"

    if tolerance is None or tolerance < 0:
        return "REVIEW"

    if uncertainty is None:
        return "PASS" if abs(error) <= tolerance else "FAIL"

    if not math.isfinite(uncertainty) or uncertainty < 0:
        return "REVIEW"

    if abs(error) + uncertainty <= tolerance:
        return "PASS"

    if abs(error) - uncertainty > tolerance:
        return "FAIL"

    return "REVIEW"


def evaluate_inspection(measurements, config, registration_status):
    """
    Convert feature measurements into tolerance decisions.

    Returns an inspection report dictionary.
    """

    # Never inspect features if registration is unreliable.
    if registration_status != "ACCEPTABLE":
        return {
            "overall_status": "REVIEW",
            "reason": "Registration quality insufficient",
            "checks": []
        }

    tolerances = config["tolerances"]
    checks = []

    def add_check(name, error, tolerance, unit, quality="MEASURED"):
        if quality != "MEASURED":
            status = "REVIEW"
        else:
            status = evaluate_tolerance(error, tolerance)

        checks.append({
            "feature": name,
            "error": float(error) if error is not None else None,
            "tolerance": float(tolerance),
            "unit": unit,
            "status": status
        })

    # Hole diameter and center position
    for hole_name in ["hole_1", "hole_2"]:
        hole = measurements["holes"][hole_name]

        quality = (
            "MEASURED"
            if hole["nominal"]["status"] == "MEASURED"
            and hole["measured"]["status"] == "MEASURED"
            else "REVIEW"
        )

        add_check(
            f"{hole_name} diameter",
            hole.get("diameter_error_mm"),
            tolerances["hole_diameter_mm"],
            "mm",
            quality
        )

        add_check(
            f"{hole_name} center offset",
            hole.get("center_offset_2d_mm"),
            tolerances["hole_position_mm"],
            "mm",
            quality
        )

    # Hole spacing
    spacing = measurements["hole_spacing"]

    add_check(
        "Hole center spacing",
        spacing.get("error_mm"),
        tolerances["hole_spacing_mm"],
        "mm",
        spacing["status"]
    )

    # Flange
    flange = measurements["horizontal_flange"]

    add_check(
        "Flange nominal-plane deviation P95",
        flange.get("nominal_plane_deviation_p95_mm"),
        tolerances["flange_plane_deviation_mm"],
        "mm",
        flange["status"]
    )

    add_check(
        "Flange angular deviation",
        flange.get("angular_deviation_deg"),
        tolerances["flange_angle_deg"],
        "degrees",
        flange["status"]
    )

    statuses = [item["status"] for item in checks]

    if "FAIL" in statuses:
        overall = "FAIL"
    elif "REVIEW" in statuses:
        overall = "REVIEW"
    else:
        overall = "PASS"

    return {
        "overall_status": overall,
        "decision_basis": "provisional_demo_tolerances",
        "checks": checks,
        "summary": {
            "passed": statuses.count("PASS"),
            "failed": statuses.count("FAIL"),
            "review": statuses.count("REVIEW")
        }
    }
