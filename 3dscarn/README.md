# 3dscarn — 3D Object Reconstruction with Intel RealSense

A Python pipeline for reconstructing 3D meshes of physical objects using an Intel RealSense RGB-D camera. The camera is stationary; the object is rotated manually. Background and hand interference are removed via depth subtraction.

---

## Hardware Required

- Intel RealSense depth camera (D4xx series)
- USB 3.0 port
- Object to scan (ideally matte, non-reflective surface)

---

## Software Requirements

| Package | Purpose |
|---------|---------|
| `pyrealsense2` | Intel RealSense SDK — camera streaming, recording, playback |
| `opencv-python` | Image processing, display, morphological operations |
| `open3d` | Point cloud processing, ICP registration, TSDF fusion, mesh extraction |
| `numpy` | Array operations, depth math |

Install:

```bash
pip install pyrealsense2 opencv-python open3d numpy
```

> Always activate your virtualenv first:
> ```bash
> # Windows
> venv\Scripts\activate
> ```

---

## Project Structure

```
3dscarn/
├── viewer.py          # Live camera preview
├── capture_bag.py     # Record a scan session to .bag
├── capture_BG.py      # Capture background depth reference
├── playback.py        # Export frames from a recorded .bag
├── cam_test.py        # Environment / dependency check
├── README.md          # This file
├── CLAUDE.md          # Rules for AI-assisted development sessions
├── Claude_todo.md     # Task tracker
├── Claude_log.md      # Session log
├── docs/
│   ├── PROJECT_OVERVIEW.md    # Goals, motivation, scope
│   ├── SYSTEM_ARCHITECTURE.md # Pipeline design and flowcharts
│   └── TECHNICAL_DESIGN.md    # Algorithms, parameters, file layout
└── data/
    └── sessions/
        └── <YYYY-MM-DD_HH-MM-SS>_<name>/
            ├── raw/
            │   └── capture.bag
            └── export/
                ├── color/          ← per-frame RGB PNGs
                ├── depth_npy/      ← per-frame depth arrays (.npy)
                └── meta/
                    ├── intrinsics.json
                    ├── frame_timestamps.csv
                    └── bg_depth.npy
```

---

## Scripts — What Each One Does

### `cam_test.py` — Environment Check

Verifies that all required libraries (`pyrealsense2`, `open3d`, `cv2`) are installed and importable.

**Run this first on any new machine before anything else.**

```bash
python cam_test.py
```

---

### `viewer.py` — Live Camera Preview

Opens three OpenCV windows showing the live camera feed:

| Window | Content |
|--------|---------|
| `Color Stream` | Raw RGB image |
| `Depth Stream` | Depth frame colourised with JET colourmap |
| `Overlay` | Weighted blend of colour + depth (50/50) |

Depth and colour are aligned so pixels correspond spatially.

Press `q` to quit.

```bash
python viewer.py
```

**Use this to:**
- Verify the camera is connected and working
- Check your scene setup and lighting before a scan
- Confirm the object is within the camera's depth range

---

### `capture_BG.py` — Capture Background Reference

Records an empty scene (no object, no hand) and computes the median depth across 30 frames. Saves the result as `bg_depth.npy`.

```bash
python capture_BG.py
```

You will be prompted for an output folder path — enter the `meta/` folder of your session, or any directory you choose.

**This must be run before every scan session.** The object and hand are identified by comparing scan frames against this reference. If the background changes (you move the camera, or something in the scene shifts), recapture it.

**Output:** `bg_depth.npy` — a `(H, W)` float array of background depth in millimetres.

---

### `capture_bag.py` — Record a Scan Session

Records live RGB + depth frames to a `.bag` file. Creates a timestamped session folder automatically.

```bash
python capture_bag.py
```

You will be prompted for a session name (e.g. `mug`, `shoe`, `test1`). The recording saves to:

```
data/sessions/<YYYY-MM-DD_HH-MM-SS>_<name>/raw/capture.bag
```

Press `q` to stop recording.

**During recording:**
- Keep the camera stationary
- Rotate the object slowly and steadily
- Try to cover all sides — top, bottom, and sides
- Keep your hand as consistent in depth as possible (it will be subtracted later)

**Output:** `.bag` file — RealSense's native format containing synchronised RGB + depth streams.

---

### `playback.py` — Export Frames from Recording

Reads a `.bag` file and exports every frame as individual files for offline processing.

