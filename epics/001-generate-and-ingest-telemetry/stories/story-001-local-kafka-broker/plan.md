# Implementation Plan: S1 — Local Kafka broker

## Overview

Implement only `SPEC.md` for epic 001, outline S1, issue #2. Deliver a local
Kafka broker, explicit topic initialization and Kafka UI in `docker-compose.yml`.
No generator, backend, SSE, frontend or README changes belong to this story.
Tasks and verification evidence are tracked in `tasks/todo.md`.

## Architecture Decisions

- Use `apache/kafka:latest` for the broker, following the user's decision to
  track the current upstream release. Keep the Kafka UI tag at
  `ghcr.io/kafbat/kafka-ui:v1.5.0`. Verify the current Kafka tag and
  image-specific configuration before implementation; report any mismatch.
- One combined KRaft broker/controller, with auto topic creation disabled.
- Host listener advertises `127.0.0.1:9092`; host clients bootstrap at the same
  address to avoid IPv6 resolution against the IPv4-only port binding. Internal listener advertises
  `kafka:19092`; controller port is 9093 and is not published.
- Bind published ports explicitly to `127.0.0.1` (9092 and UI 8081). The spec's
  abbreviated `9092:9092` example does not enforce its local-only boundary.
- Broker health gates initialization; initialization creates `fleet.positions`
  with six partitions and replication factor one using `--if-not-exists`.
- UI connects to the internal listener. Gate UI on successful initialization so
  the inspection interface starts with the required topic ready.
- No configured volumes. Verify that the selected image does not leave Kafka
  data in an anonymous volume that defeats the promised reset behavior.
- No application tests or extra services. Static Compose validation and focused
  local integration checks fit this configuration-only story.

## Dependency and Implementation Order

`docker compose up -d` → healthy `kafka` → successful `kafka-init` → `kafka-ui`.

Build the actual Compose entry point first, then add each dependent service in
its own small edit. There are no helper functions or caller skeletons to invent.
Task 1 is independently inspectable; Task 2 makes the broker usable for later
stories; Task 3 completes the inspection interface. Task 4 verifies the assembled
story. A partial task does not claim the complete story's success criteria.

## Task List

- [x] ~~Task 1: Configure the local KRaft broker.~~
- [x] ~~Task 2: Create the topic after broker readiness.~~
- [x] ~~Checkpoint A: Review broker and initialization configuration.~~
- [x] ~~Task 3: Add Kafka UI.~~
- [x] ~~Task 4: Verify startup, connectivity and reset behavior.~~
- [x] ~~Checkpoint B: Review complete S1 acceptance evidence.~~

## Verification Boundaries

Planning runs no containers, downloads no images and produces no messages.
Static `docker compose config --quiet` is appropriate once the file exists.
Starting services, publishing the smoke-test message and resetting broker data
require the user's explicit instruction to run the local checks. Before a reset,
identify existing project containers and state; never destroy unrelated data.

The console test in SPEC.md runs inside the Kafka container. It proves a broker
round-trip but cannot prove a client on the host can reach the advertised host
listener. Task 4 therefore includes a separate host-based Kafka client check.
Select an already installed compatible client when available; if none exists,
record that check as pending and agree on a temporary client before installation.
A TCP port probe alone is insufficient because it does not test Kafka metadata.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Image tag or script path differs from the spec | Startup blocked | Check official image documentation and registry metadata before coding; confirm scripts during authorized runtime validation |
| Wrong advertised address | Initial connection works but operations fail | Test host and Compose-network clients separately |
| Topic init failure hidden by detached startup | Later stories cannot publish | Check init exit code and describe topic; UI depends on successful completion |
| Existing wrong partition count | `--if-not-exists` does not repair it | Describe the topic and fail verification on mismatch; do not silently repartition |
| Repeated `up` reuses an exited init container | False claim that init reran | Check lifecycle evidence; explicitly rerun init to prove idempotency |
| Reset leaves data behind | Spec's ephemeral-data promise fails | Inspect mounts and test topic emptiness after authorized down/up |

## Open Questions and Readiness

- SPEC.md already references issue #2, so its question about whether to create a
  story issue is stale. The current branch is `main`; resolve the story branch
  before implementation without creating another issue.
- Exact image availability, image defaults and Docker availability remain
  unverified. They are implementation preflight checks, not assumed facts.
- CI, lint and type gates are explicitly deferred in STACK.md; this story does
  not satisfy the broader automated engineering gates yet.
- User approved this plan on 2026-10-30. Stop at the implementation checkpoints
  in the task list; runtime checks still require explicit authorization.

## Planning Checklist

- [x] ~~Read the S1 spec, epic, architecture and stack decisions.~~
- [x] ~~Confirm no existing tasks plan would be overwritten.~~
- [x] ~~Define ordered tasks, acceptance checks and verification boundaries.~~
- [x] ~~Human has reviewed and approved the plan (2026-10-30).~~
