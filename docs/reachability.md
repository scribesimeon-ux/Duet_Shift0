# Stage 06: reachability foundation

Stage 06 asks a limited question: can an arm place its existing SO-101 `gripperframe` site near a requested world-space point while respecting joint limits and avoiding detected contacts at that endpoint?

A `reachable` result means a position solution within 2 mm and no detected contact involving the chosen arm at that endpoint. It does **not** demonstrate a grasp, the right gripper orientation, a collision-free path, simultaneous bimanual motion, or physical tracking under load. There is no live motion-command API in this stage.

## Architecture and API

`src/duetshift/sim/reachability.py` works directly with `ChallengeScene`, its current `ArmInfo` records, named sites, joints, control ranges, object registry and drawer handle. No robot description is duplicated, and Stage 05 files/acceptance behavior are unchanged.

```python
from duetshift.sim.challenge_scene import load_challenge_scene
from duetshift.sim.reachability import ReachabilitySolver, end_effector_state

scene = load_challenge_scene(seed=42)
solver = ReachabilitySolver()
state = end_effector_state(scene, "arm_a")
target = solver.approach_target(scene, "plate", arm="arm_a")
result = solver.solve(scene, target)
print(result.status.value, result.position_error_m)
if result.reachable:
    preview = solver.preview_data(scene, result)  # independent MjData, not scene.data
```

`TaskTarget` contains a nonempty name/semantic role, three Cartesian coordinates in **world metres**, an optional `arm_a`/`arm_b` association, and an optional unit quaternion in wxyz order. Invalid shapes, non-finite values, booleans, unknown arms and nonunit quaternions are rejected. If a target has no associated arm, provide an explicit arm to `solve`. Conflicting arm selections are rejected.

`EndEffectorState` returns the actual site position, world orientation quaternion, all six named joint coordinates (radians, including the jaw), and arm identity. It computes forward kinematics on independent data, so it is current even after direct joint-state changes.

Orientation is represented and reported, but the solver is intentionally **position-only**. An orientation-constrained request returns `unsupported_orientation`; it is never silently treated as satisfied.

## Bounded IK

Inverse kinematics (IK) searches for joint angles that put the gripper reference point near the target. MuJoCo supplies the positional site Jacobian: the local relationship between small joint changes and point movement. The solver takes damped least-squares steps, limits their size, clips them to the intersection of source joint/control limits, and uses a short line search to reduce position error.

Only the five non-gripper joints are solved. The moving-jaw joint stays at its existing value. Each attempt has at most 100 iterations, with up to four deterministic initial guesses. The first guess is the current pose; later guesses use a private fixed-seed NumPy generator. No global random state or Stage 05 seed stream is consumed. Defaults and approach offsets live in `configs/reachability.json`; no new dependency is needed.

Every trial uses independently copied `MjData` and the unchanged scene model. Live qpos, velocities, actuator commands, objects, drawer, simulation time and reset samples are preserved. The solver reads fresh mappings each call, so it can be reused after a scene reset. Reproducibility assumes the same input state, config and software versions.

