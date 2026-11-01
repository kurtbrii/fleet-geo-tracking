"""Tests for the vehicle simulator command-line interface."""

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from types import ModuleType

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "generator.py"


def _load_cli_module() -> ModuleType:
    """Load the CLI script as a module without running its entry guard."""
    spec = importlib.util.spec_from_file_location("generator_cli", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SCRIPT.parent))
    return module


def test_help_describes_defaults() -> None:
    """Show both supported options and their defaults in help output."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--vehicles VEHICLES" in result.stdout
    assert "--interval-ms INTERVAL_MS" in result.stdout
    assert "default: 1000" in result.stdout


def test_small_fleet_emits_initial_and_advanced_snapshots() -> None:
    """Emit two valid snapshots that keep identity and speed while moving."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--vehicles", "3", "--interval-ms", "2000"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    records = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(records) == 6
    initial, advanced = records[:3], records[3:]
    assert [record["id"] for record in initial] == [
        record["id"] for record in advanced
    ]
    assert len({record["id"] for record in initial}) == 3

    now_ms = time.time_ns() // 1_000_000
    for first, second in zip(initial, advanced):
        for record in (first, second):
            assert set(record) == {"id", "lat", "lng", "bearing", "speed", "ts"}
            assert re.fullmatch(r"[A-Z]{3}[0-9]{4}", record["id"])
            assert 14.35 <= record["lat"] <= 14.78
            assert 120.90 <= record["lng"] <= 121.13
            assert 0 <= record["bearing"] < 360
            assert 0 < record["speed"] <= 200
            assert isinstance(record["ts"], int)
            assert abs(record["ts"] - now_ms) < 60_000
        assert first["speed"] == second["speed"]
        assert (first["lat"], first["lng"]) != (second["lat"], second["lng"])


def test_default_options_emit_initial_and_advanced_snapshots() -> None:
    """Use the documented 1000-vehicle default for both emitted snapshots."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert len(result.stdout.splitlines()) == 2000


def test_maximum_vehicle_count_is_accepted_without_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accept the plate-space limit at the parser boundary without building it."""
    cli = _load_cli_module()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--vehicles", "175760000"])

    options = cli.parse_options()

    assert options.vehicles == 175_760_000


@pytest.mark.parametrize(
    ("arguments", "error_message"),
    [
        (["--vehicles", "0"], "between 1 and 175760000"),
        (["--vehicles", "175760001"], "between 1 and 175760000"),
        (["--vehicles", "not-an-integer"], "invalid int value"),
        (["--interval-ms", "0"], "positive integer"),
        (["--interval-ms", "-2"], "positive integer"),
        (["--vehicles"], "expected one argument"),
        (["--unknown"], "unrecognized arguments"),
    ],
)
def test_invalid_options_fail_before_events(
    arguments: list[str], error_message: str
) -> None:
    """Reject malformed options with a diagnostic and no event output."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "error:" in result.stderr
    assert error_message in result.stderr
