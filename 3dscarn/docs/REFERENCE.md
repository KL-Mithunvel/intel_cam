# Reference — What Is What

Complete reference for every script, file, folder, and configuration parameter
in the 3dscarn project.

---

## Scripts

### `run_pipeline.py`

**Purpose:** Interactive pipeline runner. The single entry point for the full pipeline.

**What it does:**
- Detects which pipeline steps are already complete by checking for output files
- Displays a status dashboard showing done / not done for each step
- Auto-discovers session folders under `data/sessions/`
- Prints step-specific instructions before running each script
- Launches each script as a subprocess

**Run:**
```bash
python run_pipeline.py
```

**No inputs required** — everything is prompted interactively.

---

### `cam_test.py`

**Purpose:** Sanity check — verifies the Python environment is set up correctly.

**What it does:** Attempts to import `pyrealsense2`, `open3d`, and `cv2`. Prints OK or an error for each.

**Run:** `python cam_test.py`
**Inputs:** None
**Outputs:** Console only

---

### `viewer.py`

**Purpose:** Live camera preview before a scan session.

**What it does:** Opens three OpenCV windows showing the live colour stream, depth stream (JET colourmap), and a 50/50 colour+depth overlay. Depth and colour are aligned so pixels correspond.

**Run:** `python viewer.py`
**Inputs:** Live camera
**Outputs:** None (display only). Press `q` to quit.

---

### `capture_BG.py`

**Purpose:** Capture the empty-scene background depth reference.

**What it does:**
1. Starts the camera with auto-detected resolution
2. Waits 2 seconds
3. Captures 30 aligned depth frames
4. Computes pixel-wise median across all 30 frames (robust to sensor noise)
5. Saves the result as `bg_depth.npy`

**Run:** `python capture_BG.py`
**Inputs (prompted):** Output folder path — enter the `meta/` folder of your session
**Outputs:** `bg_depth.npy` — shape `(H, W)`, dtype `uint16`, values in millimetres

**Important:** Must be run with the scene empty and the camera in its final position. Do not move the camera after this.

---

### `capture_bag.py`

**Purpose:** Record an RGB-D scan session.

**What it does:** Streams live RGB and depth from the RealSense camera and records to a `.bag` file. Creates a timestamped session folder automatically.

**Run:** `python capture_bag.py`
**Inputs (prompted):** Session name (e.g. `mug`)
**Outputs:** `data/sessions/<timestamp>_<name>/raw/capture.bag`

Press `q` to stop recording.

---

### `playback.py`

**Purpose:** Export individual frames from a `.bag` recording.

**What it does:**
1. Opens a `.bag` file in non-real-time playback mode
2. Aligns depth to colour for each frame
3. Saves every colour frame as a PNG
4. Saves every depth frame as a `.npy` array (uint16, millimetres)
5. Writes `intrinsics.json` and `frame_timestamps.csv` once

**Run:** `python playback.py`
**Inputs (prompted):** Path to `.bag` file
**Outputs:** `export/color/`, `export/depth_npy/`, `export/meta/`

---

### `preprocess.py`

**Purpose:** Remove background and hand from every depth frame.

**What it does (per frame):**
1. Loads the depth frame and matching colour frame
2. Computes `|depth − bg_depth| > depth_threshold_mm` → foreground mask
3. Runs MediaPipe Hands on the colour frame → convex hull of hand landmarks → hand mask
4. Dilates the hand mask by `hand_mask_dilation` pixels to catch wrist edges
5. Subtracts hand mask from foreground: `object_mask = foreground AND NOT hand`
6. Applies morphological open (removes noise blobs) then close (fills holes)
7. Removes any connected components smaller than `min_blob_area` pixels
8. Zeros all non-object pixels in the depth array
9. Saves to `export/depth_masked/`

**Run:** `python preprocess.py`
**Inputs (prompted):** Session export folder
**Reads:** `meta/bg_depth.npy`, `depth_npy/*.npy`, `color/*.png`, `config.yaml`
**Outputs:** `export/depth_masked/*.npy`

---

### `make_pointclouds.py`

**Purpose:** Convert masked depth frames into coloured 3D point clouds.

**What it does (per frame):**
1. Loads masked depth + colour frame
2. For every non-zero pixel `(u, v)` with depth `Z` (in metres):
   ```
   X = (u − ppx) × Z / fx
   Y = (v − ppy) × Z / fy
   point = (X, Y, Z)
   ```
