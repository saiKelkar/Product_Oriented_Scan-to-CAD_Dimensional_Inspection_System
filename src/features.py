
import numpy as np
from scipy.optimize import least_squares


def measure_horizontal_hole(
    points,
    approx_y,
    approx_x,
    search_radius=3.5,
    z_min=1.2,
    z_max=3.2,
    nominal_radius=2.5,
    min_points=50,
    max_rmse=0.20,
    min_coverage_percent=70.0,
    num_sectors=36
):
    """
    Guided cylindrical-hole measurement.

    Checks point count, fitting quality,
    angular coverage, and parameter bounds.
    """

    import numpy as np
    from scipy.optimize import least_squares

    points = np.asarray(points, dtype=float)

    radial = np.sqrt(
        (points[:, 1] - approx_y)**2 +
        (points[:, 0] - approx_x)**2
    )

    mask = (
        (radial < search_radius) &
        (points[:, 2] > z_min) &
        (points[:, 2] < z_max)
    )

    wall_points = points[mask]
    n = len(wall_points)

    if n < min_points:
        return {
            "status": "REVIEW",
            "reason": "Insufficient candidate wall points",
            "num_points": int(n)
        }

    xy = wall_points[:, [1, 0]]

    def residuals(params):
        cy, cx, radius = params

        return np.sqrt(
            (xy[:, 0] - cy)**2 +
            (xy[:, 1] - cx)**2
        ) - radius

    lower = np.array([
        approx_y - 1.0,
        approx_x - 1.0,
        2.0
    ])

    upper = np.array([
        approx_y + 1.0,
        approx_x + 1.0,
        3.0
    ])

    fit = least_squares(
        residuals,
        x0=[approx_y, approx_x, nominal_radius],
        bounds=(lower, upper)
    )

    cy, cx, radius = fit.x

    rmse = float(np.sqrt(np.mean(fit.fun**2)))

    # Angular coverage around fitted center
    angles = np.mod(
        np.arctan2(
            xy[:, 1] - cx,
            xy[:, 0] - cy
        ),
        2 * np.pi
    )

    sectors = np.floor(
        angles / (2 * np.pi) * num_sectors
    ).astype(int) % num_sectors

    occupied = np.zeros(num_sectors, dtype=bool)
    occupied[sectors] = True

    occupied_count = int(occupied.sum())

    coverage_percent = (
        100.0 * occupied_count / num_sectors
    )

    # Largest consecutive sequence of empty sectors,
    # including across the 0/360-degree boundary
    if occupied_count == 0:
        largest_gap_sectors = num_sectors
    elif occupied_count == num_sectors:
        largest_gap_sectors = 0
    else:
        doubled = np.concatenate([
            occupied, occupied
        ])

        current_gap = 0
        largest_gap_sectors = 0

        for observed in doubled:
            if not observed:
                current_gap += 1
                largest_gap_sectors = max(
                    largest_gap_sectors,
                    current_gap
                )
            else:
                current_gap = 0

        largest_gap_sectors = min(
            largest_gap_sectors,
            num_sectors
        )

    largest_gap_deg = (
        360.0 * largest_gap_sectors / num_sectors
    )

    result = {
        "status": "MEASURED",
        "center_y_mm": float(cy),
        "center_x_mm": float(cx),
        "diameter_mm": float(2 * radius),
        "fit_rmse_mm": rmse,
        "num_points": int(n),
        "angular_coverage_percent": float(
            coverage_percent
        ),
        "occupied_sectors": occupied_count,
        "total_sectors": int(num_sectors),
        "largest_empty_sector_gap_deg": float(
            largest_gap_deg
        )
    }

    if not fit.success or not np.isfinite(rmse):
        result["status"] = "REVIEW"
        result["reason"] = "Circle fitting failed"

    elif np.any(fit.x - lower < 0.01) or np.any(
        upper - fit.x < 0.01
    ):
        result["status"] = "REVIEW"
        result["reason"] = "Circle fit reached parameter bounds"

    elif rmse > max_rmse:
        result["status"] = "REVIEW"
        result["reason"] = "Poor circle-fitting quality"

    elif coverage_percent < min_coverage_percent:
        result["status"] = "REVIEW"
        result["reason"] = "Insufficient angular coverage"

    return result



def fit_plane_svd(points):
    """
    Fit a least-squares plane using SVD.
    Returns centroid, unit normal, and signed residuals.
    """

    points = np.asarray(points, dtype=float)

    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("Expected an Nx3 point array.")

    if len(points) < 3:
        raise ValueError("At least 3 points are required.")

    centroid = points.mean(axis=0)
    centered = points - centroid

    _, singular_values, vh = np.linalg.svd(
        centered,
        full_matrices=False
    )

    if singular_values[1] < 1e-8:
        raise ValueError("Points do not define a unique plane.")

    normal = vh[-1]
    normal = normal / np.linalg.norm(normal)

    if normal[2] < 0:
        normal = -normal

    residuals = centered @ normal

    return centroid, normal, residuals


