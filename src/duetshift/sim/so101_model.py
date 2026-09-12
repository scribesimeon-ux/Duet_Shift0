"""Inspection and constant-rest initialization of the upstream SO-101 model."""

from dataclasses import dataclass
from pathlib import Path

import mujoco
import numpy as np


SOURCE_REPOSITORY = "https://github.com/TheRobotStudio/SO-ARM100"
SOURCE_COMMIT = "eecbe3e0a9ebb23e25ad7b2759b03884c6660903"
SOURCE_FILE = "Simulation/SO101/so101_new_calib.xml"

# Source joint order and semantic roles. Numeric limits/mappings come from MJCF.
JOINT_ROLES = (
    ("shoulder_pan", "base yaw"),
    ("shoulder_lift", "shoulder elevation"),
    ("elbow_flex", "elbow flexion"),
    ("wrist_flex", "wrist pitch"),
    ("wrist_roll", "wrist roll"),
    ("gripper", "moving jaw hinge"),
)


@dataclass(frozen=True)
class JointInfo:
    source_name: str
    role: str
    name: str
    joint_id: int
    qpos_address: int
    joint_type: str
    limits: tuple[float, float] | None
    actuator_name: str
    actuator_id: int
    control_range: tuple[float, float]
    force_range: tuple[float, float]


@dataclass(frozen=True)
class ArmInfo:
    prefix: str
    base: str
    end_effector: str
    moving_jaw: str
    joints: tuple[JointInfo, ...]
    bodies: tuple[str, ...]
    sites: tuple[str, ...]

    @property
    def gripper(self) -> JointInfo:
        return next(joint for joint in self.joints if joint.source_name == "gripper")


def asset_directory() -> Path:
    directory = Path(__file__).resolve().parents[3] / "assets" / "robots" / "so101"
    if not (directory / "upstream" / "so101_new_calib.xml").is_file():
        raise FileNotFoundError("SO-101 assets missing: use the complete repository in editable mode")
    return directory


