"""Inspect two independently named SO-101 arms without task control."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

import mujoco
import numpy as np

from duetshift.sim.dual_so101_scene import load_dual_so101
from duetshift.sim.so101_model import SOURCE_COMMIT, print_arm, contact_report, validate_idle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--viewer", action="store_true", help="Show both arms for up to 8 seconds")
    parser.add_argument("--viewer-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        scene = load_dual_so101()
        if args.viewer_worker:
            from duetshift.sim.so101_viewer import show_model
            show_model(scene.model, scene.data)
            return 0
        print(f"MuJoCo: {mujoco.__version__}; TheRobotStudio SO-ARM100 commit: {SOURCE_COMMIT}")
        for arm in (scene.arm_a, scene.arm_b):
            print_arm(arm)
            print(f"Base world position: {scene.data.body(arm.base).xpos}")
        separation = float(np.linalg.norm(
            scene.data.body(scene.arm_a.base).xpos - scene.data.body(scene.arm_b.base).xpos
        ))
        initial = contact_report(scene.model, scene.data)
        inter = scene.inter_arm_contacts()
        print(f"Base separation: {separation:.3f} m; initial contacts: {initial}; inter-arm contacts: {inter}")
        result = validate_idle(scene.model, scene.data)
        print(json.dumps(result, indent=2))
        if separation < 0.4 or initial or inter or not result["passed"]:
            print("DUAL SO-101 FAIL")
            return 1
        print("DUAL SO-101 PASS", flush=True)
        if args.viewer:
            try:
                worker = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--viewer-worker"], timeout=25)
                if worker.returncode:
                    print(f"VIEWER FAIL: exit code {worker.returncode}; dual physics passed.")
                    return 2
            except subprocess.TimeoutExpired:
                print("VIEWER FAIL: exceeded 25 seconds and terminated; dual physics passed.")
                return 2
    except Exception as exc:
        print(f"DUAL SO-101 FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
