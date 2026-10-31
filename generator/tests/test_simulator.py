"""Tests for the vehicle fleet state."""

import random
import re

import pytest

from generator.simulator import create_fleet, plate_for_index, position_record


def test_initial_fleet_has_stable_unique_in_range_values() -> None:
    """Keep identities repeatable while initial positions remain valid."""
    small = create_fleet(20, random.Random(7))
    repeated = create_fleet(20, random.Random(7))
    larger = create_fleet(30, random.Random(7))

    assert small == repeated
    assert [vehicle.id for vehicle in small] == [vehicle.id for vehicle in larger[:20]]
    assert len({vehicle.id for vehicle in small}) == 20
    for vehicle in small:
        assert re.fullmatch(r"[A-Z]{3}[0-9]{4}", vehicle.id)
        assert 14.35 <= vehicle.lat <= 14.78
        assert 120.90 <= vehicle.lng <= 121.13
        assert 0 <= vehicle.bearing < 360
        assert 0 < vehicle.speed <= 200


def test_position_record_uses_the_six_field_contract() -> None:
    """Expose identity, position, bearing, speed and timestamp exactly once."""
    vehicle = create_fleet(1, random.Random(7))[0]

    record = position_record(vehicle, 1_793_400_000_000)

    assert record == {
        "id": vehicle.id,
        "lat": vehicle.lat,
        "lng": vehicle.lng,
        "bearing": vehicle.bearing,
        "speed": vehicle.speed,
        "ts": 1_793_400_000_000,
    }
    assert isinstance(record["ts"], int)
