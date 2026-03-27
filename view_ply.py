import open3d as o3d

# Load point cloud
pcd = o3d.io.read_point_cloud('pointcloud.ply')

# Visualize
o3d.visualization.draw_geometries([pcd])