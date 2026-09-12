"""Stage 05 scene composition, seeded initialization and physical inspection only.

Robot meshes, joints and actuator definitions are attached unchanged from Stage 04.
No task controller, inverse kinematics, grasping or learned perception lives here.
"""

from dataclasses import dataclass
from pathlib import Path
import json
import math
import random
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from .so101_model import asset_directory, describe_arm, initialize_rest

CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs" / "challenge_scene.json"


def _text(values):
    return " ".join(str(float(v)) for v in values)


def _element(parent, tag, **attributes):
    return ET.SubElement(parent, tag, {k: str(v) for k, v in attributes.items()})


@dataclass(frozen=True)
class ObjectInfo:
    semantic_name: str
    body_name: str
    body_id: int
    free_joint: str
    joint_id: int
    geom_ids: tuple[int, ...]
    initial_pose: tuple[float, ...]  # xyz followed by quaternion wxyz
    randomization_category: str
    support: str


@dataclass(frozen=True)
class DrawerInfo:
    body_name: str
    body_id: int
    joint_name: str
    joint_id: int
    limits: tuple[float, float]
    handle_geoms: tuple[str, ...]


@dataclass(frozen=True)
class CameraInfo:
    name: str
    camera_id: int
    role: str


def _object_geometry(body, name, sample, color):
    """Small compound primitives with local bottom at z=0; lengths are metres."""
    parts = []

    def part(kind, size, pos=(0, 0, 0), **attrs):
        parts.append((kind, size, pos, attrs))

    if name == "plate":
        part("cylinder", (.065, .003), (0, 0, .003))
        for i in range(20):
            angle = 2 * math.pi * i / 20
            part("box", (.004, .0106, .002), (.065 * math.cos(angle), .065 * math.sin(angle), .008),
                 quat=_text((math.cos(angle / 2), 0, 0, math.sin(angle / 2))))
    elif name == "mug":
        part("cylinder", (.028, .002), (0, 0, .002))
        for i in range(16):
            angle = 2 * math.pi * i / 16
            part("box", (.002, .0056, .0305), (.026 * math.cos(angle), .026 * math.sin(angle), .0345),
                 quat=_text((math.cos(angle / 2), 0, 0, math.sin(angle / 2))))
        # Three bars leave an actual opening through the mug handle.
        part("box", (.011, .004, .004), (.036, 0, .015))
        part("box", (.011, .004, .004), (.036, 0, .055))
        part("box", (.004, .004, .024), (.047, 0, .035))
    elif name == "bottle":
        part("cylinder", (.024, .042), (0, 0, .042))
        part("ellipsoid", (.024, .024, .018), (0, 0, .080))
        part("cylinder", (.010, .013), (0, 0, .103))
    elif name == "fork":
        part("box", (.035, .003, .002), (-.018, 0, .002))
        part("box", (.010, .012, .002), (.023, 0, .002))
        for y in (-.009, -.003, .003, .009):
            part("box", (.012, .001, .002), (.044, y, .002))
    elif name == "spoon":
        part("box", (.037, .003, .002), (-.016, 0, .002))
        part("ellipsoid", (.019, .012, .003), (.037, 0, .003))
    else:
        raise ValueError(f"Unknown primitive object: {name}")
    for i, (kind, size, pos, attrs) in enumerate(parts):
        scale = sample["scale"]
        _element(body, "geom", name=f"object/{name}/{i}", type=kind,
                 size=_text(np.array(size) * scale), pos=_text(np.array(pos) * scale),
                 mass=sample["mass"] / len(parts), rgba=_text(color),
                 friction=f'{sample["friction"]} 0.005 0.0001', condim="3", solref="0.008 1", **attrs)


