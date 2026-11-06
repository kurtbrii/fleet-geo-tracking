# Fleet Geo-Tracking Pipeline

A local, open-source streaming pipeline that simulates 10,000 delivery vehicles driving around Metro Manila, pushes their GPS telemetry through Apache Kafka at ~50,000 events/second, conflates it in a Quarkus service, and renders every vehicle live on a browser map.

The core problem it addresses: a browser cannot draw 50,000 position updates per second. The backend reduces the stream to **one snapshot per second** containing the latest position of every vehicle, and the frontend draws that snapshot on a **canvas layer** instead of 10,000 DOM markers.

> Status: in development. Performance numbers below are targets until measured; the Benchmarks section is filled in from real runs only.

---

## Architecture

```
┌────────────────────────┐   ~50k msgs/s    ┌──────────────┐   ~50k msgs/s   ┌──────────────────────────┐   1 frame/s    ┌──────────────────────┐
│ Python generator        │ ───────────────▶ │ Apache Kafka │ ──────────────▶ │ Quarkus conflation svc   │ ─────────────▶ │ Browser (Leaflet +   │
│ (confluent-kafka,       │  key=vehicleId   │ (KRaft, 1    │                 │ latest-position map +    │   SSE          │  canvas layer)       │
│  N processes)           │                  │  broker)     │                 │ 1s snapshot ticker       │                │                      │
└────────────────────────┘                  └──────────────┘                 └──────────────────────────┘                └──────────────────────┘
```

### 1. Simulation (Python)
- 10,000 vehicles, each emitting `{id, lat, lng, bearing, speed, ts}` every 200 ms → 50,000 events/s.
- Movement model: **random heading drift** inside the Metro Manila bounding box (lat 14.35–14.78, lng 120.90–121.13). Heading changes by a small random amount each tick; vehicles bounce off the box edges. **Vehicles are not road-snapped** — they will cross buildings and water. This is a load generator, not a routing simulator.
- Uses `confluent-kafka` (librdkafka, C-backed), not `kafka-python`. Load is split across multiple OS processes (`multiprocessing`) because Python threads are limited by the GIL.
- Producer tuning: `linger.ms`, `batch.size`, `compression.type=lz4`, `acks=1`.
- Prints actual achieved throughput every second so the 50k/s figure is verified, not assumed.

### 2. Ingestion (Apache Kafka)
- Single broker in KRaft mode (no ZooKeeper), via Docker Compose.
- Topic `fleet.positions`, 6 partitions, keyed by `vehicleId` so each vehicle's events stay ordered.
- Kafka UI container for inspecting topics, partitions and consumer lag.

### 3. Conflation (Quarkus)
- SmallRye Reactive Messaging consumes `fleet.positions` in batches.
- Each event overwrites that vehicle's entry in a `ConcurrentHashMap<vehicleId, Position>` — only the latest position is kept.
- A `Multi.createFrom().ticks().every(1s)` stream snapshots the map and broadcasts it to all SSE clients.
- This is **conflation** (keep latest, emit on a timer), not per-message throttling. It reduces client-bound traffic from ~50,000 messages/s to 1 frame/s, at the cost of dropping 4 of every 5 intermediate positions per vehicle.
- Snapshot wire format is a compact array to keep frames small:
  `[[id, lat, lng, bearing], ...]` with coordinates rounded to 5 decimals (~1 m).
- Optional: client sends its map bounds; server sends only vehicles inside the viewport.
- Exposes metrics (Micrometer / Prometheus endpoint): events consumed/s, snapshot size, snapshot build time, consumer lag.

### 4. Presentation (Leaflet)
- One `EventSource` connection, one JSON frame per second.
- Vehicles drawn on a **canvas layer** (single `<canvas>`, redrawn per frame), not as individual `L.marker` DOM nodes.
- Optional interpolation between frames with `requestAnimationFrame` for smooth motion.
- On-screen HUD: vehicles shown, frame size, frame parse + draw time, FPS.
- Served as static files by Quarkus at `http://localhost:8080`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Generator | Python 3.11+, `confluent-kafka`, `multiprocessing` |
| Broker | Apache Kafka (KRaft) via Docker Compose, Kafka UI |
| Backend | Quarkus 3.x, Java 21, SmallRye Reactive Messaging (Kafka), Mutiny, Micrometer |
| Push | Server-Sent Events |
| Frontend | Leaflet.js, canvas rendering, OpenStreetMap tiles |

All components are free and open source. Map tiles are fetched from OpenStreetMap's public tile servers, which is fine for local development but subject to the [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/); for anything beyond local use, self-host tiles or use a tile provider.

---

## Repository Layout

```
fleet-geo-tracking/
├── docker-compose.yml          # Kafka (KRaft) + Kafka UI
├── generator/
│   ├── requirements.txt        # confluent-kafka
│   └── generator.py            # multiprocess producer, throughput logging
├── backend/                    # Quarkus app
│   ├── pom.xml
│   └── src/main/
│       ├── java/.../
│       │   ├── Position.java
│       │   ├── PositionConsumer.java   # Kafka → latest-position map
│       │   ├── SnapshotBroadcaster.java # 1s ticker → SSE
│       │   └── SnapshotResource.java    # GET /stream (SSE)
│       └── resources/
│           ├── application.properties
│           └── META-INF/resources/      # frontend (index.html, map.js)
└── README.md
```

