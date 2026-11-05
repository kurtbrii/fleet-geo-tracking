---
epic: 001-generate-and-ingest-telemetry
---

# Plan: Generate and ingest telemetry

> Written by `/sdd:create-epic`. Ends with open questions, answered in chat before
> `epic.md` and `architecture.md` are written.

## Problem

Nothing in the pipeline exists yet. The snapshot stream and the map both need a
steady flow of vehicle positions arriving in Quarkus, and right now there is no
broker, no source of positions and no consumer.

## Goal

Simulated vehicle positions travel from a Python generator through a local Kafka
broker into a Quarkus service that validates them.

## Scope

Features 1–3 of `docs/ideas/fleet-geo-tracking.md`:

- **Local startup:** Kafka (KRaft, single broker) through Docker Compose, the
  `fleet.positions` topic with 6 partitions, and documented start/stop steps for
  the broker, backend and generator.
- **Simulated telemetry:** a Python generator with stable vehicle IDs and
  random-drift movement inside the Metro Manila bounding box (lat 14.35–14.78,
  lng 120.90–121.13). It publishes `id`, `lat`, `lng`, `bearing`, `speed`, `ts`
  keyed by vehicle ID, takes vehicle count and emission interval as options,
  rejects invalid options and reports events sent per second and publish
  failures.
- **Kafka consumption:** a Quarkus service in consumer group `fleet-conflation`
  that reads `fleet.positions`, validates each event, applies an explicit policy
  to malformed events and reports consumed-event activity. Broker unavailability
  is visible.

## Non-goals

- **Keeping the latest position per vehicle, snapshots, SSE:** epic 2. This epic
  ends at a validated event inside Quarkus.
- **Map and frontend:** epic 3.
- **Reaching 10,000 vehicles or 50,000 events/s:** optional targets measured
  later; no throughput number gates this epic.
- **Road-following movement, real GPS data, a database, replicated Kafka.**
  Excluded in the idea doc.

## Constraints

- Stack is fixed by the repo's `STACK.md`: Quarkus 3.40.1.1 LTS
  on Java 21 with SmallRye Reactive Messaging (Kafka); `apache/kafka:latest` in
  KRaft mode; Python 3.12 with `confluent-kafka` 2.16.0.
- Local-only. No hosting, no external writes. Map tiles are not part of this
  epic.
- Topic name `fleet.positions`, 6 partitions, key = vehicle ID: fixed in
  README.md.

## Library research

No new libraries. Everything needed is already chosen in `STACK.md`.

| Library | For | Fits stack because | Alternative considered |
|---|---|---|---|

## Open questions

- [x] **Default load.** What vehicle count and emission interval run comfortably
  on this machine by default?
  **Answer:** 1,000 vehicles every 1,000 ms (about 1,000 events/s).
- [x] **Generator processes.** `STACK.md` and README describe a multiprocess
  generator, which only matters for high throughput. Single process for this
  epic, with multiprocess deferred to the optional performance work?
  **Answer:** Single process. Multiprocess is deferred to the optional
  performance work.
- [x] **Malformed-event policy.** What does the consumer do with an event that
  fails validation (bad JSON, missing field, coordinates outside the box)?
  **Answer:** Drop it, log a warning and count it. No dead-letter topic.
- [x] **Out-of-order and stale events.** Should the consumer reject an event
  whose `ts` is older than the last one seen for that vehicle, or leave that to
  epic 2's latest-position map?
  **Answer:** Leave it to epic 2. This epic validates each event on its own.
- [x] **Offset reset on startup.** When the consumer group has no stored offset,
  start from the newest events (`latest`) or replay the topic (`earliest`)?
  **Answer:** `latest`.
- [x] **Broker unavailable.** What should each side do when Kafka is down?
  **Answer:** The generator keeps retrying and logs publish failures each
  second. The backend starts, logs connection errors and exposes a health check
  that reports Kafka as down.
- [x] **Kafka UI container.** Include `kafbat/kafka-ui` in Compose, or rely on
  the generator's and backend's own counters?
  **Answer:** Include it, as an inspection aid. The generator's and backend's
  own counters remain the primary evidence of activity.
