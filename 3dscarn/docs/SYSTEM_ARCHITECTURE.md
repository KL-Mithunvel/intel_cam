# System Architecture

## 1. System Overview

The pipeline is divided into four major layers:

| Layer | Responsibility |
|-------|---------------|
| **Data Acquisition** | Capture RGB + depth frames from the RealSense camera |
| **Preprocessing** | Background removal, noise filtering, mask generation |
| **Reconstruction** | Point cloud generation, registration (ICP), volumetric fusion (TSDF) |
| **Output** | Mesh extraction, file export, visualisation |

---

## 2. Layer Descriptions

### 2.1 Data Acquisition Layer

- Streams RGB and depth frames using the RealSense SDK (`pyrealsense2`)
- Aligns depth to the colour frame so both share the same pixel coordinate system
- Records to a `.bag` file for offline processing

**Output:** `data/sessions/<timestamp>_<name>/raw/capture.bag`

### 2.2 Preprocessing Layer

This is the most critical stage — it determines the quality of the final mesh.

**Functions:**

| Function | Description |
|----------|-------------|
| Background modelling | Capture empty scene; compute median depth across N frames |
| Depth subtraction | Subtract background depth from current frame |
| Foreground mask | Pixels where `|current_depth − bg_depth| > threshold` are foreground |
| Noise filtering | Morphological operations to clean the binary mask |

**Goal:** Isolate only the object — no hand, no background pixels in the output point cloud.

### 2.3 Reconstruction Layer

| Step | Method |
|------|--------|
| Depth → 3D points | Unproject each pixel using camera intrinsics |
| Frame alignment | ICP (Iterative Closest Point) |
| Volume fusion | TSDF (Truncated Signed Distance Function) |

### 2.4 Output Layer

- Extract triangle mesh from the TSDF volume
- Export to `.ply` / `.obj`
- Optionally visualise in Open3D

---

## 3. Detailed Workflow

### Step 1 — RGB-D Capture

The camera produces two synchronised streams per frame:

- **Depth image:** each pixel stores distance in millimetres (`uint16`)
- **RGB image:** colour frame in BGR format (`uint8 × 3`)

### Step 2 — Depth-to-Colour Alignment

Depth is reprojected onto the colour frame's coordinate system using `rs.align`. After this step, depth pixel `(u, v)` directly corresponds to colour pixel `(u, v)`.

### Step 3 — Background Modelling

```
1. Clear the scene (no object, no hand)
2. Capture N frames (default: 30)
3. Stack depth arrays → shape (N, H, W)
4. bg_depth = median(stack, axis=0)  ← robust to sensor noise
5. Save bg_depth.npy
```

### Step 4 — Foreground Extraction

```
foreground_mask = |current_depth − bg_depth| > THRESHOLD
```

Pixels that differ from the background by more than `THRESHOLD` (in mm) are considered foreground (the object or the hand).

### Step 5 — Hand Removal / Mask Cleaning

Morphological operations are applied to remove noise and fill small holes:

```
Opening  (erode → dilate) → removes small noise blobs
Closing  (dilate → erode) → fills gaps inside the object mask
```

### Step 6 — Point Cloud Generation

Each foreground pixel `(u, v)` with depth `Z` is unprojected to 3D using the camera's intrinsic parameters:

```
Z = depth[v, u]   (in metres)
X = (u − ppx) × Z / fx
Y = (v − ppy) × Z / fy
```

Where `fx`, `fy`, `ppx`, `ppy` come from `intrinsics.json`.

**Camera intrinsics (from recorded session):**

| Parameter | Value |
|-----------|-------|
| `fx` | 907.475 |
| `fy` | 907.370 |
| `ppx` | 649.217 |
| `ppy` | 377.003 |
| Distortion model | `inverse_brown_conrady` (all coefficients = 0) |

### Step 7 — Registration (ICP)

ICP aligns successive point clouds into a common coordinate frame:

```
1. Find closest-point correspondences between source and target
2. Compute the rigid transformation (R, t) that minimises distance
3. Apply transformation to source
4. Repeat until convergence (change < epsilon)
```

### Step 8 — TSDF Fusion

The TSDF volume stores a signed distance field over a 3D voxel grid:

- Positive values → outside the surface
- Negative values → inside the surface
- Zero crossing → the surface itself

Each registered point cloud votes into the grid. Averaging across many frames produces a smooth, noise-reduced surface representation.

### Step 9 — Mesh Extraction

Marching Cubes is run on the TSDF volume to extract a triangle mesh at the zero-crossing (the object surface).

---

## 4. Pipeline Flowchart

```
Camera Initialisation
        │
        ▼
RGB-D Frame Capture  ──────────────────────────────┐
        │                                           │
        ▼                                           │
Depth-to-Colour Alignment                          │ (offline, from .bag)
        │                                           │
        ▼                                           │
Background Model Creation (capture_BG.py)          │
        │                                           │
        ▼                                           │
Frame Export (playback.py) ─────────────────────────┘
        │
        ▼
Depth Subtraction  (foreground = |depth − bg| > threshold)
        │
        ▼
Mask Generation + Noise Removal (morphological ops)
        │
        ▼
Point Cloud Creation  (unproject depth → XYZ)
        │
        ▼
ICP Registration  (align frames to common frame)
        │
        ▼
TSDF Fusion  (volumetric integration)
        │
        ▼
Mesh Extraction  (Marching Cubes)
        │
        ▼
Mesh Cleanup + Export  (.ply / .obj)
        │
        ▼
Final Output
```

---

## 5. Data Flow

```
RealSense Camera
    │
    ├─ capture_bag.py ──► data/sessions/<session>/raw/capture.bag
    │
    ├─ capture_BG.py  ──► export/meta/bg_depth.npy
    │
    └─ playback.py    ──► export/color/<frame>.png
                          export/depth_npy/<frame>.npy
                          export/meta/intrinsics.json
                          export/meta/frame_timestamps.csv
                               │
                               ▼
                    [preprocessing + reconstruction]  ← NOT YET BUILT
                               │
                               ▼
                        output/mesh.ply
```

---

## 6. Module Responsibilities

| Script | Role | Input | Output |
|--------|------|-------|--------|
| `viewer.py` | Live camera preview | Camera stream | OpenCV windows |
| `capture_bag.py` | Record session | Camera stream | `.bag` file |
| `capture_BG.py` | Capture background reference | Camera stream | `bg_depth.npy` |
| `playback.py` | Export frames from recording | `.bag` file | PNGs, `.npy`, JSON, CSV |
| `cam_test.py` | Environment sanity check | — | Console output |