# Decision: Diagnostic Model

> **Session:** S2 — Evidence Inventory + Referential Validation
> **Date:** 2026-03-11
> **Status:** Decided
> **Audience:** Contributors, CLI consumers, validator implementors
> **Reading order:** [docs/decisions/README.md](README.md) → this document

**Decision:** Validation results are represented as structured `Diagnostic` Pydantic models from day one, not as print statements or raw JSON dicts.

## Context and Requirements

S2 adds two new validation layers (referential checks and filesystem checks) on top of S1's Pydantic structural validation. All three layers produce results that must be:
- Rendered to the human-readable CLI
- Potentially serialized to machine-readable output in future sessions
- Grouped and sorted deterministically
- Comparable in tests (equality, subset checks)

The question is how to represent those results internally.

## Options Evaluated

### Option A: Print-only output

Validation functions call `print()` or `console.print()` directly. Results are strings that flow immediately to stdout.

**Trade-offs:**
- Pro: Simplest initial implementation.
- Con: Untestable at the library level — tests must capture stdout.
- Con: No grouping/sorting without buffering output, which re-introduces structure.
- Con: Machine-readable output (e.g., `--format json`) would require a rewrite.
- Con: Cross-layer aggregation (e.g., "any errors across all layers?") requires reparsing strings.

### Option B: Structured Diagnostic model (chosen)

A frozen Pydantic `BaseModel` with fields: `severity`, `category`, `code`, `path`, `message`, `related_path`.

```python
class Diagnostic(BaseModel):
    model_config = ConfigDict(frozen=True)
    severity: Literal["error", "warning"]
    category: Literal["structure", "reference", "filesystem"]
    code: str
    path: str
    message: str
    related_path: str | None = None
```

Validation functions return `list[Diagnostic]`. The CLI renders them. Tests assert on the list directly.

**Trade-offs:**
- Pro: Testable at the library level without stdout capture.
- Pro: Grouping, sorting, and aggregation are operations on Python lists — no reparsing.
- Pro: `frozen=True` ensures immutability throughout the pipeline.
- Pro: Free JSON serialization via Pydantic for future `--format json`.
- Pro: Consistent with the project convention that all data structures use Pydantic.
- Con: Slightly more code than a plain `@dataclass` or `TypedDict`.

### Option C: JSON-only output

Validation functions return raw `dict` objects or JSON strings. The CLI renders from dicts.

**Trade-offs:**
- Pro: Trivially serializable.
- Con: No type safety — field names are strings, not attributes.
- Con: No validation of the diagnostic payload itself.
- Con: Inconsistent with the project Pydantic convention.

## Chosen Approach: Option B

`Diagnostic` is a frozen Pydantic `BaseModel`. All three validation layers (structural, referential, filesystem) return `list[Diagnostic]`. The CLI composes the lists and renders them grouped by category in deterministic order: `STRUCTURE`, `REFERENCE`, `FILESYSTEM`, then sorted by `path`, then `code`.

Using `BaseModel` rather than `@dataclass` aligns with the project convention and provides free JSON serialization. `frozen=True` makes diagnostics safe to compare, hash, and collect across layers without mutation risk.

The `--format json` output option is deferred (no automation consumer exists yet), but the library API is already machine-readable.

## Related

- Code: `src/sdlc_control_plane/verification/diagnostics.py` — `Diagnostic` model, `pydantic_errors_to_diagnostics()`
- Docs: [docs/verification/diagnostics.md](../verification/diagnostics.md) — component documentation
- Spec: `docs/superpowers/specs/2026-03-11-s2-evidence-inventory-referential-validation-design.md`, Sections 2.3, 5.5
