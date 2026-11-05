---
epic: 001-generate-and-ingest-telemetry
outline_key: S1
github_issue: kurtbrii/fleet-geo-tracking#2
---

# Spec: Local Kafka broker

## Objective

One command starts a local Kafka broker, creates the `fleet.positions` topic with
6 partitions, and starts Kafka UI; one command stops all of it. Every later story
(the generator, the Quarkus consumer) publishes to or reads from this broker.

Traces to epic 001 acceptance criteria:

- `docker compose up -d` starts a single KRaft broker on `127.0.0.1:9092` and
  Kafka UI; `docker compose down` stops both.
- `fleet.positions` exists with 6 partitions as soon as Compose is up, created
  explicitly rather than on the first publish.

Design source: `epics/001-generate-and-ingest-telemetry/architecture.md`
(Components, Listener setup, Interfaces exposed, Decisions). This spec does not
change anything decided there.

## Assumptions

1. **Ports.** Host clients use `127.0.0.1:9092`. Inside the Compose network the
   broker is reached at `kafka:19092`. The KRaft controller listens on `9093`
   and is not published to the host. Kafka UI is published at
   `http://localhost:8081` (the README's address; the container itself listens
   on 8080).
2. **Auto topic creation is turned off** on the broker. Combined with the
   explicit init step, a typo in a topic name fails loudly instead of quietly
   creating a 1-partition topic.
3. **Topic init is a one-shot Compose service** that uses the same
   `apache/kafka:latest` image, waits for the broker to report healthy, runs
   `kafka-topics.sh --create --if-not-exists` (6 partitions, replication factor
   1), and exits 0.
4. **The broker has a Compose healthcheck**, so the init service and Kafka UI
   start only once the broker accepts connections.
5. **No volume** (epic decision): `docker compose down` deletes the topic and all
   data; the next `up` recreates the topic empty.
6. **Cluster ID** uses the image's built-in default for a single local node.
   Nothing depends on its value.
7. **Image tags** are taken from `STACK.md`: `apache/kafka:latest` and
   `ghcr.io/kafbat/kafka-ui:v1.5.0`. The Kafka tag follows upstream releases;
   script paths inside the image (`/opt/kafka/bin/...`) are confirmed on the
   first run.

## Tech Stack

- Docker with Compose v2 (`docker compose`, not `docker-compose`)
- `apache/kafka:latest`: KRaft, one node acting as broker and controller
- `ghcr.io/kafbat/kafka-ui:v1.5.0`

No Python or Java in this story.

## Commands

```bash
# Start broker, create topic, start Kafka UI
docker compose up -d

# Status: kafka + kafka-ui "running" (kafka "healthy"), topic init "exited (0)"
docker compose ps -a

# Confirm the topic and its 6 partitions
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server 127.0.0.1:9092 --describe --topic fleet.positions

# Round-trip one message (producer, then consumer)
echo 'NAB1234:hello' | docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server 127.0.0.1:9092 --topic fleet.positions \
  --property parse.key=true --property key.separator=:
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server 127.0.0.1:9092 --topic fleet.positions \
  --from-beginning --max-messages 1 --property print.key=true

# Logs
docker compose logs -f kafka

# Stop and delete everything (no volume, so the topic is gone)
docker compose down
```

## Project Structure

```
fleet-geo-tracking/
├── docker-compose.yml     ← new: kafka, topic init, kafka-ui
└── README.md              ← untouched here; start/stop docs are S5
```

## Code Style

- Compose service names are short and lowercase: `kafka`, `kafka-init`,
  `kafka-ui`.
- Broker settings use the image's `KAFKA_*` environment variables, one per line.
- Comment only the *why* of a non-obvious line (listeners, auto-create off), in
  one line.
- No `version:` key (obsolete in Compose v2).

```yaml
services:
  kafka:
    image: apache/kafka:latest
    ports:
      - "9092:9092"
    environment:
      # Host clients get IPv4 loopback; containers get kafka:19092.
      KAFKA_ADVERTISED_LISTENERS: HOST://127.0.0.1:9092,INTERNAL://kafka:19092
```

## Testing Strategy

There is no application code in this story, so it has no pytest or JUnit tests.
Verification is the manual run in **Commands**, done once on a clean start
(`docker compose down` first), checking:

1. `docker compose ps -a`: `kafka` healthy, `kafka-ui` running, `kafka-init`
   exited with code 0.
2. `--describe` shows `PartitionCount: 6` and `ReplicationFactor: 1`.
3. The console round-trip prints `NAB1234	hello`. This proves a client on
   `127.0.0.1:9092` can produce and consume, which is the listener setup that
   is easiest to get wrong.
4. Kafka UI at `http://localhost:8081` lists `fleet.positions` with 6 partitions.
5. `docker compose up -d` run a second time is harmless: init exits 0 again
   (`--if-not-exists`), with no error.
6. `docker compose down`, then `up -d` again: the topic is back and empty.

A **walkthrough** of `docker-compose.yml` and the checks above is deferred: its
form and location are decided later, not in this story.

## Boundaries

- **Always:** pin image tags exactly as in `STACK.md`; keep Kafka reachable only
  from this machine (published ports only, no extra network exposure); verify
  from a clean `down`/`up`.
- **Ask first:** adding a volume; changing ports from the ones above; adding
  any service beyond `kafka`, `kafka-init` and `kafka-ui`; changing the partition
  count.
- **Never:** start a second broker; enable authentication or TLS in this
  story; edit the README start/stop section (that's S5); write generator or
  backend code.

## Success Criteria

- [x] `docker compose up -d` from the repo root starts `kafka` and `kafka-ui`, and
  `kafka-init` exits 0.
- [x] `fleet.positions` exists with 6 partitions and replication factor 1 right
  after `up`, before anything publishes.
- [x] Auto topic creation is off on the broker.
- [x] A console producer and consumer on `127.0.0.1:9092` round-trip a keyed
  message.
- [x] Kafka UI at `http://localhost:8081` shows the topic and its 6 partitions.
- [x] Running `up -d` twice causes no errors; `down` removes all containers and
  data.

## Deferred

- **Walkthrough** of `docker-compose.yml` and the checks: form and location
  decided later.

## Open Questions

- **Story issue and branch.** Run `/sdd:create-gh-story` for S1 first (giving a
  `epic-1/story-<M>-local-kafka-broker` branch), or build on a plain branch and
  skip the story issue?
