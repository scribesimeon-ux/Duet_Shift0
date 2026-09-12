"""Reachability evidence, failure modes and isolation from the live scene."""

from dataclasses import replace
from copy import deepcopy

import mujoco
import numpy as np
import pytest

from duetshift.sim.challenge_scene import load_challenge_scene
from duetshift.sim.reachability import (
    TaskTarget, ReachabilitySolver, ReachabilityStatus, end_effector_state,
)


@pytest.fixture(scope="module")
def scene():
    return load_challenge_scene(42)


@pytest.fixture
def solver():
    return ReachabilitySolver()


@pytest.mark.parametrize("position", [(1, 2), (1, 2, 3, 4), (np.nan, 0, 1), (0, np.inf, 1), (True, 0, 1), "123", None])
def test_malformed_position(position):
    with pytest.raises(ValueError):
        TaskTarget("bad", position)


def test_target_metadata_validation():
    for kwargs in ({"name": " "}, {"arm": "arm_c"}, {"orientation_wxyz": (0, 0, 0, 0)}):
        params = dict(name="target", position=(.3, 0, .9))
        params.update(kwargs)
        with pytest.raises(ValueError):
            TaskTarget(**params)


@pytest.mark.parametrize("arm", ["arm_a", "arm_b"])
def test_end_effector_state_matches_model(scene, arm):
    state = end_effector_state(scene, arm)
    metadata = getattr(scene, arm)
    assert state.site_name == metadata.end_effector
    assert state.arm == arm
    assert np.isfinite(state.position).all()
    assert np.linalg.norm(state.orientation_wxyz) == pytest.approx(1.)
    assert state.position == pytest.approx(scene.data.site(metadata.end_effector).xpos)
    matrix = np.empty(9)
    mujoco.mju_quat2Mat(matrix, np.array(state.orientation_wxyz))
    assert matrix == pytest.approx(scene.data.site(metadata.end_effector).xmat)
    assert state.joint_names == tuple(j.name for j in metadata.joints)
    assert all(name.startswith(arm + "/") for name in state.joint_names)


@pytest.mark.parametrize("seed", [0, 42, 43])
def test_semantic_targets_for_both_arms(seed, solver):
    scene = load_challenge_scene(seed)
    # Same semantic target set is evaluated for each arm, including difficult cross-arm targets.
    results = {}
    for arm in ("arm_a", "arm_b"):
        for name in ("table", "plate", "mug", "bottle", "fork", "spoon", "drawer_handle"):
            target = solver.approach_target(scene, name, arm)
            result = solver.solve(scene, target)
            results[arm, name] = result
            assert result.status not in (ReachabilityStatus.SOLVER_ERROR, ReachabilityStatus.OUTSIDE_WORKSPACE)
            assert result.iterations <= solver.config["max_iterations"] * solver.config["restarts"]
            if result.reachable:
                assert result.position_error_m <= solver.config["tolerance_m"]
                data = solver.preview_data(scene, result)
                assert data.site(getattr(scene, arm).end_effector).xpos == pytest.approx(target.position, abs=.002)
                for joint, q in zip(result.joint_names, result.joint_positions):
                    limits = scene.model.joint(joint).range
                    assert limits[0] <= q <= limits[1]
    # There must be useful actual solutions, rather than accepting any solver outcome.
    for name in ("table", "plate", "fork", "spoon", "drawer_handle"):
        assert results["arm_a", name].reachable, results["arm_a", name]
        assert results["arm_b", name].reachable, results["arm_b", name]
    assert results["arm_a", "bottle"].reachable
    assert results["arm_b", "mug"].reachable