def _build_xml(config, samples):
    root = ET.Element("mujoco", model="duetshift_challenge_stage05")
    _element(root, "option", timestep=config["simulation"]["timestep"], gravity="0 0 -9.81")
    _element(root, "size", njmax="2000", nconmax="1000")
    asset = _element(root, "asset")
    _element(asset, "model", name="so101", file=str(asset_directory() / "upstream" / "so101_new_calib.xml"))
    world = _element(root, "worldbody")
    _element(world, "light", name="workspace_light", pos="0.2 -0.3 2", diffuse=_text([.7 * samples["light_gain"]] * 3))
    _element(world, "geom", name="room/floor", type="plane", size="2 2 .05", rgba=_text(samples["background"]))
    table = config["table"]
    sx, sy, thickness = table["size"]
    tx, ty = table["center_xy"]
    surface = table["surface_z"]
    _element(world, "geom", name="table/top", type="box", size=_text((sx / 2, sy / 2, thickness / 2)),
             pos=_text((tx, ty, surface - thickness / 2)), rgba=".60 .44 .28 1", solref="0.008 1", friction="0.6 0.005 0.0001")
    for i, (dx, dy) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        height = surface - thickness
        _element(world, "geom", name=f"table/leg{i}", type="box", size=_text((.022, .022, height / 2)),
                 pos=_text((tx + dx * (sx / 2 - .04), ty + dy * (sy / 2 - .04), height / 2)), rgba=".25 .25 .27 1")
    for arm, pos in config["robots"].items():
        frame = _element(world, "frame", name=f"{arm}_mount", pos=_text(pos))
        _element(frame, "attach", model="so101", body="base", prefix=f"{arm}/")

    d = config["drawer"]
    x, y = d["center_xy"]
    width, depth, height = d["cabinet_size"]
    cabinet = _element(world, "body", name="drawer/cabinet", pos=_text((x, y, surface)))
    _element(cabinet, "geom", name="drawer/cabinet_bottom", type="box", size=_text((width / 2, depth / 2, .002)), pos="0 0 .002", rgba=".28 .32 .38 1")
    for side in (-1, 1):
        _element(cabinet, "geom", name=f"drawer/cabinet_side{side}", type="box", size=_text((.003, depth / 2, height / 2)), pos=_text((side * (width / 2 - .003), 0, height / 2)), rgba=".28 .32 .38 1")
    _element(cabinet, "geom", name="drawer/cabinet_back", type="box", size=_text((width / 2, .003, height / 2)), pos=_text((0, -depth / 2 + .003, height / 2)), rgba=".28 .32 .38 1")
    # Open top deliberately exposes utensils to cameras. Slide joint is the guide.
    tray = _element(world, "body", name="drawer/tray", pos=_text((x, y, d["floor_z"] - .002)))
    _element(tray, "joint", name="drawer/slide", type="slide", axis="0 1 0", limited="true", range=f'0 {d["travel"]}', damping="2", frictionloss="0.4")
    tw, td, th = d["tray_size"]
    wall = d["wall"]
    _element(tray, "geom", name="drawer/tray_floor", type="box", size=_text((tw / 2, td / 2, .002)), mass=".12", rgba=".65 .69 .74 1", solref="0.008 1", friction="0.6 0.005 0.0001")
    for side in (-1, 1):
        _element(tray, "geom", name=f"drawer/tray_side{side}", type="box", size=_text((wall / 2, td / 2, th / 2)), pos=_text((side * (tw / 2 - wall / 2), 0, th / 2)), mass=".015", rgba=".65 .69 .74 1")
        _element(tray, "geom", name=f"drawer/tray_end{side}", type="box", size=_text((tw / 2, wall / 2, th / 2)), pos=_text((0, side * (td / 2 - wall / 2), th / 2)), mass=".015", rgba=".65 .69 .74 1")
    for side in (-1, 1):
        _element(tray, "geom", name=f"drawer/handle_post{side}", type="box", size=".004 .010 .004", pos=_text((side * .028, td / 2 + .008, .021)), mass=".004", rgba=".12 .13 .15 1")
    _element(tray, "geom", name="drawer/handle", type="box", size=".032 .004 .004", pos=_text((0, td / 2 + .019, .021)), mass=".012", rgba=".12 .13 .15 1")
    for name, obj in config["objects"].items():
        sample = samples["objects"][name]
        body = _element(world, "body", name=f"object/{name}", pos=_text(sample["xyz"]), quat=_text(sample["quat"]))
        _element(body, "freejoint", name=f"object/{name}/free")
        _object_geometry(body, name, sample, obj["rgba"])
    for name, camera in config["cameras"].items():
        z = np.array(camera["pos"]) - camera["target"]
        z /= np.linalg.norm(z)
        x_axis = np.cross([0., 0., 1.], z)
        x_axis /= np.linalg.norm(x_axis)
        y_axis = np.cross(z, x_axis)
        _element(world, "camera", name=name, pos=_text(camera["pos"]), xyaxes=_text(np.r_[x_axis, y_axis]), fovy=camera["fovy"])
    return ET.tostring(root, encoding="unicode")


