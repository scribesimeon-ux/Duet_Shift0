"""Position reachability on the existing challenge scene; never moves the live scene.

A converged endpoint is not a trajectory, a grasp, or proof of manipulability.
"""

from copy import copy
from dataclasses import dataclass
from enum import Enum
import json
from numbers import Real
from pathlib import Path

import mujoco
import numpy as np

from .challenge_scene import ChallengeScene
from .so101_model import ArmInfo

CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "reachability.json"
ARM_NAMES = ("arm_a", "arm_b")


def _vector(value, length, name):
    try:
        items = tuple(value)
    except TypeError as exc:
        raise ValueError(f"{name} must contain {length} finite numbers") from exc
    if len(items) != length or any(isinstance(v, bool) or not isinstance(v, Real) or not np.isfinite(v) for v in items):
        raise ValueError(f"{name} must contain {length} finite numbers")
    return tuple(float(v) for v in items)


@dataclass(frozen=True)
class TaskTarget:
    name: str
    position: tuple[float, float, float]
    arm: str | None = None
    orientation_wxyz: tuple[float, float, float, float] | None = None

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("target name must be nonempty")
        if self.arm is not None and self.arm not in ARM_NAMES:
            raise ValueError("arm must be arm_a, arm_b or None")
        object.__setattr__(self, "position", _vector(self.position, 3, "position"))
        if self.orientation_wxyz is not None:
            quat = _vector(self.orientation_wxyz, 4, "orientation_wxyz")
            if not np.isclose(np.linalg.norm(quat), 1., atol=1e-6, rtol=0):
                raise ValueError("orientation_wxyz must be a unit quaternion")
            object.__setattr__(self, "orientation_wxyz", quat)


@dataclass(frozen=True)
class EndEffectorState:
    arm: str
    site_name: str
    position: tuple[float, float, float]
    orientation_wxyz: tuple[float, float, float, float]
    joint_names: tuple[str, ...]
    joint_positions: tuple[float, ...]


class ReachabilityStatus(str, Enum):
    REACHABLE = "reachable"
    OUTSIDE_WORKSPACE = "outside_workspace"
    IK_FAILED = "ik_failed"
    COLLISION = "endpoint_collision"
    SOLVER_ERROR = "solver_error"
    UNSUPPORTED_ORIENTATION = "unsupported_orientation"


@dataclass(frozen=True)
class ReachabilityResult:
    status: ReachabilityStatus
    arm: str
    target: TaskTarget
    position_error_m: float | None
    iterations: int
    joint_names: tuple[str, ...]
    joint_positions: tuple[float, ...]
    contacts: tuple[str, ...]
    message: str

    @property
    def reachable(self) -> bool:
        return self.status == ReachabilityStatus.REACHABLE


def arm_metadata(scene: ChallengeScene, arm: str) -> ArmInfo:
    if arm not in ARM_NAMES:
        raise ValueError("arm must be arm_a or arm_b")
    selected = getattr(scene, arm)
    other = scene.arm_b if arm == "arm_a" else scene.arm_a
    if selected.prefix != arm + "/" or {j.actuator_id for j in selected.joints} & {j.actuator_id for j in other.joints}:
        raise ValueError("invalid or overlapping arm mapping")
    return selected


def _scratch(scene: ChallengeScene) -> mujoco.MjData:
    # MuJoCo's copy implementation owns independent arrays, including contacts/ctrl.
    data = copy(scene.data)
    if not all(np.isfinite(v).all() for v in (data.qpos, data.qvel, data.ctrl)):
        raise ValueError("scene state contains non-finite values")
    mujoco.mj_forward(scene.model, data)
    return data


def end_effector_state(scene: ChallengeScene, arm: str) -> EndEffectorState:
    metadata = arm_metadata(scene, arm)
    data = _scratch(scene)
    site = scene.model.site(metadata.end_effector).id
    quat = np.empty(4)
    mujoco.mju_mat2Quat(quat, data.site_xmat[site])
    return EndEffectorState(arm, metadata.end_effector, tuple(map(float, data.site_xpos[site])),
                           tuple(map(float, quat)), tuple(j.name for j in metadata.joints),
                           tuple(float(data.qpos[j.qpos_address]) for j in metadata.joints))


def _arm_contacts(scene: ChallengeScene, data: mujoco.MjData, arm: str) -> tuple[str, ...]:
    pairs = set()
    for contact in data.contact:
        bodies = tuple(scene.model.body(scene.model.geom_bodyid[gid]).name for gid in (contact.geom1, contact.geom2))
        if any(name.startswith(arm + "/") for name in bodies) and contact.dist <= 0:
            pairs.add(f"{bodies[0]} <-> {bodies[1]}")
    return tuple(sorted(pairs))


