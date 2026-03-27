import pyrealsense2 as rs
import numpy as np
import cv2


def display_depth_map():
    """Display depth map using OpenCV"""

    # Create pipeline
    pipeline = rs.pipeline()
    config = rs.config()

    # Configure streams
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

    try:
        # Start streaming
        pipeline.start(config)

        while True:
            # Wait for frames
            frames = pipeline.wait_for_frames()

            # Get frames
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()

            if depth_frame and color_frame:
                # Convert to numpy arrays
                depth_image = np.asanyarray(depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())

                # Normalize depth image for display
                depth_colormap = cv2.applyColorMap(
                    cv2.convertScaleAbs(depth_image, alpha=0.03),
                    cv2.COLORMAP_JET
                )

                # Display images
                cv2.imshow('Color Stream', color_image)
                cv2.imshow('Depth Stream', depth_colormap)

                # Break on 'q' key press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


# Run the display function
display_depth_map()