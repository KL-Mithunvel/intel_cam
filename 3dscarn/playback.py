import os
import json
import csv
import sys
import numpy as np
import cv2

try:
    import pyrealsense2 as rs
except ImportError:
    print("pyrealsense2 not found.")
    sys.exit(1)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def write_intrinsics(profile, out_path: str):
    color_stream = profile.get_stream(rs.stream.color).as_video_stream_profile()
    intr = color_stream.get_intrinsics()
    data = {
        "width": intr.width,
        "height": intr.height,
        "fx": intr.fx,
        "fy": intr.fy,
        "ppx": intr.ppx,
        "ppy": intr.ppy,
        "model": str(intr.model),
        "coeffs": list(intr.coeffs),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    bag_path = input("Path to .bag (e.g. data\\sessions\\...\\raw\\capture.bag): ").strip()
    if not os.path.isfile(bag_path):
        print("Bag file not found.")
        sys.exit(1)

    session_root = os.path.dirname(os.path.dirname(bag_path))  # .../<session>/raw -> .../<session>
    export_dir = os.path.join(session_root, "export")
    color_dir = os.path.join(export_dir, "color")
    depth_dir = os.path.join(export_dir, "depth_npy")
    meta_dir  = os.path.join(export_dir, "meta")

    for d in (color_dir, depth_dir, meta_dir):
        ensure_dir(d)

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_device_from_file(bag_path, repeat_playback=False)
    config.enable_stream(rs.stream.color)
    config.enable_stream(rs.stream.depth)

    profile = pipeline.start(config)
    playback = profile.get_device().as_playback()
    playback.set_real_time(False)

    align = rs.align(rs.stream.color)

    write_intrinsics(profile, os.path.join(meta_dir, "intrinsics.json"))

    ts_csv = os.path.join(meta_dir, "frame_timestamps.csv")
    idx = 0
    with open(ts_csv, "w", newline="", encoding="utf-8") as fcsv:
        writer = csv.writer(fcsv)
        writer.writerow(["frame_idx", "timestamp_ms"])

        try:
            while True:
                frames = pipeline.wait_for_frames()
                frames = align.process(frames)

                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()
                if not depth_frame or not color_frame:
                    continue

                color = np.asanyarray(color_frame.get_data())
                depth = np.asanyarray(depth_frame.get_data()).astype(np.uint16)

                cv2.imwrite(os.path.join(color_dir, f"{idx:06d}.png"), color)
                np.save(os.path.join(depth_dir, f"{idx:06d}.npy"), depth)

                writer.writerow([idx, depth_frame.get_timestamp()])
                idx += 1
        except RuntimeError:
            # End of recording
            pass
        finally:
            pipeline.stop()

    print(f"Export complete.")
    print(f"Export dir: {export_dir}")
    print(f"Frames exported: {idx}")


if __name__ == "__main__":
    main()