3. Attaches the BGR→RGB colour of the pixel to each point
4. Voxel-downsamples the cloud at `downsample_voxel_m` to reduce size
5. Saves as a coloured Open3D `.ply`

**Run:** `python make_pointclouds.py`
**Inputs (prompted):** Session export folder
**Reads:** `depth_masked/*.npy`, `color/*.png`, `meta/intrinsics.json`, `config.yaml`
**Outputs:** `export/pointclouds/*.ply`

---

### `register.py`

**Purpose:** Align all per-frame point clouds into a single coordinate frame.

**What it does:**
1. Loads all `.ply` files from `pointclouds/` in sorted order
2. Frame 0 is the world reference — identity transform
3. For each subsequent frame, runs **point-to-plane ICP** against the previous registered frame
4. Accumulates transforms: `T_world = T_curr_to_prev × T_world_prev`
5. Applies the cumulative transform and saves each cloud to `registered/`
6. Saves all 4×4 transformation matrices as `transforms.npy`

**Run:** `python register.py`
**Inputs (prompted):** Session export folder
**Reads:** `pointclouds/*.ply`, `config.yaml`
**Outputs:** `export/registered/*.ply`, `export/registered/transforms.npy`

---

### `fuse.py`

**Purpose:** Integrate all registered frames into a smooth volumetric mesh.

**What it does:**
1. Creates an Open3D `ScalableTSDFVolume`
2. For each frame, loads the masked depth + colour and constructs an RGBD image
3. Integrates into the volume using the frame's camera pose from `transforms.npy`
4. After all frames: runs Marching Cubes on the volume to extract the surface mesh
5. Saves `export/tsdf/fused_mesh.ply`

**Run:** `python fuse.py`
**Inputs (prompted):** Session export folder
**Reads:** `depth_masked/*.npy`, `color/*.png`, `registered/transforms.npy`, `meta/intrinsics.json`, `config.yaml`
**Outputs:** `export/tsdf/fused_mesh.ply`

---

### `extract_mesh.py`

**Purpose:** Clean and export the final mesh.

**What it does:**
1. Loads `export/tsdf/fused_mesh.ply`
2. Runs `cluster_connected_triangles` — keeps only the largest connected cluster
3. Applies Laplacian smoothing (5 iterations)
4. Recomputes vertex normals
5. Saves to `output/mesh.ply`
6. Optionally opens the Open3D viewer

**Run:** `python extract_mesh.py`
**Inputs (prompted):** Session export folder; then `y/n` for viewer
**Reads:** `export/tsdf/fused_mesh.ply`, `config.yaml`
**Outputs:** `output/mesh.ply`

---

## Configuration — `config.yaml`

All tunable parameters. Edit this file to change pipeline behaviour without
touching any script.

### `preprocessing` section

| Parameter | Default | Description |
|-----------|---------|-------------|
| `depth_threshold_mm` | `30` | Minimum depth difference (mm) for a pixel to be considered foreground. Lower → stricter (may miss thin regions). Higher → more noise included. |
| `morph_kernel_size` | `5` | Pixel size of the morphological kernel used for open + close operations. Larger = more aggressive noise removal but may erode fine detail. |
| `min_blob_area` | `500` | Connected components smaller than this (pixels) are discarded as noise. |
| `hand_detection_confidence` | `0.7` | MediaPipe minimum confidence to count a detection as a hand. Lower = more sensitive but more false positives. |
| `hand_mask_dilation` | `20` | Extra pixels to dilate around the MediaPipe hand convex hull. Covers wrist and edge pixels MediaPipe may miss. |

