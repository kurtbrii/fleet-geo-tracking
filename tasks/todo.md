# Tasks: S2 — Vehicle simulator

Source: root `SPEC.md`. Rationale and dependencies: `tasks/plan.md`.
The author approved the five-task outline on 2026-10-31. No implementation task
is complete. Check and strike through items only after recording their evidence.
Each task is implemented as consecutive small edits, one function per edit,
following the real caller downward. Stop at task boundaries and review gates.

## Before implementation

- [x] ~~Create GitHub story issue #5 through its workflow and record it in
  SPEC.md, linked to epic issue #1.~~
- [x] ~~Create `epic-1/story-5-vehicle-simulator` from the updated
  `epic-1-generate-and-ingest-telemetry` branch.~~
- [x] ~~Confirm the existing root `venv/` uses Python 3.14.6 and configure the
  project for Python 3.14 or newer.~~

## Task 1: CLI entry and validated options

- [x] ~~**Task 1 complete**~~

### Implementation checklist

- [x] ~~Add the `main()` skeleton and script entry guard.~~
- [x] ~~Parse and validate CLI options before any simulation work.~~
- [x] ~~Cover defaults, valid overrides, and invalid input with CLI tests.~~
- [x] ~~Pin and lock pytest dependencies and write the test walkthrough.~~

**Description:** Start with the script entry guard calling the documented
`main()` skeleton. Wire the options branch before implementing it and finish
that branch before wiring simulation. Set up the pinned pytest environment.
The interim CLI validates configuration; simulation remains a visible TODO.

**Acceptance criteria:**
- [x] ~~The real entry guard calls `main()`; the options branch is complete with
  typed, documented functions, and future simulation siblings remain TODO-only.~~
- [x] ~~Defaults are 1000 vehicles and 1000 ms; valid overrides work. Invalid
  counts, plate-space overflow, intervals, missing values and unknown options
  fail clearly on stderr before allocation or event output; help succeeds.~~
- [x] ~~pytest and transitive dependencies are exactly locked in `uv.lock`;
  CLI tests and their walkthrough are present.~~

**Verification:**
- [x] ~~`UV_PROJECT_ENVIRONMENT=venv uv run --locked python -m pytest generator/tests/test_cli.py -q` (11 passed)~~
- [x] ~~`uv lock --check`~~
- [x] ~~Review the entry point and use bounded tests to verify invalid inputs
  emit no events. Test the fleet-size limit without allocating a huge fleet.~~

**Dependencies:** Before-implementation checklist.
**Files likely touched:** `generator/generator.py`,
`pyproject.toml`, `uv.lock`, `generator/tests/test_cli.py`,
`generator/TESTING.md`.
**Estimated scope:** Medium, five implementation/documentation files.
**Evidence:** On Python 3.14.6, uv synced five packages from the lock; focused
CLI suite: 11 passed; `uv lock --check` succeeded. Invalid CLI tests confirmed
stderr diagnostics and empty stdout, including the maximum fleet boundary.

## Checkpoint A: CLI review and motion decision

- [x] ~~Task 1 passed 11 focused CLI tests and the uv lock check; the author
  reviewed the result at Checkpoint A.~~
- [x] ~~The author approved fixed random positive speeds up to 200 km/h and
  heading drift up to 10 degrees per tick; SPEC.md and the plan were updated.~~
- [x] ~~Human review complete before Task 2; speed remains fixed across ticks.~~

## Task 2: Initial fleet and JSON output

- [x] ~~**Task 2 complete**~~

**Description:** Add the real simulation call from the completed options caller.
Build the fleet branch depth-first, then its JSON-output sibling. At this task's
boundary the CLI emits one initial snapshot; repetition arrives in Task 4.

**Acceptance criteria:**
- [x] ~~Requested fleet size is exact; plate IDs match the format, are unique,
  repeat across runs, and stay stable when the fleet size increases.~~
- [x] ~~Each vehicle emits one JSON record with the six fields and valid finite
  values, including integer epoch milliseconds; initial speed is random,
  positive and at most 200 km/h, and controlled randomness is injectable.~~
- [x] ~~The CLI emits the initial snapshot immediately, keeps stdout JSON-only,
  flushes the tick and documents the new tests.~~

**Verification:**
- [x] ~~`UV_PROJECT_ENVIRONMENT=venv uv run --locked python -m pytest generator/tests/test_simulator.py generator/tests/test_cli.py -q` (13 passed)~~
- [x] ~~Test snapshots with controlled randomness/time; parse stdout and verify
  record count, fields, ranges and timestamps without Kafka.~~