class ReachabilitySolver:
    """Bounded damped least-squares position IK with deterministic restart seeds."""

    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        cfg = self.config
        for key, maximum in (("max_iterations", 1000), ("restarts", 16)):
            if type(cfg[key]) is not int or not 1 <= cfg[key] <= maximum:
                raise ValueError(f"invalid {key}")
        for key in ("tolerance_m", "damping", "max_joint_step_rad", "object_clearance_m", "drawer_front_offset_m", "drawer_up_offset_m", "table_target_height_m"):
            if isinstance(cfg[key], bool) or not isinstance(cfg[key], Real) or not np.isfinite(cfg[key]) or cfg[key] <= 0:
                raise ValueError(f"invalid {key}")
        heights = _vector(cfg["workspace_height_m"], 2, "workspace_height_m")
        if not 0 < heights[0] < heights[1]:
            raise ValueError("invalid workspace height limits")
        factors = cfg["line_search_factors"]
        if not isinstance(factors, list) or not 1 <= len(factors) <= 10 or any(isinstance(v, bool) or not isinstance(v, Real) or not np.isfinite(v) or not 0 < v <= 1 for v in factors):
            raise ValueError("invalid line search factors")

    def approach_target(self, scene: ChallengeScene, semantic_name: str, arm: str | None = None) -> TaskTarget:
        """Use current object geometry bounds, or the drawer's actual current handle pose."""
        data, model = _scratch(scene), scene.model
        if semantic_name == "table":
            xy = np.mean(scene.config["workspace_xy"], axis=1)
            point = [*xy, scene.config["table"]["surface_z"] + self.config["table_target_height_m"]]
        elif semantic_name == "drawer_handle":
            gid = model.geom(scene.drawer.handle_geoms[0]).id
            point = data.geom_xpos[gid] + [0, self.config["drawer_front_offset_m"], self.config["drawer_up_offset_m"]]
        elif semantic_name in scene.objects:
            obj = scene.objects[semantic_name]
            top = -np.inf
            for gid in obj.geom_ids:
                rotation = data.geom_xmat[gid].reshape(3, 3)
                center, half = model.geom_aabb[gid, :3], model.geom_aabb[gid, 3:]
                top = max(top, (data.geom_xpos[gid] + rotation @ center)[2] + (np.abs(rotation) @ half)[2])
            point = [*data.xpos[obj.body_id, :2], top + self.config["object_clearance_m"]]
        else:
            raise ValueError(f"unknown semantic target: {semantic_name}")
        return TaskTarget(semantic_name + "_approach", tuple(point), arm)

    def solve(self, scene: ChallengeScene, target: TaskTarget, arm: str | None = None) -> ReachabilityResult:
        if not isinstance(target, TaskTarget):
            raise ValueError("target must be a TaskTarget")
        arm = target.arm if arm is None else arm
        metadata = arm_metadata(scene, arm)
        if target.arm is not None and target.arm != arm:
            raise ValueError("target arm disagrees with requested arm")
        # The gripper jaw is never used as an extra positioning degree of freedom.
        joints = tuple(j for j in metadata.joints if j.joint_id != metadata.gripper.joint_id)
        names = tuple(j.name for j in joints)
        def result(status, error=None, iterations=0, q=(), contacts=(), message=""):
            return ReachabilityResult(status, arm, target, error, iterations, names, tuple(map(float, q)), contacts, message)
        if target.orientation_wxyz is not None:
            return result(ReachabilityStatus.UNSUPPORTED_ORIENTATION, message="Position-only IK does not enforce orientation; request was not silently ignored.")
        table = scene.config["table"]
        half = np.array(table["size"][:2]) / 2
        xy = np.array(target.position[:2]) - table["center_xy"]
        height = target.position[2] - table["surface_z"]
        if np.any(np.abs(xy) > half) or not self.config["workspace_height_m"][0] <= height <= self.config["workspace_height_m"][1]:
            return result(ReachabilityStatus.OUTSIDE_WORKSPACE, message="Outside configured table-volume policy; IK was not attempted.")
        try:
            data = _scratch(scene)
            model = scene.model
            qadr = np.array([j.qpos_address for j in joints])
            dofs = np.array([model.jnt_dofadr[j.joint_id] for j in joints])
            limits = np.array([(max(j.limits[0], j.control_range[0]), min(j.limits[1], j.control_range[1])) for j in joints])
            if np.any(limits[:, 0] >= limits[:, 1]):
                raise ValueError("empty joint/control limit intersection")
            site = model.site(metadata.end_effector).id
            point = np.array(target.position)
            initial = np.clip(data.qpos[qadr], limits[:, 0], limits[:, 1])
            # Local RNG, fixed seed; it never consumes scene/global random state.
            rng = np.random.default_rng(0)
            starts = [initial] + [rng.uniform(limits[:, 0] * .65, limits[:, 1] * .65) for _ in range(self.config["restarts"] - 1)]
            jac = np.zeros((3, model.nv))
            best_error, best_q, total = float("inf"), initial.copy(), 0
            collision_candidate = None
            for start in starts:
                q = start.copy()
                for _ in range(self.config["max_iterations"]):
                    total += 1
                    data.qpos[qadr] = q
                    mujoco.mj_forward(model, data)
                    delta = point - data.site_xpos[site]
                    error = float(np.linalg.norm(delta))
                    if not np.isfinite(error):
                        raise FloatingPointError("non-finite IK error")
                    if error < best_error:
                        best_error, best_q = error, q.copy()
                    if error <= self.config["tolerance_m"]:
                        contacts = _arm_contacts(scene, data, arm)
                        if not contacts:
                            return result(ReachabilityStatus.REACHABLE, error, total, q, message="Position converged and endpoint has no detected arm contacts. Path and grasp are untested.")
                        collision_candidate = (error, q.copy(), contacts)
                        break
                    mujoco.mj_jacSite(model, data, jac, None, site)
                    j = jac[:, dofs]
                    step = j.T @ np.linalg.solve(j @ j.T + self.config["damping"] ** 2 * np.eye(3), delta)
                    if not np.isfinite(step).all():
                        raise FloatingPointError("non-finite IK step")
                    step *= min(1., self.config["max_joint_step_rad"] / max(float(np.max(np.abs(step))), 1e-12))
                    improved = False
                    for factor in self.config["line_search_factors"]:
                        trial = np.clip(q + factor * step, limits[:, 0], limits[:, 1])
                        data.qpos[qadr] = trial
                        mujoco.mj_forward(model, data)
                        if np.linalg.norm(point - data.site_xpos[site]) < error - 1e-10:
                            q, improved = trial, True
                            break
                    if not improved:
                        break
            if collision_candidate is not None:
                error, q, contacts = collision_candidate
                return result(ReachabilityStatus.COLLISION, error, total, q, contacts, "IK converged but tested endpoints had arm contacts; no collision-free endpoint was found.")
            return result(ReachabilityStatus.IK_FAILED, best_error, total, best_q, message="Bounded local IK did not converge; this does not prove geometric impossibility.")
        except (ValueError, FloatingPointError, np.linalg.LinAlgError, mujoco.FatalError) as exc:
            return result(ReachabilityStatus.SOLVER_ERROR, message=f"{type(exc).__name__}: {exc}")

    def preview_data(self, scene: ChallengeScene, result: ReachabilityResult) -> mujoco.MjData:
        """Detached static endpoint preview, NOT an execution or motion-planning API.

        Revalidates against current scene after reset/object/other-arm changes.
        Only selected positioning joints and their actuator targets are assigned.
        """
        if not result.reachable or result.target.arm not in (None, result.arm):
            raise ValueError("preview requires a reachable result for the selected arm")
        metadata = arm_metadata(scene, result.arm)
        joints = tuple(j for j in metadata.joints if j.joint_id != metadata.gripper.joint_id)
        if result.joint_names != tuple(j.name for j in joints):
            raise ValueError("result joint mapping does not match current arm")
        q = _vector(result.joint_positions, len(joints), "solution joints")
        data = _scratch(scene)
        for joint, value in zip(joints, q):
            if not max(joint.limits[0], joint.control_range[0]) <= value <= min(joint.limits[1], joint.control_range[1]):
                raise ValueError("solution violates joint/control limits")
            data.qpos[joint.qpos_address] = value
            data.ctrl[joint.actuator_id] = value
        mujoco.mj_forward(scene.model, data)
        site = scene.model.site(metadata.end_effector).id
        if np.linalg.norm(data.site_xpos[site] - result.target.position) > self.config["tolerance_m"] or _arm_contacts(scene, data, result.arm):
            raise ValueError("solution is stale or unsafe in the current scene")
        return data
