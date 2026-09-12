"""Bounded official MuJoCo viewer for Stage 4 model inspection only."""

import time

import mujoco


def inspection_camera() -> mujoco.MjvCamera:
    camera = mujoco.MjvCamera()
    camera.lookat[:] = (0.2, 0, 0.18)
    camera.distance = 1.15
    camera.azimuth = 135
    camera.elevation = -25
    return camera


def show_model(model: mujoco.MjModel, data: mujoco.MjData) -> None:
    import mujoco.viewer

    updates = 0
    with mujoco.viewer.launch_passive(model, data) as viewer:
        if not viewer.is_running():
            raise RuntimeError("MuJoCo viewer did not open")
        camera = inspection_camera()
        with viewer.lock():
            viewer.cam.lookat[:] = camera.lookat
            viewer.cam.distance = camera.distance
            viewer.cam.azimuth = camera.azimuth
            viewer.cam.elevation = camera.elevation
        viewer.sync()
        print("Viewer opened. Close it to exit early; it auto-closes after 8 seconds.", flush=True)
        start = time.monotonic()
        while viewer.is_running() and time.monotonic() - start < 8:
            tick = time.monotonic()
            with viewer.lock():
                mujoco.mj_step(model, data, nstep=5)
            viewer.sync()
            updates += 1
            time.sleep(max(0, 5 * model.opt.timestep - (time.monotonic() - tick)))
    print(f"VIEWER PASS: {updates} updates; closed cleanly.")
