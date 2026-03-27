# Technical Design

## 1. Hardware

### Intel RealSense Camera

| Property | Detail |
|----------|--------|
| Sensing principle | Stereo vision + structured light (active IR) |
| Depth unit | Millimetres (`uint16`) |
| Colour format | BGR8 |
| Capture resolution | 640 × 480 (recording), 1280 × 720 (some sessions) |
| Frame rate | 30 FPS |
| SDK | `pyrealsense2` |

---

## 2. Software Stack

| Library | Version requirement | Role |
|---------|-------------------|------|
| `pyrealsense2` | Latest stable | Camera interface — streaming, recording, playback |
| `Open3D` | Latest stable | 3D data processing — point clouds, ICP, TSDF, mesh |
| `OpenCV` (`cv2`) | Latest stable | Image processing — masks, morphology, visualisation |
| `NumPy` | Latest stable | Numerical operations, array manipulation |
| Python | Latest stable (3.10+) | Runtime |

### Library Roles in Detail

**`pyrealsense2`**
- Initialises and configures the RealSense pipeline
- Handles depth/colour stream alignment (`rs.align`)
- Records to `.bag` and plays back from `.bag`
- Provides camera intrinsics via the stream profile

**`Open3D`**
- Creates `PointCloud` objects from depth + intrinsics
- ICP registration (`o3d.pipelines.registration`)
- TSDF integration (`o3d.pipelines.integration.ScalableTSDFVolume`)
- Mesh extraction (Marching Cubes) and export

**`OpenCV`**
- Converts colour frames for display
- HSV conversion and colour masking
- Morphological operations (erosion, dilation, opening, closing)
- Canny edge detection (used in MV experiments)

---

## 3. Algorithm Details

### 3.1 Background Subtraction

**Key idea:** The background (table, wall, etc.) is static — only the object and hand change between frames.

```
Procedure:
1. Capture N frames of the empty scene (no object)
2. bg_depth = median(all_frames, axis=0)
   ← median is robust to single-frame sensor noise
3. For each scan frame:
   diff = |scan_depth − bg_depth|
   foreground_mask = diff > DEPTH_THRESHOLD
```

`DEPTH_THRESHOLD` is typically 5–20 mm. Tune based on sensor noise floor.

### 3.2 Morphological Filtering

Applied to the binary foreground mask to clean noise and fill holes:

| Operation | Sequence | Effect |
|-----------|----------|--------|
| Opening | Erode → Dilate | Removes small isolated noise blobs |
| Closing | Dilate → Erode | Fills small gaps/holes inside the object region |

Kernel size (e.g. 3×3 or 5×5) controls aggressiveness. Larger kernels remove more noise but may erode fine detail.

### 3.3 Point Cloud Generation

Each foreground pixel `(u, v)` is unprojected to 3D using the pinhole camera model:

```python
Z = depth_frame[v, u] / 1000.0   # convert mm → metres
X = (u - ppx) * Z / fx
Y = (v - ppy) * Z / fy
point_3d = (X, Y, Z)
```

Parameters `fx`, `fy`, `ppx`, `ppy` are loaded from `export/meta/intrinsics.json`.

### 3.4 ICP Registration (Iterative Closest Point)

Aligns successive point clouds into a common world frame:

```
Inputs:   source cloud (frame N), target cloud (frame N-1)
          initial transform estimate (identity or from previous iteration)

Loop until convergence:
  1. Find closest point in target for each source point
  2. Reject correspondences with distance > max_correspondence_dist
  3. Compute optimal rigid transform (R, t) via SVD
  4. Apply (R, t) to source
  5. Check convergence: if Δtransform < ε, stop

Output:   4×4 transformation matrix, fitness score, RMSE
```

Open3D provides `o3d.pipelines.registration.registration_icp()`.

### 3.5 TSDF Fusion (Truncated Signed Distance Function)

Accumulates many registered point clouds into a smooth volumetric representation:

```
Volume:   3D voxel grid, each voxel stores:
          - SDF value: signed distance to the nearest surface
          - Weight:    how many observations have voted into this voxel

Positive SDF → outside the object
Negative SDF → inside the object
Zero crossing → the surface

Truncation:  SDF values beyond ±truncation_distance are clamped
             → focuses accuracy near the surface, saves memory
```

**Advantages over naive point cloud merging:**
- Smooth surfaces (sensor noise averages out across frames)
- Gap filling (sparse regions are interpolated)
- Natural handling of overlapping observations

### 3.6 Mesh Extraction

Marching Cubes is run on the completed TSDF volume. It finds the zero-crossing isosurface and outputs a triangle mesh. The mesh is then:

1. Cleaned (remove isolated fragments, smooth if needed)
2. Exported as `.ply` or `.obj`

---

## 4. File System Design

```
3dscarn/
├── viewer.py          # live preview
├── capture_bag.py     # session recording
├── capture_BG.py      # background reference capture
├── playback.py        # frame export from .bag
├── cam_test.py        # environment check
├── claude.md          # project rules for Claude
├── docs/              # reference documents
│   ├── PROJECT_OVERVIEW.md
│   ├── SYSTEM_ARCHITECTURE.md
│   └── TECHNICAL_DESIGN.md
└── data/
    └── sessions/
        └── <YYYY-MM-DD_HH-MM-SS>_<name>/
            ├── raw/
            │   └── capture.bag
            └── export/
                ├── color/
                │   └── 000000.png  ...
                ├── depth_npy/
                │   └── 000000.npy  ...
                └── meta/
                    ├── intrinsics.json
                    ├── frame_timestamps.csv
                    └── bg_depth.npy
```

**Why structured session folders?**

| Reason | Benefit |
|--------|---------|
| Each session is self-contained | Easy to delete, archive, or re-process a single scan |
| Raw and export are separated | Re-running export doesn't overwrite the original `.bag` |
| Meta alongside export | Intrinsics and background always travel with their frames |
| Timestamped session names | No collision between multiple scan sessions |

---

## 5. Challenges and Solutions

| Challenge | Root Cause | Solution |
|-----------|-----------|----------|
| Hand interference in mesh | Hand occludes object and appears in depth frames | Depth mask: subtract background and threshold; hand + object both appear, but hand is at consistent depth offset |
| Sensor noise in depth | Stereo/IR quantisation noise, especially at edges | Median background model + morphological filtering + TSDF averaging |
| Frame misalignment | Object or camera vibration between frames | ICP registration with a tight max correspondence distance |
| Holes in mesh | Occluded regions never seen by camera | TSDF gap-filling + optional MeshLab post-processing |
| Depth/colour pixel mismatch | Depth and colour sensors are physically offset | `rs.align` reprojects depth onto colour coordinate frame |

---
## 6. Parameters to Tune

| Parameter | Where Used | Typical Value | Effect |
|-----------|-----------|---------------|--------|
| `N_FRAMES` | `capture_BG.py` | 30 | More frames = more robust background median |
| `DEPTH_THRESHOLD` | Preprocessing | 10–30 mm | Lower = stricter (may miss thin regions); higher = more noise included |
| Morphology kernel size | Preprocessing | 3×3 to 5×5 | Larger = more aggressive noise removal |
| ICP `max_correspondence_distance` | Registration | 0.02–0.05 m | Trade-off between accuracy and convergence speed |
| TSDF `voxel_length` | Fusion | 0.002–0.005 m | Smaller = higher resolution, more memory |
| TSDF `sdf_trunc` | Fusion | 3–5× voxel_length | Controls surface smoothing radius |