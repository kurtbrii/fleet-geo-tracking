"""Command-line entry point for the vehicle simulator."""

import argparse
import json
import random
import sys
import time

from simulator import Vehicle, advance_vehicle, create_fleet


def parse_options() -> argparse.Namespace:
    """Parse and validate the supported command-line options."""
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
    """Run the vehicle simulator command-line application."""
    options = parse_options()
    run_simulation(options)


def run_simulation(options: argparse.Namespace) -> None:
    """Create the fleet, emit it, then emit one advanced tick."""
    rng = random.Random()
    fleet = create_fleet(options.vehicles, rng)
    emit_snapshot(fleet, time.time_ns() // 1_000_000)
    elapsed_seconds = options.interval_ms / 1000.0
    fleet = [advance_vehicle(vehicle, elapsed_seconds, rng) for vehicle in fleet]
    emit_snapshot(fleet, time.time_ns() // 1_000_000)


def emit_snapshot(fleet: list[Vehicle], ts: int) -> None:
    """Write one JSON record per vehicle for a single tick."""
    for vehicle in fleet:
        vehicle_record = {
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
