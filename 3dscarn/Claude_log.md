# Claude Log

## 2026-04-06 — Pipeline runner, full docs, assignment README

- Created `run_pipeline.py`: ANSI status dashboard, auto-discovers session folders, prints per-step instructions with session path substituted in, launches each script as subprocess
- Created `docs/PIPELINE_GUIDE.md`: full step-by-step operations manual with inputs/outputs, tuning notes, troubleshooting table, and complete session folder layout
- Created `docs/REFERENCE.md`: complete "what is what" — every script, config param, data format, and folder explained
- Rewrote `README.md` as assignment-submission document: abstract, problem statement, architecture section (depth subtraction, MediaPipe hand removal, unprojection, ICP, TSDF), full project structure, session layout, troubleshooting, docs index

## 2026-04-06 — Built full processing pipeline (Steps 6–10)

- Fixed `capture_BG.py`: removed hardcoded 640×480, now auto-detects resolution from live camera stream and prints it
- Created `config.yaml`: all tuneable parameters (depth threshold, morph kernel, hand mask dilation, ICP, TSDF, output path)
- Created `preprocess.py`: depth subtraction → foreground mask; MediaPipe hand detection → convex hull hand mask with dilation; mask combined and morphologically cleaned; masked depth saved to `export/depth_masked/`; handles bg/depth resolution mismatch with a warning + resize
- Created `make_pointclouds.py`: unprojection using intrinsics.json; attaches BGR→RGB colours to each point; voxel downsamples; saves coloured `.ply` per frame to `export/pointclouds/`
- Created `register.py`: frame-to-frame point-to-plane ICP with cumulative transform accumulation; saves registered clouds to `export/registered/` and `transforms.npy`
- Created `fuse.py`: Open3D ScalableTSDFVolume integration of all registered coloured RGBD frames; saves `export/tsdf/fused_mesh.ply`
- Created `extract_mesh.py`: largest cluster filter, Laplacian smoothing (5 iter), saves to `output/mesh.ply`; optional viewer
- Updated `requirements.txt`: added `pyyaml>=6.0` and `mediapipe>=0.10.0`
- Two new deps not yet installed in .venv: `pyyaml` and `mediapipe` — user must run `pip install pyyaml mediapipe`

## 2026-03-27 — Initial session: codebase read, docs formatted, companion files created

- Read all scripts in `3dscarn/`: `viewer.py`, `capture_bag.py`, `capture_BG.py`, `playback.py`, `cam_test.py`
- Read `MV/red_depth.py` — confirmed fully independent from 3dscarn
- Read all three docs in `docs/` — all were raw unformatted text
- Reformatted `docs/PROJECT_OVERVIEW.md` — added `#` headings, tables, bullet lists, scope section
- Reformatted `docs/SYSTEM_ARCHITECTURE.md` — added headings, ASCII pipeline flowchart, formula code blocks, module table
- Reformatted `docs/TECHNICAL_DESIGN.md` — added hardware table, software stack table, algorithm details with code blocks, parameter tuning table, challenges table
- Created `Claude_todo.md` with completed tasks and the remaining pipeline stages as Not Started
- Created `Claude_log.md` (this file)
- Saved project memories to `.claude/` memory system

**Pipeline status understood:** Capture, background capture, and frame export are done. Everything from background subtraction onward is not yet built.