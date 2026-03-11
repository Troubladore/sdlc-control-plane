"""CLI entry points for the SDLC Control Plane."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from pydantic import ValidationError
from rich.console import Console

from sdlc_control_plane.verification.diagnostics import (
    Diagnostic,
    pydantic_errors_to_diagnostics,
)
from sdlc_control_plane.verification.locator_fs import validate_filesystem
from sdlc_control_plane.verification.models import validate_certificate
from sdlc_control_plane.verification.referential import validate_refs

console = Console(soft_wrap=True)

_CATEGORY_ORDER = {"structure": 0, "reference": 1, "filesystem": 2}
_CATEGORY_LABELS = {"structure": "STRUCTURE", "reference": "REFERENCE", "filesystem": "FILESYSTEM"}


def _sort_diagnostics(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    return sorted(
        diagnostics,
        key=lambda d: (_CATEGORY_ORDER.get(d.category, 99), d.path, d.code),
    )


def _render_diagnostics(file_path: str, diagnostics: list[Diagnostic]) -> None:
    has_errors = any(d.severity == "error" for d in diagnostics)
    icon = "[red]\u2717[/red]" if has_errors else "[yellow]![/yellow]"
    console.print(f"{icon} {file_path}")

    sorted_diags = _sort_diagnostics(diagnostics)
    current_category: str | None = None
    for d in sorted_diags:
        if d.category != current_category:
            current_category = d.category
            console.print(f"  [bold]{_CATEGORY_LABELS.get(d.category, d.category)}[/bold]")
        sev_color = "red" if d.severity == "error" else "yellow"
        sev_label = "error" if d.severity == "error" else "warn "
        related = f" (see {d.related_path})" if d.related_path else ""
        line = f"    [{sev_color}]{sev_label}[/{sev_color}]  "
        line += f"{d.path}: {d.code} \u2014 {d.message}{related}"
        console.print(line)


@click.group()
@click.version_option()
def main() -> None:
    """SDLC Control Plane -- certificate-driven development governance."""


@main.command()
@click.argument("files", nargs=-1, required=True, type=click.Path())
@click.option("--type", "cert_type", default=None, help="Certificate type override.")
@click.option(
    "--project-root",
    "project_root",
    default=None,
    type=click.Path(),
    help="Project root for filesystem locator checks.",
)
def validate(files: tuple[str, ...], cert_type: str | None, project_root: str | None) -> None:
    """Validate certificate artifacts against the schema bundle."""
    resolved_root: Path | None = None
    if project_root is not None:
        resolved_root = Path(project_root)
        if not resolved_root.is_dir():
            console.print(
                f"[red]\u2717[/red] --project-root is not a valid directory: {project_root}"
            )
            sys.exit(2)

    exit_code = 0
    for file_path_str in files:
        file_path = Path(file_path_str)

        # Layer 1: Load JSON
        try:
            data: dict[str, Any] = json.loads(file_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            console.print(f"[red]\u2717[/red] {file_path} \u2014 {e}")
            exit_code = max(exit_code, 2)
            continue

        if cert_type is not None:
            data["certificate_type"] = cert_type

        # Layer 2: Pydantic structural validation
        try:
            cert = validate_certificate(data)
        except KeyError as e:
            console.print(f"[red]\u2717[/red] {file_path} \u2014 {e}")
            exit_code = max(exit_code, 1)
            continue
        except ValidationError as e:
            diagnostics = pydantic_errors_to_diagnostics(e, str(file_path))
            _render_diagnostics(str(file_path), diagnostics)
            exit_code = max(exit_code, 1)
            continue

        # Layer 3: Referential validation
        all_diagnostics: list[Diagnostic] = []
        all_diagnostics.extend(validate_refs(cert))

        # Layer 4: Filesystem locator checks (opt-in)
        if resolved_root is not None:
            all_diagnostics.extend(validate_filesystem(cert, resolved_root))

        # Render results
        if all_diagnostics:
            _render_diagnostics(str(file_path), all_diagnostics)
            if any(d.severity == "error" for d in all_diagnostics):
                exit_code = max(exit_code, 1)
        else:
            console.print(f"[green]\u2713[/green] {file_path}")

    sys.exit(exit_code)
