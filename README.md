# DuetShift

Project for the Intel Physical AI Online Challenge: **Bimanual VLA Manipulation with Multi-Modal Reasoning**.

**CURRENT STATUS: Stage 2 — Python environment and package setup.** No simulation, robot control, AI policy, or OpenVINO functionality is implemented.

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
- `configs/`, `assets/`: reserved for later stages.
- `evaluation/`, `benchmarks/`: reserved for reproducible evaluation and Intel deployment evidence.
- `docs/`: project scope, plans, status, and audit findings.

There is no runnable robotics application. Local development uses the `duetshift-dev` Conda environment with Python 3.12 and pytest; see the development guide. Final Intel deployment is a separate later stage.
