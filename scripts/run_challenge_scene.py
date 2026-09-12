"""Inspect the Stage 05 challenge scene; no manipulation is performed."""

import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
import zlib

import mujoco

from duetshift.sim.challenge_scene import load_challenge_scene


def save_png(path, rgb):
    """Write inspection RGB using only the standard library; no imaging dependency."""
    height, width, _ = rgb.shape
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
    pixels = b"".join(b"\x00" + row.tobytes() for row in rgb)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


def show_viewer(scene, seconds):
    import mujoco.viewer
    with mujoco.viewer.launch_passive(scene.model, scene.data) as viewer:
        with viewer.lock():
            viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
            viewer.cam.fixedcamid = scene.cameras["overview"].camera_id
        deadline = time.monotonic() + seconds
        while viewer.is_running() and time.monotonic() < deadline:
            with viewer.lock():
                mujoco.mj_step(scene.model, scene.data, nstep=5)
            viewer.sync()
            time.sleep(.01)
    print(f"VIEWER PASS: window opened; bounded session ({seconds:g} seconds maximum) closed.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--render", action="store_true", help="Validate RGB and visibility for all three cameras")
    parser.add_argument("--save-images", action="store_true", help="Also save rendered PNGs under ignored tmp/challenge_scene")
    parser.add_argument("--viewer", action="store_true", help="Open the viewer for a bounded session")
    parser.add_argument("--viewer-seconds", type=float, default=8, help="Viewer duration, 1 to 300 seconds (default 8)")
    parser.add_argument("--worker", choices=("viewer", "render"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.viewer_seconds <= 300:
        parser.error("--viewer-seconds must be between 1 and 300")
    try:
        scene = load_challenge_scene(args.seed)
        initial_errors = scene.spawn_errors()
        result = scene.validate_stability()
        if initial_errors or not result["passed"]:
            print(json.dumps({"initial_errors": initial_errors, "physics": result}, indent=2))
            return 1
        if args.worker == "viewer":
            show_viewer(scene, args.viewer_seconds)
            return 0
        if args.worker == "render":
            frames, reports = scene.render_cameras()
            print("CAMERA PASS: " + json.dumps(reports, indent=2), flush=True)
            if args.save_images:
                directory = Path(__file__).resolve().parents[1] / "tmp" / "challenge_scene"
                directory.mkdir(parents=True, exist_ok=True)
                for name, rgb in frames.items():
                    path = directory / f"seed_{args.seed}_{name}.png"
                    save_png(path, rgb)
                    print(f"Inspection image: {path}")
            return 0
        print(f"MuJoCo {mujoco.__version__}; seed {scene.seed}")
        for arm in (scene.arm_a, scene.arm_b):
            print(f"{arm.prefix}: base={arm.base}, joints={len(arm.joints)}, gripper={arm.gripper.name}, ee={arm.end_effector}")
        print("Actual sampled reset configuration: " + json.dumps(scene.samples, indent=2))
        for name, obj in scene.objects.items():
            print(f"{name}: support={obj.support}; settled xyz={scene.data.body(obj.body_name).xpos.tolist()}")
        drawer_position = scene.data.qpos[scene.model.jnt_qposadr[scene.drawer.joint_id]]
        print(f"Drawer: physical slide; q={drawer_position:.6f} m; limits={scene.drawer.limits}; closed reset")
        print("Cameras: " + ", ".join(f"{c.name} ({c.role})" for c in scene.cameras.values()))
        print("Initial collision validity: PASS")
        print("Physics: " + json.dumps(result, indent=2))
        for mode, enabled in (("render", args.render or args.save_images), ("viewer", args.viewer)):
            if enabled:
                command = [sys.executable, str(Path(__file__).resolve()), "--seed", str(args.seed), "--worker", mode,
                           "--viewer-seconds", str(args.viewer_seconds)]
                if args.save_images:
                    command.append("--save-images")
                worker = subprocess.run(command, timeout=args.viewer_seconds + 25 if mode == "viewer" else 40)
                if worker.returncode:
                    print(f"{mode.upper()} FAIL: worker exit {worker.returncode}")
                    return 2
        print("CHALLENGE SCENE PASS")
        return 0
    except Exception as exc:
        print(f"CHALLENGE SCENE FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
