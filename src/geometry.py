
from pathlib import Path

import numpy as np
import open3d as o3d


def load_cad(path):
    """Load and validate a nominal CAD triangle mesh."""

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(
            f"CAD file not found: {path}"
        )

    mesh = o3d.io.read_triangle_mesh(str(path))

    if mesh.is_empty() or len(mesh.triangles) == 0:
        raise ValueError("CAD mesh is empty or invalid.")

    vertices = np.asarray(mesh.vertices)

    if not np.all(np.isfinite(vertices)):
        raise ValueError(
            "CAD contains non-finite vertex coordinates."
        )

    mesh.compute_triangle_normals()
    mesh.compute_vertex_normals()

    return mesh


def load_scan(path):
    """Load and validate a 3D point cloud."""

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Scan file not found: {path}"
        )

    scan = o3d.io.read_point_cloud(str(path))

    if scan.is_empty():
        raise ValueError("Scan point cloud is empty.")

    points = np.asarray(scan.points)

    if not np.all(np.isfinite(points)):
        raise ValueError(
            "Scan contains non-finite coordinates."
        )

    return scan


def get_geometry_info(geometry):
    """Return basic geometric information."""

    bbox = geometry.get_axis_aligned_bounding_box()

    info = {
        "dimensions": bbox.get_extent().tolist(),
        "min_bound": bbox.get_min_bound().tolist(),
        "max_bound": bbox.get_max_bound().tolist()
    }

    if isinstance(geometry, o3d.geometry.TriangleMesh):
        info["vertices"] = len(geometry.vertices)
        info["triangles"] = len(geometry.triangles)

    elif isinstance(geometry, o3d.geometry.PointCloud):
        info["points"] = len(geometry.points)

    return info
