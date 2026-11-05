# Tasks: S1 — Local Kafka broker

Source: `SPEC.md`. Rationale and boundaries: `tasks/plan.md`.
The user approved the plan on 2026-10-30. Tasks 1–4 are implemented and
verified; Checkpoint B review is pending.
Check and strike through completed tasks only after recording verification.
Runtime checks require an explicit instruction to run them.

## Task 1: Configure the local KRaft broker

- [x] ~~**Task 1 complete**~~

**Description:** Verify the current image tag and configuration against official
documentation, resolve the story branch, then create the Compose entry point
with one combined broker/controller and a readiness healthcheck.

**Acceptance criteria:**
- [x] ~~`kafka` uses the specified image and required host, internal and controller listeners.~~
- [x] ~~Host port 9092 binds only to loopback; auto topic creation is disabled and no persistent volume is configured.~~
- [x] ~~A bounded Kafka protocol healthcheck and necessary single-broker internal-topic settings are present.~~

**Verification:**
- [x] ~~`docker compose config --quiet` succeeds; inspect resolved listeners, bindings and healthcheck.~~
- [x] ~~Record official image/configuration references; report unavailable pins without substituting versions.~~
- [ ] No app build or unit tests apply; runtime verification is Task 4.

**Dependencies:** None.
**Files likely touched:** `docker-compose.yml`.
**Estimated scope:** Small, one implementation file.

**Evidence:** `docker compose config --quiet` succeeded. Resolved config shows
`apache/kafka:latest`, host binding `127.0.0.1:9092`, three listeners, auto
topic creation disabled, and `/tmp/kraft-combined-logs` on tmpfs. The pinned
Kafka image is documented by [Apache's Kafka 4.3 Docker guide](https://kafka.apache.org/43/getting-started/docker/).

## Task 2: Create the topic after broker readiness

- [x] ~~**Task 2 complete**~~

**Description:** Add one-shot `kafka-init`, using the same Kafka image and the
internal listener `kafka:19092`, dependent on broker health.

**Acceptance criteria:**
- [x] ~~Creates `fleet.positions` with six partitions and replication factor one using `--if-not-exists`.~~
- [x] ~~Waits for broker health and exposes initialization failure through a nonzero exit status.~~
- [x] ~~Has no published ports, volumes or unconditional restart loop.~~

**Verification:**
- [x] ~~`docker compose config --quiet` succeeds.~~
- [x] ~~Inspect resolved command, dependency condition and failure propagation.~~
- [ ] Runtime topic checks are Task 4; no application build or unit tests apply.

**Dependencies:** Task 1.
**Files likely touched:** `docker-compose.yml`.
**Estimated scope:** Small, one implementation file.

**Evidence:** `docker compose config --quiet` succeeded. Resolved config shows
`kafka-init` uses the Kafka image, waits for `kafka` health, and invokes
`kafka-topics.sh --create --if-not-exists` with six partitions and replication
factor one. No runtime services were started.

## Checkpoint A: Broker configuration

- [x] ~~Tasks 1–2 pass static checks.~~
- [x] ~~Review with human before proceeding to Task 3 (user explicitly directed Task 3).~~

## Task 3: Add Kafka UI

- [x] ~~**Task 3 complete**~~

**Description:** Add the pinned UI service, using the internal Kafka listener,
starting after successful topic initialization.

**Acceptance criteria:**
- [x] ~~Uses `ghcr.io/kafbat/kafka-ui:v1.5.0` and `kafka:19092`.~~
- [x] ~~Container port 8080 is exposed only on `127.0.0.1:8081`.~~
- [x] ~~Exactly three specified services exist; UI depends on successful init.~~

**Verification:**
- [x] ~~`docker compose config --quiet` succeeds; review the full resolved configuration.~~
- [ ] Browser verification is Task 4; no application build or unit tests apply.

**Dependencies:** Task 2 and Checkpoint A review.
**Files likely touched:** `docker-compose.yml`.
**Estimated scope:** Small, one implementation file.

**Evidence:** `docker compose config --quiet` succeeded. The resolved config
shows three services, Kafka UI on `127.0.0.1:8081`, connection to `kafka:19092`,
and a dependency on `kafka-init` completing successfully. UI startup was not
tested in a browser; that remains in Task 4.

## Task 4: Verify the broker lifecycle

- [x] ~~**Task 4 complete**~~

**Description:** After explicit authorization, run local integration checks and
record evidence here. Update S1 success checkboxes only for verified outcomes.

**Acceptance criteria:**
- [x] ~~Clean startup gives a healthy broker, successful init and running UI; topic has six partitions and replication factor one.~~
- [x] ~~Internal and genuine host Kafka clients round-trip a keyed message; UI shows the topic and partition count.~~
- [x] ~~Repeated startup and explicit init rerun succeed; authorized down/up recreates an empty topic without persistent broker data.~~

**Verification:**
- [x] ~~Inspect existing project state before the authorized reset, then run `docker compose down` and `docker compose up -d`.~~
- [x] ~~Run `docker compose ps -a`; inspect init exit status.~~
- [x] ~~Describe the topic with the image's `kafka-topics.sh`, using `kafka:19092` internally.~~
- [x] ~~Run the in-container console round-trip. Use host `kcat` against `127.0.0.1:9092` for metadata discovery and keyed produce/consume.~~
- [x] ~~Open `http://localhost:8081` and confirm the topic and six partitions.~~
- [x] ~~Repeat `docker compose up -d`; its output showed `kafka-init` ran and exited against the existing topic.~~
- [x] ~~Inspect broker mounts; after down/up, confirm topic recreation and zero end offsets on all six partitions before publishing.~~
- [x] ~~Reconcile SPEC.md success criteria with evidence. No application build or unit-test suite applies.~~

**Dependencies:** Task 3, explicit runtime authorization, suitable host client.
**Files likely touched:** `SPEC.md`, `tasks/todo.md`, `tasks/plan.md`.
**Estimated scope:** Medium, three documentation files. Configuration fixes return
to the relevant task and repeat affected checks.

**Evidence:** `docker compose ps -a` showed Kafka healthy, `kafka-init` exited 0,
and Kafka UI running. Topic description showed six partitions and replication
factor one. The in-container console round-trip returned `NAB1234\thello`.
Host `kcat -b 127.0.0.1:9092 -L` listed the broker and topic; host produce and
consume returned `HOST1234\thost-smoke`. `localhost:9092` resolved to IPv6
`::1`, while Compose publishes IPv4 only, so the advertised listener and host
client instructions now use `127.0.0.1:9092`. The user-provided UI screenshot
showed the topic and partition row. After `docker compose down` / `up -d`, the
broker was healthy, init exited 0, UI ran, topic description showed six
partitions, and `kafka-get-offsets.sh --time -1` returned end offset 0 for all
six partitions. `docker compose logs kafka-init` showed successful topic
creation. The image also attaches anonymous volumes, but Kafka logs are
configured on tmpfs at `/tmp/kraft-combined-logs`; no Kafka data persisted.

## Checkpoint B: S1 review

- [x] ~~Every S1 success criterion has verification evidence.~~
- [x] ~~Diff contains only this story's configuration and planning/status updates.~~
- [x] ~~README, generator/backend work and deferred walkthrough remain out of scope.~~
- [x] ~~Human reviewed and approved the result before story finishing or starting S2.~~
