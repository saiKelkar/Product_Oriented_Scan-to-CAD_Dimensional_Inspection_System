
import copy
import numpy as np
import open3d as o3d


def register_scan(nominal_mesh, raw_scan, config):
    """
    Align raw scan to nominal CAD.

    Returns:
        registered_scan
        diagnostics
    """

    cfg = config["registration"]
    voxel = cfg["voxel_size_mm"]

    # 1. Reference point cloud
    target = nominal_mesh.sample_points_poisson_disk(
        number_of_points=10000
    )

    source = copy.deepcopy(raw_scan)

    # 2. Downsample
    source_down = source.voxel_down_sample(voxel)
    target_down = target.voxel_down_sample(voxel)

    # 3. Estimate normals
    normal_radius = voxel * cfg["normal_radius_multiplier"]

    for cloud in [source_down, target_down]:
        cloud.estimate_normals(
            o3d.geometry.KDTreeSearchParamHybrid(
                radius=normal_radius,
                max_nn=30
            )
        )

    # 4. Compute FPFH
    feature_radius = voxel * cfg["fpfh_radius_multiplier"]

    def compute_fpfh(cloud):
        return o3d.pipelines.registration.compute_fpfh_feature(
            cloud,
            o3d.geometry.KDTreeSearchParamHybrid(
                radius=feature_radius,
                max_nn=100
            )
        )

    source_fpfh = compute_fpfh(source_down)
    target_fpfh = compute_fpfh(target_down)

    # 5. RANSAC coarse registration
    distance = voxel * cfg["ransac_distance_multiplier"]

    ransac = (
        o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
            source_down,
            target_down,
            source_fpfh,
            target_fpfh,
            mutual_filter=True,
            max_correspondence_distance=distance,
            estimation_method=(
                o3d.pipelines.registration.TransformationEstimationPointToPoint(
                    False
                )
            ),
            ransac_n=3,
            checkers=[
                o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(
                    0.9
                ),
                o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(
                    distance
                )
            ],
            criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(
                100000, 0.999
            )
        )
    )

    # 6. Full ICP
    full_icp = o3d.pipelines.registration.registration_icp(
        source,
        target,
        cfg["icp_distance_mm"],
        ransac.transformation,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        o3d.pipelines.registration.ICPConvergenceCriteria(
            max_iteration=100
        )
    )

    # 7. Transform a temporary source for stable-region selection
    source_coarse = copy.deepcopy(source)
    source_coarse.transform(full_icp.transformation)

    source_points = np.asarray(source_coarse.points)
    target_points = np.asarray(target.points)

    y_max = cfg["stable_region_y_max_mm"]

    source_indices = np.where(source_points[:, 1] < y_max)[0]
    target_indices = np.where(target_points[:, 1] < y_max)[0]

    source_stable = source_coarse.select_by_index(
        source_indices.tolist()
    )

    target_stable = target.select_by_index(
        target_indices.tolist()
    )

    # 8. Stable-region ICP
    stable_icp = o3d.pipelines.registration.registration_icp(
        source_stable,
        target_stable,
        cfg["icp_distance_mm"],
        np.eye(4),
        o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        o3d.pipelines.registration.ICPConvergenceCriteria(
            max_iteration=100
        )
    )

    # Compose transformations
    final_transform = (
        stable_icp.transformation @ full_icp.transformation
    )

    # 9. Apply to original scan
    registered_scan = copy.deepcopy(raw_scan)
    registered_scan.transform(final_transform)

    # 10. Evaluate final alignment against the same reference
    final_eval = o3d.pipelines.registration.evaluate_registration(
        raw_scan,
        target,
        cfg["icp_distance_mm"],
        final_transform
    )

    diagnostics = {
        "ransac_fitness": float(ransac.fitness),
        "ransac_rmse_mm": float(ransac.inlier_rmse),
        "full_icp_fitness": float(full_icp.fitness),
        "full_icp_rmse_mm": float(full_icp.inlier_rmse),
        "stable_icp_fitness": float(stable_icp.fitness),
        "stable_icp_rmse_mm": float(stable_icp.inlier_rmse),
        "final_fitness": float(final_eval.fitness),
        "final_rmse_mm": float(final_eval.inlier_rmse),
        "stable_source_points": int(len(source_stable.points)),
        "stable_target_points": int(len(target_stable.points)),
        "transformation": final_transform.tolist()
    }

    return registered_scan, diagnostics
