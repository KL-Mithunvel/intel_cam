# 3D Object Reconstruction Using Intel RealSense RGB-D Camera

**Author:** KL Mithunvel
**Platform:** Windows 11 | Python 3.10+
**Hardware:** Intel RealSense D4xx depth camera

---

## Abstract

This project implements a complete offline pipeline for reconstructing a 3D mesh
of a physical object using a consumer-grade Intel RealSense RGB-D camera.
The camera remains stationary; the object is rotated manually by hand.
Background removal is achieved through depth subtraction against a pre-captured
reference frame. Hand interference is removed using MediaPipe hand landmark
detection combined with foreground masking. The pipeline produces a coloured,
textured triangle mesh exported as a `.ply` file compatible with standard
CAD and simulation tools.

---

## Problem Statement

Design and implement a Python-based 3D reconstruction pipeline that:

1. Captures aligned RGB and depth data from a stationary Intel RealSense camera
2. Removes the static background and the operator's hand from every frame
3. Converts depth data into coloured 3D point clouds using camera intrinsics
4. Aligns multiple point clouds across frames using ICP registration
5. Fuses the registered clouds into a smooth volumetric representation (TSDF)
6. Extracts and exports a clean, coloured triangle mesh

---

## Hardware Requirements

| Component | Specification |
|-----------|--------------|
| Depth camera | Intel RealSense D4xx series |
| USB port | USB 3.0 (USB 2.0 will not work) |
| Object | Matte, non-reflective surface preferred |

---

## Software Requirements

| Package | Version | Purpose |
|---------|---------|---------|
| `pyrealsense2` | 2.56+ | Intel RealSense SDK — camera streaming, recording, playback |
| `open3d` | 0.19+ | Point clouds, ICP registration, TSDF fusion, mesh extraction |
| `opencv-python` | 4.13+ | Image processing, morphological operations |
| `numpy` | 2.2+ | Array operations |
| `mediapipe` | 0.10+ | Hand landmark detection for hand removal |
| `pyyaml` | 6.0+ | Configuration file parsing |

### Installation

```bash
# Activate the virtual environment first
.venv\Scripts\activate          # Windows

# Install all dependencies
pip install -r requirements.txt
```

---

## Pipeline Overview

The pipeline consists of 10 steps across two stages:

```
STAGE 1 — CAPTURE
─────────────────────────────────────────────────────────────────
  Step 1   cam_test.py         Verify environment and libraries
  Step 2   viewer.py           Live camera preview — check scene
  Step 3   capture_BG.py       Capture empty-scene background reference
  Step 4   capture_bag.py      Record scan session to .bag file
  Step 5   playback.py         Export frames (PNG + .npy) from recording

STAGE 2 — PROCESSING
─────────────────────────────────────────────────────────────────
  Step 6   preprocess.py       Depth subtraction + MediaPipe hand removal
  Step 7   make_pointclouds.py Unproject depth → coloured 3D point clouds
  Step 8   register.py         ICP alignment → all clouds in one frame
  Step 9   fuse.py             TSDF fusion → volumetric mesh
  Step 10  extract_mesh.py     Mesh cleanup → output/mesh.ply
```

---

## Quickstart

```bash
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Enter the project folder
cd 3dscarn

# 3. Launch the interactive pipeline runner
python run_pipeline.py
```

The runner displays pipeline status and guides you through each step.
For detailed instructions see [`docs/PIPELINE_GUIDE.md`](docs/PIPELINE_GUIDE.md).

---

## Architecture

### Background Removal — Depth Subtraction

An empty-scene reference depth image is captured before every scan.
During preprocessing, each scan frame is compared against this reference:

```
foreground_mask = |depth_frame − bg_depth| > threshold_mm
```

Pixels that differ by more than the threshold are classified as foreground
(object or hand). This cleanly removes the static background regardless of
scene complexity.

### Hand Removal — MediaPipe + Mask Subtraction

MediaPipe Hands detects hand landmarks in the corresponding colour frame.
A convex hull is computed from the 21 landmark points and dilated by a
configurable number of pixels to cover the wrist and edges:

```
hand_mask      = convex_hull(landmarks) + dilation
object_mask    = foreground_mask AND NOT hand_mask
```

The combined mask is then morphologically cleaned (open → close → blob filter)
before being applied to the depth frame.

### Point Cloud Generation — Depth Unprojection

Each non-zero masked depth pixel `(u, v)` is unprojected to 3D using the
pinhole camera model and saved intrinsic parameters:

```
Z = depth[v, u] / 1000.0        (mm → metres)
X = (u − ppx) × Z / fx
Y = (v − ppy) × Z / fy
```

The corresponding RGB colour is attached to each point.

### Registration — ICP (Iterative Closest Point)

