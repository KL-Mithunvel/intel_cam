# Pipeline Guide — Step-by-Step Operations Manual

This document explains how to run the 3dscarn pipeline from start to finish.
Follow every step in order. Do not skip steps.

---

## Quick Start

The fastest way to run the pipeline is through the interactive runner:

```bash
# 1. Activate the virtualenv
.venv\Scripts\activate          # Windows

# 2. Launch the runner
cd 3dscarn
python run_pipeline.py
```

The runner shows which steps are done, prints instructions before each step,
and launches each script for you.

---

## Prerequisites

### Install dependencies

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

Key packages: `pyrealsense2`, `open3d`, `opencv-python`, `numpy`, `pyyaml`, `mediapipe`

### Hardware

- Intel RealSense D4xx camera connected via **USB 3.0**
- Object to scan: matte, non-reflective surface works best
- Stable lighting — avoid shadows that shift between background capture and scan

---

## Stage 1 — Capture

### Step 1 — Environment check

```bash
python cam_test.py
```

Verifies all libraries import correctly. Run this first on any new machine.
All output should say OK. If any import fails, install the missing package.

---

### Step 2 — Preview the scene

```bash
python viewer.py
```

Opens three live windows:

| Window | Content |
|--------|---------|
| `Color Stream` | Raw RGB from camera |
| `Depth Stream` | Depth colourised with JET colourmap |
| `Overlay` | 50/50 blend of colour and depth |

Use this to:
- Confirm the camera is working
- Position your object within depth range (0.3–1.5 m from camera)
- Check that lighting is stable and even

Press `q` to close.

---

### Step 3 — Capture background reference

**Remove the object from the scene first.** The camera must see only the empty background.

```bash
python capture_BG.py
```

When prompted:
```
Output folder for background: data\sessions\<your_session>\export\meta
```

The script:
1. Waits 2 seconds for you to step back
2. Captures 30 depth frames
3. Computes the median → saves `bg_depth.npy`

> **Critical:** Do not move the camera after this step. The background reference
> is only valid for the camera position it was captured at.

---

### Step 4 — Record the scan

Place the object back in the scene.

```bash
python capture_bag.py
```

When prompted for a session name, type a short label: `mug`, `bolt`, `shoe`, etc.

The recording saves to:
```
data/sessions/<YYYY-MM-DD_HH-MM-SS>_<name>/raw/capture.bag
```

**Note the session folder path printed to console — you will need it in every step below.**

**During recording:**
- Keep the camera completely still
- Rotate the object slowly and steadily by hand
- Cover all sides: front, back, left, right, top, bottom
- Keep your hand as consistent in position as possible (it will be removed later)
- Aim for 30–60 seconds of footage

Press `q` to stop.

---

### Step 5 — Export frames

```bash
python playback.py
```

When prompted:
```
Path to .bag: data\sessions\<session_name>\raw\capture.bag
```

Exports to `data/sessions/<session>/export/`:

| Folder / File | Content |
|---------------|---------|
| `color/000000.png` ... | Per-frame RGB images |
| `depth_npy/000000.npy` ... | Per-frame depth arrays (mm, uint16) |
| `meta/intrinsics.json` | Camera focal length, principal point, resolution |
| `meta/frame_timestamps.csv` | Timestamp of every frame |

---

## Stage 2 — Processing

All processing steps take the **session export folder** as input.
This is: `data/sessions/<session_name>/export`

---

### Step 6 — Preprocess (background subtraction + hand removal)

```bash
python preprocess.py
```

When prompted:
```
Path to session export folder: data\sessions\<session_name>\export
```

What happens:
1. Loads `meta/bg_depth.npy` as the background reference
2. For each depth frame: computes `|depth − bg_depth| > threshold` → foreground mask
3. Runs MediaPipe hand detection on the colour frame → hand mask (convex hull + dilation)
4. Removes hand pixels from the foreground mask
5. Applies morphological open (noise removal) + close (fill holes)
6. Zeros out all non-object pixels in the depth frame
7. Saves to `export/depth_masked/`

**If you see a resolution warning:** The background was captured at a different
resolution than the depth frames. The script handles this automatically by resizing.
To avoid this in future, ensure `capture_BG.py` and `capture_bag.py` use the same
stream resolution (the camera auto-detects now, so just run both with the same
camera settings).

**Tuning:** If the object mask has holes or noise, edit `config.yaml`:
- Increase `depth_threshold_mm` if foreground is too sparse
- Decrease it if background is leaking in
- Adjust `morph_kernel_size` for more/less noise removal

---

### Step 7 — Generate point clouds

```bash
python make_pointclouds.py
```

When prompted:
```
Path to session export folder: data\sessions\<session_name>\export
```

What happens:
1. Loads each masked depth frame + matching colour frame
2. Unprojects every non-zero pixel to 3D using `intrinsics.json`:
   ```
   Z = depth[v,u] / 1000.0     (mm → metres)
   X = (u − ppx) × Z / fx
   Y = (v − ppy) × Z / fy
   ```
