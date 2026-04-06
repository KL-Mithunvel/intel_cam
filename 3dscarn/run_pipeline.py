"""
run_pipeline.py

Interactive pipeline runner for 3dscarn.
Shows the current status of each stage, prints instructions before each step,
then launches the script. Use this as your single entry point for the pipeline.
"""

import os
import sys
import subprocess
import textwrap


# ---------------------------------------------------------------------------
# Colours (works on Windows 10+ terminal and any ANSI terminal)
# ---------------------------------------------------------------------------
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    DIM    = "\033[2m"


def bold(s):   return f"{C.BOLD}{s}{C.RESET}"
def green(s):  return f"{C.GREEN}{s}{C.RESET}"
def yellow(s): return f"{C.YELLOW}{s}{C.RESET}"
def red(s):    return f"{C.RED}{s}{C.RESET}"
def cyan(s):   return f"{C.CYAN}{s}{C.RESET}"
def dim(s):    return f"{C.DIM}{s}{C.RESET}"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
session_export_dir = None   # set when user picks a session


def get_session_export_dir() -> str | None:
    return session_export_dir


def set_session_export_dir(path: str):
    global session_export_dir
    session_export_dir = path


# ---------------------------------------------------------------------------
# Status checks
# Each check returns True if the step's expected output exists.
# ---------------------------------------------------------------------------

def check_cam_test() -> bool:
    """cam_test.py has no file output — assume OK if camera scripts exist."""
    return os.path.isfile(os.path.join(SCRIPT_DIR, "cam_test.py"))


def check_viewer() -> bool:
    """viewer.py has no file output — always mark as runnable."""
    return True


def check_capture_bg() -> bool:
    if not session_export_dir:
        return False
    return os.path.isfile(os.path.join(session_export_dir, "meta", "bg_depth.npy"))


def check_capture_bag() -> bool:
    """Check if any session raw .bag exists."""
    sessions_dir = os.path.join(SCRIPT_DIR, "data", "sessions")
    if not os.path.isdir(sessions_dir):
        return False
    for entry in os.listdir(sessions_dir):
        bag = os.path.join(sessions_dir, entry, "raw", "capture.bag")
        if os.path.isfile(bag):
            return True
    return False


def check_playback() -> bool:
    if not session_export_dir:
        return False
    color_dir = os.path.join(session_export_dir, "color")
    if not os.path.isdir(color_dir):
        return False
    return len([f for f in os.listdir(color_dir) if f.endswith(".png")]) > 0


def check_preprocess() -> bool:
    if not session_export_dir:
        return False
    masked_dir = os.path.join(session_export_dir, "depth_masked")
    if not os.path.isdir(masked_dir):
        return False
    return len([f for f in os.listdir(masked_dir) if f.endswith(".npy")]) > 0


def check_pointclouds() -> bool:
    if not session_export_dir:
        return False
    pc_dir = os.path.join(session_export_dir, "pointclouds")
    if not os.path.isdir(pc_dir):
        return False
    return len([f for f in os.listdir(pc_dir) if f.endswith(".ply")]) > 0


def check_register() -> bool:
    if not session_export_dir:
        return False
    return os.path.isfile(os.path.join(session_export_dir, "registered", "transforms.npy"))


def check_fuse() -> bool:
    if not session_export_dir:
        return False
    return os.path.isfile(os.path.join(session_export_dir, "tsdf", "fused_mesh.ply"))


def check_extract_mesh() -> bool:
    output_path = os.path.join(SCRIPT_DIR, "output", "mesh.ply")
    return os.path.isfile(output_path)


# ---------------------------------------------------------------------------
# Pipeline step definitions
# ---------------------------------------------------------------------------

