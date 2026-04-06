"""
extract_mesh.py

Post-processes the fused mesh from fuse.py:
  1. Removes disconnected fragments (keeps only the largest cluster)
  2. Removes statistical outlier vertices
  3. Smooths the mesh (Laplacian)
  4. Saves the final mesh to output/mesh.ply

Reads output path from config.yaml.
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


def keep_largest_cluster(mesh: o3d.geometry.TriangleMesh) -> o3d.geometry.TriangleMesh:
    """Remove all triangle clusters except the largest one."""
    triangle_clusters, cluster_n_triangles, _ = mesh.cluster_connected_triangles()
    triangle_clusters = np.asarray(triangle_clusters)
    cluster_n_triangles = np.asarray(cluster_n_triangles)

    largest_cluster_idx = cluster_n_triangles.argmax()
    triangles_to_keep = triangle_clusters == largest_cluster_idx
    mesh.remove_triangles_by_mask(~triangles_to_keep)
    mesh.remove_unreferenced_vertices()
    return mesh


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    cfg = load_config(config_path)
    mesh_cfg = cfg["mesh"]

    export_dir = input(
        "Path to session export folder (e.g. data\\sessions\\...\\export): "
    ).strip()

    fused_mesh_path = os.path.join(export_dir, "tsdf", "fused_mesh.ply")
    if not os.path.isfile(fused_mesh_path):
        print(f"fused_mesh.ply not found at {fused_mesh_path}. Run fuse.py first.")
        sys.exit(1)

    output_dir = os.path.join(script_dir, mesh_cfg["output_dir"])
    ensure_dir(output_dir)
    output_path = os.path.join(output_dir, mesh_cfg["output_filename"])

    print(f"Loading fused mesh from: {fused_mesh_path}")
    mesh = o3d.io.read_triangle_mesh(fused_mesh_path)
    print(f"  Vertices: {len(mesh.vertices)}  Triangles: {len(mesh.triangles)}")

    # Step 1: keep only the largest connected cluster
    print("Removing disconnected fragments...")
    mesh = keep_largest_cluster(mesh)
    print(f"  After clustering — Vertices: {len(mesh.vertices)}  Triangles: {len(mesh.triangles)}")

    # Step 2: Laplacian smoothing (light pass)
    print("Smoothing mesh (Laplacian, 5 iterations)...")
    mesh = mesh.filter_smooth_laplacian(number_of_iterations=5)
    mesh.compute_vertex_normals()

    # Step 3: save
    o3d.io.write_triangle_mesh(output_path, mesh)
    print(f"\nFinal mesh saved to: {output_path}")
    print(f"  Vertices: {len(mesh.vertices)}  Triangles: {len(mesh.triangles)}")

    # Optional: open viewer
    view = input("\nOpen mesh in viewer? [y/n]: ").strip().lower()
    if view == "y":
        o3d.visualization.draw_geometries(
            [mesh],
            window_name="3dscarn — Final Mesh",
            width=1280,
            height=720,
        )


if __name__ == "__main__":
    main()