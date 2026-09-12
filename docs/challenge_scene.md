# Stage 05 challenge scene

This is a physical and visual environment foundation. It does not perform manipulation or complete a challenge task. No official Intel starter scene was present locally. The table, drawer and household objects are original simplified MuJoCo primitives, not claimed to be official challenge assets.

## Composition and robot provenance

`src/duetshift/sim/challenge_scene.py` composes a generated MJCF wrapper around the unchanged Stage 04 SO-101 model. See [SO-101 provenance](so101_model_provenance.md): TheRobotStudio/SO-ARM100 commit `eecbe3e0a9ebb23e25ad7b2759b03884c6660903`, Apache-2.0. No upstream file, mesh, robot collision mask, inertia, joint limit or actuator gain is changed. The old single/dual wrappers remain available.

`configs/challenge_scene.json` centralizes table dimensions, base placement, workspace bounds, drawer dimensions/travel, object spawn regions/masses/colors, camera poses and conservative randomization. Object primitive dimensions are grouped in `_object_geometry`, rather than duplicated in XML assets. All lengths are metres, masses kilograms, and yaw values radians. No additional asset or Python package download is required.

## Table and layout

The fixed four-legged table has a 0.68 by 0.80 m top, 0.035 m thick, with its surface at z=0.70 m. It spans x=-0.12..0.56 and y=-0.40..0.40. Both arms face +X at bases `(0, -0.22, 0.703)` and `(0, 0.22, 0.703)`, retaining the 0.44 m separation. They are fixed mounts, with their actual lowest base mesh vertices about 0.6 mm above the table surface to avoid initial penetration.

Table-object bounds are x=0.25..0.51, y=-0.24..0.25. The drawer occupies the central area nearer the bases. A shared region ahead and between the arms remains available for future cooperation. This layout is geometrically plausible; joint-space reachability and manipulation feasibility have not been solved or certified.

## Physical drawer

The cabinet center is `(0.14, -0.02)` on the table. Its envelope is 0.18 by 0.16 by 0.055 m. The tray is 0.15 by 0.13 m with 0.035 m walls and a floor support surface at z=0.710 m. Cabinet sides/back/bottom, tray floor/walls and a protruding three-part handle all have collision geometry.

`drawer/slide` is a physical prismatic joint along +Y, limited to 0..0.09 m. It starts closed at zero, has damping 2 and friction loss 0.4, and has no actuator. The joint is the mechanical guide: it prevents the tray from falling or rotating. Clearance separates tray/cabinet collision shapes. The cabinet has an intentionally open top so the fork/spoon can be inspected in the closed state. This is a simplified drawer fixture, not an opaque full-size household cabinet.

`initialize_drawer_position(position)` is diagnostic initialization at a valid joint coordinate; it shifts utensil starting poses with the tray. It is not an opening trajectory or controller. Tests initialize and settle the scene at closed, quarter, half, three-quarter and fully open positions. Reset always restores the closed state.

## Objects and metadata

- **Plate:** 130 mm main disk, 6 mm thick, with a low segmented raised rim; nominal mass 120 g.
- **Mug:** hollow compound cup with a bottom, ring of walls and an open three-bar handle; nominal mass 90 g. Handle clearance is present, but grasp feasibility is untested.
- **Bottle:** flat-bottom cylinder, rounded shoulder and narrow neck; nominal mass 140 g. It is rigid and contains no liquid.
- **Fork:** handle, shoulder and four separate tines; nominal mass 18 g, initially inside the tray.
- **Spoon:** handle and simple ellipsoid bowl; nominal mass 18 g, initially inside the tray. Its bowl is solid, not a fluid container.

Every object is one free rigid body with positive inferred inertia and collidable primitive parts. Mass is distributed across its parts as a simple approximation, not calibrated material density. The `ObjectInfo` registry supplies semantic/body/joint names and IDs, geometry IDs, initial xyz+wxyz quaternion, support and randomization category. Colors and names remain identifiable.

`ChallengeScene` exposes `model`, `data`, `arm_a`, `arm_b`, `objects`, `drawer`, `cameras`, `config`, `seed` and `samples`. This is scene metadata, not a task world-state system.

## Deterministic reset

```python
from duetshift.sim.challenge_scene import load_challenge_scene
scene = load_challenge_scene(seed=42)
original = scene.samples
scene.reset(seed=43)
scene.reset(seed=42)
assert scene.samples == original
```

Each reset uses a private `random.Random(seed)` and recreates model/data so sampled scale, mass and inferred inertia are consistent. The same seed plus the same configuration and software versions produces the same sampled configuration. It does not promise identical simulation across different MuJoCo/hardware versions. References to old model/data or IDs must be refreshed after reset.

Enabled conservative ranges:

- Table-object XY jitter: +/-8 mm per axis; drawer utensils: +/-2 mm.
- Yaw: +/-0.06 rad (about 3.4 degrees).
- Mass: nominal times 0.9..1.1.
- Object sliding friction: 0.7..0.9. Supporting surfaces use 0.6, so their friction does not mask the sampled value.
- Uniform size variants: 0.98, 1.00 or 1.02, retaining object identity; no alternative topology yet.
- Light intensity multiplier: 0.9..1.1; two neutral floor/background color variants.

`scene.samples` and the runner expose every actual sampled value. Configuring zero jitter/yaw, equal multiplier endpoints or singleton variant lists disables the corresponding variation. The supplied conservative configuration is validated; arbitrary user range increases are not automatically made safe. Invalid sampled layouts raise a clear error instead of silently spawning objects through geometry.

## Cameras and inspection

- `overview`: complete work surface and both arms; small utensils may be occluded at this angle.
- `task`: overhead angle showing all five objects and the central workspace.
- `drawer`: closer view of the tray and both utensils.

The renderer checks 320x240 uint8 RGB frames for shape and non-uniform content. MuJoCo geometry segmentation verifies both arms/table in overview, plate/mug/bottle in task, and fork/spoon in drawer. This is visibility validation using simulator IDs, not AI perception. Routine tests keep frames in memory. Optional PNGs go to ignored `tmp/challenge_scene/`.

## Physical checks and limits

The timestep remains 0.002 s. A standard check steps 750 times (1.5 simulated seconds), holds the existing constant source servo targets, and monitors finite state, warning counters, time progression, joint limits, robot/drawer drift, unexpected contacts and final object support/speed. No contact is allowed at the initial 2 mm spawn gap. During settling only each object's assigned table/tray-floor contact is accepted, with at most 0.8 mm temporary soft penetration. Scene object/support `solref="0.008 1"` keeps thin-object settling within this limit. Robot contact parameters remain unchanged. See the [MuJoCo contact parameter documentation](https://mujoco.readthedocs.io/en/stable/modeling.html#contact-parameters).

Footprint checks account for scale and yaw, table/drawer bounds and pairwise overlap. Actual MuJoCo contacts detect robot-object, robot-table, inter-arm and utensil-wall conflicts. Because the upstream base omits some collision geometry, actual transformed base mesh vertices are also checked against the table height. No robot safety collider has been invented. This protects the supplied initial poses, not all future robot motions.

The scene is a small reproducible teaching/test environment. Object shapes, masses, contacts, drawer guide and camera coverage need later task-specific validation. No IK, grasping, drawer-opening control, handoff, perception, planning, recovery, policy, liquid simulation or final Intel deployment is included.
