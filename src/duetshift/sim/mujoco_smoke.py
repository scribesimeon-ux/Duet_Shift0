"""Load, step, reset, and check the repository's single-body smoke scene."""

from dataclasses import dataclass
from pathlib import Path

import mujoco


def scene_path() -> Path:
    """Resolve assets from the editable repository installation, independent of cwd."""
    path = Path(__file__).resolve().parents[3] / "assets" / "mujoco" / "smoke_scene.xml"
    if not path.is_file():
        raise FileNotFoundError(
            f"Smoke scene not found at {path}. Use an editable install from the complete repository."
        )
    return path


class SmokeSimulation:
    """One independent model/data pair for the Stage 3 scene."""

    def __init__(self):
        self.model = mujoco.MjModel.from_xml_path(str(scene_path()))
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)

    @property
    def time(self) -> float:
        return float(self.data.time)

    @property
    def position(self) -> tuple[float, float, float]:
        return tuple(float(value) for value in self.data.body("falling_body").xpos)

    def step(self, steps: int = 1) -> None:
        if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
            raise ValueError("steps must be a non-negative integer")
        if steps:
            mujoco.mj_step(self.model, self.data, nstep=steps)
            # Refresh derived positions and contacts after the final integration step.
            mujoco.mj_forward(self.model, self.data)

    def reset(self) -> None:
        mujoco.mj_resetData(self.model, self.data)
        mujoco.mj_forward(self.model, self.data)

    def render_rgb(self):
        """Render one small frame; graphics errors propagate separately from physics."""
        with mujoco.Renderer(self.model, height=120, width=160) as renderer:
            renderer.update_scene(self.data, camera="smoke_camera")
            return renderer.render().copy()


@dataclass(frozen=True)
class PhysicsResult:
    initial_position: tuple[float, float, float]
    early_position: tuple[float, float, float]
    final_position: tuple[float, float, float]
    final_time: float
    checks: tuple[tuple[str, bool], ...]

    @property
    def passed(self) -> bool:
        return all(passed for _, passed in self.checks)


def validate_physics(sim: SmokeSimulation) -> PhysicsResult:
    """Check 2 seconds of actual dynamics, then restore the initial state."""
    sim.reset()
    initial = sim.position
    sim.step(50)  # 0.1 seconds: still in free fall.
    early = sim.position
    sim.step(450)  # 1 second total: should have reached the floor.
    settled = sim.position
    sim.step(500)  # Another second establishes sustained floor support.
    final = sim.position
    final_time = sim.time
    floor = sim.model.geom("floor").id
    sphere = sim.model.geom("falling_sphere").id
    touching_floor = any(
        {int(contact.geom1), int(contact.geom2)} == {floor, sphere}
        for contact in sim.data.contact
    )
    checks = (
        ("time advanced", abs(final_time - 1000 * sim.model.opt.timestep) < 1e-9),
        ("gravity moved the body downward", early[2] < initial[2] - 0.01),
        ("floor supports the sphere", touching_floor and 0.045 < final[2] < 0.06),
        ("support persists", 0.045 < settled[2] < 0.06 and abs(final[2] - settled[2]) < 0.005),
    )
    sim.reset()
    restored = (
        sim.time == 0.0
        and all(abs(a - b) < 1e-12 for a, b in zip(sim.position, initial))
        and bool((sim.data.qvel == 0).all())
    )
    return PhysicsResult(initial, early, final, final_time, checks + (("reset restored initial state", restored),))
