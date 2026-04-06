# Claude TODO

## In Progress

_(none)_

## Done

- [x] Read all existing scripts and understand pipeline — 2026-03-27
- [x] Format docs/PROJECT_OVERVIEW.md as proper markdown — 2026-03-27
- [x] Format docs/SYSTEM_ARCHITECTURE.md as proper markdown — 2026-03-27
- [x] Format docs/TECHNICAL_DESIGN.md as proper markdown — 2026-03-27
- [x] Create Claude_todo.md and Claude_log.md companion files — 2026-03-27
- [x] Fix capture_BG.py — auto-detect camera resolution instead of hardcoding 640×480 — 2026-04-06
- [x] Create config.yaml — all tuneable parameters (thresholds, voxel size, ICP, TSDF) — 2026-04-06
- [x] Create preprocess.py — depth subtraction + MediaPipe hand removal → masked depth per frame — 2026-04-06
- [x] Create make_pointclouds.py — unproject masked depth + attach RGB → coloured .ply per frame — 2026-04-06
- [x] Create register.py — frame-to-frame ICP → registered point clouds + transforms.npy — 2026-04-06
- [x] Create fuse.py — TSDF integration of registered coloured clouds → fused_mesh.ply — 2026-04-06
- [x] Create extract_mesh.py — cluster filter + Laplacian smooth → output/mesh.ply — 2026-04-06
- [x] Update requirements.txt with pyyaml and mediapipe — 2026-04-06

## Not Started

- [ ] `tests/` directory and pytest suite for preprocessing logic (dev-machine testable)
- [ ] Install missing dependencies: `pip install pyyaml mediapipe` inside .venv
- [x] Create run_pipeline.py — interactive status + runner for all 10 steps — 2026-04-06
- [x] Create docs/PIPELINE_GUIDE.md — step-by-step operations manual — 2026-04-06
- [x] Create docs/REFERENCE.md — complete script/file/config reference — 2026-04-06
- [x] Rewrite README.md as assignment-submission document — 2026-04-06