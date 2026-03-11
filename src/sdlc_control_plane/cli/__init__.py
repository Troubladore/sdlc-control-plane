"""CLI entry points for the SDLC Control Plane."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from pydantic import ValidationError
from rich.console import Console

from sdlc_control_plane.verification.models import validate_certificate

console = Console(soft_wrap=True)


@click.group()
@click.version_option()
def main() -> None:
    """SDLC Control Plane -- certificate-driven development governance."""


@main.command()
@click.argument("files", nargs=-1, required=True, type=click.Path())
@click.option("--type", "cert_type", default=None, help="Certificate type override.")
def validate(files: tuple[str, ...], cert_type: str | None) -> None:
    """Validate certificate artifacts against the schema bundle."""
    exit_code = 0
    for file_path_str in files:
        file_path = Path(file_path_str)
        try:
            data: dict[str, Any] = json.loads(file_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            console.print(f"[red]\u2717[/red] {file_path} \u2014 {e}")
            exit_code = max(exit_code, 2)
            continue
        if cert_type is not None:
            data["certificate_type"] = cert_type
        try:
            validate_certificate(data)
            console.print(f"[green]\u2713[/green] {file_path}")
        except KeyError as e:
            console.print(f"[red]\u2717[/red] {file_path} \u2014 {e}")
            exit_code = max(exit_code, 1)
        except ValidationError as e:
            console.print(f"[red]\u2717[/red] {file_path}")
            for error in e.errors():
                loc = " \u2192 ".join(str(p) for p in error["loc"])
                console.print(f"    {loc}: {error['msg']}")
            exit_code = max(exit_code, 1)
    sys.exit(exit_code)
