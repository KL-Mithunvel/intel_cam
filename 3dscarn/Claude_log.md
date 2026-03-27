# Claude Log

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