
import numpy as np
import open3d as o3d


def cluster_flange_defects(
    nominal_mesh,
    registered_scan,
    config
):
    """
    Identify candidate excessive deviations on the
    horizontal flange using DBSCAN.

    Returns cluster summaries and diagnostics.
    """

    points = np.asarray(registered_scan.points)

    if len(points) == 0:
        return {
            "status": "REVIEW",
            "reason": "Empty registered scan",
            "clusters": []
        }

    # Estimate normals
    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)

    cloud.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(
            radius=2.0,
            max_nn=40
        )
    )

    normals = np.asarray(cloud.normals)
    normal_z = np.abs(normals[:, 2])

    # Guided horizontal top-flange segmentation
    mask = (
        (points[:, 0] > -1.5) &
        (points[:, 0] < 14.5) &
        (points[:, 1] > 8.0) &
        (points[:, 1] < 49.0) &
        (points[:, 2] > 3.5) &
        (points[:, 2] < 9.0) &
        (normal_z > 0.90)
    )

    flange_points = points[mask]

    if len(flange_points) < 100:
        return {
            "status": "REVIEW",
            "reason": "Insufficient flange surface points",
            "clusters": []
        }

    # Reference plane from nominal top surface
    nominal_points = np.asarray(
        nominal_mesh.sample_points_poisson_disk(
            number_of_points=30000
        ).points
    )

    nominal_mask = (
        (nominal_points[:, 1] > 8.0) &
        (np.abs(nominal_points[:, 2] - 4.5) < 0.05)
    )

    nominal_top = nominal_points[nominal_mask]

    if len(nominal_top) < 100:
        return {
            "status": "REVIEW",
            "reason": "Insufficient nominal reference points",
            "clusters": []
        }

    # SVD reference plane
    centroid = nominal_top.mean(axis=0)
    centered = nominal_top - centroid

    _, _, vh = np.linalg.svd(
        centered,
        full_matrices=False
    )

    normal = vh[-1]

    if normal[2] < 0:
        normal = -normal

    normal /= np.linalg.norm(normal)

    # Signed deviation from nominal plane
    deviations = (flange_points - centroid) @ normal

    tolerance = config["tolerances"][
        "flange_plane_deviation_mm"
    ]

    failure_mask = np.abs(deviations) > tolerance

    failure_points = flange_points[failure_mask]
    failure_deviations = deviations[failure_mask]

    if len(failure_points) == 0:
        return {
            "status": "NO_CANDIDATES",
            "inspected_points": int(len(flange_points)),
            "candidate_points": 0,
            "clusters": []
        }

    # DBSCAN
    failure_cloud = o3d.geometry.PointCloud()
    failure_cloud.points = o3d.utility.Vector3dVector(
        failure_points
    )

    clustering_cfg = config["defect_clustering"]

    labels = np.asarray(
        failure_cloud.cluster_dbscan(
            eps=clustering_cfg["eps_mm"],
            min_points=clustering_cfg["min_points"],
            print_progress=False
        )
    )

    clusters = []

    for cluster_id in sorted(set(labels)):
        if cluster_id == -1:
            continue

        cluster_mask = labels == cluster_id

        cluster_pts = failure_points[cluster_mask]
        cluster_dev = failure_deviations[cluster_mask]

        center = cluster_pts.mean(axis=0)

        clusters.append({
            "cluster_id": int(cluster_id),
            "feature": "horizontal_flange",
            "num_points": int(len(cluster_pts)),
            "center_xyz_mm": center.tolist(),
            "maximum_absolute_deviation_mm": float(
                np.max(np.abs(cluster_dev))
            ),
            "mean_absolute_deviation_mm": float(
                np.mean(np.abs(cluster_dev))
            ),
            "status": "CANDIDATE_DEFECT"
        })

    return {
        "status": "COMPLETED",
        "inspected_points": int(len(flange_points)),
        "candidate_points": int(len(failure_points)),
        "unclustered_points": int(np.sum(labels == -1)),
        "num_clusters": len(clusters),
        "clusters": clusters
    }
