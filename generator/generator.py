"""Command-line entry point for the vehicle simulator."""

import argparse
import random

from simulator import create_fleet


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
    run_simulation(options)  # TODO: (emit the initial fleet) run_simulation


def run_simulation(options: argparse.Namespace) -> None:
    """Create the fleet and emit its initial positions."""
    fleet = create_fleet(options.vehicles, random.Random())
    # TODO: (emit one JSON record per vehicle) emit_snapshot


if __name__ == "__main__":
    main()
