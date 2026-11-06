"""Command-line entry point for the vehicle simulator."""

import argparse
import itertools
import json
import random
import subprocess
import time
from collections.abc import Callable

from confluent_kafka import Producer
from simulator import Vehicle, advance_vehicle, create_fleet


def parse_options() -> argparse.Namespace:
    """Parse and validate the supported command-line options.

    Returns:
        argparse.Namespace(vehicles=1000, interval_ms=1000) when run without options
    """
    parser = argparse.ArgumentParser(
        description="Generate simulated vehicle positions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--vehicles", type=int, default=1000, help="fleet size")
    parser.add_argument("--interval-ms", type=int, default=1000, help="target tick interval in milliseconds")
    options = parser.parse_args()

    if not 1 <= options.vehicles <= 26**3 * 10_000:
        parser.error("--vehicles must be between 1 and 175760000")
    if options.interval_ms <= 0:
        parser.error("--interval-ms must be a positive integer")
    return options


def main() -> None:
    """Run the vehicle simulator command-line application.

    Returns:
        None; runs until interrupted, then exits without a traceback
    """
    options = parse_options()
    producer = Producer({"bootstrap.servers": "127.0.0.1:9092", "message.timeout.ms": 10000})
    try:
        run_simulation(options, producer)
    except KeyboardInterrupt:
        pass


def run_simulation(
    options: argparse.Namespace,
    producer: Producer,
    *,
    clock: Callable[[], float] = time.monotonic,
    wait: Callable[[float], None] = time.sleep,
    tick_limit: int | None = None,
) -> None:
    """Create the fleet, publish it, then publish one tick per target interval.

    Args:
        options: The parsed command-line options. ex:
            argparse.Namespace(
                vehicles=2,
                interval_ms=2000,
            )
        producer: The Kafka producer that sends each position. ex:
            Producer({
                "bootstrap.servers": "127.0.0.1:9092",
                "message.timeout.ms": 10000,
            })
        clock: Monotonic seconds, used to measure each tick. ex: time.monotonic
        wait: Sleeps for the rest of the interval. ex: time.sleep
        tick_limit: How many ticks to run after the first snapshot; None runs
            until interrupted. ex: 3

    Returns:
        None; produces one message per vehicle per tick to fleet.positions. ex:
            key=b"AAA0000"
            value={"id": "AAA0000", "lat": 14.5, "lng": 121.0, "bearing": 90.0, "speed": 45.0, "ts": 1793400000000}
    """
    subprocess.run(["clear"], shell=True, check=False)
    rng = random.Random()
    fleet = create_fleet(options.vehicles, rng)
    interval_seconds = options.interval_ms / 1000.0
    previous = clock()
    publish_snapshot(producer, fleet, time.time_ns() // 1_000_000)
    ticks = itertools.count() if tick_limit is None else range(tick_limit)
    for _ in ticks:
        wait(max(0.0, interval_seconds - (clock() - previous)))  # sleep only what's left of the interval
        now = clock()
        fleet = [advance_vehicle(vehicle, now - previous, rng) for vehicle in fleet]
        publish_snapshot(producer, fleet, time.time_ns() // 1_000_000)
        producer.poll(0)  # serve delivery callbacks without blocking
        previous = now


def publish_snapshot(producer: Producer, fleet: list[Vehicle], ts: int) -> None:
    """Produce one message per vehicle for a single tick, keyed by its plate.

    Args:
        producer: The Kafka producer that sends each position. ex:
            Producer({
                "bootstrap.servers": "127.0.0.1:9092",
            })
        fleet: Every vehicle's position at this tick. ex:
            [
                Vehicle(id="AAA0000", lat=14.5, lng=121.0, bearing=90.0, speed=45.0),
            ]
        ts: Epoch milliseconds stamped on every record. ex: 1793400000000

    Returns:
        None; queues one message per vehicle on fleet.positions. ex:
            key="AAA0000"
            value='{"id": "AAA0000", "lat": 14.5, "lng": 121.0, "bearing": 90.0, "speed": 45.0, "ts": 1793400000000}'
    """
    for vehicle in fleet:
        vehicle_record: dict[str, str | float | int] = {
            "id": vehicle.id,
            "lat": vehicle.lat,
            "lng": vehicle.lng,
            "bearing": vehicle.bearing,
            "speed": vehicle.speed,
            "ts": ts,
        }

        producer.produce("fleet.positions", key=vehicle.id, value=json.dumps(vehicle_record))


if __name__ == "__main__":
    main()