3. Attaches the RGB colour of each pixel to its 3D point
4. Voxel-downsamples the cloud (reduces points, speeds up ICP)
5. Saves to `export/pointclouds/` as `.ply` files

Output: one coloured `.ply` file per input frame.

---

### Step 8 — ICP registration

```bash
python register.py
```

When prompted:
```
Path to session export folder: data\sessions\<session_name>\export
```

What happens:
1. Loads all per-frame point clouds in order
2. Frame 0 is the reference — all other frames are aligned to it
3. For each consecutive pair, runs **point-to-plane ICP** to find the rigid
   transform (rotation + translation) that best aligns source to target
4. Accumulates transforms so every frame ends up in frame-0 coordinate space
5. Saves transformed clouds to `export/registered/`
6. Saves all 4×4 pose matrices to `export/registered/transforms.npy`

**Watch the output:**
- `fitness` close to 1.0 = good alignment, many inlier correspondences
- `fitness` below 0.3 = poor alignment — the object may have rotated too fast
  between frames; try re-recording with slower rotation

**Tuning:** If ICP diverges, increase `icp_max_distance_m` in `config.yaml`.
If it is too loose, decrease it.

This step is the slowest in the pipeline. Expected time: 2–10 minutes
depending on frame count and machine speed.

---

### Step 9 — TSDF fusion

```bash
python fuse.py
```

When prompted:
```
Path to session export folder: data\sessions\<session_name>\export
```

What happens:
1. Creates an Open3D `ScalableTSDFVolume` (a 3D voxel grid)
2. For each registered frame, integrates the RGBD image into the volume
   using the frame's camera pose from `transforms.npy`
3. Each voxel accumulates signed distance values and colour from all frames
   that can see it — this averages out noise and fills gaps
4. After all frames are integrated, runs Marching Cubes to extract the surface
5. Saves to `export/tsdf/fused_mesh.ply`

**Tuning:**
- `tsdf_voxel_size_m`: smaller = more detail, more memory. Start at `0.004`.
  Try `0.002` for fine detail on small objects.
- `tsdf_truncation_m`: should be 4–6× `tsdf_voxel_size_m`.

---

### Step 10 — Extract and clean final mesh

```bash
python extract_mesh.py
```

When prompted:
```
Path to session export folder: data\sessions\<session_name>\export
```

What happens:
1. Loads `export/tsdf/fused_mesh.ply`
2. Removes all disconnected fragments — keeps only the largest connected cluster
3. Applies Laplacian smoothing (5 iterations) to reduce surface roughness
4. Recomputes vertex normals
5. Saves to `output/mesh.ply`

At the end, type `y` to open the interactive 3D viewer, or `n` to skip.

---

## Output

The final mesh is at:
```
3dscarn/output/mesh.ply
```

This is a coloured triangle mesh in PLY format. It can be opened in:
- Open3D viewer (built into `extract_mesh.py`)
- MeshLab (free, recommended for inspection)
- Blender
- Any CAD/simulation tool that supports PLY or OBJ import

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Depth window all black | Object too far or close | Keep object 0.3–1.5 m from camera |
| `bg_depth.npy not found` | Background not captured for this session | Run Step 3 and save to `meta/` inside the session |
| `mediapipe not found` | Not installed | `pip install mediapipe` |
| Hand still visible in mesh | Hand mask too small | Increase `hand_mask_dilation` in `config.yaml` |
| Object has holes | Parts never seen by camera | Rotate more thoroughly during recording; lower `tsdf_voxel_size_m` |
| ICP fitness < 0.3 | Object rotated too fast | Re-record with slower rotation |
| TSDF step runs out of memory | Voxel grid too fine or too large | Increase `tsdf_voxel_size_m`; reduce `tsdf_volume_size` |
| Final mesh is fragmented | Poor ICP alignment | Check registration fitness scores; retune `icp_max_distance_m` |

---

## Re-running a step

Every processing step (6–10) is safe to re-run. Output folders are overwritten.
If you change `config.yaml`, re-run from Step 6 onwards.

---

## Session data layout (full)

```
3dscarn/data/sessions/<timestamp>_<name>/
├── raw/
│   └── capture.bag                     ← Step 4 output (never overwritten)
└── export/
    ├── color/
    │   └── 000000.png ... 00NNNN.png   ← Step 5
    ├── depth_npy/
    │   └── 000000.npy ... 00NNNN.npy   ← Step 5
    ├── meta/
    │   ├── intrinsics.json             ← Step 5
    │   ├── frame_timestamps.csv        ← Step 5
    │   └── bg_depth.npy                ← Step 3
    ├── depth_masked/
    │   └── 000000.npy ...              ← Step 6
    ├── pointclouds/
    │   └── 000000.ply ...              ← Step 7
    ├── registered/
    │   ├── 000000.ply ...              ← Step 8
    │   └── transforms.npy              ← Step 8
    └── tsdf/
        └── fused_mesh.ply              ← Step 9

3dscarn/output/
└── mesh.ply                            ← Step 10 (final output)
```