STEPS = [
    {
        "num":    1,
        "name":   "Environment check",
        "script": "cam_test.py",
        "check":  check_cam_test,
        "needs_session": False,
        "instructions": """
            Verifies all required Python libraries are installed.
            Run this first on any new machine.

            No prompts — just watch the output.
            All libraries should print OK.
        """,
    },
    {
        "num":    2,
        "name":   "Live camera preview",
        "script": "viewer.py",
        "check":  check_viewer,
        "needs_session": False,
        "instructions": """
            Opens 3 live windows: Color / Depth / Overlay.
            Use this to check your scene before scanning.

            Press  q  to close and return here.
        """,
    },
    {
        "num":    3,
        "name":   "Capture background reference",
        "script": "capture_BG.py",
        "check":  check_capture_bg,
        "needs_session": True,
        "instructions": """
            BEFORE RUNNING:
              - Remove the object from the scene
              - Keep the camera exactly where it will be during the scan
              - Lighting must match what it will be during scanning

            When prompted for output folder, enter:
              {export_dir}\\meta

            Wait for 30 frames to capture (takes ~3 seconds).
            Do NOT move the camera after this step.
        """,
    },
    {
        "num":    4,
        "name":   "Record scan session (.bag)",
        "script": "capture_bag.py",
        "check":  check_capture_bag,
        "needs_session": False,
        "instructions": """
            Place the object back in the scene.

            When prompted for a session name, type a short label
            e.g.  mug   shoe   bolt   test1

            During recording:
              - Keep the camera completely still
              - Slowly rotate the object to show all sides
              - Try to cover top, bottom, and all side angles
              - Keep your hand as consistent in position as possible

            Press  q  to stop recording.

            NOTE the session folder path printed to console —
            you will need it in Step 5 onwards.
        """,
    },
    {
        "num":    5,
        "name":   "Export frames from recording",
        "script": "playback.py",
        "check":  check_playback,
        "needs_session": True,
        "instructions": """
            When prompted, enter the full path to the .bag file, e.g.:
              data\\sessions\\2026-04-06_12-00-00_mug\\raw\\capture.bag

            This exports:
              color/       — per-frame RGB images
              depth_npy/   — per-frame depth arrays
              meta/        — intrinsics.json + frame_timestamps.csv
        """,
    },
    {
        "num":    6,
        "name":   "Preprocess — background subtraction + hand removal",
        "script": "preprocess.py",
        "check":  check_preprocess,
        "needs_session": True,
        "instructions": """
            Removes background and hand from every depth frame.
            Hand detection uses MediaPipe — ensure mediapipe is installed.

            When prompted for export folder, enter:
              {export_dir}

            Output: export/depth_masked/  — one .npy per frame, hand+background zeroed.

            If you see a resolution warning, ignore it — it is handled automatically.
        """,
    },
    {
        "num":    7,
        "name":   "Generate point clouds",
        "script": "make_pointclouds.py",
        "check":  check_pointclouds,
        "needs_session": True,
        "instructions": """
            Converts each masked depth frame into a coloured 3D point cloud.

            When prompted for export folder, enter:
              {export_dir}

            Output: export/pointclouds/  — one .ply per frame with XYZ + RGB.
            Each cloud is voxel-downsampled for faster ICP in the next step.
        """,
    },
    {
        "num":    8,
        "name":   "ICP registration",
        "script": "register.py",
        "check":  check_register,
        "needs_session": True,
        "instructions": """
            Aligns all per-frame point clouds into a single coordinate frame
            using Iterative Closest Point (ICP).

            When prompted for export folder, enter:
              {export_dir}

            Output:
              export/registered/        — transformed clouds
              export/registered/transforms.npy  — 4x4 pose matrix per frame

            This step can take several minutes depending on frame count.
            Watch the fitness score — values close to 1.0 mean good alignment.
        """,
    },
    {
        "num":    9,
        "name":   "TSDF fusion",
        "script": "fuse.py",
        "check":  check_fuse,
        "needs_session": True,
        "instructions": """
            Fuses all registered coloured frames into a smooth volumetric mesh
            using the Truncated Signed Distance Function (TSDF).

            When prompted for export folder, enter:
              {export_dir}

            Output: export/tsdf/fused_mesh.ply

            If the mesh looks noisy, reduce tsdf_voxel_size_m in config.yaml
            (e.g. 0.002 for finer detail, uses more memory).
        """,
    },
    {
        "num":    10,
        "name":   "Extract and clean final mesh",
        "script": "extract_mesh.py",
        "check":  check_extract_mesh,
        "needs_session": True,
        "instructions": """
            Cleans the fused mesh:
              - Removes disconnected fragments (keeps only the largest piece)
              - Laplacian smoothing (5 iterations)
              - Saves to output/mesh.ply

            When prompted for export folder, enter:
              {export_dir}

            At the end you will be asked if you want to open the mesh viewer.
            Type  y  to preview the result.
        """,
    },
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def status_icon(done: bool) -> str:
    return green("[DONE]") if done else yellow("[    ]")


def print_header():
    print(bold(cyan("=" * 60)))
    print(bold(cyan("   3dscarn — 3D Reconstruction Pipeline Runner")))
    print(bold(cyan("=" * 60)))
    if session_export_dir:
        print(dim(f"   Session: {session_export_dir}"))
    else:
        print(yellow("   Session: not set  (choose option S below)"))
    print()


def print_pipeline_status():
    print(bold("  Pipeline steps:"))
    print()
    for step in STEPS:
        done = step["check"]()
        icon = status_icon(done)
        print(f"  {icon}  {step['num']:>2}.  {step['name']}")
    print()


def set_session():
    """Let the user type or pick their session export directory."""
    print(bold("\n  Set session export directory"))
    print(dim("  This is the 'export' folder inside a session, e.g.:"))
    print(dim("  data\\sessions\\2026-04-06_12-00-00_mug\\export\n"))

    # Auto-discover sessions
    sessions_root = os.path.join(SCRIPT_DIR, "data", "sessions")
    candidates = []
    if os.path.isdir(sessions_root):
        for entry in sorted(os.listdir(sessions_root)):
            export_path = os.path.join(sessions_root, entry, "export")
            if os.path.isdir(export_path):
                candidates.append(export_path)

    if candidates:
        print("  Found sessions:")
        for i, path in enumerate(candidates, 1):
            print(f"    {i}. {path}")
        print()
        choice = input("  Enter number to select, or type a custom path: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            set_session_export_dir(candidates[int(choice) - 1])
        elif choice:
            set_session_export_dir(choice)
    else:
        path = input("  Enter path to session export folder: ").strip()
        if path:
            set_session_export_dir(path)

    print(green(f"\n  Session set to: {session_export_dir}"))
    input("  Press Enter to continue...")


def run_step(step: dict):
    """Print instructions and launch the script."""
    clear()
    print_header()
    print(bold(f"  Step {step['num']}: {step['name']}"))
    print(bold("  " + "-" * 50))

    # Format instructions with session path substituted in
    export_dir = session_export_dir or "<session_export_dir>"
    raw_instructions = textwrap.dedent(step["instructions"]).strip()
    instructions = raw_instructions.replace("{export_dir}", export_dir)

    for line in instructions.splitlines():
        print(f"  {line}")

    print()
    confirm = input(bold("  Run this step now? [y/n]: ")).strip().lower()
    if confirm != "y":
        print(yellow("  Skipped."))
        input("  Press Enter to return to menu...")
        return

    print()
    print(dim("  " + "-" * 50))
    script_path = os.path.join(SCRIPT_DIR, step["script"])
    result = subprocess.run([sys.executable, script_path])
    print(dim("  " + "-" * 50))

    if result.returncode == 0:
        print(green("\n  Step completed successfully."))
    else:
        print(red(f"\n  Script exited with code {result.returncode}. Check output above."))

    input("  Press Enter to return to menu...")


def main():
    while True:
        clear()
        print_header()
        print_pipeline_status()

        print(bold("  Options:"))
        print("   1-10  Run a pipeline step")
        print("      S  Set / change session folder")
        print("      Q  Quit")
        print()

        choice = input(bold("  Enter choice: ")).strip().upper()

        if choice == "Q":
            print("\n  Goodbye.\n")
            break
        elif choice == "S":
            set_session()
        elif choice.isdigit() and 1 <= int(choice) <= len(STEPS):
            step = STEPS[int(choice) - 1]
            if step["needs_session"] and not session_export_dir:
                print(yellow("\n  This step needs a session set first.  Choose S first."))
                input("  Press Enter to continue...")
            else:
                run_step(step)
        else:
            print(red("  Invalid choice."))
            input("  Press Enter to continue...")


if __name__ == "__main__":
    main()