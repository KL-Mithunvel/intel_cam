import os
import sys
import time
from datetime import datetime

try:
    import pyrealsense2 as rs
except ImportError:
    print("pyrealsense2 not found.")
    sys.exit(1)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def main():
    session_name = input("Session name (e.g. cube, mug): ").strip() or "session"
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    session_dir = os.path.join("data", "sessions", f"{stamp}_{session_name}", "raw")
    ensure_dir(session_dir)

    bag_path = os.path.join(session_dir, "capture.bag")

    pipeline = rs.pipeline()
    config = rs.config()

    # Record to bag file
    config.enable_record_to_file(bag_path)

    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

    print(f"Bag will be saved at: {bag_path}")
    print("Starting in 2 seconds...")
    time.sleep(2)

    pipeline.start(config)
    print("Recording... Press Ctrl+C in this terminal to stop.")

    try:
        while True:
            pipeline.wait_for_frames()
    except KeyboardInterrupt:
        print("Stopping recording...")
    finally:
        pipeline.stop()
        print(f"Saved .bag: {bag_path}")


if __name__ == "__main__":
    main()