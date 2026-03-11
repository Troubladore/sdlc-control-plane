"""Diagnostic model and Pydantic error translation utilities."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError


class Diagnostic(BaseModel):
    """A single validation finding — error or warning."""

    model_config = ConfigDict(frozen=True)

    severity: Literal["error", "warning"]
    category: Literal["structure", "reference", "filesystem"]
    code: str
    path: str
    message: str
    related_path: str | None = None


def pydantic_errors_to_diagnostics(
    error: ValidationError,
) -> list[Diagnostic]:
    """Translate a Pydantic ValidationError into Diagnostic objects.

    Formats paths in dot/bracket JSON-path style (e.g. "premises[0].artifact_ref")
    to match the rest of the diagnostic system.
    """
    diagnostics: list[Diagnostic] = []
    for err in error.errors():
        parts: list[str] = []
        for p in err["loc"]:
            if isinstance(p, int):
                parts.append(f"[{p}]")
            else:
                if parts:
                    parts.append(f".{p}")
                else:
                    parts.append(str(p))
        loc = "".join(parts)
        diagnostics.append(
            Diagnostic(
                severity="error",
                category="structure",
                code="pydantic_validation_error",
                path=loc,
                message=err["msg"],
            )
        )
    return diagnostics
