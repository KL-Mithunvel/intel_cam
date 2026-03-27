# Claude TODO

## In Progress

_(none)_

## Done

- [x] Read all existing scripts and understand pipeline — 2026-03-27
- [x] Format docs/PROJECT_OVERVIEW.md as proper markdown — 2026-03-27
- [x] Format docs/SYSTEM_ARCHITECTURE.md as proper markdown — 2026-03-27
- [x] Format docs/TECHNICAL_DESIGN.md as proper markdown — 2026-03-27
- [x] Create Claude_todo.md and Claude_log.md companion files — 2026-03-27

## Not Started

- [ ] Background subtraction script (apply `bg_depth.npy` to exported frames, produce masked depth)
- [ ] Point cloud generation script (unproject masked depth → `.ply` point clouds per frame)
- [ ] ICP registration script (align all per-frame point clouds to a common frame)
- [ ] TSDF fusion script (integrate registered point clouds into a volume)
- [ ] Mesh extraction and export script (Marching Cubes → `.ply`/`.obj`)
- [ ] `tests/` directory and pytest suite for preprocessing logic (dev-machine testable)
- [ ] `config.yaml` for all tuneable parameters (thresholds, voxel size, etc.)