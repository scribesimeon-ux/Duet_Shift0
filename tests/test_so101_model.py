"""Validate source provenance and single-arm model properties, not manipulation."""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import pytest

from duetshift.sim.so101_model import (
    SOURCE_COMMIT, JOINT_ROLES, asset_directory, load_so101, contact_report, validate_idle,
)


@pytest.fixture(scope="module")
def single_model():
    return load_so101()[0]


def test_upstream_files_match_manifest():
    directory = asset_directory()
    manifest = json.loads((directory / "source_manifest.json").read_text())
    assert manifest["commit"] == SOURCE_COMMIT
    assert manifest["license"] == "Apache-2.0"
    for entry in manifest["files"]:
        data = (directory / "upstream" / entry["local_file"]).read_bytes()
        assert len(data) == entry["bytes"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    assert len(list((directory / "upstream" / "assets").glob("*.stl"))) == 13


def test_source_joints_limits_and_actuator_mapping(single_model):
    model = single_model
    source = ET.parse(asset_directory() / "upstream" / "so101_new_calib.xml")
    joints = source.findall(".//worldbody//joint")
    assert tuple(j.attrib["name"] for j in joints) == tuple(name for name, _ in JOINT_ROLES)
    assert model.njnt == model.nq == model.nv == model.nu == 6
    for j in joints:
        jid = model.joint(j.attrib["name"]).id
        aid = model.actuator(j.attrib["name"]).id
        assert model.jnt_type[jid] == mujoco.mjtJoint.mjJNT_HINGE
        assert model.jnt_limited[jid]
        assert model.jnt_range[jid] == pytest.approx(tuple(map(float, j.attrib["range"].split())))
        assert model.jnt_range[jid, 0] < model.jnt_range[jid, 1]
        assert model.actuator_trnid[aid, 0] == jid
        assert model.actuator_trntype[aid] == mujoco.mjtTrn.mjTRN_JOINT
        assert model.actuator_ctrllimited[aid] and model.actuator_forcelimited[aid]
        assert model.actuator_ctrlrange[aid] == pytest.approx(model.jnt_range[jid], abs=1e-5)
        assert model.actuator_forcerange[aid] == pytest.approx((-3.35, 3.35))


def test_gripper_and_reference_sites(single_model):
    model = single_model
    assert model.body("base").id > 0
    assert model.body("moving_jaw_so101_v1").id == model.jnt_bodyid[model.joint("gripper").id]
    assert model.site("gripperframe").bodyid == model.body("gripper").id
    assert model.site("baseframe").bodyid == model.body("base").id
    assert model.body_jntnum[model.body("base").id] == 0


def test_single_rest_and_gravity_stability():
    model, data, arm = load_so101()
    assert tuple(j.source_name for j in arm.joints) == tuple(name for name, _ in JOINT_ROLES)
    assert arm.gripper.source_name == "gripper"
    assert model.opt.gravity == pytest.approx((0, 0, -9.81))
    assert model.opt.timestep == pytest.approx(0.002)
    assert data.qpos == pytest.approx(np.zeros(6))
    assert data.ctrl == pytest.approx(np.zeros(6))
    assert contact_report(model, data) == []
    result = validate_idle(model, data)
    assert result["passed"], result
    assert result["simulation_time_s"] == pytest.approx(2)


def test_collision_meshes_are_active(single_model):
    model = single_model
    collision = model.geom_group == 3
    assert np.count_nonzero(collision) > 0
    assert np.all(model.geom_contype[collision] != 0)
    assert np.all(model.geom_conaffinity[collision] != 0)
    assert np.all(model.geom_contype[model.geom_group == 2] == 0)


def test_asset_loading_outside_repository(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().anchor)
    assert load_so101()[0].nu == 6
