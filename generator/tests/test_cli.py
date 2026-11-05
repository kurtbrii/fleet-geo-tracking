"""Tests for the vehicle simulator command-line interface."""

import importlib.util
import json
from pathlib import Path
import random
import re
import signal
import subprocess
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "generator.py"


class FakeClock:
    """A monotonic clock advanced only by waiting or explicit work."""

    def __init__(self) -> None:
        self.seconds = 0.0
        self.waits: list[float] = []

    def now(self) -> float:
        return self.seconds

    def wait(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.seconds += seconds

    def spend(self, seconds: float) -> None:
        self.seconds += seconds


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


def test_small_fleet_emits_initial_and_advanced_tick(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Emit two valid snapshots that keep identity and speed while moving."""
    cli = _load_cli_module()
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), "--vehicles", "3", "--interval-ms", "2000"]
    )
    options = cli.parse_options()
    fake = FakeClock()

    cli.run_simulation(options, clock=fake.now, wait=fake.wait, tick_limit=1)

    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
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


def test_default_options_emit_initial_and_advanced_tick(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Use the documented 1000-vehicle default for both emitted snapshots."""
    cli = _load_cli_module()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    options = cli.parse_options()
    fake = FakeClock()

    cli.run_simulation(options, clock=fake.now, wait=fake.wait, tick_limit=1)

    assert len(capsys.readouterr().out.splitlines()) == 2000


def test_later_ticks_wait_for_the_target_interval(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Wait the full interval before each later tick."""
    cli = _load_cli_module()
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), "--vehicles", "1", "--interval-ms", "1000"]
    )
    options = cli.parse_options()
    fake = FakeClock()

    cli.run_simulation(options, clock=fake.now, wait=fake.wait, tick_limit=3)

    assert fake.waits == [1.0, 1.0, 1.0]


def test_movement_uses_measured_elapsed_time(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Move by the real clock delta even when the wait runs late."""
    cli = _load_cli_module()
    expected_rng = random.Random(7)
    vehicle = cli.create_fleet(1, expected_rng)[0]
    expected = cli.advance_vehicle(vehicle, 2.0, expected_rng)
    fake = FakeClock()

    def late_wait(seconds: float) -> None:
        fake.waits.append(seconds)
        fake.seconds += seconds + 1.0

    simulation_rng = random.Random(7)
    monkeypatch.setattr(cli.random, "Random", lambda: simulation_rng)
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), "--vehicles", "1", "--interval-ms", "1000"]
    )
    options = cli.parse_options()

    cli.run_simulation(options, clock=fake.now, wait=late_wait, tick_limit=1)

    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(records) == 2
    assert (records[1]["lat"], records[1]["lng"]) == (expected.lat, expected.lng)


def test_slow_output_is_absorbed_without_catch_up_ticks(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Tick immediately after slow output instead of bursting to catch up."""
    cli = _load_cli_module()
    fake = FakeClock()
    emit_snapshot = cli.emit_snapshot

    def slow_emit(fleet: list[object], ts: int) -> None:
        emit_snapshot(fleet, ts)
        fake.spend(2.5)

    monkeypatch.setattr(cli, "emit_snapshot", slow_emit)
    monkeypatch.setattr(
        sys, "argv", [str(SCRIPT), "--vehicles", "1", "--interval-ms", "1000"]
    )
    options = cli.parse_options()

    cli.run_simulation(options, clock=fake.now, wait=fake.wait, tick_limit=2)

    assert fake.waits == [0.0, 0.0]


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


def test_main_exits_cleanly_on_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return normally when the simulation is interrupted."""
    cli = _load_cli_module()
    monkeypatch.setattr(
        cli, "parse_options", lambda: SimpleNamespace(vehicles=1, interval_ms=1000)
    )

    def interrupted(options: SimpleNamespace) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "run_simulation", interrupted)

    assert cli.main() is None


def test_process_stops_cleanly_on_interrupt() -> None:
    """Stop the real CLI with SIGINT without a traceback."""
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--vehicles", "2", "--interval-ms", "10"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None and process.stderr is not None
    try:
        lines = [process.stdout.readline() for _ in range(4)]
        process.send_signal(signal.SIGINT)
        returncode = process.wait(timeout=10)
        stderr = process.stderr.read()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()

    assert returncode == 0
    assert stderr == ""
    assert len(lines) == 4
    assert all(json.loads(line) for line in lines)
