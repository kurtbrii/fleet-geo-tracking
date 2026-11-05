---
id: 001-generate-and-ingest-telemetry
title: Generate and ingest telemetry
github_issue: kurtbrii/fleet-geo-tracking#1
status: in-progress
---

# Epic: Generate and ingest telemetry

## Goal

Simulated vehicle positions travel from a Python generator through a local Kafka
broker into a Quarkus service that validates them.

## User-facing outcome

Starting the broker, backend and generator with the documented commands produces
a visible flow of positions: the generator reports events sent per second, the
backend reports events consumed and events rejected, and Kafka UI shows the
`fleet.positions` topic, its 6 partitions and the `fleet-conflation` consumer
group. Before this epic, none of the pipeline runs.

## Acceptance criteria

- [ ] `docker compose up -d` starts a single KRaft broker on `127.0.0.1:9092`
  and Kafka UI; `docker compose down` stops both.
- [ ] `fleet.positions` exists with 6 partitions as soon as Compose is up,
  created explicitly rather than on the first publish.
- [ ] The generator publishes `id` (a plate such as `NAB1234`), `lat`, `lng`,
  `bearing` (degrees, 0–359), `speed` (km/h, 0–200) and `ts` (epoch
  milliseconds) for each vehicle, keyed by vehicle ID, with positions that
  change over time and stay inside lat 14.35–14.78, lng 120.90–121.13.
- [ ] By default the generator runs 1,000 vehicles every 1,000 ms; both values
  are options, and invalid values are rejected with a clear message before any
  event is sent.
- [ ] The generator prints events sent per second, and publish failures are
  logged rather than silently lost.
- [ ] The backend consumes `fleet.positions` in consumer group
  `fleet-conflation`, starting from `latest` when the group has no stored
  offset.
- [ ] Valid events are counted; malformed events (bad JSON, missing or
  wrong-typed field, any field out of range, message key different from `id`)
  are dropped, logged and counted, and never passed on. An automated test proves
  this.
- [ ] The valid and rejected counts are readable at `/q/metrics`.
- [ ] With the broker stopped, the generator keeps retrying and logs failures,
  and the backend logs connection errors and `/q/health` reports Kafka as down.
  Restarting the broker resumes the flow without restarting either side.
- [ ] The generator and backend have automated tests (pytest, JUnit), and each
  story that adds tests includes a plain-language walkthrough of them.
- [ ] README start and stop instructions match what actually runs.

## Story Outline

> Keys are stable. Each row is one slice that can be specified, built and shipped
> on its own, and tested without the other rows. Order rows by dependency. Don't
> name functions or call chains, and size by reviewable scope, not a count. Each
> story is specified with `/spec-driven-development`, then `/sdd:finish-story`
> moves it under this epic and fills its Story and Status cells.

| Key | Title | Summary | Story | Status |
|---|---|---|---|---|
| S1 | [feat] Local Kafka broker | Start and stop a single KRaft broker plus Kafka UI with one command, with `fleet.positions` created explicitly with 6 partitions | [Story 1](stories/story-001-local-kafka-broker/SPEC.md) · #2 | done |
| S2 | [feat] Vehicle simulator | Generate stable plate-ID vehicles that drift randomly inside the Metro Manila box, with validated count and interval options, tested with pytest and a walkthrough, no Kafka needed | [Story 5](stories/story-005-vehicle-simulator/SPEC.md) · #5 | done |
| S3 | [feat] Publish positions to Kafka | Send each vehicle's position to `fleet.positions` keyed by vehicle ID, reporting events sent per second and publish failures | — | outline |
| S4 | [feat] Consume and validate positions | Quarkus reads `fleet.positions` as `fleet-conflation`, counts valid events at `/q/metrics`, and drops, logs and counts malformed ones, tested with JUnit and a walkthrough | — | outline |
| S5 | [feat] Broker-down visibility and startup docs | `/q/health` reports Kafka down, both sides recover when it returns, and README start/stop steps match reality | — | outline |

Status values: `outline` → `done`, plus `cancelled`.

## Risks

- **Advertised listener misconfiguration.** Kafka must advertise
  `127.0.0.1:9092` to host clients and a separate internal address to Kafka UI
  in the Compose network. Getting this wrong lets clients connect once, then
  fail.
- **Quarkus 3.40 is new to the author.** Configuration names and Dev Services
  behavior differ across Quarkus versions; Kafka Dev Services may try to start
  its own broker unless disabled.

## Out of scope

- Latest-position map, snapshots and SSE (epic 2).
- Map and frontend (epic 3).
- Rejecting out-of-order or stale events (epic 2).
- Multiprocess generator and any throughput target.
- Dead-letter topic, replication, hosting.

## Changelog

- 2026-10-30: Created.
- 2026-10-30: Updated from the author's answers: plate IDs, explicit topic creation, tests with walkthrough, health and metrics endpoints, stricter malformed-event rules.
- 2026-10-30: Issue created: kurtbrii/fleet-geo-tracking#1
- 2026-10-31: Finished Story 1 and moved its spec and task notes under the epic; the local Kafka broker and UI are implemented and verified.
- 2026-11-05: Finished Story 5 (S2, vehicle simulator) and moved its spec and task notes under the epic; the simulator CLI is implemented and all success criteria are verified.
