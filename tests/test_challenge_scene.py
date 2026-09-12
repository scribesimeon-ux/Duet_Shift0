"""Stage 05 physical scene and reproducibility acceptance checks."""

import copy
import json
from pathlib import Path
import subprocess
import sys

import mujoco
import numpy as np
import pytest

from duetshift.sim.challenge_scene import load_challenge_scene


@pytest.fixture
def scene():
    return load_challenge_scene(42)


def test_scene_registry_and_physical_objects(scene):
    model = scene.model
    assert len(scene.arm_a.joints) == len(scene.arm_b.joints) == 6
    assert {j.actuator_id for j in scene.arm_a.joints}.isdisjoint(j.actuator_id for j in scene.arm_b.joints)
    assert model.geom("table/top").contype != 0
    assert model.body("drawer/cabinet").id > 0
    assert set(scene.objects) == {"plate", "mug", "bottle", "fork", "spoon"}
    assert {name for name, obj in scene.objects.items() if obj.support == "drawer"} == {"fork", "spoon"}
    for name, obj in scene.objects.items():
        assert model.jnt_type[obj.joint_id] == mujoco.mjtJoint.mjJNT_FREE
        assert model.body_mass[obj.body_id] == pytest.approx(scene.samples["objects"][name]["mass"])
        assert .01 < model.body_mass[obj.body_id] < .2
        assert np.all(model.body_inertia[obj.body_id] > 0)
        assert len(obj.initial_pose) == 7
        assert obj.geom_ids and all(model.geom_contype[i] != 0 for i in obj.geom_ids)
    assert set(scene.cameras) == {"overview", "task", "drawer"}


def test_seeded_reset_restores_model_and_data(scene):
    sample = copy.deepcopy(scene.samples)
    initial_qpos = scene.data.qpos.copy()
    mass = scene.model.body_mass.copy()
    friction = scene.model.geom_friction.copy()
    sizes = scene.model.geom_size.copy()
    mujoco.mj_step(scene.model, scene.data, nstep=100)
    scene.model.body_mass[scene.objects["plate"].body_id] *= 2
    scene.reset(43)
    scene.reset(42)
    assert scene.samples == sample
    assert np.array_equal(scene.data.qpos, initial_qpos)
    assert np.array_equal(scene.model.body_mass, mass)
    assert np.array_equal(scene.model.geom_friction, friction)
    assert np.array_equal(scene.model.geom_size, sizes)
    assert scene.data.time == 0


def test_different_seed_varies_object_pose(scene):
    first = copy.deepcopy(scene.samples)
    scene.reset(43)
    assert any(first["objects"][n]["xyz"] != scene.samples["objects"][n]["xyz"] for n in scene.objects)
    assert scene.spawn_errors() == []


@pytest.mark.parametrize("seed", [0, 1, 42, 43, 99])
def test_representative_seeds_settle_without_bad_contacts(seed):
    scene = load_challenge_scene(seed)
    assert scene.spawn_errors() == []
    assert scene.data.ncon == 0
    result = scene.validate_stability()
    assert result["passed"], result
    assert scene.unexpected_contacts() == []
    for obj in scene.objects.values():
        support_z = scene.config["table"]["surface_z"] if obj.support == "table" else scene.config["drawer"]["floor_z"]
        assert scene.data.body(obj.body_name).xpos[2] >= support_z - .001


@pytest.mark.parametrize("fraction", [0., .25, .5, .75, 1.])
def test_drawer_at_valid_positions(scene, fraction):
    model, drawer = scene.model, scene.drawer
    assert model.jnt_type[drawer.joint_id] == mujoco.mjtJoint.mjJNT_SLIDE
    assert model.jnt_limited[drawer.joint_id]
    assert drawer.limits[0] == 0 < drawer.limits[1]
    assert not any(model.actuator_trnid[:, 0] == drawer.joint_id)
    assert all(model.geom(name).contype for name in drawer.handle_geoms)
    position = drawer.limits[0] + fraction * (drawer.limits[1] - drawer.limits[0])
    scene.initialize_drawer_position(position)
    assert scene.unexpected_contacts() == []
    result = scene.validate_stability()
    assert result["passed"], result
    assert scene.data.qpos[model.jnt_qposadr[drawer.joint_id]] == pytest.approx(position, abs=.002)


def test_drawer_invalid_initialization_rejected(scene):
    with pytest.raises(ValueError, match="outside joint limits"):
        scene.initialize_drawer_position(scene.drawer.limits[1] + .01)


def test_spawn_validator_rejects_out_of_bounds_configuration(scene):
    scene.config["objects"]["plate"]["xy"] = [2, 2]
    with pytest.raises(ValueError, match="outside its support bounds"):
        scene.reset(42)


def test_spawn_validator_detects_actual_robot_contact(scene):
    obj = scene.objects["bottle"]
    adr = scene.model.jnt_qposadr[obj.joint_id]
    # Deliberately initialize a bottle through a shoulder collision shape.
    shoulder = scene.model.body("arm_a/shoulder").id
    scene.data.qpos[adr:adr + 3] = scene.data.xpos[shoulder]
    mujoco.mj_forward(scene.model, scene.data)
    assert scene.unexpected_contacts()


def test_challenge_preserves_stage4_robot_dynamics_and_collision_masks(scene):
    from duetshift.sim.dual_so101_scene import load_dual_so101
    previous = load_dual_so101()
    old, new = previous.model, scene.model
    for arm in (scene.arm_a, scene.arm_b):
        for joint in arm.joints:
            old_jid = old.joint(joint.name).id
            assert new.jnt_range[joint.joint_id] == pytest.approx(old.jnt_range[old_jid])
            old_aid = old.actuator(joint.actuator_name).id
            assert new.actuator_gainprm[joint.actuator_id] == pytest.approx(old.actuator_gainprm[old_aid])
        for body in arm.bodies:
            a, b = old.body(body).id, new.body(body).id
            assert new.body_mass[b] == pytest.approx(old.body_mass[a])
            assert new.body_inertia[b] == pytest.approx(old.body_inertia[a])
            assert new.body_geomnum[b] == old.body_geomnum[a]
            for offset in range(old.body_geomnum[a]):
                ga, gb = old.body_geomadr[a] + offset, new.body_geomadr[b] + offset
                for values in ("geom_pos", "geom_quat", "geom_size", "geom_contype", "geom_conaffinity", "geom_friction", "geom_solref"):
                    assert getattr(new, values)[gb] == pytest.approx(getattr(old, values)[ga])


@pytest.mark.rendering
@pytest.mark.parametrize("seed", [42, 43])
def test_all_cameras_render_useful_rgb(seed):
    # Match the existing smoke test: isolate OpenGL/native errors and bound startup.
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_challenge_scene.py"
    result = subprocess.run([sys.executable, str(script), "--seed", str(seed), "--worker", "render"],
                            capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("CAMERA PASS: ")
    reports = json.loads(result.stdout.removeprefix("CAMERA PASS: "))
    assert set(reports) == {"overview", "task", "drawer"}
    for report in reports.values():
        assert report["shape"] == [240, 320, 3]
        assert report["dtype"] == "uint8"
        assert report["std"] > 2
    assert all(reports["drawer"]["visible_pixels"][n] >= 4 for n in ("fork", "spoon"))
