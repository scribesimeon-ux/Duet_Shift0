"""Inspect one authentic SO-101 and validate a short constant-rest hold."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

import mujoco

from duetshift.sim.so101_model import (
    SOURCE_REPOSITORY, SOURCE_COMMIT, SOURCE_FILE,
    load_so101, print_arm, contact_report, validate_idle,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--viewer", action="store_true", help="Open a viewer for up to 8 seconds")
    parser.add_argument("--viewer-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        model, data, arm = load_so101()
        if args.viewer_worker:
            from duetshift.sim.so101_viewer import show_model
            show_model(model, data)
            return 0
        print(f"MuJoCo: {mujoco.__version__}")
        print(f"Source: {SOURCE_REPOSITORY}@{SOURCE_COMMIT} / {SOURCE_FILE}")
        print(f"Timestep: {model.opt.timestep} s; gravity: {model.opt.gravity}")
        print_arm(arm)
        print(f"Initial qpos(rad): {data.qpos}; fixed targets(rad): {data.ctrl}")
        initial = contact_report(model, data)
        print(f"Initial contacts: {initial}")
        result = validate_idle(model, data)
        print(json.dumps(result, indent=2))
        if initial or not result["passed"]:
            print("SINGLE SO-101 FAIL")
            return 1
        print("SINGLE SO-101 PASS", flush=True)
        if args.viewer:
            try:
                worker = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--viewer-worker"], timeout=25)
                if worker.returncode:
                    print(f"VIEWER FAIL: exit code {worker.returncode}; single physics passed.")
                    return 2
            except subprocess.TimeoutExpired:
                print("VIEWER FAIL: exceeded 25 seconds and terminated; single physics passed.")
                return 2
    except Exception as exc:
        print(f"SO-101 FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