```bash
python playback.py
```

You will be prompted for the path to the `.bag` file.

**Exports to the session's `export/` folder:**

| Output | Format | Description |
|--------|--------|-------------|
| `export/color/000000.png` ... | PNG | Per-frame colour images |
| `export/depth_npy/000000.npy` ... | NumPy `.npy` | Per-frame depth arrays (mm, uint16) |
| `export/meta/intrinsics.json` | JSON | Camera intrinsic parameters |
| `export/meta/frame_timestamps.csv` | CSV | Timestamp of every exported frame |

**Intrinsics JSON format:**
```json
{
  "fx": 907.475,
  "fy": 907.370,
  "ppx": 649.217,
  "ppy": 377.003,
  "width": 1280,
  "height": 720,
  "model": "inverse_brown_conrady",
  "coeffs": [0, 0, 0, 0, 0]
}
```

These parameters are needed to unproject depth pixels into 3D points.

---

## User Manual — Full Scan Workflow

Follow these steps in order for every scan session.

### Step 1 — Check the environment

```bash
python cam_test.py
```

Confirm all imports pass before proceeding.

---

### Step 2 — Preview the scene

```bash
python viewer.py
```

- Place the camera and object
- Check depth range — the object should appear clearly in the depth window
- Confirm stable lighting
- Press `q` when satisfied

---

### Step 3 — Capture the background

Remove the object. Leave the scene exactly as it will look during the scan (same camera position, same surface, same lighting).

```bash
python capture_BG.py
```

- Enter the output path when prompted (e.g. `data/sessions/my_session/export/meta`)
- Wait for 30 frames to be captured (a few seconds)
- Confirm `bg_depth.npy` is saved

> **Do not move the camera after this step.**

---

### Step 4 — Record the scan

Place the object back in the scene.

```bash
python capture_bag.py
```

- Enter a session name (e.g. `mug`)
- Note the session folder path printed to console
- Slowly rotate the object by hand, covering all sides
- Press `q` when done

---

### Step 5 — Export frames

```bash
python playback.py
```

- Enter the path to the `.bag` file from Step 4
- Wait for all frames to export
- Confirm `color/`, `depth_npy/`, and `meta/` folders are populated

---

### Steps 6–10 — Processing pipeline

> **These scripts are not yet built.** They will be added to this section as development progresses.

| Step | Script | What it will do |
|------|--------|----------------|
| 6 | `preprocess.py` | Load `bg_depth.npy` + depth frames → subtract background → apply threshold + morphology → masked depth per frame |
| 7 | `make_pointclouds.py` | Unproject masked depth using `intrinsics.json` → one `.ply` point cloud per frame |
| 8 | `register.py` | ICP — align all per-frame clouds into a single coordinate frame |
| 9 | `fuse.py` | TSDF — integrate registered clouds into a volumetric grid |
| 10 | `extract_mesh.py` | Marching Cubes → `output/mesh.ply` |

---

## Key Concepts

### Why depth subtraction?

The camera captures everything in the scene — background, table, and your hand. By capturing an empty scene first (`capture_BG.py`), you get a reference. During processing, any pixel whose depth differs from the reference by more than a threshold is considered foreground (object or hand). This cleanly removes the static background.

### Why `.bag` files?

`.bag` is Intel RealSense's native recording format. It stores synchronised RGB and depth streams with timestamps and camera metadata, so you can replay the exact frames offline without the camera connected.

### Why per-frame `.npy` files?

NumPy arrays are the most convenient format for numerical processing. They load directly into Python with `np.load()` and preserve the exact `uint16` depth values without any compression artefacts.

### Why save intrinsics?

The camera's intrinsic parameters (`fx`, `fy`, `ppx`, `ppy`) are needed to convert a 2D depth pixel into a 3D point. Without them, you cannot unproject depth frames correctly. They are saved once from the recording and reused for every frame in the session.

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| `No module named 'pyrealsense2'` | Library not installed or venv not active | `pip install pyrealsense2` inside the venv |
| Camera not detected | USB 2.0 port, or driver issue | Use USB 3.0; reinstall Intel RealSense SDK |
| Depth window is all black | Object too far or too close | Move object to 0.3–1.5 m from camera |
| `.bag` file is very large | Long recording or high resolution | Keep sessions under 2 minutes; use 640×480 |
| Exported frame count is 0 | Wrong `.bag` path, or corrupted file | Check path; re-record if needed |