### `pointcloud` section

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_depth_mm` | `2000` | Pixels deeper than this (mm) are discarded. Removes far-field noise. |
| `min_depth_mm` | `100` | Pixels closer than this (mm) are discarded. Removes near-field sensor artefacts. |
| `downsample_voxel_m` | `0.003` | Voxel size (metres) for downsampling each per-frame cloud before ICP. Smaller = more points kept, slower ICP. |

### `registration` section

| Parameter | Default | Description |
|-----------|---------|-------------|
| `icp_max_distance_m` | `0.02` | Maximum point-to-point correspondence distance (m). Points farther than this are rejected as non-corresponding. Increase if ICP diverges; decrease for tighter alignment. |
| `icp_relative_fitness` | `1e-6` | ICP stops when fitness improvement between iterations falls below this. |
| `icp_relative_rmse` | `1e-6` | ICP stops when RMSE improvement between iterations falls below this. |
| `icp_max_iterations` | `50` | Hard limit on iterations per frame pair. Increase if alignment is poor. |

### `fusion` section

| Parameter | Default | Description |
|-----------|---------|-------------|
| `tsdf_voxel_size_m` | `0.004` | Size of each voxel (metres) in the TSDF grid. Smaller = finer detail, more memory. `0.002` for small objects; `0.005` if memory is limited. |
| `tsdf_truncation_m` | `0.02` | TSDF truncation distance. Should be 4–8× `tsdf_voxel_size_m`. Controls the surface smoothing radius. |
| `tsdf_volume_size` | `512` | Number of voxels per side of the volume grid. Reduce if running out of memory. |

### `mesh` section

| Parameter | Default | Description |
|-----------|---------|-------------|
| `output_dir` | `output` | Directory where the final mesh is saved (relative to `3dscarn/`). |
| `output_filename` | `mesh.ply` | Filename of the final mesh. |

---

## Data Files

### Files committed to git

| File | Purpose |
|------|---------|
| `*.py` scripts | Pipeline source code |
| `config.yaml` | Pipeline parameters |
| `README.md` | Project overview and user guide |
| `docs/*.md` | Technical documentation |
| `requirements.txt` | Python dependencies |

### Files NOT committed to git (runtime-generated)

| File / Folder | Generated by | Description |
|---------------|-------------|-------------|
| `data/sessions/*/raw/capture.bag` | `capture_bag.py` | Raw recording — large binary, not tracked |
| `data/sessions/*/export/` | `playback.py`, processing scripts | All exported and processed data |
| `output/mesh.ply` | `extract_mesh.py` | Final mesh output |

> `.bag` files and large data folders should be added to `.gitignore`.

---

## Key Data Formats

| Format | Used for | Notes |
|--------|---------|-------|
| `.bag` | Raw RealSense recording | Intel's native format, contains synced RGB + depth + timestamps |
| `.npy` | Depth arrays | `uint16`, values in millimetres, shape `(H, W)` |
| `.png` | Colour frames | BGR order (OpenCV convention) |
| `intrinsics.json` | Camera parameters | `fx, fy, ppx, ppy, width, height, model, coeffs` |
| `.ply` | Point clouds + meshes | Open3D coloured point clouds and triangle meshes |
| `transforms.npy` | ICP pose matrices | Shape `(N, 4, 4)`, float64, one 4×4 rigid transform per frame |

---

## Folder Layout — Full Tree

```
intel_cam/
├── .venv/                          ← Python virtualenv
├── requirements.txt                ← Dependencies
└── 3dscarn/
    ├── run_pipeline.py             ← Pipeline runner (start here)
    ├── cam_test.py                 ← Environment check
    ├── viewer.py                   ← Live preview
    ├── capture_BG.py               ← Background capture
    ├── capture_bag.py              ← Scan recording
    ├── playback.py                 ← Frame export
    ├── preprocess.py               ← Background subtraction + hand removal
    ├── make_pointclouds.py         ← Depth → coloured point clouds
    ├── register.py                 ← ICP alignment
    ├── fuse.py                     ← TSDF fusion
    ├── extract_mesh.py             ← Mesh cleanup + export
    ├── config.yaml                 ← All tuneable parameters
    ├── README.md                   ← Assignment-ready overview
    ├── Claude_todo.md              ← Task tracker
    ├── Claude_log.md               ← Session log
    ├── docs/
    │   ├── PROJECT_OVERVIEW.md     ← Goals, motivation, scope
    │   ├── SYSTEM_ARCHITECTURE.md ← Pipeline design + flowcharts
    │   ├── TECHNICAL_DESIGN.md    ← Algorithms + parameter details
    │   ├── PIPELINE_GUIDE.md      ← Step-by-step operations manual
    │   └── REFERENCE.md           ← This file
    ├── data/
    │   └── sessions/
    │       └── <timestamp>_<name>/
    │           ├── raw/capture.bag
    │           └── export/
    │               ├── color/
    │               ├── depth_npy/
    │               ├── meta/
    │               ├── depth_masked/
    │               ├── pointclouds/
    │               ├── registered/
    │               └── tsdf/
    └── output/
        └── mesh.ply                ← Final result
```