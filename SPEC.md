---
epic: 001-generate-and-ingest-telemetry
outline_key: S2
github_issue: kurtbrii/fleet-geo-tracking#5
---

# Spec: Vehicle simulator

## Objective

Give the developer a runnable source of simulated vehicle positions before
connecting it to Kafka. Maintain a fleet with stable plate IDs, advance its
positions over time, and keep every vehicle inside the Metro Manila box.

This is epic 001, outline S2: **Vehicle simulator**. It implements simulation,
validated vehicle-count and interval options, pytest tests, and a plain-language
test walkthrough. Kafka publication and delivery reporting belong to S3.

Design sources: `epics/001-generate-and-ingest-telemetry/epic.md` (S2) and
`epics/001-generate-and-ingest-telemetry/architecture.md` (simulation, event
contract, generator entry point). Their decisions supersede the older README's
multiprocess and throughput targets.

## Approval

The author approved S2 on 2026-10-31 and confirmed one JSON record per vehicle
per tick. The author approved the motion defaults on 2026-10-31, with no sudden
speed changes between ticks. GitHub story issue #5 is linked to epic #1.

## Decisions and assumptions

1. The standalone CLI prints newline-delimited JSON: one position per vehicle
   per tick. The author confirmed this output choice on 2026-10-31.
2. Initial coordinates and bearings are random; each vehicle receives a random
   positive speed no greater than 200 km/h and keeps that speed for this story.
   Speed is chosen once at initialization, so a vehicle at 5 km/h does not jump
   to 200 km/h on a later tick.
   Only plate IDs, not random initial positions, must match across runs.
3. Before each movement, heading drifts by a random amount in [-10, 10] degrees.
   This is a simple load simulation, with no road routing or acceleration model.
4. The first tick emits the initial fleet immediately. Later ticks advance it
   using elapsed time, with `--interval-ms` setting the target tick spacing.
5. Use Python's standard library for runtime code and uv for the pytest
   development dependency and locked project environment.

## Tech Stack

- Python 3.14, matching the author's existing Python 3.14.6 virtual environment.
- Standard library: argument parsing, data models, math, randomness, JSON, and
  timing. No runtime third-party package is required by this story.
