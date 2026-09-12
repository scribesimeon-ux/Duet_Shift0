"""Check Stage 06 reachability; optional previews show a static IK endpoint, not motion."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
import zlib

import mujoco
import numpy as np

from duetshift.sim.challenge_scene import load_challenge_scene
from duetshift.sim.reachability import (
    TaskTarget, ReachabilitySolver, ReachabilityStatus, end_effector_state,
)

SEMANTIC_TARGETS = ("table", "plate", "mug", "bottle", "fork", "spoon", "drawer_handle")


def add_marker(render_scene, position):
    if render_scene.ngeom >= render_scene.maxgeom:
        raise RuntimeError("no room for target marker")
    mujoco.mjv_initGeom(render_scene.geoms[render_scene.ngeom], mujoco.mjtGeom.mjGEOM_SPHERE,
                       np.array([.008, .008, .008]), np.array(position), np.eye(3).ravel(),
                       np.array([1., .1, .7, .65], dtype=np.float32))
    render_scene.ngeom += 1


def preview(scene, solver, result, mode, seconds, save_image):
    data = solver.preview_data(scene, result)
    if mode == "viewer":
        from mujoco import viewer as mujoco_viewer
        with mujoco_viewer.launch_passive(scene.model, data) as viewer:
            with viewer.lock():
                viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
                viewer.cam.fixedcamid = scene.cameras["overview"].camera_id
                add_marker(viewer.user_scn, result.target.position)
            end = time.monotonic() + seconds
            while viewer.is_running() and time.monotonic() < end:
                viewer.sync()
                time.sleep(.02)
        print("VIEWER PASS: bounded static endpoint preview closed; no trajectory was executed.")
    else:
        with mujoco.Renderer(scene.model, height=480, width=640) as renderer:
            renderer.update_scene(data, camera="overview")
            add_marker(renderer.scene, result.target.position)
            rgb = renderer.render().copy()
        if rgb.shape != (480, 640, 3) or rgb.dtype != np.uint8 or rgb.std() < 2:
            raise RuntimeError("invalid preview RGB")
        print("RENDER PASS: 640x480 uint8 RGB static endpoint and pink target marker.")
        if save_image:
            directory = Path(__file__).resolve().parents[1] / "tmp" / "reachability"
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"seed_{scene.seed}_{result.arm}.png"
            def chunk(kind, payload):
                return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
            pixels = b"".join(b"\x00" + row.tobytes() for row in rgb)
            path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 640, 480, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))
            print(f"Inspection image: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--arm", choices=("arm_a", "arm_b"))
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument("--target", choices=SEMANTIC_TARGETS)
    targets.add_argument("--position", nargs=3, type=float, metavar=("X", "Y", "Z"))
    parser.add_argument("--all", action="store_true", help="Check all seven semantic targets with both arms")
    parser.add_argument("--viewer", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--save-image", action="store_true", help="Save static preview under ignored tmp/reachability")
    parser.add_argument("--viewer-seconds", type=float, default=8)
    parser.add_argument("--worker", choices=("viewer", "render"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.viewer_seconds <= 300:
        parser.error("viewer duration must be 1-300 seconds")
    if args.all and any((args.arm, args.target, args.position, args.viewer, args.render, args.save_image, args.worker)):
        parser.error("--all is a headless matrix check; use a single target for previews")
    try:
        scene, solver = load_challenge_scene(args.seed), ReachabilitySolver()
        physics = scene.validate_stability()
        if not physics["passed"]:
            raise RuntimeError(f"Stage 05 baseline physics failed: {physics}")
        if args.all:
            results = [solver.solve(scene, solver.approach_target(scene, name, arm))
                       for arm in ("arm_a", "arm_b") for name in SEMANTIC_TARGETS]
            for result in results:
                print(json.dumps(asdict(result)))
            # Coverage is an explicit validation objective, not a claim that every arm reaches every object.
            covered = all(any(r.reachable and r.target.name == name + "_approach" for r in results) for name in SEMANTIC_TARGETS)
            both_arms = all(any(r.reachable and r.arm == arm for r in results) for arm in ("arm_a", "arm_b"))
            clean = all(r.status in (ReachabilityStatus.REACHABLE, ReachabilityStatus.IK_FAILED, ReachabilityStatus.COLLISION) for r in results)
            passed = covered and both_arms and clean
            print(f"SEMANTIC COVERAGE {'PASS' if passed else 'FAIL'}: each target needs at least one arm; failed pairings remain reported.")
            return 0 if passed else 1
        arm = args.arm or "arm_a"
        target = TaskTarget("custom", tuple(args.position), arm) if args.position else solver.approach_target(scene, args.target or "plate", arm)
        result = solver.solve(scene, target)
        print("Current end-effector: " + json.dumps(asdict(end_effector_state(scene, arm))))
        print("Reachability: " + json.dumps(asdict(result)))
        if not result.reachable:
            print("REACHABILITY FAIL: selected target has no accepted endpoint.")
            return 1
        if args.worker:
            preview(scene, solver, result, args.worker, args.viewer_seconds, args.save_image)
            return 0
        for mode, enabled in (("render", args.render or args.save_image), ("viewer", args.viewer)):
            if enabled:
                command = [sys.executable, str(Path(__file__).resolve()), "--seed", str(args.seed), "--arm", arm, "--worker", mode, "--viewer-seconds", str(args.viewer_seconds)]
                command += ["--position", *map(str, args.position)] if args.position else ["--target", args.target or "plate"]
                if args.save_image:
                    command.append("--save-image")
                worker = subprocess.run(command, timeout=args.viewer_seconds + 25 if mode == "viewer" else 40)
                if worker.returncode:
                    raise RuntimeError(f"{mode} worker failed: exit {worker.returncode}")
        print("REACHABILITY PASS: endpoint only; motion path, orientation and grasp remain unvalidated.")
        return 0
    except Exception as exc:
        print(f"REACHABILITY FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
