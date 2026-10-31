"""Tests for the vehicle simulator command-line interface."""

from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "generator.py"


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


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--vehicles", "2", "--interval-ms", "2000"],
        ["--vehicles", "175760000"],
    ],
)
def test_valid_options_exit_without_events(arguments: list[str]) -> None:
    """Accept defaults and valid overrides without emitting simulation events."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


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
