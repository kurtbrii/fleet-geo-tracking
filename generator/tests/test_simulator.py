"""Tests for the vehicle fleet state."""

import random
import re

import pytest

from generator.simulator import create_fleet


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