- pytest 9.2.0. Its published metadata requires Python >=3.10 and lists 3.14:
  [pytest on PyPI](https://pypi.org/project/pytest/).
- Pin pytest in the `dev` dependency group in `pyproject.toml`; resolve its
  complete dependency set into the root `uv.lock` during implementation.

## Behaviour and contracts

### Fleet identity and position data

Each tick produces exactly one position per vehicle, with these fields:

| Field | Type | Rule |
|---|---|---|
| `id` | string | Unique generated plate matching `^[A-Z]{3}[0-9]{4}$`; stable across ticks and runs |
| `lat` | finite number | 14.35 <= lat <= 14.78 |
| `lng` | finite number | 120.90 <= lng <= 121.13 |
| `bearing` | finite number | Degrees clockwise from north, 0 <= bearing < 360 |
| `speed` | finite number | km/h, 0 <= speed <= 200 |
| `ts` | integer | Current Unix epoch milliseconds at emission |

Derive IDs deterministically from vehicle index. Increasing fleet size retains
the smaller fleet's IDs. The plate space has 26^3 * 10^4 = 175,760,000 unique
values; reject larger requested fleets rather than repeating IDs. This is an
identity limit, not a claim that such a fleet fits in memory.

Example output, with illustrative coordinates and timestamp:

```json
{"id":"NAB1234","lat":14.5995,"lng":120.9842,"bearing":90.0,"speed":45.0,"ts":1793400000000}
```

### Movement

- Initialise vehicles inside the box. Preserve vehicle identity between ticks.
- Normalise heading after drift and edge reflections to [0, 360).
- Move according to speed, elapsed seconds, and heading, accounting for the
  different latitude/longitude degree distances. A local geographic approximation
  is sufficient; this story promises no routing or surveying accuracy.
- Reflect overshoot at each crossed edge and reflect the heading. Handle corner
  crossings and large elapsed times without emitting an out-of-bounds coordinate.
- A moving vehicle changes position under a controlled ordinary movement case;
  zero speed leaves its position unchanged. Do not regenerate the fleet per tick.
- Keep the simulation separate from sleeping, terminal output, and wall-clock
  access. Supply randomness and elapsed time explicitly so tests are repeatable.

### CLI and scheduling

- Entry point: `generator/generator.py`.
- `--vehicles`: integer from 1 through the plate-space limit; default 1000.
- `--interval-ms`: positive integer milliseconds; default 1000.
- `--help` describes both options and defaults, then exits successfully.
- Reject zero, negatives, nonintegers, missing values, and unsupported options
  with a useful stderr message and nonzero status before fleet allocation or
  output. No `--processes` option is introduced.
- Run one process until Ctrl+C. Exit cleanly on Ctrl+C without a traceback.
- Output: one JSON record per vehicle per tick on stdout, flushed at each tick; diagnostics
  go to stderr. No Kafka imports, connections, messages, or sent-event claims.
- Use monotonic time for scheduling and elapsed movement; use wall-clock epoch
  time only for `ts`. Account for processing/output time in tick spacing. If a
  tick overruns, continue without an unbounded burst of catch-up ticks.
- Timing is best effort. No throughput or real-time latency target gates S2.

## Commands

Run from the repository root after implementation. These are proposed commands,
not commands executed while specifying the story.

```bash
# Use the existing Python 3.14.6 virtual environment with uv
export UV_PROJECT_ENVIRONMENT=venv
uv sync --locked

# Run the default fleet; Ctrl+C stops it
uv run --locked python generator/generator.py

# Inspect two vehicles at a slower interval
uv run --locked python generator/generator.py --vehicles 2 --interval-ms 2000

# Help and a validation failure (the latter must exit nonzero without events)
uv run --locked python generator/generator.py --help
uv run --locked python generator/generator.py --vehicles 0

# Run automated tests without Docker or Kafka
uv run --locked python -m pytest generator/tests -q

# Check the lock matches project metadata
uv lock --check
```

There is no application build step. Lint, type, complexity, hook and CI gates
remain deferred in `STACK.md`; S2 does not claim to satisfy those broader project
standards. Their setup belongs to the separate tooling work.

## Project Structure

```text
generator/
  generator.py             CLI entry point, scheduling, terminal output
  simulator.py             Fleet state and movement without external I/O
  tests/                   Simulator and CLI behaviour tests
  TESTING.md               Plain-language test walkthrough and commands
pyproject.toml              Python version and pytest dev dependency
uv.lock                     Fully resolved dependency versions and hashes
```

This is the intended responsibility split. The implementation plan determines
function signatures and the caller-first build order. The entry point must call
the simulator; no unused helper module or future Kafka stub is part of S2.

### Caller-first implementation contract

The real top of this story is:

```text
python generator/generator.py
  └── script entry guard
        └── main() ← start implementation here
```

Follow AGENTS.md Rules 1, 2 and 2b throughout implementation:

- First show and create the `main()` skeleton with its docstring and TODOs,
  connected to the script's `if __name__ == "__main__"` entry guard. Do this
  before building the simulator or any helper function.
- Add one real immediate-child call in an existing caller before implementing
  that child. Keep the required TODO on the call until the entire child branch
  is implemented. Use real arguments already in scope, never fabricated inputs.
- Descend depth-first and finish that branch before wiring the next sibling.
  Future siblings remain TODO comments until their turn. Parse and validate
  options before proceeding to fleet creation or simulation.
- Make each small implementation edit its own tool call, with at most one new
  function. Continue between steps without approval pauses, except at documented
  review gates or genuine unresolved design decisions.
- Give functions and models real types and docstrings immediately. A stub with
  a non-None return type raises `NotImplementedError`. Importing a helper or
  adding its stub does not count as completing it.
- Each step's explanation shows only the call path from the script entry to
  the function currently being built. Keep this hierarchy in prose and update
  the implementation checklist as steps finish.

The leaf-function example below illustrates style only; it does not authorise
implementing a helper before its caller is wired.

## Code Style

Use descriptive snake_case names, explicit types, brief docstrings on every
function and data model, and small functions with one job. Keep I/O at the CLI
boundary. Example of the intended leaf-function style (not an implementation
contract):

```python
def normalise_bearing(bearing: float) -> float:
    """Return a heading in degrees clockwise from north."""
    return bearing % 360.0
```

Inject randomness, clocks, and waiting where needed for tests. Let configuration
errors fail at the CLI boundary. Do not suppress lint or type errors, hide failed
tests, or add dependencies for functionality covered by the standard library.

## Testing Strategy

Use pytest, without a broker, network, real sleeps, or an indefinitely running
test process. Supply controlled random values and fake clocks/waiting for timing
tests. Assert observable results rather than helper-call order.

Cover:

- Unique valid plates, repeatability across starts, and stability when fleet
  size grows. Check plate-space boundaries without allocating a huge fleet.
- Exact fleet size, all event fields, finite numeric values, valid ranges,
  integer epoch timestamps, and unchanged IDs over repeated ticks.
- Deterministic movement, heading wrapping, elapsed-time scaling with controlled
  drift, zero speed, four edges, corners, and overshoot across multiple box widths.
- Long sequences with controlled randomness staying inside all field ranges.
- CLI defaults and valid overrides; invalid counts and intervals, malformed or
  missing arguments, unknown flags, and help. Invalid input emits no events.
- First tick, later tick spacing, output-time accounting, overrun behaviour,
  JSON output shape, and clean interruption, without real waiting.

`generator/TESTING.md` explains what each test verifies, why it matters, its inputs
and expected result, and the exact command to run it. Cover each documented
failure mode. No numeric coverage floor has been established for this story;
adding a coverage tool or CI threshold is deferred to the tooling work.

## Boundaries

- **Always:** follow the epic's field contract and single-process design;
  validate options before generating events; build from the real CLI entry point
  one function at a time; maintain checklist evidence; run local automated tests
  before committing implementation; keep dependencies reproducible.
- **Always:** when implementation starts, branch from
  `epic-1-generate-and-ingest-telemetry`, using
  `epic-1/story-<GitHub-story-issue>-vehicle-simulator`. Story PRs target the epic
  branch, following the author's workflow decision. No new issue number is
  assumed by this spec.
- **Ask first:** change the event schema, CLI contract, motion assumptions, Python
  version, or bounding box; add runtime dependencies or persistent storage;
  launch a live Kafka producer or consumer.
- **Never:** publish to Kafka, add a backend, start or reset containers, add
  multiprocessing, claim throughput measurements, introduce routing/maps, or
  implement CI/hooks/logger infrastructure as part of S2.
- **Local planning files:** preserve the author's ignore rules for `SPEC.md`,
  tasks, epics, ideas and the local `generator/TESTING.md` walkthrough.

## Success Criteria

- [x] ~~Default CLI simulates 1000 vehicles at a target interval of 1000 ms.~~
- [x] ~~Valid options change fleet size and target interval; invalid input fails
  before fleet allocation or event output with a clear message.~~
- [x] ~~IDs are unique, match the plate format, and remain stable across ticks,
  repeated runs and fleet-size increases.~~
- [x] ~~Positions evolve according to elapsed time and remain finite and inside
  the box, including edge, corner and overshoot cases.~~
- [x] ~~Each vehicle starts with a random positive speed no greater than 200 km/h;
  its speed stays unchanged across ticks.~~
- [x] ~~Every emitted event satisfies the six-field contract, including integer
  epoch milliseconds and a normalised bearing.~~
- [x] ~~The standalone CLI emits one JSON record per vehicle per tick and
  Ctrl+C stops it without a traceback.~~
- [x] ~~Automated tests pass locally without Kafka, network access or real sleeps;
  the plain-language walkthrough covers the tests and how to run them.~~
- [x] ~~Test dependencies are exactly pinned and locked; installation and tests use
  the documented commands. No unapproved runtime dependency is added.~~

## Open Questions

None for the S2 motion defaults.

## Specification Checklist

- [x] ~~Read the S2 outline, epic architecture, stack and repository layout.~~
- [x] ~~Draft objective, commands, structure, style, tests and boundaries.~~
- [x] ~~Define testable success criteria and surface assumptions.~~
- [x] ~~Make the real CLI entry point and AGENTS.md caller-first ordering explicit.~~
- [x] ~~Author confirmed one JSON record per vehicle per tick.~~
- [x] ~~Author approved the story on 2026-10-31, with motion review deferred.~~
- [x] ~~Confirm fixed random positive speed and heading drift up to 10 degrees
  per tick, with no speed changes between ticks.~~
- [x] ~~Create GitHub story issue #5 and link it to epic issue #1.~~

## Sources

- [Python 3.14 argparse](https://docs.python.org/3.14/library/argparse.html):
  standard-library CLI parsing, help and invalid-argument handling.
- [Python 3.14 time](https://docs.python.org/3.14/library/time.html): monotonic
  scheduling versus epoch timestamps.
- [pytest package metadata](https://pypi.org/project/pytest/): version 9.2.0 and
  Python compatibility, checked 2026-10-31. No installation or test execution
  occurred while writing this specification.
- [uv project guide](https://docs.astral.sh/uv/guides/projects/): project
  metadata, lockfiles and `uv run` behaviour.
- [uv development dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/):
  `dev` dependency groups and their default sync behaviour.

## Changelog

- 2026-10-31: Drafted S2 from the epic's simulator slice so simulation can be
  reviewed and tested before Kafka publishing is added in S3.
- 2026-10-31: Made the caller-first implementation contract explicit so the
  script invokes the top-level skeleton before any helper is built, with one
  branch completed before the next sibling is wired.
- 2026-10-31: Recorded story approval and confirmed JSON output per vehicle per
  tick; deferred motion-default review and GitHub story-issue creation at the
  author's request.
- 2026-10-31: Updated the runtime to Python 3.14 to match the author's existing
  environment and recorded story issue #5.
- 2026-10-31: Approved random initial speed and bounded heading drift, with a
  fixed speed per vehicle to prevent sudden jumps between ticks.