**Dependencies:** Task 1 and Checkpoint A.
**Files likely touched:** `generator/generator.py`, `generator/simulator.py`,
`generator/tests/test_simulator.py`, `generator/tests/test_cli.py`,
`generator/TESTING.md`.
**Estimated scope:** Medium, five files.
**Evidence:** On Python 3.14.6, the focused simulator and CLI suites passed 12
tests in 0.66 s after the record builder was inlined into `emit_snapshot`. A
local two-vehicle run emitted two six-field JSON records with the same integer
millisecond timestamp. The old subprocess check for the maximum fleet size now
parses the limit in-process, because that case would otherwise allocate
175,760,000 vehicles and hang; the rejection boundary still runs as a
subprocess. The CLI snapshot test uses a seeded fleet and checks the six-field
record contract, field ranges, IDs and current epoch milliseconds.

## Task 3: Bounded movement

- [x] ~~**Task 3 complete**~~

**Description:** Wire the advance operation at its real position in the
simulation caller before implementing it. Descend into movement and reflection
one branch at a time. Scheduling siblings remain TODO-only until Task 4; record
any temporary incomplete wiring rather than claiming a finished runtime loop.

**Acceptance criteria:**
- [x] ~~Movement uses speed, elapsed time and the approved drift policy; IDs and
  speeds stay unchanged across ticks, bearings normalise, and zero speed leaves
  coordinates unchanged.~~
- [x] ~~Reflection handles each edge, corners and overshoot across multiple box
  widths, producing finite coordinates inside the specified box.~~
- [x] ~~Controlled tests cover displacement, repeated ticks and unchanged speed;
  the walkthrough explains the scenarios without testing helper-call order.~~

**Verification:**
- [x] ~~`UV_PROJECT_ENVIRONMENT=venv uv run --locked python -m pytest generator/tests/test_simulator.py -q` (14 passed)~~
- [x] ~~Review the real caller path and remaining TODOs. Test elapsed-time scaling
  with controlled drift and repeated in-range movement without real sleeps.~~

**Temporary wiring:** The CLI emits the initial snapshot and exactly one
advanced tick, then exits. The advance call sits at its final position in the
tick path, but the repeating loop and measured monotonic elapsed time belong to
Task 4. No production TODO comments remain; the single-tick limit is recorded
here rather than in the code.

**Evidence:** On Python 3.14.6, the focused simulator suite passed 14 tests and
the full generator suite passed 25. Movement uses speed times elapsed seconds,
a random drift in [-10, 10] degrees, and latitude/longitude degree distances;
reflection handles all four edges, corners and multi-width overshoot. Controlled
testing uses `FixedDrift` and seeded fleets, so no real time passes. A 2000-tick
run preserved every ID and speed and kept all values finite and in range.

**Dependencies:** Task 2 and the recorded motion decision.
**Files likely touched:** `generator/generator.py`, `generator/simulator.py`,
`generator/tests/test_simulator.py`, `generator/TESTING.md`.
**Estimated scope:** Medium, four files.

## Checkpoint B: Fleet and motion review

- [x] ~~Tasks 2–3 have verification evidence and no unapproved motion assumptions.~~
- [x] ~~Run all existing local tests; record any deliberate unfinished CLI wiring.~~
- [x] ~~Human reviews the fleet and motion results before Task 4.~~

## Task 4: Repeating ticks and clean interruption

- [x] ~~**Task 4 complete**~~

**Description:** Complete the scheduling branch around the existing fleet,
movement and output paths. Inject time and waiting so the real loop is testable
without indefinite execution. Handle Ctrl+C at the CLI boundary.

**Acceptance criteria:**
- [x] ~~Emit the initial fleet immediately, then one JSON record per vehicle per
  tick; retain state and use monotonic elapsed time for subsequent movement.~~
- [x] ~~Requested tick spacing accounts for work/output time, with bounded overrun
  behaviour; timestamps use epoch milliseconds and output flushes each tick.~~
- [x] ~~Ctrl+C exits without a traceback; bounded tests and walkthrough cover
  timing, slow output, overrun and interruption. No incomplete production stubs
  or stale TODOs remain in the completed path.~~

**Verification:**
- [x] ~~`UV_PROJECT_ENVIRONMENT=venv uv run --locked python -m pytest generator/tests/test_cli.py -q` (15 passed)~~
- [x] ~~Test multiple ticks using fake clocks and waiting; verify observable
  positions, JSON counts, timing and interruption without real sleeps.~~