def test_determinism_and_complete_live_state_isolation(scene, solver):
    signature = mujoco.mjtState.mjSTATE_INTEGRATION
    before = np.empty(mujoco.mj_stateSize(scene.model, signature))
    mujoco.mj_getState(scene.model, scene.data, before, signature)
    model_mass = scene.model.body_mass.copy()
    model_positions = scene.model.body_pos.copy()
    samples = deepcopy(scene.samples)
    target = solver.approach_target(scene, "plate", "arm_a")
    first = solver.solve(scene, target)
    second = solver.solve(scene, target)
    assert first == second and first.reachable
    preview = solver.preview_data(scene, first)
    assert not np.shares_memory(preview.qpos, scene.data.qpos)
    assert not np.shares_memory(preview.ctrl, scene.data.ctrl)
    after = np.empty_like(before)
    mujoco.mj_getState(scene.model, scene.data, after, signature)
    assert np.array_equal(before, after)
    assert np.array_equal(scene.model.body_mass, model_mass)
    assert np.array_equal(scene.model.body_pos, model_positions)
    assert scene.samples == samples


@pytest.mark.parametrize("arm", ["arm_a", "arm_b"])
def test_preview_assigns_only_selected_position_joints(scene, solver, arm):
    result = solver.solve(scene, solver.approach_target(scene, "plate", arm))
    preview = solver.preview_data(scene, result)
    selected = getattr(scene, arm)
    commanded = [j for j in selected.joints if j.joint_id != selected.gripper.joint_id]
    aids = [j.actuator_id for j in commanded]
    addresses = [j.qpos_address for j in commanded]
    assert preview.ctrl[aids] == pytest.approx(result.joint_positions)
    assert preview.qpos[addresses] == pytest.approx(result.joint_positions)
    assert np.array_equal(np.delete(preview.ctrl, aids), np.delete(scene.data.ctrl, aids))
    assert np.array_equal(np.delete(preview.qpos, addresses), np.delete(scene.data.qpos, addresses))
    assert preview.ctrl[selected.gripper.actuator_id] == scene.data.ctrl[selected.gripper.actuator_id]


def test_arm_mismatch_rejected(scene, solver):
    target = solver.approach_target(scene, "plate", "arm_a")
    with pytest.raises(ValueError, match="disagrees"):
        solver.solve(scene, target, "arm_b")
    with pytest.raises(ValueError, match="arm must"):
        end_effector_state(scene, "arm_c")


@pytest.mark.parametrize("point", [(10., 0, .9), (.3, 0, .5), (.3, 0, 10.)])
def test_outside_workspace_is_not_solver_failure(scene, solver, point):
    result = solver.solve(scene, TaskTarget("outside", point, "arm_a"))
    assert result.status == ReachabilityStatus.OUTSIDE_WORKSPACE
    assert result.iterations == 0 and result.position_error_m is None
    with pytest.raises(ValueError, match="reachable"):
        solver.preview_data(scene, result)


def test_unreachable_inside_policy_and_iteration_budget(scene, solver):
    # Far corner remains inside the configured box; local IK must fail cleanly.
    target = TaskTarget("far corner", (.55, .39, 1.24), "arm_a")
    before = scene.data.qpos.copy()
    result = solver.solve(scene, target)
    assert result.status == ReachabilityStatus.IK_FAILED
    assert np.isfinite(result.position_error_m) and result.position_error_m > .002
    assert result.iterations <= 400
    assert np.array_equal(before, scene.data.qpos)
    solver.config.update(max_iterations=1, restarts=1)
    result = solver.solve(scene, solver.approach_target(scene, "fork", "arm_a"))
    assert result.status == ReachabilityStatus.IK_FAILED and result.iterations == 1


def test_orientation_not_silently_ignored(scene, solver):
    target = TaskTarget("oriented", end_effector_state(scene, "arm_a").position, "arm_a", (1., 0., 0., 0.))
    assert solver.solve(scene, target).status == ReachabilityStatus.UNSUPPORTED_ORIENTATION


