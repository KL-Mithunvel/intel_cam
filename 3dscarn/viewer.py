import sys
import numpy as np
import cv2

try:
    import pyrealsense2 as rs
except ImportError:
    print("pyrealsense2 not found. Install it inside this venv.")
    sys.exit(1)


def main():
    pipeline = rs.pipeline()
    config = rs.config()

    # 640x480, 30 FPS – stable and enough for now
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

    profile = pipeline.start(config)

    # Align depth to color
    align = rs.align(rs.stream.color)

    colorizer = rs.colorizer()

    print("Viewer started. Press 'q' to quit.")
    try:
        while True:
            frames = pipeline.wait_for_frames()
            frames = align.process(frames)

            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            if not depth_frame or not color_frame:
                continue

            color = np.asanyarray(color_frame.get_data())
            depth_color = np.asanyarray(colorizer.colorize(depth_frame).get_data())

            overlay = cv2.addWeighted(color, 0.7, depth_color, 0.3, 0)

            cv2.imshow("Color", color)
            cv2.imshow("Depth (aligned, colorized)", depth_color)
            cv2.imshow("Overlay", overlay)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()