class ChallengeScene:
    """Model/data and scene metadata. Reset recompiles to keep mass/inertia consistent."""

    def __init__(self, seed=42, config_path=CONFIG_PATH):
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.reset(seed)

    def reset(self, seed=42):
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("seed must be an integer")
        rng = random.Random(seed)
        self.seed = seed
        config = self.config
        policy = config["randomization"]
        self.samples = {"seed": seed, "light_gain": rng.uniform(*policy["light_gain"]),
                        "background": list(rng.choice(policy["backgrounds"])), "objects": {}}
        for name, obj in config["objects"].items():
            support = obj["support"]
            jitter = policy[f"{support}_xy"]
            xy = [value + rng.uniform(-jitter, jitter) for value in obj["xy"]]
            yaw = rng.uniform(-policy["yaw"], policy["yaw"])
            z = config["table"]["surface_z"] if support == "table" else config["drawer"]["floor_z"]
            self.samples["objects"][name] = {
                "xyz": [*xy, z + policy["spawn_gap"]],
                "quat": [math.cos(yaw / 2), 0., 0., math.sin(yaw / 2)], "yaw": yaw,
                "mass": obj["mass"] * rng.uniform(*policy["mass_multiplier"]),
                "friction": rng.uniform(*policy["friction"]), "scale": rng.choice(policy["scale_variants"]),
            }
        self.model = mujoco.MjModel.from_xml_string(_build_xml(config, self.samples))
        self.arm_a = describe_arm(self.model, "arm_a/")
        self.arm_b = describe_arm(self.model, "arm_b/")
        self.data = initialize_rest(self.model, (self.arm_a, self.arm_b))
        self.objects = {}
        for name, obj in config["objects"].items():
            body_name, joint_name = f"object/{name}", f"object/{name}/free"
            body_id = self.model.body(body_name).id
            sample = self.samples["objects"][name]
            self.objects[name] = ObjectInfo(name, body_name, body_id, joint_name,
                self.model.joint(joint_name).id,
                tuple(int(i) for i in np.flatnonzero(self.model.geom_bodyid == body_id)),
                tuple(sample["xyz"] + sample["quat"]), f'{obj["support"]}_object', obj["support"])
        jid = self.model.joint("drawer/slide").id
        self.drawer = DrawerInfo("drawer/tray", self.model.body("drawer/tray").id, "drawer/slide", jid,
                                 tuple(map(float, self.model.jnt_range[jid])),
                                 ("drawer/handle", "drawer/handle_post-1", "drawer/handle_post1"))
        self.cameras = {name: CameraInfo(name, self.model.camera(name).id, camera["role"])
                        for name, camera in config["cameras"].items()}
        errors = self.spawn_errors()
        if errors:
            raise ValueError("Invalid initialized scene: " + "; ".join(errors))
        return self

    def spawn_errors(self):
        """Check conservative footprints, support heights, actual contacts and base clearance."""
        errors, footprints = [], {}
        config = self.config
        for name, obj in config["objects"].items():
            sample = self.samples["objects"][name]
            x, y, z = sample["xyz"]
            a = abs(sample["yaw"])
            hx, hy = np.array(obj["footprint"]) * sample["scale"]
            ext = np.array([hx * math.cos(a) + hy * math.sin(a), hx * math.sin(a) + hy * math.cos(a)])
            footprints[name] = (np.array([x, y]), ext)
            if obj["support"] == "table":
                bounds = np.array(config["workspace_xy"])
                support_z = config["table"]["surface_z"]
            else:
                d = config["drawer"]
                half = np.array(d["tray_size"][:2]) / 2 - d["wall"]
                center = np.array(d["center_xy"])
                bounds = np.column_stack((center - half, center + half))
                support_z = d["floor_z"]
            if np.any(np.array([x, y]) - ext < bounds[:, 0]) or np.any(np.array([x, y]) + ext > bounds[:, 1]):
                errors.append(f"{name} outside its support bounds")
            if z < support_z or z > support_z + .01:
                errors.append(f"{name} has invalid support height")
        names = list(footprints)
        for i, name in enumerate(names):
            for other in names[i + 1:]:
                p, ext = footprints[name]
                q, other_ext = footprints[other]
                if np.all(np.abs(p - q) < ext + other_ext):
                    errors.append(f"overlapping spawn footprints: {name}, {other}")
        # The upstream base has visual meshes but incomplete collision geometry.
        # Check actual transformed mesh vertices; rotated AABBs overestimate clearance.
        surface = config["table"]["surface_z"]
        for arm in (self.arm_a, self.arm_b):
            bid = self.model.body(arm.base).id
            for gid in np.flatnonzero(self.model.geom_bodyid == bid):
                center, half = self.model.geom_aabb[gid, :3], self.model.geom_aabb[gid, 3:]
                rotation = self.data.geom_xmat[gid].reshape(3, 3)
                if self.model.geom_type[gid] == mujoco.mjtGeom.mjGEOM_MESH:
                    mid = self.model.geom_dataid[gid]
                    start = self.model.mesh_vertadr[mid]
                    vertices = self.model.mesh_vert[start:start + self.model.mesh_vertnum[mid]]
                    bottom = float((vertices @ rotation.T + self.data.geom_xpos[gid])[:, 2].min())
                else:
                    bottom = (self.data.geom_xpos[gid] + rotation @ center)[2] - (np.abs(rotation) @ half)[2]
                if bottom < surface - .0001:
                    errors.append(f"{arm.base} visual bound intersects table")
        errors.extend(str(item) for item in self.unexpected_contacts())
        return errors

    def unexpected_contacts(self):
        bad = []
        tolerance = self.config["simulation"]["penetration_tolerance"]
        for contact in self.data.contact:
            a, b = (self.model.geom(int(gid)).name for gid in (contact.geom1, contact.geom2))
            names = {a, b}
            expected = False
            for obj in self.objects.values():
                if any(n.startswith(obj.body_name + "/") for n in names):
                    support = "table/top" if obj.support == "table" else "drawer/tray_floor"
                    expected = support in names
                    break
            if not expected or contact.dist < -tolerance:
                bad.append({"geom_a": a, "geom_b": b, "distance_m": float(contact.dist), "expected_support_pair": expected, "body_a": self.model.body(self.model.geom_bodyid[contact.geom1]).name, "body_b": self.model.body(self.model.geom_bodyid[contact.geom2]).name})
        return bad

    def initialize_drawer_position(self, position):
        """Diagnostic initialization, carrying utensil poses; this is not an opening controller."""
        if not self.drawer.limits[0] <= position <= self.drawer.limits[1]:
            raise ValueError("drawer position outside joint limits")
        adr = self.model.jnt_qposadr[self.drawer.joint_id]
        delta = position - self.data.qpos[adr]
        self.data.qpos[adr] = position
        for obj in self.objects.values():
            if obj.support == "drawer":
                self.data.qpos[self.model.jnt_qposadr[obj.joint_id] + 1] += delta
        self.data.qvel[:] = 0
        mujoco.mj_forward(self.model, self.data)

    def validate_stability(self, steps=None):
        steps = self.config["simulation"]["settle_steps"] if steps is None else steps
        if not isinstance(steps, int) or isinstance(steps, bool) or steps <= 0:
            raise ValueError("steps must be a positive integer")
        model, data = self.model, self.data
        cfg = self.config["simulation"]
        addresses = [j.qpos_address for arm in (self.arm_a, self.arm_b) for j in arm.joints]
        initial_robot = data.qpos[addresses].copy()
        initial_ctrl = data.ctrl.copy()
        drawer_adr = model.jnt_qposadr[self.drawer.joint_id]
        initial_drawer, start = float(data.qpos[drawer_adr]), float(data.time)
        errors, maximum_drift, maximum_drawer_drift = [], 0., 0.
        for i in range(steps):
            mujoco.mj_step(model, data)
            if not all(np.isfinite(v).all() for v in (data.qpos, data.qvel, data.qacc)) or data.warning.number.any():
                errors.append("non-finite physics state or MuJoCo warning")
                break
            if abs(data.time - (start + (i + 1) * model.opt.timestep)) > 1e-8:
                errors.append("simulation time discontinuity")
                break
            maximum_drift = max(maximum_drift, float(np.max(np.abs(data.qpos[addresses] - initial_robot))))
            maximum_drawer_drift = max(maximum_drawer_drift, abs(float(data.qpos[drawer_adr]) - initial_drawer))
            bad = self.unexpected_contacts()
            if bad:
                errors.append(f"unexpected contact: {bad[:3]}")
                break
        mujoco.mj_forward(model, data)
        if self.unexpected_contacts():
            errors.append("unexpected final contact")
        for arm in (self.arm_a, self.arm_b):
            for joint in arm.joints:
                q = data.qpos[joint.qpos_address]
                if not joint.limits[0] - .001 <= q <= joint.limits[1] + .001:
                    errors.append(f"joint outside limits: {joint.name}")
        if maximum_drift > cfg["max_robot_drift"] or maximum_drawer_drift > .002:
            errors.append("robot or drawer drift exceeded rest tolerance")
        if not np.array_equal(initial_ctrl, data.ctrl):
            errors.append("rest servo targets changed")
        speeds = {}
        for name, obj in self.objects.items():
            dof = model.jnt_dofadr[obj.joint_id]
            linear = float(np.linalg.norm(data.qvel[dof:dof + 3]))
            angular = float(np.linalg.norm(data.qvel[dof + 3:dof + 6]))
            speeds[name] = {"linear_m_s": linear, "angular_rad_s": angular}
            if linear > cfg["max_object_speed"] or angular > cfg["max_object_angular_speed"]:
                errors.append(f"{name} did not settle")
            support = "table/top" if obj.support == "table" else "drawer/tray_floor"
            support_id = model.geom(support).id
            supported = any((int(c.geom1) in obj.geom_ids and c.geom2 == support_id) or
                            (int(c.geom2) in obj.geom_ids and c.geom1 == support_id) for c in data.contact)
            if not supported:
                errors.append(f"{name} has no resting support contact")
        return {"passed": not errors, "errors": errors, "time_s": float(data.time),
                "max_robot_drift_rad": maximum_drift, "max_drawer_drift_m": maximum_drawer_drift,
                "object_speeds": speeds, "warning_counts": data.warning.number.tolist()}

    def render_cameras(self, width=320, height=240):
        """RGB frames and geometric visibility counts; no learned perception or saved images."""
        frames, reports = {}, {}
        with mujoco.Renderer(self.model, height=height, width=width) as renderer:
            for name in self.cameras:
                renderer.disable_segmentation_rendering()
                renderer.update_scene(self.data, camera=name)
                rgb = renderer.render().copy()
                if rgb.shape != (height, width, 3) or rgb.dtype != np.uint8 or float(rgb.std()) < 2:
                    raise RuntimeError(f"Invalid or blank RGB camera: {name}")
                frames[name] = rgb
                renderer.enable_segmentation_rendering()
                renderer.update_scene(self.data, camera=name)
                segmentation = renderer.render()
                ids = segmentation[:, :, 0]
                is_geom = segmentation[:, :, 1] == mujoco.mjtObj.mjOBJ_GEOM
                counts = {obj.semantic_name: int(np.count_nonzero(is_geom & np.isin(ids, obj.geom_ids))) for obj in self.objects.values()}
                counts["table"] = int(np.count_nonzero(is_geom & (ids == self.model.geom("table/top").id)))
                for arm in (self.arm_a, self.arm_b):
                    geom_ids = [i for i in range(self.model.ngeom) if self.model.body(self.model.geom_bodyid[i]).name.startswith(arm.prefix)]
                    counts[arm.prefix.rstrip("/")] = int(np.count_nonzero(is_geom & np.isin(ids, geom_ids)))
                required = {"overview": ("table", "arm_a", "arm_b"), "task": ("table", "plate", "mug", "bottle"), "drawer": ("fork", "spoon")}[name]
                if any(counts[item] < 4 for item in required):
                    raise RuntimeError(f"Camera {name} missing required visibility: {counts}")
                reports[name] = {"shape": list(rgb.shape), "dtype": str(rgb.dtype), "std": float(rgb.std()), "visible_pixels": counts}
        return frames, reports


def load_challenge_scene(seed=42, config_path=CONFIG_PATH):
    return ChallengeScene(seed, config_path)
