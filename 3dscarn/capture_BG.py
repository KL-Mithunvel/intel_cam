import os
import sys
import time
import numpy as np

try:
    import pyrealsense2 as rs
except ImportError:
    print("pyrealsense2 not found. Run inside the correct venv.")
    sys.exit(1)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def main():
    # Where to save background? (put inside a session export/meta/)
    out_dir = input(
        "Output folder for background (e.g. data\\sessions\\...\\export\\meta): "
    ).strip()

    if not out_dir:
        print("No folder given.")
        return

    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, "bg_depth.npy")

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

    align = rs.align(rs.stream.color)

    N_FRAMES = 30
    print(f"Make sure the scene is EMPTY (no object, no hand).")
    print(f"Capturing {N_FRAMES} frames in 2 seconds...")
    time.sleep(2)

    pipeline.start(config)

    depths = []
    try:
        for i in range(N_FRAMES):
            frames = pipeline.wait_for_frames()
            frames = align.process(frames)

            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                continue

            depth = np.asanyarray(depth_frame.get_data()).astype(np.uint16)
            depths.append(depth)
            print(f"Captured background frame {i+1}/{N_FRAMES}")

        if not depths:
            print("No depth frames captured.")
            return

        # Stack and take median along frame axis
        stack = np.stack(depths, axis=0)
        bg_depth = np.median(stack, axis=0).astype(np.uint16)

        np.save(out_path, bg_depth)
        print(f"Background depth saved to: {out_path}")
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()