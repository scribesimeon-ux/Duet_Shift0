"""Verify independent instances, placement, and idle stability of two SO-101s."""

import mujoco
import numpy as np
import pytest

from duetshift.sim.dual_so101_scene import load_dual_so101
from duetshift.sim.so101_model import load_so101, contact_report, validate_idle


@pytest.fixture(scope="module")
def scene():
    return load_dual_so101()


def test_unique_names_and_independent_mappings(scene):
    a, b = scene.arm_a, scene.arm_b
    assert scene.model.njnt == scene.model.nu == 12
    assert tuple(j.source_name for j in a.joints) == tuple(j.source_name for j in b.joints)
    assert set(j.actuator_id for j in a.joints).isdisjoint(j.actuator_id for j in b.joints)
    assert set(j.joint_id for j in a.joints).isdisjoint(j.joint_id for j in b.joints)
    assert set(j.qpos_address for j in a.joints).isdisjoint(j.qpos_address for j in b.joints)
    assert set(a.bodies).isdisjoint(b.bodies) and set(a.sites).isdisjoint(b.sites)
    for arm in (a, b):
        assert all(j.name.startswith(arm.prefix) and j.actuator_name.startswith(arm.prefix) for j in arm.joints)
        assert arm.gripper.name == arm.prefix + "gripper"
        assert scene.model.site(arm.end_effector).bodyid == scene.model.body(arm.prefix + "gripper").id


def test_dual_matches_validated_single_geometry_and_dynamics(scene):
    single, _, original = load_so101()
    for arm in (scene.arm_a, scene.arm_b):
        for expected, actual in zip(original.joints, arm.joints):
            assert actual.limits == expected.limits
            assert actual.control_range == expected.control_range
            assert actual.force_range == expected.force_range
            assert scene.model.actuator_gainprm[actual.actuator_id] == pytest.approx(single.actuator_gainprm[expected.actuator_id])
        for name in original.bodies:
            old, new = single.body(name).id, scene.model.body(arm.prefix + name).id
            assert scene.model.body_mass[new] == pytest.approx(single.body_mass[old])
            assert scene.model.body_inertia[new] == pytest.approx(single.body_inertia[old])
        # Each attached collision/visual geom retains its mesh vertices and body-local pose.
        for gid in range(single.ngeom):
            body_name = single.body(single.geom_bodyid[gid]).name
            if body_name == "world":
                continue
            old_body = single.body(body_name).id
            new_body = scene.model.body(arm.prefix + body_name).id
            offset = gid - single.body_geomadr[old_body]
            new_gid = scene.model.body_geomadr[new_body] + offset
            assert scene.model.geom_pos[new_gid] == pytest.approx(single.geom_pos[gid])
            assert scene.model.geom_quat[new_gid] == pytest.approx(single.geom_quat[gid])
            old_mesh, new_mesh = single.geom_dataid[gid], scene.model.geom_dataid[new_gid]
            count = single.mesh_vertnum[old_mesh]
            assert scene.model.mesh_vertnum[new_mesh] == count
            old_start, new_start = single.mesh_vertadr[old_mesh], scene.model.mesh_vertadr[new_mesh]
            np.testing.assert_allclose(
                scene.model.mesh_vert[new_start:new_start + count], single.mesh_vert[old_start:old_start + count], atol=1e-7,
            )


def test_bases_separated_and_initial_contacts_absent(scene):
    a = scene.data.body(scene.arm_a.base).xpos
    b = scene.data.body(scene.arm_b.base).xpos
    assert np.linalg.norm(a - b) == pytest.approx(0.44)  # Intentional scene configuration.
    assert contact_report(scene.model, scene.data) == []
    assert scene.inter_arm_contacts() == []


def test_dual_idle_stability():
    scene = load_dual_so101()
    targets = scene.data.ctrl.copy()
    result = validate_idle(scene.model, scene.data)
    assert result["passed"], result
    assert result["simulation_time_s"] == pytest.approx(2)
    assert scene.data.ctrl == pytest.approx(targets)
    assert scene.inter_arm_contacts() == []


def test_inter_arm_collision_reporting_detects_overlap():
    # Test-only base overlap proves inter-arm collisions have not been disabled.
    scene = load_dual_so101()
    scene.model.body_pos[scene.model.body(scene.arm_b.base).id] = scene.model.body_pos[scene.model.body(scene.arm_a.base).id]
    mujoco.mj_forward(scene.model, scene.data)
    assert scene.inter_arm_contacts()
    assert any(c["distance_m"] < 0 for c in scene.inter_arm_contacts())
