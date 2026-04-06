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
    out_dir = input(
        "Output folder for background (e.g. data\\sessions\\...\\export\\meta): "
    ).strip()

    if not out_dir:
        print("No folder given.")
        return

    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, "bg_depth.npy")

    # Start pipeline with default streams — camera decides resolution
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color)
    config.enable_stream(rs.stream.depth)

    align = rs.align(rs.stream.color)

    N_FRAMES = 30
    print("Make sure the scene is EMPTY (no object, no hand).")
    print(f"Capturing {N_FRAMES} frames in 2 seconds...")
    time.sleep(2)

    profile = pipeline.start(config)

    # Read actual resolution from the live stream
    depth_profile = profile.get_stream(rs.stream.depth).as_video_stream_profile()
    w, h = depth_profile.width(), depth_profile.height()
    print(f"Camera streaming at {w}x{h}")

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
            print(f"Captured background frame {i + 1}/{N_FRAMES}")

        if not depths:
            print("No depth frames captured.")
            return

        stack = np.stack(depths, axis=0)
        bg_depth = np.median(stack, axis=0).astype(np.uint16)

        np.save(out_path, bg_depth)
        print(f"Background depth saved to: {out_path}  shape={bg_depth.shape}")
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()