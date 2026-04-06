"""
register.py

Aligns all per-frame point clouds into a single coordinate frame using
frame-to-frame ICP, accumulating transformations to bring every frame
into the coordinate system of frame 0.

Output: export/registered/<frame>.ply  (transformed clouds)
        export/registered/transforms.npy  (4x4 matrices, one per frame)

Reads all parameters from config.yaml.
"""

import os
import sys
import yaml
import numpy as np
import open3d as o3d


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def run_icp(
    source: o3d.geometry.PointCloud,
    target: o3d.geometry.PointCloud,
    max_distance: float,
    relative_fitness: float,
    relative_rmse: float,
    max_iterations: int,
    init_transform: np.ndarray = None,
) -> tuple[o3d.pipelines.registration.RegistrationResult, np.ndarray]:
    """Run point-to-plane ICP. Returns (result, 4x4 transform matrix)."""
    if init_transform is None:
        init_transform = np.eye(4)

    # Estimate normals needed for point-to-plane ICP
    source.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.02, max_nn=30)
    )
    target.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.02, max_nn=30)
    )

    result = o3d.pipelines.registration.registration_icp(
        source,
        target,
        max_distance,
        init_transform,
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        o3d.pipelines.registration.ICPConvergenceCriteria(
            relative_fitness=relative_fitness,
            relative_rmse=relative_rmse,
            max_iteration=max_iterations,
        ),
    )
    return result, np.asarray(result.transformation)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    cfg = load_config(config_path)
    reg_cfg = cfg["registration"]

    max_dist       = reg_cfg["icp_max_distance_m"]
    rel_fitness    = reg_cfg["icp_relative_fitness"]
    rel_rmse       = reg_cfg["icp_relative_rmse"]
    max_iterations = reg_cfg["icp_max_iterations"]

    export_dir = input(
        "Path to session export folder (e.g. data\\sessions\\...\\export): "
    ).strip()

    clouds_dir     = os.path.join(export_dir, "pointclouds")
    registered_dir = os.path.join(export_dir, "registered")
    ensure_dir(registered_dir)

    cloud_files = sorted(f for f in os.listdir(clouds_dir) if f.endswith(".ply"))
    if not cloud_files:
        print("No point cloud files found. Run make_pointclouds.py first.")
        sys.exit(1)

    print(f"Found {len(cloud_files)} point clouds.")

    transforms = []         # one 4x4 matrix per frame
    cumulative = np.eye(4)  # accumulated transform to frame-0 space

    prev_cloud = o3d.io.read_point_cloud(os.path.join(clouds_dir, cloud_files[0]))
    # Frame 0 is the reference — identity transform
    transforms.append(cumulative.copy())
    prev_cloud_transformed = prev_cloud  # frame 0 stays in place

    for i, fname in enumerate(cloud_files[1:], start=1):
        cloud_path = os.path.join(clouds_dir, fname)
        curr_cloud = o3d.io.read_point_cloud(cloud_path)

        result, T_curr_to_prev = run_icp(
            source=curr_cloud,
            target=prev_cloud_transformed,
            max_distance=max_dist,
            relative_fitness=rel_fitness,
            relative_rmse=rel_rmse,
            max_iterations=max_iterations,
        )

        # Compose with cumulative transform to get pose in frame-0 space
        cumulative = T_curr_to_prev @ cumulative
        transforms.append(cumulative.copy())

        # Apply cumulative transform and save
        curr_cloud_transformed = curr_cloud.transform(cumulative)
        out_path = os.path.join(registered_dir, fname)
        o3d.io.write_point_cloud(out_path, curr_cloud_transformed)

        prev_cloud_transformed = curr_cloud_transformed

        if i % 20 == 0 or i == len(cloud_files) - 1:
            print(
                f"  Registered {i}/{len(cloud_files) - 1} "
                f"fitness={result.fitness:.4f}  rmse={result.inlier_rmse:.6f}"
            )

    # Save frame 0 (no transform needed, just copy)
    src = o3d.io.read_point_cloud(os.path.join(clouds_dir, cloud_files[0]))
    o3d.io.write_point_cloud(os.path.join(registered_dir, cloud_files[0]), src)

    # Save all transforms
    transforms_path = os.path.join(registered_dir, "transforms.npy")
    np.save(transforms_path, np.stack(transforms, axis=0))

    print(f"\nDone. Registered clouds saved to: {registered_dir}")
    print(f"Transforms saved to: {transforms_path}")


if __name__ == "__main__":
    main()