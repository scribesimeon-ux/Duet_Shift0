# DuetShift

Project for the Intel Physical AI Online Challenge: **Bimanual VLA Manipulation with Multi-Modal Reasoning**.

**CURRENT STATUS: Stage 5 - challenge scene, objects and cameras.** Authentic dual SO-101 arms share a physical table with a sliding drawer and five objects, reproducible seeded resets, and three verified RGB cameras. Manipulation, AI policies, and OpenVINO are not implemented.

DuetShift's intended final concept is a pair of simulated SO-101 arms that follow natural-language goals, observe a shared workspace, and verify multi-step manipulation. When the world or the user's goal changes, the future system should revise affected steps, reconsider arm assignments, use handoffs when helpful, and verify the revised result. These are plans, not demonstrated capabilities.

## Documentation

- [Challenge requirements](docs/challenge_requirements.md)
- [Intended architecture](docs/architecture.md)
- [Build status](docs/build_status.md)
- [Repository and environment report](docs/environment_report.md)
- [Windows development setup](docs/development.md)
- [SO-101 model provenance](docs/so101_model_provenance.md)
- [Challenge scene](docs/challenge_scene.md)

## Repository layout

- `src/duetshift/`: package foundation and placeholders for future components.
- `scripts/`, `tests/`: environment verification and basic package tests.
- `assets/mujoco/`: smoke scene; `assets/robots/`: authenticated SO-101 assets; `configs/`: challenge scene configuration.
- `evaluation/`, `benchmarks/`: reserved for reproducible evaluation and Intel deployment evidence.
- `docs/`: project scope, plans, status, and audit findings.

Run `python scripts/run_challenge_scene.py --seed 42 --viewer` in the `duetshift-dev` Python 3.12 environment. Earlier smoke and robot inspection scripts remain available. Task execution is not implemented. Final Intel deployment is a separate later stage.
