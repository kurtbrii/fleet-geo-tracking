"""Fleet state for the vehicle simulator."""

from dataclasses import dataclass
import math
import random

LAT_MIN, LAT_MAX = 14.35, 14.78
LNG_MIN, LNG_MAX = 120.90, 121.13
KM_PER_LATITUDE_DEGREE = 110.574
KM_PER_LONGITUDE_DEGREE_AT_EQUATOR = 111.320
MAX_HEADING_DRIFT = 10.0


@dataclass
class Vehicle:
    """A vehicle's stable identity and current position.

    Attributes:
        id: "AAA0000"
        lat: 14.48924808887826
        lng: 120.93469531000264
        bearing: 234.33641029434736
        speed: 15.41482104684101
    """

    id: str
    lat: float
    lng: float
    bearing: float
    speed: float


def create_fleet(count: int, rng: random.Random) -> list[Vehicle]:
    """Create vehicles with stable plates and random initial positions.

    Args:
        count: 2
        rng: random.Random(7)

    Returns:
        [
            Vehicle(id="AAA0000", lat=14.48924808887826, lng=120.93469531000264, bearing=234.33641029434736, speed=15.41482104684101),
            Vehicle(id="AAA0001", lat=14.580429261851876, lng=120.98410845088989, bearing=20.879612918894452, speed=101.97971090469463),
        ]
    """
    if not 1 <= count <= 26**3 * 10_000:
        raise ValueError("fleet size exceeds the plate space")
    return [
        Vehicle(
            id=plate_for_index(index),
            lat=rng.uniform(LAT_MIN, LAT_MAX),
            lng=rng.uniform(LNG_MIN, LNG_MAX),
            bearing=rng.uniform(0.0, 360.0) % 360.0,
            speed=rng.uniform(1.0, 200.0),
        )
        for index in range(count)
    ]


def reflect_coordinate(value: float, low: float, high: float) -> tuple[float, bool]:
    """Reflect a target coordinate into a box, reporting an odd edge crossing.

    Args:
        value: 14.90
        low: 14.35
        high: 14.78

    Returns:
        (14.66, True)
    """
    span = high - low
    steps = (value - low) / span
    crossings = math.floor(steps)
    fraction = steps - crossings
    if crossings % 2 == 0:
        reflected = low + fraction * span
    else:
        reflected = high - fraction * span
    return min(high, max(low, reflected)), crossings % 2 == 1


def advance_vehicle(vehicle: Vehicle, elapsed_seconds: float, rng: random.Random) -> Vehicle:
    """Return a vehicle after one tick of heading drift and movement.

    Args:
        vehicle: Vehicle(id="AAA0000", lat=14.48924808887826, lng=120.93469531000264, bearing=234.33641029434736, speed=15.41482104684101)
        elapsed_seconds: 2.0
        rng: random.Random(7)

    Returns:
        Vehicle(id="AAA0000", lat=14.489199152850045, lng=120.93463372407732, bearing=230.8130655910106, speed=15.41482104684101)
    """
    bearing = (vehicle.bearing + rng.uniform(-MAX_HEADING_DRIFT, MAX_HEADING_DRIFT)) % 360.0
    km_per_longitude_degree = KM_PER_LONGITUDE_DEGREE_AT_EQUATOR * math.cos(math.radians(vehicle.lat))
    distance_km = vehicle.speed * elapsed_seconds / 3600.0
    lat_target = vehicle.lat + distance_km * math.cos(math.radians(bearing)) / KM_PER_LATITUDE_DEGREE
    lng_target = vehicle.lng + distance_km * math.sin(math.radians(bearing)) / km_per_longitude_degree
    lat, crossed_lat = reflect_coordinate(lat_target, LAT_MIN, LAT_MAX)
    lng, crossed_lng = reflect_coordinate(lng_target, LNG_MIN, LNG_MAX)
    if crossed_lat:
        bearing = 180.0 - bearing
    if crossed_lng:
        bearing = -bearing
    return Vehicle(
        id=vehicle.id,
        lat=lat,
        lng=lng,
        bearing=bearing % 360.0,
        speed=vehicle.speed,
    )


def plate_for_index(index: int) -> str:
    """Return a unique, repeatable plate for an index in the plate space.

    Args:
        index: 0

    Returns:
        "AAA0000"
    """
    if not 0 <= index < 26**3 * 10_000:
        raise ValueError("plate index is outside the plate space")
    letters, digits = divmod(index, 10_000)
    return f"{chr(65 + letters // 676)}" f"{chr(65 + letters // 26 % 26)}" f"{chr(65 + letters % 26)}" f"{digits:04d}"
