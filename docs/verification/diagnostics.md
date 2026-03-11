# Diagnostics

> **Status:** Normative — authoritative for current behavior
> **Audience:** Certificate authors (human or LLM) and validator contributors
> **Reading order:** [docs/verification/README.md](README.md) → this document
> **Prerequisite:** Familiarity with the validation pipeline ([README.md](README.md))

The `Diagnostic` model is the shared contract for all validation results. Every validation layer — structural, referential, and filesystem — produces `list[Diagnostic]`. The CLI renders them; the library API exposes them directly.

## The Diagnostic Model

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

### Field semantics

| Field | Description |
|-------|-------------|
| `severity` | `"error"` causes exit 1; `"warning"` is informative only |
| `category` | Which validation layer produced this diagnostic |
| `code` | Machine-readable check code (e.g., `duplicate_claim_id`) |
| `path` | JSON path to the offending node (e.g., `premises[0].evidence_refs[1]`) |
| `message` | Human-readable explanation |
| `related_path` | For duplicates: JSON path of the first definition of the conflicting ID |

`frozen=True` makes diagnostics immutable — safe to compare, hash, and collect across validation layers without mutation risk. `BaseModel` (not `@dataclass`) provides free JSON serialization for future machine-readable output.

## Category/Code Taxonomy

Categories map directly to validation layers:

| Category | Layer | Codes |
|----------|-------|-------|
| `structure` | Pydantic structural validation | `pydantic_validation_error` |
| `reference` | Pure referential validation (`referential.py`) | `duplicate_claim_id`, `duplicate_evidence_id`, `duplicate_artifact_id`, `missing_claim_ref`, `missing_evidence_in_verification`, `empty_locator`, `note_only_locator`, `invalid_line_range`, `absolute_path_not_allowed`, `path_escapes_project_root`, `missing_artifact_from_inventory`, `missing_evidence_from_inventory`, `unused_artifact_inventory_entry`, `unused_evidence_inventory_entry`, `artifact_definition_mismatch`, `evidence_definition_mismatch` |
| `filesystem` | Filesystem locator checks (`locator_fs.py`) | `unresolvable_path`, `line_range_exceeds_file`, `path_not_regular_file` |

See [referential-validation.md](referential-validation.md) for the full description of each code.

## pydantic_errors_to_diagnostics

Pydantic `ValidationError` objects carry structured error information but use Pydantic's internal path format. The `pydantic_errors_to_diagnostics()` utility translates them into `Diagnostic` objects with normalized JSON paths:

```python
def pydantic_errors_to_diagnostics(
    error: ValidationError,
    file_path: str,
) -> list[Diagnostic]:
    ...
```

One `Diagnostic` is produced per Pydantic error entry. The `path` field is constructed from the error's `loc` tuple — a sequence of field names and list indices — joined into a dot-notation string (e.g., `premises.0.evidence_refs.1.evidence_id`).

## CLI Rendering

The CLI renders diagnostics grouped by category in deterministic order: `STRUCTURE`, `REFERENCE`, `FILESYSTEM`. Within each group, diagnostics are sorted by `path`, then `code`.

Example output:

```
STRUCTURE
  error  pydantic_validation_error  certificate_type
         Input should be 'task_review' [...]

REFERENCE
  error  duplicate_claim_id  assertions[1].claim_id
         Claim ID 'A1' already defined at premises[0].claim_id
  warning  empty_locator  premises[0].evidence_refs[0].artifact_ref.locator
           Locator exists but all fields are None
```

Any diagnostic with `severity = "error"` causes exit 1. Warnings are printed but do not affect the exit code.

## Machine-Readable API

The library API is machine-readable today:

```python
from sdlc_control_plane.verification.referential import validate_refs
from sdlc_control_plane.verification.locator_fs import validate_filesystem
from sdlc_control_plane.verification.diagnostics import pydantic_errors_to_diagnostics

diagnostics: list[Diagnostic] = validate_refs(certificate)
errors = [d for d in diagnostics if d.severity == "error"]
```

`--format json` CLI output is deferred until a real automation consumer exists.

## Related

- Code: `src/sdlc_control_plane/verification/diagnostics.py`
- Decision: [Diagnostic Model](../decisions/s2-diagnostic-model.md)
- Spec: `docs/superpowers/specs/2026-03-11-s2-evidence-inventory-referential-validation-design.md`, Section 2.3
