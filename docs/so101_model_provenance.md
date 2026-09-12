# SO-101 model provenance and integration

## Source selection

No SO-101 or Intel challenge starter files were present in the repository before Stage 4. Public searches did not identify a verifiable official Intel challenge asset download. This does not establish that none exists; no private challenge portal was accessed. The permitted priority-2 source was therefore used directly: **TheRobotStudio's SO-101 simulation asset**, not a generic robot or an unknown community adaptation. This is an upstream robot model, not an Intel-certified challenge starter package.

- Repository: [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100).
- Pinned commit: `eecbe3e0a9ebb23e25ad7b2759b03884c6660903`.
- MJCF: [Simulation/SO101/so101_new_calib.xml](https://github.com/TheRobotStudio/SO-ARM100/blob/eecbe3e0a9ebb23e25ad7b2759b03884c6660903/Simulation/SO101/so101_new_calib.xml).
- Source description: [SO101 README at the same revision](https://github.com/TheRobotStudio/SO-ARM100/blob/eecbe3e0a9ebb23e25ad7b2759b03884c6660903/Simulation/SO101/README.md).
- The upstream XML identifies its Onshape CAD document and `onshape-to-robot` export. The upstream repository describes the SO-101 hardware family and its LeRobot association.

## Exact copied material and licensing

`assets/robots/so101/upstream/` preserves 16 files byte-for-byte: the MJCF, model README, root Apache-2.0 LICENSE, and these 13 meshes from `Simulation/SO101/assets/`:

- `waveshare_mounting_plate_so101_v2.stl`
- `sts3215_03a_v1.stl`
- `motor_holder_so101_base_v1.stl`
- `wrist_roll_follower_so101_v1.stl`
- `moving_jaw_so101_v1.stl`
- `base_motor_holder_so101_v1.stl`
- `upper_arm_so101_v1.stl`
- `wrist_roll_pitch_so101_v2.stl`
- `under_arm_so101_v1.stl`
- `rotation_pitch_so101_v1.stl`
- `motor_holder_so101_wrist_v1.stl`
- `sts3215_03a_no_horn_v1.stl`
- `base_so101_v2.stl`

The authoritative file inventory, original paths, byte sizes, and SHA256 values are in [source_manifest.json](../assets/robots/so101/source_manifest.json). Copied material totals 16,156,001 bytes (about 15.4 MiB), dominated by original binary STL meshes. These are necessary source assets, not generated results. No complete framework, camera variant, URDF, CAD exporter, or model package was installed/downloaded.

The [upstream Apache-2.0 license](../assets/robots/so101/upstream/LICENSE), [README](../assets/robots/so101/upstream/README.md), and all embedded credits are retained. [Local attribution](../assets/robots/so101/ATTRIBUTION.md) distinguishes our wrappers from upstream work. No applicable NOTICE file appeared in the inspected upstream tree. `.gitattributes` disables line-ending conversion only for the vendored originals so hashes survive Git checkout. The upstream files are not edited or reformatted.

The upstream README contains two lines with intentional Markdown trailing spaces. A whitespace attribute scoped to that README preserves those originals without reporting them as local trailing-space errors; local source/docs retain normal whitespace checks.

## Integration and local changes

No conversion was needed: upstream already supplies MJCF and STL meshes. There are no local robot geometry, collision, inertia, actuator, or limit changes. In particular, the separate upstream `joints_properties.xml` is not used: the chosen MJCF already embeds its actuator defaults, which differ from that standalone file.

DuetShift's `single_scene.xml` uses MuJoCo's native model attachment to import the unchanged `base` subtree, retaining its original names. This copies the referenced meshes/materials and existing actuators. An initial plain-include wrapper failed to resolve mesh paths; native attachment fixed the wrapper without editing upstream paths. The single arm was loaded and validated before constructing the dual scene.

The two attachments in `dual_scene.xml` add `arm_a/` and `arm_b/` prefixes to robot names and references. Both have identity orientation, facing approximately +X in the zero pose. Fixed bases are at `(0, -0.22, 0)` and `(0, 0.22, 0)` metres: 0.44 m apart, with a shared region ahead and between them intended for later cooperation. This placement is an initial scene choice, not a validated bimanual reachability or task solution. No handoff-specific placement optimization or IK was performed.

Both wrappers add a simple floor at z = -0.003 m and one light; the floor sits just below the upstream base visual extent. The bases are rigidly attached to the world, not supported by simulated base contact or added fake mounting geometry. Gravity is `(0, 0, -9.81)` and timestep 0.002 seconds, explicitly matching the tested MuJoCo defaults. There is no table or challenge object.

## Source-of-truth joint and actuator data

`JOINT_ROLES` and `describe_arm()` in [so101_model.py](../src/duetshift/sim/so101_model.py) are the code joint table. Numeric values are read from compiled upstream MJCF, rather than maintained as a conflicting second configuration. `inspect_so101.py` prints the complete table, including joint IDs, limits, actuator IDs/control ranges, and force ranges. The source order is:

1. `shoulder_pan`: base yaw; hinge; limits approximately [-1.9198621772, 1.9198621772] rad; same-name position actuator.
2. `shoulder_lift`: shoulder elevation; hinge; [-1.7453292520, 1.7453292520] rad; same-name position actuator.
3. `elbow_flex`: elbow flexion; hinge; [-1.69, 1.69] rad; same-name position actuator.
4. `wrist_flex`: wrist pitch; hinge; [-1.6580628495, 1.6580627293] rad; same-name position actuator.
5. `wrist_roll`: wrist roll; hinge; [-2.7438472970, 2.8412063094] rad; same-name position actuator.
6. `gripper`: moving-jaw hinge; [-0.1745329776, 1.7453291996] rad; same-name position actuator.

Control ranges are rounded upstream versions of these angular limits (within 1e-5 rad). All six existing position actuators have kp = 998.22, kv = 2.731, and per-actuator force range [-3.35, 3.35] N m. The inline defaults' [-2.94, 2.94] range is overridden by those actuator-level values. Joint damping 0.60, friction loss 0.052, and armature 0.028 are upstream settings. None were tuned locally, and these simulator gains are not asserted to equal real servo gains.

The single arm has six joints/actuators, IDs 0–5. In the dual model arm A uses 0–5 and arm B uses 6–11, with the same semantic order. Code resolves named IDs rather than assuming these offsets. Base body/site: `base` / `baseframe`. Tool reference: `gripperframe` on the `gripper` body. Moving finger: `moving_jaw_so101_v1`, driven by the `gripper` hinge. Prefix these names for each dual instance. The fixed jaw is part of the source gripper geometry; this is not a two-prismatic-finger abstraction.

## Initial pose and validation limits

The chosen new-calibration model initializes all six joint coordinates to zero. DuetShift sets constant position-actuator targets to those existing zero coordinates and leaves them unchanged. This is minimal rest initialization using source servos, not a new controller or trajectory. The gripper model's angular values are not LeRobot's normalized 0–100 open/closed convention.

Two-second idle checks monitor every physics step for finite state/acceleration, time advance, warning counters, joint-limit violation, unexpected contact, drift below 0.05 rad, and speed below 1 rad/s. Single and dual models passed, with maximum drift about 0.000765 rad and peak speed about 0.05035 rad/s, no contacts, and no numerical warnings.

Upstream visual geoms have collision disabled; the separate group-3 collision meshes remain active. Base collision meshes were already omitted upstream. MuJoCo uses convex mesh collision representations and normal parent-body filtering; no full-range self-collision or grasp-quality claim is made. The zero pose has no self/floor/inter-arm contacts. An intentional overlap in an isolated test produces inter-arm penetration, verifying that absence of contact in the normal scene is not due to disabled inter-arm collision. Collision refinements for future task poses must be assessed and documented in later stages.

Other limitations: no physical robot calibration/system identification was performed, no robot task was executed, and no reachability planner or hardware driver was added. The source rest pose is stable under active position servos; that is not a claim of passive unpowered stability.

The dual viewer opened, updated, and closed after its timed run. A separate render was visually checked: both complete arms are visible, separately mounted, and not visibly intersecting. All 23 previous/new tests passed, including source-hash verification and the Stage 3 renderer test. These results validate this initial integration, not later bimanual behavior.
