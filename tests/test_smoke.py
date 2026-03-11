"""Smoke tests to verify the project is wired correctly."""

from sdlc_control_plane import __version__


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_cli_import() -> None:
    from sdlc_control_plane.cli import main

    assert main is not None
