# DuetShift

Project for the Intel Physical AI Online Challenge: **Bimanual VLA Manipulation with Multi-Modal Reasoning**.

**CURRENT STATUS: Stage 3 — MuJoCo smoke foundation.** A sphere falls onto a floor with verified physics, optional viewing, and a small RGB render check. No robot control, AI policy, or OpenVINO functionality is implemented.

DuetShift's intended final concept is a pair of simulated SO-101 arms that follow natural-language goals, observe a shared workspace, and verify multi-step manipulation. When the world or the user's goal changes, the future system should revise affected steps, reconsider arm assignments, use handoffs when helpful, and verify the revised result. These are plans, not demonstrated capabilities.

## Documentation

- [Challenge requirements](docs/challenge_requirements.md)
- [Intended architecture](docs/architecture.md)
- [Build status](docs/build_status.md)
- [Repository and environment report](docs/environment_report.md)
- [Windows development setup](docs/development.md)

## Repository layout

- `src/duetshift/`: package foundation and placeholders for future components.
- `scripts/`, `tests/`: environment verification and basic package tests.
- `assets/mujoco/`: minimal smoke scene; `configs/` is reserved for later stages.
- `evaluation/`, `benchmarks/`: reserved for reproducible evaluation and Intel deployment evidence.
- `docs/`: project scope, plans, status, and audit findings.

Run `python scripts/run_mujoco_smoke.py` in the `duetshift-dev` Python 3.12 environment; see the development guide. There is no robot or challenge application yet. Final Intel deployment is a separate later stage.
