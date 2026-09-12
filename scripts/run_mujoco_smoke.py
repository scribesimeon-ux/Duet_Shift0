"""Run headless physics, with separately bounded optional graphics checks."""

import argparse
from pathlib import Path
import subprocess
import sys
import time

import mujoco

from duetshift.sim.mujoco_smoke import SmokeSimulation, validate_physics


def render_check():
    sim = SmokeSimulation()
    frame = sim.render_rgb()
    if frame.shape != (120, 160, 3) or str(frame.dtype) != "uint8" or frame.max() == frame.min():
        raise RuntimeError(f"Unexpected RGB frame: shape={frame.shape}, dtype={frame.dtype}")
    print(f"OFFSCREEN PASS: shape={frame.shape}, dtype={frame.dtype}, range={frame.min()}..{frame.max()}")


def viewer_check():
    import mujoco.viewer

    sim = SmokeSimulation()
    frames = 0
    with mujoco.viewer.launch_passive(sim.model, sim.data) as viewer:
        if not viewer.is_running():
            raise RuntimeError("Viewer did not open")
        with viewer.lock():
            viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
            viewer.cam.fixedcamid = sim.model.camera("smoke_camera").id
        viewer.sync()
        print("Viewer opened; close the window to exit, or wait for the 8-second limit.", flush=True)
        start = time.monotonic()
        while viewer.is_running() and time.monotonic() - start < 8:
            tick = time.monotonic()
            with viewer.lock():
                sim.step(5)
            viewer.sync()
            frames += 1
            time.sleep(max(0, 5 * sim.model.opt.timestep - (time.monotonic() - tick)))
    print(f"VIEWER PASS: closed cleanly after {frames} updates.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--viewer", action="store_true", help="Open the official viewer for up to 8 seconds")
    parser.add_argument("--render", action="store_true", help="Attempt one 160x120 offscreen RGB frame")
    parser.add_argument("--graphics-worker", choices=("viewer", "render"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.graphics_worker:
        try:
            (viewer_check if args.graphics_worker == "viewer" else render_check)()
        except Exception as exc:
            print(f"{args.graphics_worker.upper()} FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        return 0

    try:
        sim = SmokeSimulation()
        print(f"MuJoCo version: {mujoco.__version__}")
        print(f"Model timestep: {sim.model.opt.timestep:.3f} seconds")
        print(f"Initial object position: {sim.position}")
        result = validate_physics(sim)
        print(f"Free-fall position at 0.1 seconds: {result.early_position}")
        print(f"Final simulation time: {result.final_time:.3f} seconds")
        print(f"Final object position: {result.final_position}")
        for label, passed in result.checks:
            print(f"{'PASS' if passed else 'FAIL'}: {label}")
        print(f"PHYSICS {'PASS' if result.passed else 'FAIL'}")
        if not result.passed:
            return 1
    except Exception as exc:
        print(f"PHYSICS FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    sys.stdout.flush()
    for mode, enabled in (("render", args.render), ("viewer", args.viewer)):
        if not enabled:
            continue
        try:
            process = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--graphics-worker", mode],
                timeout=20,
            )
            if process.returncode:
                print(f"{mode.upper()} WARNING: graphics process exited {process.returncode}; physics passed.")
        except subprocess.TimeoutExpired:
            print(f"{mode.upper()} WARNING: graphics process exceeded 20 seconds and was terminated; physics passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