def describe_arm(model: mujoco.MjModel, prefix: str = "") -> ArmInfo:
    """Read the source-of-truth joint table from compiled MJCF; validate mappings."""
    joints = []
    for source_name, role in JOINT_ROLES:
        name = prefix + source_name
        jid = model.joint(name).id
        matches = [
            i for i in range(model.nu)
            if model.actuator_trntype[i] == mujoco.mjtTrn.mjTRN_JOINT
            and model.actuator_trnid[i, 0] == jid
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one joint actuator for {name}, got {matches}")
        aid = matches[0]
        if model.jnt_type[jid] != mujoco.mjtJoint.mjJNT_HINGE:
            raise ValueError(f"Expected the source hinge joint: {name}")
        if not model.actuator_ctrllimited[aid] or not model.actuator_forcelimited[aid]:
            raise ValueError(f"Missing source control/force limits: {name}")
        limits = tuple(map(float, model.jnt_range[jid])) if model.jnt_limited[jid] else None
        control = tuple(map(float, model.actuator_ctrlrange[aid]))
        force = tuple(map(float, model.actuator_forcerange[aid]))
        if limits is None or limits[0] >= limits[1] or control[0] >= control[1]:
            raise ValueError(f"Invalid source limits: {name}")
        joints.append(JointInfo(
            source_name, role, name, jid, int(model.jnt_qposadr[jid]), "hinge",
            limits, model.actuator(aid).name, aid, control, force,
        ))
    base, ee, jaw = prefix + "base", prefix + "gripperframe", prefix + "moving_jaw_so101_v1"
    model.body(base)
    model.site(ee)
    model.body(jaw)
    bodies = tuple(model.body(i).name for i in range(1, model.nbody) if model.body(i).name.startswith(prefix))
    sites = tuple(model.site(i).name for i in range(model.nsite) if model.site(i).name.startswith(prefix))
    return ArmInfo(prefix, base, ee, jaw, tuple(joints), bodies, sites)


def initialize_rest(model: mujoco.MjModel, arms: tuple[ArmInfo, ...]) -> mujoco.MjData:
    """Use source qpos0 and constant matching servo targets; no trajectory or controller."""
    data = mujoco.MjData(model)
    for arm in arms:
        for joint in arm.joints:
            target = data.qpos[joint.qpos_address]
            if not joint.control_range[0] <= target <= joint.control_range[1]:
                raise ValueError(f"Rest pose is outside control range: {joint.name}")
            data.ctrl[joint.actuator_id] = target
    mujoco.mj_forward(model, data)
    return data


def load_so101() -> tuple[mujoco.MjModel, mujoco.MjData, ArmInfo]:
    model = mujoco.MjModel.from_xml_path(str(asset_directory() / "single_scene.xml"))
    arm = describe_arm(model)
    return model, initialize_rest(model, (arm,)), arm


def contact_report(model: mujoco.MjModel, data: mujoco.MjData) -> list[dict]:
    """Report active contact pairs, including self, floor, and inter-arm contacts."""
    return [
        {
            "body_a": model.body(model.geom_bodyid[c.geom1]).name,
            "body_b": model.body(model.geom_bodyid[c.geom2]).name,
            "distance_m": float(c.dist),
        }
        for c in data.contact
    ]


def validate_idle(model: mujoco.MjModel, data: mujoco.MjData, steps: int = 1000) -> dict:
    """Monitor a short rest hold under gravity; never changes servo targets or qpos."""
    if not isinstance(steps, int) or isinstance(steps, bool) or steps <= 0:
        raise ValueError("steps must be a positive integer")
    initial_qpos, initial_ctrl = data.qpos.copy(), data.ctrl.copy()
    start = float(data.time)
    max_drift = max_speed = 0.0
    max_contacts = data.ncon
    passed = True
    for step in range(steps):
        mujoco.mj_step(model, data)
        finite = all(np.isfinite(values).all() for values in (data.qpos, data.qvel, data.qacc))
        passed &= finite and abs(data.time - (start + (step + 1) * model.opt.timestep)) < 1e-8
        passed &= not bool(data.warning.number.any())
        if not passed:
            break
        max_drift = max(max_drift, float(np.max(np.abs(data.qpos - initial_qpos))))
        max_speed = max(max_speed, float(np.max(np.abs(data.qvel))))
        max_contacts = max(max_contacts, data.ncon)
        for jid in range(model.njnt):
            if model.jnt_limited[jid]:
                q = data.qpos[model.jnt_qposadr[jid]]
                lo, hi = model.jnt_range[jid]
                passed &= lo - 0.01 <= q <= hi + 0.01
    mujoco.mj_forward(model, data)
    passed &= max_drift < 0.05 and max_speed < 1.0
    passed &= bool(np.array_equal(initial_ctrl, data.ctrl)) and max_contacts == 0
    return {
        "passed": bool(passed), "simulation_time_s": float(data.time),
        "max_joint_drift_rad": max_drift, "max_speed_rad_s": max_speed,
        "max_contacts": int(max_contacts), "warning_counts": data.warning.number.tolist(),
        "final_qpos_rad": data.qpos.tolist(),
    }


def print_arm(arm: ArmInfo) -> None:
    print(f"Base: {arm.base}; end-effector site: {arm.end_effector}; moving jaw: {arm.moving_jaw}")
    for j in arm.joints:
        print(f"  {j.name}[joint {j.joint_id}]: {j.role}; {j.joint_type}; range(rad)={j.limits}; "
              f"actuator={j.actuator_name}[{j.actuator_id}]; ctrl(rad)={j.control_range}; force(Nm)={j.force_range}")
    print(f"Gripper: {arm.gripper.name} -> {arm.gripper.actuator_name} (angular, not LeRobot 0-100)")
    print(f"Bodies: {arm.bodies}")
    print(f"Sites: {arm.sites}")