def test_approach_uses_current_geometry_and_drawer_pose(solver):
    scene = load_challenge_scene()
    for name, obj in scene.objects.items():
        point = solver.approach_target(scene, name).position
        assert point[:2] == pytest.approx(scene.data.xpos[obj.body_id, :2])
        assert point[2] > scene.data.xpos[obj.body_id, 2] + .08
    closed = solver.approach_target(scene, "drawer_handle")
    scene.initialize_drawer_position(.05)
    opened = solver.approach_target(scene, "drawer_handle")
    assert np.array(opened.position) - closed.position == pytest.approx([0, .05, 0])
    obj = scene.objects["mug"]
    scene.data.qpos[scene.model.jnt_qposadr[obj.joint_id]] += .02
    moved = solver.approach_target(scene, "mug")
    assert moved.position[0] == pytest.approx(scene.samples["objects"]["mug"]["xyz"][0] + .02)


def test_collision_rejection_and_stale_preview(solver):
    scene = load_challenge_scene()
    target = TaskTarget("obstructed", end_effector_state(scene, "arm_a").position, "arm_a")
    valid = solver.solve(scene, target)
    assert valid.reachable
    bottle = scene.objects["bottle"]
    adr = scene.model.jnt_qposadr[bottle.joint_id]
    scene.data.qpos[adr:adr + 3] = np.array(target.position) - [0, 0, .04]
    mujoco.mj_forward(scene.model, scene.data)
    result = solver.solve(scene, target)
    assert result.status == ReachabilityStatus.COLLISION, result
    assert result.contacts
    with pytest.raises(ValueError, match="stale or unsafe"):
        solver.preview_data(scene, valid)


def test_solver_numerical_failure_preserves_state(scene, solver, monkeypatch):
    before = scene.data.qpos.copy()
    def fail(*args, **kwargs):
        raise np.linalg.LinAlgError("injected linear solve failure")
    monkeypatch.setattr(np.linalg, "solve", fail)
    result = solver.solve(scene, solver.approach_target(scene, "fork", "arm_a"))
    assert result.status == ReachabilityStatus.SOLVER_ERROR
    assert "injected" in result.message
    assert np.array_equal(before, scene.data.qpos)


def test_reuse_after_reset_and_stage5_physics(solver):
    scene = load_challenge_scene(42)
    first = solver.solve(scene, solver.approach_target(scene, "plate", "arm_b"))
    scene.reset(43)
    assert solver.solve(scene, solver.approach_target(scene, "plate", "arm_b")).reachable
    scene.reset(42)
    assert solver.solve(scene, solver.approach_target(scene, "plate", "arm_b")) == first
    assert scene.spawn_errors() == []
    assert scene.validate_stability()["passed"]


def test_preview_rejects_wrong_mapping_and_bad_limits(scene, solver):
    result = solver.solve(scene, solver.approach_target(scene, "plate", "arm_a"))
    with pytest.raises(ValueError, match="mapping"):
        solver.preview_data(scene, replace(result, joint_names=("wrong",) * 5))
    with pytest.raises(ValueError, match="limits"):
        solver.preview_data(scene, replace(result, joint_positions=(100.,) * 5))


@pytest.mark.parametrize("arguments,code,expected", [
    (["--arm", "arm_a", "--target", "bottle"], 0, "REACHABILITY PASS"),
    (["--arm", "arm_b", "--target", "mug"], 0, "REACHABILITY PASS"),
    (["--arm", "arm_a", "--position", "10", "0", "1"], 1, "outside_workspace"),
])
def test_runner_exit_status(arguments, code, expected):
    from pathlib import Path
    import subprocess
    import sys
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_reachability.py"
    result = subprocess.run([sys.executable, str(script), *arguments], capture_output=True, text=True, timeout=30)
    assert result.returncode == code, result.stdout + result.stderr
    assert expected in result.stdout


@pytest.mark.rendering
def test_static_preview_render_worker():
    from pathlib import Path
    import subprocess
    import sys
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_reachability.py"
    result = subprocess.run([sys.executable, str(script), "--arm", "arm_a", "--target", "bottle", "--worker", "render"],
                            capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RENDER PASS" in result.stdout
