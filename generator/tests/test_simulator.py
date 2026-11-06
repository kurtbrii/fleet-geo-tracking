"""Tests for the vehicle fleet state."""

import math
import random
import re

import pytest

from generator.simulator import (
    LAT_MAX,
    LAT_MIN,
    LNG_MAX,
    LNG_MIN,
    Vehicle,
    advance_vehicle,
    create_fleet,
    reflect_coordinate,
)


class FixedDrift(random.Random):
    """A random source that returns the same heading drift every call."""

    def __init__(self, drift: float) -> None:
        super().__init__(0)
        self.drift = drift

    def uniform(self, a: float, b: float) -> float:
        return self.drift


def test_advance_vehicle_moves_north_by_speed_and_elapsed_time() -> None:
    """Move 0.1 degrees north at a controlled speed and zero drift."""
    vehicle = Vehicle(id="AAA0000", lat=14.5, lng=121.0, bearing=0.0, speed=11.0574)

    moved = advance_vehicle(vehicle, 3600.0, FixedDrift(0.0))

    assert moved.id == vehicle.id
    assert moved.speed == vehicle.speed
    assert moved.lat == pytest.approx(14.6)
    assert moved.lng == pytest.approx(121.0)
    assert moved.bearing == pytest.approx(0.0)


def test_advance_vehicle_uses_longitude_degree_distance() -> None:
    """Move 0.01 degrees east using the longitude distance at this latitude."""
    km_per_longitude_degree = 111.320 * math.cos(math.radians(14.5))
    vehicle = Vehicle(
        id="AAA0000",
        lat=14.5,
        lng=121.0,
        bearing=90.0,
        speed=km_per_longitude_degree / 100,
    )

    moved = advance_vehicle(vehicle, 3600.0, FixedDrift(0.0))

    assert moved.lat == pytest.approx(14.5)
    assert moved.lng == pytest.approx(121.01)
    assert moved.bearing == pytest.approx(90.0)


def test_advance_vehicle_scales_displacement_with_elapsed_time() -> None:
    """A half-hour move covers half the latitude of a one-hour move."""
    vehicle = Vehicle(id="AAA0000", lat=14.5, lng=121.0, bearing=0.0, speed=11.0574)

    one_hour = advance_vehicle(vehicle, 3600.0, FixedDrift(0.0))
    half_hour = advance_vehicle(vehicle, 1800.0, FixedDrift(0.0))

    one_hour_change = one_hour.lat - vehicle.lat
    half_hour_change = half_hour.lat - vehicle.lat
    assert one_hour_change == pytest.approx(2 * half_hour_change)


def test_zero_speed_keeps_position_while_heading_drifts() -> None:
    """A stationary vehicle keeps its coordinates and gains only bounded drift."""
    vehicle = Vehicle(id="AAA0000", lat=14.5, lng=121.0, bearing=30.0, speed=0.0)

    moved = advance_vehicle(vehicle, 60.0, FixedDrift(10.0))

    assert moved.lat == vehicle.lat
    assert moved.lng == vehicle.lng
    assert moved.speed == 0.0
    assert moved.bearing == pytest.approx(40.0)


@pytest.mark.parametrize(
    ("value", "low", "high", "expected", "crossed"),
    [
        (14.5, LAT_MIN, LAT_MAX, 14.5, False),
        (14.80, LAT_MIN, LAT_MAX, 14.76, True),
        (14.34, LAT_MIN, LAT_MAX, 14.36, True),
        (15.31, LAT_MIN, LAT_MAX, 14.45, False),
        (121.0, LNG_MIN, LNG_MAX, 121.0, False),
        (121.14, LNG_MIN, LNG_MAX, 121.12, True),
        (120.89, LNG_MIN, LNG_MAX, 120.91, True),
    ],
)
def test_reflect_coordinate_handles_edges_and_overshoot(
    value: float, low: float, high: float, expected: float, crossed: bool
) -> None:
    """Reflect targets across all four edges, including multiple widths."""
    reflected, crossed_edge = reflect_coordinate(value, low, high)

    assert reflected == pytest.approx(expected)
    assert crossed_edge is crossed


def test_advance_vehicle_reflects_at_a_corner() -> None:
    """Cross the north and east edges once, reversing both components."""
    north_km = 0.02 * 110.574
    east_km = 0.02 * 111.320 * math.cos(math.radians(14.77))
    bearing = math.degrees(math.atan2(east_km, north_km))
    vehicle = Vehicle(
        id="AAA0000",
        lat=14.77,
        lng=121.12,
        bearing=bearing,
        speed=math.hypot(north_km, east_km),
    )

    moved = advance_vehicle(vehicle, 3600.0, FixedDrift(0.0))

    assert moved.lat == pytest.approx(14.77)
    assert moved.lng == pytest.approx(121.12)
    assert moved.bearing == pytest.approx((bearing + 180.0) % 360.0)


def test_repeated_ticks_stay_bounded_and_keep_identity_and_speed() -> None:
    """Advance a seeded fleet for many ticks without changing IDs or speeds."""
    fleet = create_fleet(50, random.Random(7))
    rng = random.Random(11)
    initial_ids = [vehicle.id for vehicle in fleet]
    initial_speeds = [vehicle.speed for vehicle in fleet]

    for _ in range(2000):
        fleet = [advance_vehicle(vehicle, 1.0, rng) for vehicle in fleet]

    assert [vehicle.id for vehicle in fleet] == initial_ids
    assert [vehicle.speed for vehicle in fleet] == initial_speeds
    for vehicle in fleet:
        assert math.isfinite(vehicle.lat)
        assert math.isfinite(vehicle.lng)
        assert math.isfinite(vehicle.bearing)
        assert LAT_MIN <= vehicle.lat <= LAT_MAX
        assert LNG_MIN <= vehicle.lng <= LNG_MAX
        assert 0 <= vehicle.bearing < 360


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
