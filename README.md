# DuetShift

Project for the Intel Physical AI Online Challenge: **Bimanual VLA Manipulation with Multi-Modal Reasoning**.

**CURRENT STATUS: Stage 4 — dual SO-101 model.** Authentic upstream SO-101 assets load as one arm or two independently named arms, with verified idle stability and optional viewing. Manipulation, AI policies, and OpenVINO are not implemented.

DuetShift's intended final concept is a pair of simulated SO-101 arms that follow natural-language goals, observe a shared workspace, and verify multi-step manipulation. When the world or the user's goal changes, the future system should revise affected steps, reconsider arm assignments, use handoffs when helpful, and verify the revised result. These are plans, not demonstrated capabilities.

## Documentation

- [Challenge requirements](docs/challenge_requirements.md)
- [Intended architecture](docs/architecture.md)
- [Build status](docs/build_status.md)
- [Repository and environment report](docs/environment_report.md)
- [Windows development setup](docs/development.md)
- [SO-101 model provenance](docs/so101_model_provenance.md)

## Repository layout

- `src/duetshift/`: package foundation and placeholders for future components.
- `scripts/`, `tests/`: environment verification and basic package tests.
- `assets/mujoco/`: minimal smoke scene; `configs/` is reserved for later stages.
- `evaluation/`, `benchmarks/`: reserved for reproducible evaluation and Intel deployment evidence.
- `docs/`: project scope, plans, status, and audit findings.

Run `python scripts/run_dual_so101.py --viewer` in the `duetshift-dev` Python 3.12 environment; the Stage 3 smoke script remains available. There is no challenge task implementation yet. Final Intel deployment is a separate later stage.
