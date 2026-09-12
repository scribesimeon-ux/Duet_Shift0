"""Real single-body physics checks; no robots or control algorithms."""

from pathlib import Path
import subprocess
import sys

import mujoco
import pytest

from duetshift.sim.mujoco_smoke import SmokeSimulation, scene_path, validate_physics


def test_model_and_initial_state():
    sim = SmokeSimulation()
    assert mujoco.__version__
    assert sim.model.nbody == 2  # World and sphere.
    assert sim.model.ngeom == 2
    assert sim.model.nq == 7 and sim.model.nv == 6
    assert sim.model.geom("floor").type == mujoco.mjtGeom.mjGEOM_PLANE
    assert sim.model.geom("falling_sphere").type == mujoco.mjtGeom.mjGEOM_SPHERE
    assert sim.model.joint("falling_joint").type == mujoco.mjtJoint.mjJNT_FREE
    assert sim.time == 0
    assert sim.position == pytest.approx((0, 0, 0.5))


def test_gravity_and_time():
    sim = SmokeSimulation()
    sim.step(50)
    assert sim.time == pytest.approx(0.1)
    assert 0.43 < sim.position[2] < 0.48
    assert sim.data.qvel[2] < -0.8


def test_floor_support_and_reset():
    sim = SmokeSimulation()
    initial_qpos = sim.data.qpos.copy()
    for _ in range(4):
        sim.step(500)
        assert 0.045 < sim.position[2] < 0.06
        assert sim.data.ncon > 0
        assert abs(sim.data.qvel[2]) < 0.02
    sim.reset()
    assert sim.time == 0
    assert sim.data.qpos == pytest.approx(initial_qpos)
    assert sim.position == pytest.approx((0, 0, 0.5))
    assert sim.data.qvel == pytest.approx([0] * 6)


def test_validation_and_independent_instances():
    first, second = SmokeSimulation(), SmokeSimulation()
    assert validate_physics(first).passed
    first.step(10)
    assert second.time == 0
    assert second.position == pytest.approx((0, 0, 0.5))


def test_scene_path_outside_repository_cwd(monkeypatch):
    # An existing directory outside the repo is sufficient; no temp files are needed.
    monkeypatch.chdir(Path(sys.executable).resolve().parent)
    assert scene_path().is_file()
    assert SmokeSimulation().time == 0


@pytest.mark.parametrize("steps", [-1, 1.5, True])
def test_invalid_step_count(steps):
    with pytest.raises(ValueError, match="non-negative integer"):
        SmokeSimulation().step(steps)


@pytest.mark.rendering
def test_offscreen_rgb():
    # Isolate graphics/native failures and timeouts from the physics test process.
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_mujoco_smoke.py"
    result = subprocess.run(
        [sys.executable, str(script), "--graphics-worker", "render"],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OFFSCREEN PASS" in result.stdout
