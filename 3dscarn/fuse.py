"""
fuse.py

Integrates all registered, coloured point clouds into a TSDF volume
using Open3D's ScalableTSDFVolume.

Output: export/tsdf/tsdf.npz  (internal volume — passed to extract_mesh.py)
        The volume object is saved by extracting it as a mesh immediately
        after fusion and writing export/tsdf/fused_mesh.ply as an intermediate.

Reads all parameters from config.yaml.
"""

import os
import sys
import json
import yaml
import numpy as np
import open3d as o3d


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_intrinsics(meta_dir: str) -> o3d.camera.PinholeCameraIntrinsic:
    path = os.path.join(meta_dir, "intrinsics.json")
    if not os.path.isfile(path):
        print(f"intrinsics.json not found at {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return o3d.camera.PinholeCameraIntrinsic(
        width=data["width"],
        height=data["height"],
        fx=data["fx"],
        fy=data["fy"],
        cx=data["ppx"],
        cy=data["ppy"],
    )


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    cfg = load_config(config_path)
    fuse_cfg = cfg["fusion"]

    voxel_size  = fuse_cfg["tsdf_voxel_size_m"]
    trunc_dist  = fuse_cfg["tsdf_truncation_m"]

    export_dir = input(
        "Path to session export folder (e.g. data\\sessions\\...\\export): "
    ).strip()

    registered_dir = os.path.join(export_dir, "registered")
    masked_dir     = os.path.join(export_dir, "depth_masked")
    color_dir      = os.path.join(export_dir, "color")
    meta_dir       = os.path.join(export_dir, "meta")
    tsdf_dir       = os.path.join(export_dir, "tsdf")
    ensure_dir(tsdf_dir)

    transforms_path = os.path.join(registered_dir, "transforms.npy")
    if not os.path.isfile(transforms_path):
        print(f"transforms.npy not found at {transforms_path}. Run register.py first.")
        sys.exit(1)

    transforms = np.load(transforms_path)  # shape (N, 4, 4)
    intr = load_intrinsics(meta_dir)

    # Collect matched depth + colour files
    depth_files = sorted(f for f in os.listdir(masked_dir) if f.endswith(".npy"))
    if not depth_files:
        print("No masked depth frames found.")
        sys.exit(1)

    if len(depth_files) != len(transforms):
        print(
            f"[WARN] {len(depth_files)} depth frames but {len(transforms)} transforms. "
            "Using min of both."
        )

    n_frames = min(len(depth_files), len(transforms))
    print(f"Fusing {n_frames} frames into TSDF volume  "
          f"(voxel={voxel_size}m  trunc={trunc_dist}m)")

    volume = o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=voxel_size,
        sdf_trunc=trunc_dist,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8,
    )

    fused = 0
    for i in range(n_frames):
        stem = os.path.splitext(depth_files[i])[0]
        depth_path = os.path.join(masked_dir, depth_files[i])
        color_path = os.path.join(color_dir, stem + ".png")

        if not os.path.isfile(color_path):
            print(f"[WARN] frame {stem}: colour missing — skipping.")
            continue

        depth_np = np.load(depth_path).astype(np.float32)
        color_bgr = o3d.io.read_image(color_path)

        # Open3D expects depth in metres as float32
        depth_o3d = o3d.geometry.Image((depth_np / 1000.0).astype(np.float32))

        # Convert BGR colour image to RGB
        import cv2
        color_rgb = cv2.cvtColor(np.asarray(color_bgr), cv2.COLOR_BGR2RGB)
        color_o3d = o3d.geometry.Image(color_rgb)

        rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
            color_o3d,
            depth_o3d,
            depth_scale=1.0,        # already in metres
            depth_trunc=2.0,        # discard beyond 2 m
            convert_rgb_to_intensity=False,
        )

        # Extrinsic = inverse of the cumulative transform (camera pose in world)
        extrinsic = np.linalg.inv(transforms[i])

        volume.integrate(rgbd, intr, extrinsic)
        fused += 1

        if fused % 50 == 0 or fused == n_frames:
            print(f"  Integrated {fused}/{n_frames}")

    print("\nExtracting mesh from TSDF volume...")
    mesh = volume.extract_triangle_mesh()
    mesh.compute_vertex_normals()

    out_path = os.path.join(tsdf_dir, "fused_mesh.ply")
    o3d.io.write_triangle_mesh(out_path, mesh)
    print(f"Fused mesh saved to: {out_path}")
    print(f"  Vertices: {len(mesh.vertices)}  Triangles: {len(mesh.triangles)}")


if __name__ == "__main__":
    main()