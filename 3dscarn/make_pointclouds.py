"""
make_pointclouds.py

For each masked depth frame:
  1. Load masked depth + colour frame
  2. Unproject non-zero pixels to 3D using camera intrinsics
  3. Attach RGB colour to each point
  4. Downsample (voxel grid) to reduce size before ICP
  5. Save coloured point cloud to export/pointclouds/<frame>.ply

Reads all parameters from config.yaml.
"""

import os
import sys
import json
import yaml
import numpy as np
import cv2
import open3d as o3d


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def load_intrinsics(meta_dir: str) -> dict:
    path = os.path.join(meta_dir, "intrinsics.json")
    if not os.path.isfile(path):
        print(f"intrinsics.json not found at {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def depth_to_pointcloud(
    depth: np.ndarray,
    color_bgr: np.ndarray,
    fx: float, fy: float,
    ppx: float, ppy: float,
    min_depth_mm: int,
    max_depth_mm: int,
) -> o3d.geometry.PointCloud:
    """Unproject non-zero masked depth pixels to XYZ and attach RGB colours."""
    h, w = depth.shape

    # Pixel coordinate grids
    us = np.arange(w)
    vs = np.arange(h)
    uu, vv = np.meshgrid(us, vs)

    # Valid pixels: non-zero and within depth range
    valid = (depth > min_depth_mm) & (depth < max_depth_mm)
    Z = depth[valid].astype(np.float64) / 1000.0  # mm → m

    X = (uu[valid] - ppx) * Z / fx
    Y = (vv[valid] - ppy) * Z / fy

    points = np.stack([X, Y, Z], axis=1)

    # Colours: BGR → RGB, normalised to [0, 1]
    color_rgb = cv2.cvtColor(color_bgr, cv2.COLOR_BGR2RGB)
    colors = color_rgb[valid].astype(np.float64) / 255.0

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.colors = o3d.utility.Vector3dVector(colors)
    return pcd


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    cfg = load_config(config_path)
    pc_cfg = cfg["pointcloud"]

    export_dir = input(
        "Path to session export folder (e.g. data\\sessions\\...\\export): "
    ).strip()

    masked_dir  = os.path.join(export_dir, "depth_masked")
    color_dir   = os.path.join(export_dir, "color")
    meta_dir    = os.path.join(export_dir, "meta")
    clouds_dir  = os.path.join(export_dir, "pointclouds")
    ensure_dir(clouds_dir)

    intr = load_intrinsics(meta_dir)
    fx, fy   = intr["fx"], intr["fy"]
    ppx, ppy = intr["ppx"], intr["ppy"]

    min_depth_mm    = pc_cfg["min_depth_mm"]
    max_depth_mm    = pc_cfg["max_depth_mm"]
    downsample_voxel = pc_cfg["downsample_voxel_m"]

    depth_files = sorted(f for f in os.listdir(masked_dir) if f.endswith(".npy"))
    if not depth_files:
        print("No masked depth frames found. Run preprocess.py first.")
        sys.exit(1)

    print(f"Found {len(depth_files)} masked depth frames.")

    processed = 0
    skipped = 0
    for fname in depth_files:
        stem = os.path.splitext(fname)[0]
        depth_path = os.path.join(masked_dir, fname)
        color_path = os.path.join(color_dir, stem + ".png")

        depth = np.load(depth_path)

        if not os.path.isfile(color_path):
            print(f"[WARN] {stem}: colour image missing — skipping.")
            skipped += 1
            continue

        color_bgr = cv2.imread(color_path)

        pcd = depth_to_pointcloud(
            depth, color_bgr,
            fx, fy, ppx, ppy,
            min_depth_mm, max_depth_mm,
        )

        if len(pcd.points) == 0:
            skipped += 1
            continue

        # Voxel downsample
        pcd = pcd.voxel_down_sample(voxel_size=downsample_voxel)

        out_path = os.path.join(clouds_dir, stem + ".ply")
        o3d.io.write_point_cloud(out_path, pcd)
        processed += 1

        if processed % 50 == 0 or processed == len(depth_files):
            print(f"  Saved {processed}/{len(depth_files)}  ({len(pcd.points)} pts)")

    print(f"\nDone. {processed} point clouds saved to: {clouds_dir}  ({skipped} skipped)")


if __name__ == "__main__":
    main()