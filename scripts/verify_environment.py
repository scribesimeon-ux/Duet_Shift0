"""Report the Stage 2 interpreter and reject unsupported Python versions."""

import importlib.util
from pathlib import Path
import platform
import sys


def main():
    print(f"Python version: {platform.python_version()}")
    print(f"Python executable: {sys.executable}")
    print(f"Operating system: {platform.system()} {platform.release()}")
    print(f"Platform: {platform.platform()}")
    print(f"Machine architecture: {platform.machine()}")
    supported = sys.version_info[:2] == (3, 12)
    print(f"Python is 3.12: {'YES' if supported else 'NO'}")

    prefix = Path(sys.prefix)
    appears_correct = (
        prefix.name.casefold() == "duetshift-dev"
        and (prefix / "conda-meta").is_dir()
        and Path(sys.executable).resolve().is_relative_to(prefix.resolve())
    )
    print(
        "Appears inside duetshift-dev: "
        + ("YES" if appears_correct else "NOT CONFIRMED (check activation)")
    )
    mujoco_present = importlib.util.find_spec("mujoco") is not None
    print(f"MuJoCo: {'INSTALLED (required for Stage 3)' if mujoco_present else 'NOT INSTALLED (required for Stage 3)'}")
    for label, module in (
        ("OpenVINO", "openvino"),
        ("LeRobot", "lerobot"),
        ("PyTorch", "torch"),
        ("Speechmatics", "speechmatics"),
    ):
        found = importlib.util.find_spec(module) is not None
        print(f"{label}: {'PRESENT (not imported or tested)' if found else 'NOT INSTALLED (expected)'}")

    if not supported:
        print(
            "ERROR: Stage 2 requires Python 3.12. Run conda activate duetshift-dev.",
            file=sys.stderr,
        )
        return 1
    if not mujoco_present:
        print('ERROR: Install the project dependencies with python -m pip install -e ".[dev]".', file=sys.stderr)
        return 1
    print("PASS: Python version and Stage 3 MuJoCo availability requirements satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
