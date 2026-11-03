"""Command-line entry point for the vehicle simulator."""

import argparse
from collections.abc import Callable
import json
import random
import sys
import time

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
    try:
        run_simulation(options)
    except KeyboardInterrupt:
        pass


def run_simulation(
    options: argparse.Namespace,
    *,
    clock: Callable[[], float] = time.monotonic,
    wait: Callable[[float], None] = time.sleep,
    tick_limit: int | None = None,
) -> None:
    """Create the fleet, emit it, then emit one tick per target interval.

    Args:
        options: argparse.Namespace(vehicles=2, interval_ms=2000)
        clock: time.monotonic
        wait: time.sleep
        tick_limit: None runs until interrupted; 3 emits three later ticks

    Returns:
        None; writes one snapshot of two JSON records per tick
    """
    rng = random.Random()
    fleet = create_fleet(options.vehicles, rng)
    interval_seconds = options.interval_ms / 1000.0
    last_tick = clock()
    emit_snapshot(fleet, time.time_ns() // 1_000_000)
    next_tick = last_tick + interval_seconds
    ticks = 0
    while tick_limit is None or ticks < tick_limit:
        now = clock()
        if now < next_tick:
            wait(next_tick - now)
            now = clock()
        elapsed_seconds = now - last_tick
        fleet = [advance_vehicle(vehicle, elapsed_seconds, rng) for vehicle in fleet]
        emit_snapshot(fleet, time.time_ns() // 1_000_000)
        last_tick = now
        next_tick += interval_seconds
        finished_tick = clock()
        if next_tick <= finished_tick:
            next_tick = finished_tick + interval_seconds
        ticks += 1


def emit_snapshot(fleet: list[Vehicle], ts: int) -> None:
    """Write one JSON record per vehicle for a single tick.

    Args:
        fleet: [Vehicle(id="AAA0000", lat=14.5, lng=121.0, bearing=90.0, speed=45.0)]
        ts: 1793400000000

    Returns:
        None; writes {"id": "AAA0000", "lat": 14.5, "lng": 121.0, "bearing": 90.0, "speed": 45.0, "ts": 1793400000000}
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

        print(json.dumps(vehicle_record))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
