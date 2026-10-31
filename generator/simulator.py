"""Fleet state for the vehicle simulator."""

from dataclasses import dataclass
import random


@dataclass
class Vehicle:
    """A vehicle's stable identity and current position."""

    id: str
    lat: float
    lng: float
    bearing: float
    speed: float


def create_fleet(count: int, rng: random.Random) -> list[Vehicle]:
    """Create vehicles with stable plates and random initial positions."""
    if not 1 <= count <= 26**3 * 10_000:
        raise ValueError("fleet size exceeds the plate space")
    return [
        Vehicle(
            id=plate_for_index(index),
            lat=rng.uniform(14.35, 14.78),
            lng=rng.uniform(120.90, 121.13),
            bearing=rng.uniform(0.0, 360.0) % 360.0,
            speed=rng.uniform(1.0, 200.0),
        )
        for index in range(count)
    ]


def position_record(vehicle: Vehicle, ts: int) -> dict[str, str | float | int]:
    """Return one tick's JSON-ready position record for a vehicle."""
    return {
        "id": vehicle.id,
        "lat": vehicle.lat,
        "lng": vehicle.lng,
        "bearing": vehicle.bearing,
        "speed": vehicle.speed,
        "ts": ts,
    }


def plate_for_index(index: int) -> str:
    """Return a unique, repeatable plate for an index in the plate space."""
    if not 0 <= index < 26**3 * 10_000:
        raise ValueError("plate index is outside the plate space")
    letters, digits = divmod(index, 10_000)
    return (
        f"{chr(65 + letters // 676)}"
        f"{chr(65 + letters // 26 % 26)}"
        f"{chr(65 + letters % 26)}"
        f"{digits:04d}"
    )
