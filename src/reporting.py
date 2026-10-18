
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import open3d as o3d


def save_report(results, diagnostics, measurements, output_path):
    """Save a structured JSON inspection report."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "project": "3D Scan-to-CAD Dimensional Inspection",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "inspection": results,
        "registration": diagnostics,
        "measurements": measurements
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, allow_nan=False)

    return report


def create_deviation_cloud(
    nominal_mesh,
    registered_scan,
    tolerance_mm=0.5,
    max_display_distance_mm=5.0
):
    """
    Color registered scan points by unsigned
    distance to nominal CAD surface.

    Green: within tolerance
    Red: above tolerance
    Gray: large-distance/unclassified points
    """

    cad_tensor = o3d.t.geometry.TriangleMesh.from_legacy(
        nominal_mesh
    )

    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(cad_tensor)

    points = np.asarray(registered_scan.points)

    distances = scene.compute_distance(
        o3d.core.Tensor(points.astype(np.float32))
    ).numpy()

    colors = np.zeros((len(points), 3))

    good = distances <= tolerance_mm

    failing = (
        (distances > tolerance_mm) &
        (distances <= max_display_distance_mm)
    )

    unclassified = distances > max_display_distance_mm

    colors[good] = [0.0, 0.8, 0.2]
    colors[failing] = [0.95, 0.1, 0.1]
    colors[unclassified] = [0.55, 0.55, 0.55]

    colored_cloud = o3d.geometry.PointCloud()

    colored_cloud.points = o3d.utility.Vector3dVector(
        points.copy()
    )

    colored_cloud.colors = o3d.utility.Vector3dVector(
        colors
    )

    summary = {
        "total_points": int(len(points)),
        "within_tolerance_points": int(good.sum()),
        "above_tolerance_points": int(failing.sum()),
        "unclassified_points": int(unclassified.sum()),
        "median_unsigned_distance_mm": float(
            np.median(distances)
        ),
        "p95_unsigned_distance_mm": float(
            np.percentile(distances, 95)
        )
    }

    return colored_cloud, summary


def save_colored_cloud(cloud, output_path):
    """Save an annotated point cloud as PLY."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    success = o3d.io.write_point_cloud(
        str(output_path),
        cloud
    )

    if not success:
        raise IOError(f"Could not save PLY: {output_path}")

    return str(output_path)
