---
epic: 001-generate-and-ingest-telemetry
---

# Architecture: Generate and ingest telemetry

> One epic, designed as a self-contained service. Conforms to `README.md`
> (pipeline direction, repository layout) and the repo's `STACK.md` (stack,
> versions and tooling). Decisions recorded in
> `PLAN.md` are binding here.

## Overview

This epic is the front half of the pipeline: a single-process Python generator
simulates vehicles drifting inside the Metro Manila bounding box and publishes
one JSON position event per vehicle per tick to the Kafka topic
`fleet.positions`, keyed by vehicle ID. A single KRaft broker and Kafka UI run in
Docker Compose; the generator and the Quarkus backend run on the host. The
backend consumes the topic as consumer group `fleet-conflation`, validates each
event on its own, counts valid events, and drops, logs and counts malformed ones.
The epic ends at a validated position inside Quarkus; keeping the latest
position per vehicle starts in epic 2.

## Components

| Component | Responsibility |
|---|---|
| Broker (Compose service `kafka`, `apache/kafka:latest`) | Single KRaft node (broker + controller) |
| Topic init (Compose one-shot service) | Creates `fleet.positions` with 6 partitions if it does not exist, then exits; the topic never depends on a broker default or on the first publish |
| Kafka UI (Compose service `kafka-ui`, `ghcr.io/kafbat/kafka-ui:v1.5.0`) | Inspection aid for topic, partitions and consumer-group lag; not part of the data path |
| Vehicle simulator (`generator/`, Python 3.12) | Holds the fleet's state and advances it one tick at a time with random heading drift, bouncing off the box edges; no Kafka dependency |
| Generator options | Parses `--vehicles` and `--interval-ms`, rejects invalid values with a clear message before anything is sent |
| Position publisher (`generator/`, `confluent-kafka` 2.16.0) | Serialises each vehicle's position to JSON and produces it to `fleet.positions` keyed by vehicle ID; counts delivery successes and failures |
| Generator activity reporter | Prints events sent per second and publish failures per second |
| Position consumer (`backend/`, Quarkus 3.40.1.1, SmallRye Reactive Messaging Kafka) | Incoming channel bound to `fleet.positions`, group `fleet-conflation`, offset reset `latest`; receives the raw payload and the message key |
| Position validator (`backend/`) | Turns a raw payload plus key into a validated position or a rejection reason (bad JSON, missing or wrong-typed field, any field out of range, key differing from `id`) |
| Ingestion counters (`backend/`) | Micrometer counters for consumed-valid and rejected events, exposed on the Prometheus endpoint; rejections are also logged as warnings |
| Kafka health (`backend/`, `quarkus-smallrye-health`) | Health check that reports Kafka as down when the broker is unreachable |
| Automated tests | pytest for the simulator, options and publisher's message building; JUnit for the validator and for the consumer's drop behaviour (using Quarkus's in-memory connector, so no broker is needed) |

## Design patterns used

| Pattern | Where | Why |
|---|---|---|
| Partitioning by key | Publisher: message key = vehicle `id` | Keeps each vehicle's events in one partition, so epic 2 receives them in order |
| Pure simulation core, I/O at the edge | Simulator vs publisher | S2 must be testable without Kafka; the drift model has no reason to know about the broker |
| Validate at the boundary, receive raw | Consumer reads the payload as a string and validates in application code | One policy covers every malformed case, including bad JSON, instead of letting connector deserialisation failures take a separate path |
| Drop-and-acknowledge for malformed events | Consumer | Decided in PLAN.md (no DLQ); a rejected event must still be acknowledged so its offset advances and the channel does not stop |
| Fail fast on configuration | Generator options | Invalid options are rejected before the first produce call, per the acceptance criteria |
| Asynchronous produce with delivery reports | Publisher | `confluent-kafka` buffers and retries in `librdkafka`; delivery callbacks are where failures become visible counts instead of being lost |
| Explicit topic creation | Topic init service | Removes the risk of the topic silently getting 1 partition |

## Data model

**Position event** (Kafka message value, UTF-8 JSON object, one per vehicle per tick).
Any field missing, of the wrong type or outside its range makes the event malformed.

| Field | Type | Rule |
|---|---|---|
| `id` | string | Philippine-style plate, three uppercase letters then four digits (`^[A-Z]{3}[0-9]{4}$`, e.g. `NAB1234`); stable per vehicle across generator runs; also the message key. Plates are generated, not real |
| `lat` | number | 14.35 ≤ lat ≤ 14.78 |
| `lng` | number | 120.90 ≤ lng ≤ 121.13 |
| `bearing` | number | Degrees clockwise from north, 0 ≤ bearing < 360 |
| `speed` | number | km/h, 0 ≤ speed ≤ 200 |
| `ts` | integer | Event time set by the generator, Unix epoch milliseconds |

**Kafka message key:** the vehicle `id` as a UTF-8 string. A message whose key
differs from its `id` field is malformed.

**Generator in-memory state:** one record per vehicle (`id`, `lat`, `lng`,
`bearing`, `speed`), created at start-up, advanced each tick, gone when the
process exits. IDs are derived deterministically from the vehicle's index, so the
same vehicle count gives the same plates on every run. No persistence.

**Backend in-memory state:** two monotonically increasing counts (valid,
rejected). No per-vehicle state in this epic, no persistence.

## Interfaces exposed

- **Topic `fleet.positions`**: 6 partitions, replication factor 1, key = vehicle
  `id`, value = Position event JSON above. Created explicitly by the Compose
  topic-init service.
- **Consumer group `fleet-conflation`**: owned by the backend; `auto.offset.reset`
  = `latest`.
- **Generator CLI**: `--vehicles` (default 1000) and `--interval-ms` (default
  1000), names taken from the README. Bootstrap server `127.0.0.1:9092`.
- **Broker address for host clients**: `127.0.0.1:9092`.
- **Kafka UI**: `http://localhost:8081` (README).
- **Backend health check**: Kafka status (up/down) at the SmallRye Health
  default, `/q/health` (readiness at `/q/health/ready`). Renaming it to `/healthz`
  is optional and checked against the Quarkus docs in S5.
- **Backend metrics**: Prometheus-format text at `/q/metrics` (Micrometer),
  including the valid and rejected counters.
- **Validated position (in-process, backend)**: the typed result of validation,
  carrying the six event fields. This is the hand-off point epic 2 attaches to;
  the mechanism is deferred (see Decisions).

### Listener setup

- Host clients (generator, backend) bootstrap at `127.0.0.1:9092`; the broker
  advertises the same address because Compose publishes the port on IPv4 loopback.
- Kafka UI and the topic-init service run inside the Compose network and connect
  through a separate internal listener advertised under the broker's Compose
  service name. Both listeners, plus the controller listener, are declared in the
  broker's listener security map. Port numbers for the internal and controller
  listeners are an S1 detail.
- The backend sets its bootstrap servers to `127.0.0.1:9092` explicitly and
  disables Quarkus Kafka Dev Services, so Quarkus never starts its own broker in
  dev or test mode. The exact property name is checked against the 3.40 docs in
  S4.

### Failure behaviour

| Situation | Generator | Backend |
|---|---|---|
| Malformed event (bad JSON, missing or wrong-typed field, any field out of range, key differs from `id`) | n/a | Dropped, logged at warning, counted as rejected, acknowledged; never passed on. No dead-letter topic |
| Broker down | Keeps running and retrying; logs publish failures each second | Starts anyway, logs connection errors; health check reports Kafka down |
| Broker returns | Flow resumes without restart | Flow resumes without restart; health check returns to up |
| Out-of-order or stale event | n/a | Not detected here. Each event is validated on its own; ordering policy belongs to epic 2 |

## Boundaries

**Owns**

- The Docker Compose file at the repo root and its services (`kafka`, topic
  init, `kafka-ui`), including listener configuration and the 6-partition topic.
- The `fleet.positions` topic definition: name, partition count, key and value
  format.
- The Position event JSON contract, including the validity rules (field
  presence, field types, ranges, key matching `id`).
- Vehicle simulation: ID scheme, random-drift movement, edge bouncing, tick
  timing, and the generator's CLI options and their validation.
- Producing to Kafka, producer settings, and the generator's per-second
  sent/failed reporting.
- Consumer group `fleet-conflation`, its offset-reset policy, and the
  malformed-event policy (drop, log, count, acknowledge).
- The backend's ingestion counters, metrics endpoint and Kafka health reporting.
- The automated tests for the above, and the plain-language walkthrough of them.
- Start/stop instructions for broker, backend and generator in `README.md`.

**Depends on**

- Docker with Compose, Java 21 with Maven, and Python 3.12 on the local machine.
- The stack in `STACK.md`: `apache/kafka:latest`,
  `ghcr.io/kafbat/kafka-ui:v1.5.0`, Quarkus 3.40.1.1 with
  `quarkus-messaging-kafka`, `quarkus-smallrye-health`, the Micrometer
  Prometheus registry, `confluent-kafka` 2.16.0, pytest and JUnit.
- Nothing from any other epic. This is the first epic.

**Exposes** (what epics 2 and 3 may rely on)

- `fleet.positions` on `127.0.0.1:9092`, 6 partitions, keyed by vehicle `id`,
  with the Position event JSON shape above.
- Per-vehicle ordering within a partition, and nothing stronger: no global
  ordering, no deduplication, no stale-event filtering.
- Inside the backend, a stream of validated positions only. Every event that
  reaches the hand-off point has all six fields with correct types, in-range
  values and a key equal to `id`.
- The consumer group `fleet-conflation` and its `latest` reset: after a backend
  restart with no stored offset, state rebuilds from new events only.

**Does not expose** (other epics must not rely on)

- The generator's internal vehicle state, drift parameters, how plates are
  derived from a vehicle's index, or its options.
- Rejected events in any form: there is no DLQ and no record of their content
  beyond log lines.
- The counters' names, or log line format, as an API.
- Any history or replay of positions. No database exists.
- A specific Kafka UI internal listener address.

## Entry point

- **Broker and UI**: `docker compose up -d` / `docker compose down` from the repo
  root, against `docker-compose.yml` (README layout).
- **Generator**: a CLI run from the host, `generator/generator.py` per the README
  layout, with `--vehicles` and `--interval-ms`. The README's current
  `--processes` flag is removed: this epic is single-process (PLAN.md).
- **Backend**: `mvn quarkus:dev` in `backend/`. The consumer is registered as a
  SmallRye incoming channel; the channel-to-topic binding, group, offset reset
  and bootstrap servers live in `backend/src/main/resources/application.properties`.
- **Health and metrics**: `/q/health` and `/q/metrics` on the backend.
- **Tests**: `pytest` in `generator/`, `mvn test` in `backend/`.

## Decisions

Answered by the author on 2026-10-30 unless noted.

- [x] **Automated tests, with a walkthrough.** pytest for the generator, JUnit
  for the backend. Every story that adds tests also produces a plain-language
  walkthrough: what each test asserts, why, and how to run it. The original
  "no tests in v1" stack decision is superseded; the repo's `STACK.md` records
  the reconciled stack.
- [x] **Health extension.** `quarkus-smallrye-health` is added. Default path
  `/q/health`; the `/healthz` rename is optional, checked in S5.
- [x] **Counts reporting.** Micrometer counters on a Prometheus endpoint
  (`/q/metrics`) plus warning logs for rejections. Prometheus is the tool that
  scrapes and stores such metrics and Grafana draws charts from it; this epic
  ships only the endpoint, not Prometheus or Grafana containers (a monitoring
  platform is out of scope).
- [x] **`ts` format.** Unix epoch milliseconds, integer.
- [x] **`bearing` and `speed`.** Degrees clockwise from north, 0 ≤ b < 360; km/h,
  0 ≤ s ≤ 200. Out-of-range values are malformed.
- [x] **Vehicle ID.** Philippine-style plate, `^[A-Z]{3}[0-9]{4}$`. Strings are
  larger than integers on the wire, which matters only for epic 2's snapshot frame
  size at very large fleets.
- [x] **Key vs `id` mismatch.** Rejected as malformed.
- [x] **Topic creation.** Created explicitly at Compose start-up by a one-shot
  init service, not by auto-create.
- [x] **`backend/pom.xml`.** Deleted by the author; S4 creates it fresh at
  3.40.1.1.
- [x] **README drift.** S5 aligns the start/stop section with this epic
  (Python 3.12, single process, 1,000 vehicles at 1,000 ms); the conflation
  description stays as epic 2's target.
- [ ] **Hand-off to epic 2.** How validated positions leave the consumer
  (in-process channel, direct call, or CDI event). Deferred by the author: decided
  after the last story of this epic is finished.
- [x] **Broker data across `docker compose down`.** No volume: `down` wipes the
  topic and offsets. With `latest` this loses only in-flight events.

## Changelog

- 2026-10-30: Created.
- 2026-10-30: Recorded the author's answers to the open questions: tests with
  walkthrough, health extension, Prometheus endpoint, `ts`/`bearing`/`speed`/ID
  rules, key check, explicit topic creation, no broker volume. Only the epic 2
  hand-off remains open, by design.
