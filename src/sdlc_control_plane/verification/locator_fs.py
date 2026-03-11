"""Filesystem-backed locator validation (opt-in via --project-root)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from sdlc_control_plane.verification.diagnostics import Diagnostic
from sdlc_control_plane.verification.models import CertificateEnvelope, Locator

if TYPE_CHECKING:
    from pathlib import Path


def _collect_locators(obj: Any, path: str) -> list[tuple[str, Locator]]:
    """Recursively collect all Locator instances with their JSON paths."""
    results: list[tuple[str, Locator]] = []
    if not isinstance(obj, BaseModel):
        return results
    if isinstance(obj, Locator):
        results.append((path, obj))
    for field_name, field_value in obj:
        child_path = f"{path}.{field_name}" if path else field_name
        if isinstance(field_value, BaseModel):
            results.extend(_collect_locators(field_value, child_path))
        elif isinstance(field_value, list):
            for i, item in enumerate(field_value):
                results.extend(_collect_locators(item, f"{child_path}[{i}]"))
    return results


def validate_filesystem(
    certificate: CertificateEnvelope,
    project_root: Path,
) -> list[Diagnostic]:
    """Run filesystem-backed locator checks.

    Only call when --project-root is provided and is a valid directory.
    """
    diagnostics: list[Diagnostic] = []
    locators = _collect_locators(certificate, "")

    for json_path, loc in locators:
        if loc.path is None:
            continue

        resolved = project_root / loc.path

        if not resolved.exists():
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    category="filesystem",
                    code="unresolvable_path",
                    path=f"{json_path}.path",
                    message=f'Path "{loc.path}" not found relative to project root',
                )
            )
            continue

        has_lines = loc.start_line is not None or loc.end_line is not None

        if not resolved.is_file() and has_lines:
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    category="filesystem",
                    code="path_not_regular_file",
                    path=f"{json_path}.path",
                    message=f'Path "{loc.path}" is not a regular file but has line fields',
                )
            )
            continue

        if resolved.is_file() and loc.end_line is not None:
            line_count = sum(1 for _ in resolved.open())
            if loc.end_line > line_count:
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        category="filesystem",
                        code="line_range_exceeds_file",
                        path=f"{json_path}.end_line",
                        message=f"end_line ({loc.end_line}) exceeds file length ({line_count})",
                    )
                )

    return diagnostics