def measure_flange(
    nominal_points,
    scan_points,
    top_z=4.5
):
    """
    Guided horizontal-flange measurement.

    Returns REVIEW if insufficient geometry is available.
    """

    nominal_points = np.asarray(nominal_points)
    scan_points = np.asarray(scan_points)

    # Extract nominal top surface
    nominal_mask = (
        (nominal_points[:, 1] > 8.0) &
        (np.abs(nominal_points[:, 2] - top_z) < 0.05)
    )

    nominal_top = nominal_points[nominal_mask]

    if len(nominal_top) < 100:
        return {
            "status": "REVIEW",
            "reason": "Insufficient nominal top-surface points"
        }

    nominal_centroid, nominal_normal, _ = fit_plane_svd(
        nominal_top
    )

    # Estimate scan normals for guided segmentation
    import open3d as o3d

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(scan_points)

    cloud.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(
            radius=2.0,
            max_nn=40
        )
    )

    normals = np.asarray(cloud.normals)
    normal_z = np.abs(normals[:, 2])

    # Guided top-flange region
    scan_mask = (
        (scan_points[:, 0] > -1.5) &
        (scan_points[:, 0] < 14.5) &
        (scan_points[:, 1] > 8.0) &
        (scan_points[:, 1] < 49.0) &
        (scan_points[:, 2] > 3.5) &
        (scan_points[:, 2] < 9.0) &
        (normal_z > 0.90)
    )

    scan_top = scan_points[scan_mask]

    if len(scan_top) < 100:
        return {
            "status": "REVIEW",
            "reason": "Insufficient scanned flange points",
            "num_points": int(len(scan_top))
        }

    # Deviations from nominal plane
    deviations = (
        scan_top - nominal_centroid
    ) @ nominal_normal

    # Best-fit manufactured plane
    scan_centroid, scan_normal, residuals = fit_plane_svd(
        scan_top
    )

    angle = np.degrees(
        np.arccos(
            np.clip(
                np.dot(nominal_normal, scan_normal),
                -1.0,
                1.0
            )
        )
    )

    return {
        "status": "MEASURED",
        "num_points": int(len(scan_top)),
        "nominal_plane_deviation_p95_mm": float(
            np.percentile(np.abs(deviations), 95)
        ),
        "nominal_plane_deviation_max_mm": float(
            np.max(np.abs(deviations))
        ),
        "plane_fit_rmse_mm": float(
            np.sqrt(np.mean(residuals**2))
        ),
        "plane_residual_range_mm": float(
            np.ptp(residuals)
        ),
        "angular_deviation_deg": float(angle),
        "nominal_normal": nominal_normal.tolist(),
        "measured_normal": scan_normal.tolist()
    }


def measure_features(nominal_mesh, registered_scan, config):
    """
    Run all configured feature measurements.

    Returns structured measurements.
    """

    import numpy as np

    nominal_sample = nominal_mesh.sample_points_poisson_disk(
        number_of_points=30000
    )

    nominal_points = np.asarray(nominal_sample.points)
    scan_points = np.asarray(registered_scan.points)

    results = {
        "holes": {},
        "hole_spacing": {},
        "horizontal_flange": {}
    }

    for hole_name in ["hole_1", "hole_2"]:

        hole_cfg = config["features"][hole_name]

        approx_y = hole_cfg["approx_center_y_mm"]
        approx_x = hole_cfg["approx_center_x_mm"]

        nominal_result = measure_horizontal_hole(
            nominal_points,
            approx_y,
            approx_x
        )

        measured_result = measure_horizontal_hole(
            scan_points,
            approx_y,
            approx_x
        )

        feature_result = {
            "nominal": nominal_result,
            "measured": measured_result
        }

        if (
            nominal_result["status"] == "MEASURED"
            and measured_result["status"] == "MEASURED"
        ):
            feature_result["diameter_error_mm"] = (
                measured_result["diameter_mm"]
                - nominal_result["diameter_mm"]
            )

            dy = (
                measured_result["center_y_mm"]
                - nominal_result["center_y_mm"]
            )

            dx = (
                measured_result["center_x_mm"]
                - nominal_result["center_x_mm"]
            )

            feature_result["center_offset_2d_mm"] = float(
                np.sqrt(dx**2 + dy**2)
            )

        results["holes"][hole_name] = feature_result

    # Calculate spacing only if both holes were measured
    h1 = results["holes"]["hole_1"]
    h2 = results["holes"]["hole_2"]

    if all(
        h["nominal"]["status"] == "MEASURED"
        and h["measured"]["status"] == "MEASURED"
        for h in [h1, h2]
    ):
        def spacing(a, b):
            return float(np.hypot(
                a["center_y_mm"] - b["center_y_mm"],
                a["center_x_mm"] - b["center_x_mm"]
            ))

        nominal_spacing = spacing(
            h1["nominal"],
            h2["nominal"]
        )

        measured_spacing = spacing(
            h1["measured"],
            h2["measured"]
        )

        results["hole_spacing"] = {
            "status": "MEASURED",
            "nominal_mm": nominal_spacing,
            "measured_mm": measured_spacing,
            "error_mm": measured_spacing - nominal_spacing
        }

    else:
        results["hole_spacing"] = {
            "status": "REVIEW",
            "reason": "One or more holes could not be measured"
        }

    # Measure flange
    results["horizontal_flange"] = measure_flange(
        nominal_points,
        scan_points,
        top_z=4.5
    )

    return results


def calculate_hole_angular_coverage(
    points,
    center_y,
    center_x,
    num_sectors=36
):
    """
    Calculate angular coverage around a hole center.

    Assumes points belong to the cylindrical wall.
    Returns the fraction of occupied angular sectors.
    """

    import numpy as np

    points = np.asarray(points, dtype=float)

    if len(points) == 0:
        return {
            "coverage_percent": 0.0,
            "occupied_sectors": 0,
            "total_sectors": num_sectors
        }

    angles = np.arctan2(
        points[:, 0] - center_y,
        points[:, 1] - center_x
    )

    angles = np.mod(angles, 2 * np.pi)

    sector_indices = np.floor(
        angles / (2 * np.pi) * num_sectors
    ).astype(int)

    sector_indices = np.clip(
        sector_indices, 0, num_sectors - 1
    )

    occupied = len(np.unique(sector_indices))

    return {
        "coverage_percent": float(
            100 * occupied / num_sectors
        ),
        "occupied_sectors": int(occupied),
        "total_sectors": int(num_sectors)
    }
