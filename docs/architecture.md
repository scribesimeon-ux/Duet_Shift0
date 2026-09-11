# Intended architecture

**All components below are NOT IMPLEMENTED.** Stage 1 contains only documentation and empty directories. The arrows describe a proposed future flow, not working integrations.

```text
User
  -> text / optional voice input
  -> goal manager
  -> camera perception
  -> structured world state
  -> task planning
  -> bimanual scheduler
  -> learned policy / deterministic fallback
  -> dual SO-101 control
  -> MuJoCo
  -> observation
  -> verification
  -> recovery / replanning
  -> revised planning and execution
```

## Future responsibilities — all NOT IMPLEMENTED

- Text/voice input: accept instructions and optional spoken goal revisions; Speechmatics is a future optional integration.
- Goal manager: maintain the current requested outcome and revisions.
- Camera perception (`perception/`): interpret camera observations and ground instructions in the scene.
- Structured world state (`state/`): represent objects, arm state, and task predicates.
- Task planning (`planning/`): organize multi-step work and identify affected steps after changes.
- Bimanual scheduler (`planning/`): assign and coordinate both arms, reconsider assignments, and choose useful handoffs.
- Learned policy / deterministic fallback (`policies/`, `control/`): integrate a trained or fine-tuned policy such as ACT and a future fallback path; neither exists yet.
- Dual SO-101 control (`control/`): translate coordinated actions into commands for two simulated arms.
- MuJoCo (`sim/`): host the future scene, robot models, physics, and cameras.
- Observation (`sim/`, `perception/`, `state/`): feed updated measurements back into the world state.
- Verification (`runtime/`, `state/`): check task outcomes and detect mismatches during execution.
- Recovery/replanning (`recovery/`, `planning/`): invalidate affected steps, reconsider assignments, and resume toward the revised goal.
- Runtime (`runtime/`): connect the future closed-loop components, including interruption handling.

## Future supporting work — NOT IMPLEMENTED

OpenVINO optimization and Intel Core Ultra Series 2/3 deployment are later-stage work. `configs/` and `assets/` reserve space for configuration and scene resources. `scripts/`, `tests/`, `evaluation/`, and `benchmarks/` reserve space for tooling, checks, randomized-seed evaluation, and deployment measurements. No results or performance claims exist.