Point-to-plane ICP aligns successive point clouds frame-by-frame.
Transforms are accumulated so every frame ends up in the coordinate system
of frame 0. Alignment quality is reported as a fitness score (0–1).

### Fusion — TSDF (Truncated Signed Distance Function)

All registered RGBD frames are integrated into an Open3D
`ScalableTSDFVolume`. Each voxel accumulates:
- A signed distance value (positive = outside, negative = inside, 0 = surface)
- A colour value (RGB)
- A weight (number of observations)

Averaging across many frames smooths sensor noise and fills gaps.
Marching Cubes extracts the zero-crossing isosurface as a triangle mesh.

### Mesh Cleanup

The extracted mesh is cleaned by:
1. Removing all disconnected fragments — only the largest cluster is kept
2. Laplacian smoothing (5 iterations) to reduce surface roughness
3. Vertex normal recomputation

---

## Configuration

All pipeline parameters are in `config.yaml`. Edit this file to tune
behaviour without modifying any script.

Key parameters:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `depth_threshold_mm` | 30 | Foreground sensitivity |
| `hand_mask_dilation` | 20 | Hand mask coverage |
| `icp_max_distance_m` | 0.02 | ICP correspondence distance |
| `tsdf_voxel_size_m` | 0.004 | Mesh resolution (smaller = finer) |

Full parameter reference: [`docs/REFERENCE.md`](docs/REFERENCE.md)

---

## Project Structure

```
3dscarn/
├── run_pipeline.py         ← Interactive pipeline runner (start here)
├── cam_test.py             ← Environment check
├── viewer.py               ← Live camera preview
├── capture_BG.py           ← Background reference capture
├── capture_bag.py          ← Scan session recording
├── playback.py             ← Frame export from .bag
├── preprocess.py           ← Background subtraction + hand removal
├── make_pointclouds.py     ← Depth → coloured point clouds
├── register.py             ← ICP alignment
├── fuse.py                 ← TSDF volumetric fusion
├── extract_mesh.py         ← Mesh cleanup and export
├── config.yaml             ← All tuneable parameters
├── docs/
│   ├── PROJECT_OVERVIEW.md     ← Goals, motivation, scope
│   ├── SYSTEM_ARCHITECTURE.md  ← Pipeline design and flowcharts
│   ├── TECHNICAL_DESIGN.md     ← Algorithm and parameter details
│   ├── PIPELINE_GUIDE.md       ← Step-by-step operations manual
│   └── REFERENCE.md            ← Complete script and file reference
├── data/sessions/          ← Recorded scan sessions (not tracked)
└── output/
    └── mesh.ply            ← Final 3D mesh output
```

---

## Session Data Layout

```
data/sessions/<YYYY-MM-DD_HH-MM-SS>_<name>/
├── raw/
│   └── capture.bag             ← Raw recording
└── export/
    ├── color/                  ← Per-frame RGB images
    ├── depth_npy/              ← Per-frame depth arrays (uint16, mm)
    ├── meta/
    │   ├── intrinsics.json     ← Camera intrinsic parameters
    │   ├── frame_timestamps.csv
    │   └── bg_depth.npy        ← Background depth reference
    ├── depth_masked/           ← After Step 6: hand+bg removed
    ├── pointclouds/            ← After Step 7: coloured .ply per frame
    ├── registered/             ← After Step 8: aligned .ply + transforms
    └── tsdf/
        └── fused_mesh.ply      ← After Step 9: fused mesh
```

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| Camera not detected | USB 2.0 port | Use USB 3.0 |
| `No module named 'mediapipe'` | Not installed | `pip install mediapipe` |
| Hand still visible in mesh | Hand mask too small | Increase `hand_mask_dilation` in `config.yaml` |
| Object has holes | Parts never seen by camera | Rotate more fully; reduce `tsdf_voxel_size_m` |
| ICP fitness below 0.3 | Object rotated too fast | Re-record with slower rotation |
| Out of memory during fusion | TSDF grid too fine | Increase `tsdf_voxel_size_m` |

---

## Documentation

| Document | Contents |
|----------|---------|
| [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md) | Goals, motivation, applications, scope |
| [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) | Pipeline layers, flowchart, data flow |
| [`docs/TECHNICAL_DESIGN.md`](docs/TECHNICAL_DESIGN.md) | Hardware, algorithms, parameters |
| [`docs/PIPELINE_GUIDE.md`](docs/PIPELINE_GUIDE.md) | Step-by-step operations manual |
| [`docs/REFERENCE.md`](docs/REFERENCE.md) | Every script, file, config param explained |

---

## Technologies Used

- **Intel RealSense SDK** (`pyrealsense2`) — depth camera interface
- **Open3D** — 3D geometry processing, ICP, TSDF, Marching Cubes
- **OpenCV** — image processing, morphological operations
- **MediaPipe** — real-time hand landmark detection
- **NumPy** — numerical array operations
- **Python 3.10+**