The method uses the [official MuJoCo Jacobian API](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html#mj-jacsite) and [Python data-copy support](https://mujoco.readthedocs.io/en/stable/python.html). This is a bounded local solver, not an exhaustive reachability proof.

## Result meanings

- `reachable`: positional tolerance met and no detected selected-arm endpoint contacts.
- `outside_workspace`: rejected before IK by the configured table-volume policy. The full table XY rectangle is used so drawer targets remain eligible; permitted height is 15-550 mm above its surface. This is a scope boundary, not a physical reach certificate.
- `ik_failed`: the bounded local search did not converge. A different initial guess, target or future method might succeed.
- `endpoint_collision`: IK converged, but the tested converged configurations contacted robot/scene geometry. No contact-free endpoint was found.
- `solver_error`: numerical/state failure with an explanatory message; no commands are issued.
- `unsupported_orientation`: an orientation constraint was requested but is not implemented.

Results expose error in metres, total iterations, positioning joint names/angles, detected contact body pairs and an explanation. Failed results are diagnostic and cannot be previewed as accepted solutions.

## Approach targets

Semantic choices are `table`, `plate`, `mug`, `bottle`, `fork`, `spoon` and `drawer_handle`.

Object targets use the object's current XY and a conservative transformed geometry-bound top plus 80 mm. This accounts for current pose, sampled scale and objects that have settled. These are standoff points, not contact or grasp poses.

The drawer target follows its actual handle center, offset 70 mm forward along the scene drawer's +Y direction and 80 mm upward. Opening the drawer through diagnostic initialization changes the target accordingly. The table target is above the center of Stage 05's object workspace at 140 mm above the table.

Offsets are configurable. They provide simple approach intent, not a guarantee that the complete gripper or route clears every obstacle; the solver separately checks endpoint contacts.

## Dual-arm safety and previews

Arm mapping comes from Stage 05 and must be disjoint. Solving modifies **no live actuator**. A detached preview assigns only the selected arm's five positioning coordinates and matching actuator targets. The opposite arm, jaw, objects and drawer retain their copied state. Preview data is rechecked against the current model/site, limits and collisions; stale solutions that now intersect an obstacle are rejected.

Collision awareness uses contacts actually generated by the upstream MuJoCo collision model, including self, opposite arm, table, drawer and objects. It checks the final configuration only. Existing source collision exclusions, convex approximations and incomplete base collision geometry still apply. It does not establish a positive clearance margin. Do not feed these joint vectors directly into a hardware or motion controller.

The optional viewer is a **static endpoint preview**. It displays the selected arm at the solved configuration and a pink sphere at the target. There is no physics stepping, interpolation, tracking validation, grasp or movement demonstration. It auto-closes after a bounded duration; rendering/viewer workers also have parent timeouts. Inspection PNGs are optional, saved only under ignored `tmp/reachability/`.

## Beginner commands

Open the authoritative project folder, open a PowerShell terminal, activate `duetshift-dev`, and verify Python 3.12 and the package path as described in [development setup](development.md).

```powershell
python scripts/check_reachability.py
python scripts/check_reachability.py --arm arm_a --target bottle
python scripts/check_reachability.py --arm arm_b --target mug --seed 43
python scripts/check_reachability.py --seed 42 --all
python scripts/check_reachability.py --seed 43 --all
python scripts/check_reachability.py --arm arm_a --target bottle --viewer
python scripts/check_reachability.py --arm arm_b --target mug --render
```

The default is arm A's plate approach. `--all` checks all seven targets with both arms; it prints unsuccessful pairings and passes only if every semantic target has at least one accepted arm and both arms have useful solutions. That coverage test does not assign tasks or coordinate motion.

For a custom point, use `--position X Y Z`. A single rejected target returns a nonzero exit status, as intended:

```powershell
python scripts/check_reachability.py --arm arm_a --position 10 0 1
```

This reports `outside_workspace` and exits 1. An invalid/failed IK query is not disguised as success. Use `--viewer-seconds 120` for a longer static inspection (allowed 1-300 seconds). `--save-image` writes a small local preview PNG and also requests rendering.

```powershell
python -m pytest tests/test_reachability.py
python -m pytest
python -m pip check
```

## Observed coverage and later work

For the tested scenes, both arms found accepted table, plate, fork, spoon and drawer-handle approach endpoints. Arm A found the bottle approach; arm B found the mug approach. The opposite mug/bottle pairings failed to converge and remain explicitly reported. No scene objects or arm bases were moved to make those pairings pass.

Stage 07 must separately establish suitable gripper orientation, safe paths, dynamic tracking, grasp/contact feasibility and any actual object manipulation. Independently reachable arm configurations are not necessarily safe together. No scene controller, grasp planner, policy training, learned perception, networking or hardware support was added here.
