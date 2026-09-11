# DuetShift

Project for the Intel Physical AI Online Challenge: **Bimanual VLA Manipulation with Multi-Modal Reasoning**.

**CURRENT STATUS: Stage 1 only — repository and machine audit, documentation, and empty project scaffolding.** No simulation, robot control, AI policy, or OpenVINO functionality is implemented.

DuetShift's intended final concept is a pair of simulated SO-101 arms that follow natural-language goals, observe a shared workspace, and verify multi-step manipulation. When the world or the user's goal changes, the future system should revise affected steps, reconsider arm assignments, use handoffs when helpful, and verify the revised result. These are plans, not demonstrated capabilities.

## Documentation

- [Challenge requirements](docs/challenge_requirements.md)
- [Intended architecture](docs/architecture.md)
- [Build status](docs/build_status.md)
- [Repository and environment report](docs/environment_report.md)

## Repository layout

- `src/duetshift/`: empty placeholders for future components.
- `configs/`, `assets/`, `scripts/`, `tests/`: reserved for later stages.
- `evaluation/`, `benchmarks/`: reserved for reproducible evaluation and Intel deployment evidence.
- `docs/`: project scope, plans, status, and audit findings.

There is no runnable application or dependency setup yet. Stage 2 will decide the Python environment and dependency policy; nothing was installed during Stage 1.
