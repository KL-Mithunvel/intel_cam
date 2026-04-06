"""
preprocess.py

For each exported frame:
  1. Load depth frame + colour frame
  2. Depth subtraction against bg_depth.npy → foreground mask
  3. MediaPipe hand detection → hand mask
  4. Remove hand region from foreground mask
  5. Morphological cleanup (open → close)
  6. Apply mask: zero out non-object depth pixels
  7. Save masked depth to export/depth_masked/<frame>.npy

Reads all parameters from config.yaml.
"""

import os
import sys
import json
import yaml
import numpy as np
import cv2

try:
    import mediapipe as mp
except ImportError:
    print("mediapipe not found.  pip install mediapipe")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def build_hand_mask(color_bgr: np.ndarray, hands_detector, dilation_px: int) -> np.ndarray:
    """Return a boolean mask (H, W) where True = hand pixels."""
    h, w = color_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    color_rgb = cv2.cvtColor(color_bgr, cv2.COLOR_BGR2RGB)
    result = hands_detector.process(color_rgb)

    if not result.multi_hand_landmarks:
        return mask.astype(bool)

    for hand_landmarks in result.multi_hand_landmarks:
        # Collect all landmark pixel coordinates
        points = np.array(
            [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks.landmark],
            dtype=np.int32,
        )
        # Convex hull around the hand landmarks
        hull = cv2.convexHull(points)
        cv2.fillConvexPoly(mask, hull, 255)

    # Dilate to cover wrist/edge pixels MediaPipe may miss
    if dilation_px > 0:
        kernel = np.ones((dilation_px, dilation_px), dtype=np.uint8)
        mask = cv2.dilate(mask, kernel)

    return mask.astype(bool)


def build_foreground_mask(depth: np.ndarray, bg_depth: np.ndarray, threshold_mm: int) -> np.ndarray:
    """Pixels where depth differs from background by more than threshold."""
    # Ignore zero-depth pixels (no reading)
    valid = (depth > 0) & (bg_depth > 0)
    diff = np.abs(depth.astype(np.int32) - bg_depth.astype(np.int32))
    return valid & (diff > threshold_mm)


def clean_mask(mask: np.ndarray, kernel_size: int, min_blob_area: int) -> np.ndarray:
    """Morphological open (noise removal) + close (fill holes) + small blob removal."""
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
    )
    opened = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

    # Remove blobs smaller than min_blob_area
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    clean = np.zeros_like(closed)
    for label in range(1, n_labels):  # skip background (label 0)
        if stats[label, cv2.CC_STAT_AREA] >= min_blob_area:
            clean[labels == label] = 1

    return clean.astype(bool)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    cfg = load_config(config_path)
    pre = cfg["preprocessing"]

    export_dir = input(
        "Path to session export folder (e.g. data\\sessions\\...\\export): "
    ).strip()

    color_dir    = os.path.join(export_dir, "color")
    depth_dir    = os.path.join(export_dir, "depth_npy")
    meta_dir     = os.path.join(export_dir, "meta")
    masked_dir   = os.path.join(export_dir, "depth_masked")
    ensure_dir(masked_dir)

    bg_path = os.path.join(meta_dir, "bg_depth.npy")
    if not os.path.isfile(bg_path):
        print(f"bg_depth.npy not found at {bg_path}")
        sys.exit(1)

    bg_depth = np.load(bg_path)
    print(f"Background depth loaded  shape={bg_depth.shape}")

    # Collect frames
    depth_files = sorted(f for f in os.listdir(depth_dir) if f.endswith(".npy"))
    if not depth_files:
        print("No depth frames found.")
        sys.exit(1)

    print(f"Found {len(depth_files)} depth frames.")

    # Initialise MediaPipe
    mp_hands = mp.solutions.hands
    hands_detector = mp_hands.Hands(
        static_image_mode=True,
        max_num_hands=2,
        min_detection_confidence=pre["hand_detection_confidence"],
    )

    threshold_mm  = pre["depth_threshold_mm"]
    kernel_size   = pre["morph_kernel_size"]
    min_blob_area = pre["min_blob_area"]
    dilation_px   = pre["hand_mask_dilation"]

    processed = 0
    for fname in depth_files:
        stem = os.path.splitext(fname)[0]
        depth_path = os.path.join(depth_dir, fname)
        color_path = os.path.join(color_dir, stem + ".png")

        depth = np.load(depth_path)

        if bg_depth.shape != depth.shape:
            print(
                f"[WARN] frame {stem}: bg_depth shape {bg_depth.shape} != "
                f"depth shape {depth.shape} — resizing bg_depth to match."
            )
            bg_resized = cv2.resize(
                bg_depth.astype(np.float32),
                (depth.shape[1], depth.shape[0]),
                interpolation=cv2.INTER_NEAREST,
            ).astype(np.uint16)
        else:
            bg_resized = bg_depth

        # Step 1: foreground via depth subtraction
        fg_mask = build_foreground_mask(depth, bg_resized, threshold_mm)

        # Step 2: hand mask via MediaPipe (requires colour frame)
        if os.path.isfile(color_path):
            color_bgr = cv2.imread(color_path)
            hand_mask = build_hand_mask(color_bgr, hands_detector, dilation_px)
            # Remove hand from foreground
            object_mask = fg_mask & ~hand_mask
        else:
            print(f"[WARN] frame {stem}: colour image not found — skipping hand removal.")
            object_mask = fg_mask

        # Step 3: morphological cleanup
        object_mask = clean_mask(object_mask, kernel_size, min_blob_area)

        # Step 4: apply mask — zero out non-object depth
        masked_depth = depth.copy()
        masked_depth[~object_mask] = 0

        out_path = os.path.join(masked_dir, fname)
        np.save(out_path, masked_depth)
        processed += 1

        if processed % 50 == 0 or processed == len(depth_files):
            print(f"  Processed {processed}/{len(depth_files)}")

    hands_detector.close()
    print(f"\nDone. Masked depth frames saved to: {masked_dir}")


if __name__ == "__main__":
    main()