**Dependencies:** Task 3 and Checkpoint B.
**Files likely touched:** `generator/generator.py`,
`generator/tests/test_cli.py`, `generator/TESTING.md`.
**Estimated scope:** Medium, three files.
**Evidence:** On Python 3.14.6, the focused CLI suite passed 15 tests and the
full generator suite passed 29 in 0.92 s; `uv lock --check` succeeded. The loop
uses `time.monotonic` for scheduling and elapsed movement, wall-clock epoch
milliseconds only for `ts`, and resets the next deadline to `now + interval`
when emission overruns so missed ticks are skipped instead of replayed. Tests
inject a fake clock and wait, a slow 2.5 s emitter for overrun, an in-process
`KeyboardInterrupt`, and a real SIGINT subprocess that exits 0 with empty
stderr. The in-process helpers return when `tick_limit` is reached; the CLI
default remains an endless loop until Ctrl+C.

## Task 5: Complete story review and test walkthrough

- [x] ~~**Task 5 complete**~~

**Description:** Review the assembled CLI and all acceptance evidence. Finish
the walkthrough and reconcile spec/checklist status only for verified outcomes.
Any code defect returns to its originating task, with affected tests repeated.

**Acceptance criteria:**
- [x] ~~Every S2 success criterion has evidence; review the diff and full execution
  path for caller-first integration, error handling and field-contract compliance.~~
- [x] ~~Tests pass without Kafka, network calls or real sleeps; locked dependency
  consistency passes and documentation commands match the implementation.~~
- [x] ~~The plain-language walkthrough explains every test's purpose, inputs,
  expected outcome and execution; no throughput or coverage claims are invented.~~

**Verification:**
- [x] ~~`UV_PROJECT_ENVIRONMENT=venv uv run --locked python -m pytest generator/tests -q` (30 passed)~~
- [x] ~~`UV_PROJECT_ENVIRONMENT=venv uv lock --check`~~
- [x] ~~Read the complete diff and test walkthrough; update SPEC.md success
  checkboxes only where the recorded evidence supports them.~~

**Dependencies:** Task 4.
**Files likely touched:** `generator/TESTING.md`, `SPEC.md`,
`tasks/todo.md`, `tasks/plan.md`. Code fixes follow their relevant task scope.
**Estimated scope:** Medium, four documentation files.
**Evidence:** On Python 3.14.6 the full generator suite passed 30 cases (18
test functions) in 1.09 s and `uv lock --check` succeeded. The S2 diff against
the epic branch (generator, tests, pyproject, lock) has no TODOs or
suppressions; it matches the six-field contract, validates options before
allocation, uses monotonic time for scheduling and movement, and catches
Ctrl+C in `main()`. TESTING.md now covers all 18 tests, including the new
elapsed-time test and the immediate-tick overrun behaviour. One exception to
"no real sleeps": `test_process_stops_cleanly_on_interrupt` runs the real CLI
at a 10 ms interval, so it sleeps a few tens of milliseconds by design. No code
defects found; all nine SPEC.md success criteria checked.

## Checkpoint C: S2 review

- [ ] All acceptance criteria and local checks have recorded evidence.
- [ ] Human reviewed the completed story before finishing it or starting S3.
- [ ] Story-finishing workflow is a separate step; any story PR targets
  `epic-1-generate-and-ingest-telemetry`.

## Planning checklist

- [x] ~~Expand the approved outline into five tasks with acceptance criteria.~~
- [x] ~~Record focused verification, dependencies, file scope and review gates.~~
- [x] ~~Keep the motion decision and GitHub issue deferred until their checkpoints.~~

## Changelog

- 2026-10-31: Created the detailed S2 task checklist from the author's approved
  outline, with caller-first edits and explicit evidence requirements.
- 2026-11-03: Closed Checkpoint B and completed Task 4; tick loop uses
  monotonic time, skips missed deadlines, and exits 0 on Ctrl+C. Focused CLI
  suite 15 passed, full generator suite 29 passed, lock check succeeded.
- 2026-11-05: Simplified the tick loop to one clock variable (`wait(max(0,
  interval - elapsed))`). After an overrun the next tick now runs immediately
  instead of a full interval later; still no catch-up bursts. Restored Ctrl+C
  handling in `main()`. Full generator suite 30 passed.
- 2026-11-05: Completed Task 5; walkthrough updated, all S2 success criteria
  checked with evidence. Awaiting Checkpoint C.
