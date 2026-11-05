# Implementation Plan: S2 — Vehicle simulator

## Overview

Implement the approved root `SPEC.md`, epic 001 outline S2. Deliver a Python
simulator with stable vehicle IDs, bounded movement, validated CLI options and
one JSON record per vehicle per tick. Tests and their walkthrough belong to
this story. The author approved the five-task outline on 2026-10-31.

Detailed tasks and verification evidence live in `tasks/todo.md`. These planning
files stay ignored by Git, as requested.

## Architecture and scope

- Python 3.14; standard-library runtime code; pytest 9.2.0 for tests, managed by uv.
- `generator/generator.py` owns the actual CLI, scheduling and terminal output.
  `generator/simulator.py` owns state and movement without external I/O.
- Preserve all six fields and ranges in SPEC.md. Defaults are 1000 vehicles and
  1000 ms. Validate before allocating the fleet or emitting output.
- Inject randomness and time at their boundaries. Tests control clocks and
  waiting rather than sleeping. Epoch timestamps and monotonic timing have
  separate purposes.
- Pin pytest in the `dev` dependency group in `pyproject.toml`; resolve exact
  transitive versions and hashes into the root `uv.lock`.
- Maintain `generator/TESTING.md` as tests are added, explaining their inputs,
  expected behaviour, purpose and execution commands.
- Kafka publication, backend work, README alignment, CI/hooks and logger
  infrastructure belong to other stories. No containers or live services are
  needed for S2 verification.

## Dependencies and implementation order

CLI options → initial fleet and JSON → movement → repeating tick scheduling
→ complete story verification.

The dependency sequence does not authorise building helper files first. The
real top is the script entry guard calling `main()`. Its skeleton comes first.
Add one real child call, then implement that branch depth-first, before wiring
its next sibling. Later sibling calls remain TODO comments until their turn.
One new function per edit, real arguments, types and docstrings, and the required
TODO on every incomplete call site. Show only the current call path in prose.

Temporary incomplete wiring is allowed by AGENTS.md; record it honestly and do
not claim the full CLI is complete until Task 4. Function signatures and data
shapes shown in an implementation skeleton become contracts; stop if they need
an unapproved change. Small completed branches are checked before moving on.

## Task index

- [x] ~~**Task 1:** CLI entry and validated options, with uv-locked test setup.~~
- [x] ~~**Checkpoint A:** Review CLI evidence and resolve motion defaults.~~
- [x] ~~**Task 2:** Initial fleet with stable IDs and JSON output.~~
- [x] ~~**Task 3:** Bounded movement connected to its actual caller.~~
- [x] ~~**Checkpoint B:** Review fleet and motion evidence.~~
- [x] ~~**Task 4:** Repeating ticks and clean interruption.~~
- [ ] **Task 5:** Complete story review and test walkthrough.
- [ ] **Checkpoint C:** Human review before story finishing.

## Prerequisites and deferred decisions

Story issue #5 is recorded in SPEC.md. Work is on
`epic-1/story-5-vehicle-simulator`, based on the updated
`epic-1-generate-and-ingest-telemetry` branch. Story PRs target the epic branch.

The author approved fixed random positive speeds up to 200 km/h and heading
drift of up to 10 degrees per tick. Speed remains constant between ticks, so
there are no sudden speed jumps. The decision is recorded in SPEC.md and does
not change the Task 2–3 scope.

## Verification

Use the existing root `venv/` (Python 3.14.6) with uv and the committed lock.
From the repository root, set `UV_PROJECT_ENVIRONMENT=venv` for uv commands.
Then use:

```bash
uv sync --locked
uv run --locked python -m pytest generator/tests -q
uv lock --check
```

Use focused test files while implementing a task; run the full existing suite
at checkpoints and after the final change. Tests cover valid behaviour and
documented failures, with bounded CLI execution and fake time. Do not launch an
indefinite generator process to verify it. No build step applies.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Vehicle speed changes abruptly between ticks | Keep each vehicle's initial speed fixed and test it across repeated ticks |
| Wrong story branch or PR base | Resolve the issue and branch before Task 1; target the epic |
| Nondeterministic tests or slow real sleeps | Inject controlled randomness, clocks and waiting |
| Heading or boundary math produces invalid positions | Test four edges, corners, large overshoot and finite values |
| Large requested fleet duplicates IDs or exhausts memory | Reject plate-space overflow before allocation; test the limit without allocating it; no maximum-load claim |
| Processing time distorts tick spacing | Account for work duration using monotonic time; test overrun handling |
| Unfinished sibling wired too early | Keep siblings TODO-only until the current branch is complete |

Work is sequential because tasks extend the same entry point and state model.
No parallel code implementation is planned.

## Planning checklist

- [x] ~~Read the approved S2 spec and check for an existing incomplete plan.~~
- [x] ~~Record the approved five-task order, dependencies and review gates.~~
- [x] ~~Author approved the proposed task outline (2026-10-31).~~
- [x] ~~Detailed todo checklist saved and checked against this plan.~~

## Changelog

- 2026-10-31: Saved the approved S2 plan, preserving caller-first implementation
  and the author's deferred motion and GitHub issue decisions.
- 2026-10-31: Aligned the runtime and verification commands with the author's
  existing Python 3.14.6 virtual environment.
- 2026-10-31: Switched test dependency management and verification to uv,
  preserving the existing virtual environment path.
- 2026-10-31: Completed Task 1; focused CLI tests passed (11 cases) and the
  uv lock check succeeded. Paused at Checkpoint A for review and motion decision.
- 2026-10-31: Completed Checkpoint A after the author approved fixed random
  speeds and bounded heading drift, with no speed changes between ticks.
- 2026-10-31: Completed Task 2; the CLI emits one six-field JSON record per
  vehicle, and the maximum-fleet check no longer allocates 175,760,000 vehicles.
- 2026-11-01: Completed Task 3; bounded drift and reflection are wired into the
  tick path. The CLI emits the initial snapshot plus one advanced tick until
  Task 4 adds the repeating loop and measured elapsed time.
- 2026-11-03: Completed Task 4; the CLI now repeats ticks on monotonic time,
  skips missed deadlines after an overrun, and exits 0 on Ctrl+C. Focused CLI
  suite 15 passed, full generator suite 29 passed, lock check succeeded.
