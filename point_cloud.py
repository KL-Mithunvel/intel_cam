import pyrealsense2 as rs
import numpy as np
import open3d as o3d


def generate_aligned_point_cloud():
    """Generate point cloud with proper depth-color alignment"""

    # Create pipeline
    pipeline = rs.pipeline()
    config = rs.config()

    # Configure streams
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    try:
        # Start streaming
        pipeline.start(config)

        # Create align object
        align_to = rs.stream.color
        align = rs.align(align_to)

        # Wait for frames
        frames = pipeline.wait_for_frames()

        # Align frames
        aligned_frames = align.process(frames)

        # Get aligned frames
        aligned_depth_frame = aligned_frames.get_depth_frame()
        aligned_color_frame = aligned_frames.get_color_frame()

        if aligned_depth_frame and aligned_color_frame:
            # Create point cloud
            pc = rs.pointcloud()
            pc.map_to(aligned_color_frame)
            points = pc.calculate(aligned_depth_frame)

            # Get point cloud data
            vertices = np.asanyarray(points.get_vertices())
            colors = np.asanyarray(points.get_colors())

            # Filter out invalid points
            valid_mask = vertices['f2'] > 0  # Filter by depth > 0
            valid_vertices = vertices[valid_mask]
            valid_colors = colors[valid_mask]

            # Create Open3D point cloud
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(valid_vertices)
            pcd.colors = o3d.utility.Vector3dVector(valid_colors)

            return pcd

    except Exception as e:
        print(f"❌ Error generating aligned point cloud: {e}")
        return None

    finally:
        pipeline.stop()


# Generate aligned point cloud
pcd = generate_aligned_point_cloud()
if pcd:
    o3d.visualization.draw_geometries([pcd])