---

## Running Locally

Prerequisites: Docker, Java 21, Maven, Python 3.11+.

```bash
# 1. Start Kafka and Kafka UI
docker compose up -d
#    Kafka UI: http://localhost:8081

# 2. Start the backend (JVM dev mode)
cd backend
mvn quarkus:dev
#    Map: http://localhost:8080

# 3. Start the generator
cd generator
pip install -r requirements.txt
python generator.py --vehicles 10000 --interval-ms 200 --processes 4
```

Optional native build (for measuring memory footprint):

```bash
cd backend
mvn package -Dnative
./target/*-runner
```

---

## Development checks

Prerequisites: [uv](https://docs.astral.sh/uv/), and gitleaks (`brew install gitleaks`).

```bash
uv sync --locked          # installs ruff, pyrefly, pytest-cov and lefthook at the pinned versions
uv run lefthook install   # once per clone: wires the git hooks
```

The checks live in `lefthook.yml`:

- **On commit:** ruff fixes lint and formatting on staged Python files and re-stages them; commits with suppression comments (`# noqa`, `# type: ignore`, `# pyrefly: ignore`) are blocked.
- **On push:** lockfile check, `ruff check`, `ruff format --check`, `pyrefly check`, the suppression check, tests with an 80% coverage floor, and a gitleaks scan of the full git history.

Run everything by hand with `uv run lefthook run pre-push --all-files`. CI runs that same command on every push and pull request, so local and CI checks can't drift apart.

---

## Benchmarks

Fill in only from measured runs. Record hardware with every result.

| Metric | Target | Measured | How measured |
|---|---|---|---|
| Generator throughput | 50,000 msgs/s | TBD | generator's per-second counter |
| Backend consume rate | ≥ 50,000 msgs/s, lag stable | TBD | Micrometer counter + Kafka UI lag |
| Snapshot frame size (10k vehicles) | < 400 KB | TBD | backend metric |
| Snapshot build time | < 50 ms | TBD | backend metric |
| Browser parse + draw per frame | < 50 ms | TBD | HUD / Chrome Performance panel |
| Backend RSS, JVM | — | TBD | `ps` / Activity Monitor |
| Backend RSS, native image | — | TBD | `ps` / Activity Monitor |

Test machine: TBD (CPU, RAM, OS).

---

## Design Decisions

**Why conflation instead of forwarding every event?**
The browser only needs where each vehicle is now. Sending 50,000 updates/s would freeze the tab; sending the latest position of every vehicle once per second gives the same picture at a fraction of the cost. The trade-off is that intermediate positions are dropped.

**Why a canvas layer instead of Leaflet markers?**
Each `L.marker` is a DOM element. Repositioning 10,000 of them every second forces the browser to recalculate layout constantly. One `<canvas>` redrawn per frame avoids that.

**Why key Kafka messages by `vehicleId`?**
Kafka only guarantees order within a partition. Keying by vehicle sends all of one vehicle's events to the same partition, so they arrive in order and a newer position is never overwritten by an older one.

**Why `confluent-kafka` and multiple processes?**
`kafka-python` is pure Python and Python threads share one interpreter lock (the GIL), so threads alone can't reach 50,000 msgs/s. `confluent-kafka` wraps a C library, and separate processes each get their own interpreter.

**Why SSE instead of WebSockets?**
Data only flows server → browser. SSE is plain HTTP, reconnects automatically, and needs no extra protocol.

**Why no database?**
The live map only needs the current position of each vehicle, which fits in memory. Kafka already keeps recent raw events on disk. A database would only be justified by a feature that reads history, such as trip replay, which is out of scope for this version.

---

## Known Limitations

- Vehicle movement is random drift, not road-following.
- Conflation drops intermediate positions; this is a live-view design, not a trip-history store.
- Single Kafka broker, no replication — not fault tolerant.
- Snapshot is broadcast in full to every client; viewport filtering reduces this but does not scale to many concurrent viewers without further work.
- OSM public tiles are rate-limited by policy.
- No position history is stored; when the backend restarts, the map rebuilds from new events only.

---

## Build Plan

1. **Infra** — `docker-compose.yml` with Kafka (KRaft) + Kafka UI; create topic with 6 partitions.
2. **Generator** — multiprocess `confluent-kafka` producer with drift model and throughput logging. Confirm 50k/s in Kafka UI.
3. **Consumer** — Quarkus app consuming into the latest-position map; expose consume-rate metric. Confirm lag stays flat.
4. **Snapshot + SSE** — 1s ticker, compact array format, `/stream` endpoint. Verify with `curl -N`.
5. **Frontend** — Leaflet map centered on Metro Manila, canvas layer, HUD.
6. **Polish** — frame interpolation, viewport filtering, native build.
7. **Measure** — run full load, fill in Benchmarks table, record a GIF for the README.
