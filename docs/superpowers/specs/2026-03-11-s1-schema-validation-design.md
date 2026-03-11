# Session 1: Schema Bundle as Pydantic Models + CLI Validator

> Design spec for S1 of the SDLC Control Plane implementation.
> Date: 2026-03-11

## Goal

Expose the JSON Schema bundle as type-safe Pydantic models with a CLI validator that accepts certificate JSON files and reports structural validation results.

**Ends with:** `sdlc validate certificate.json` validates/rejects certificate files.

## Approach

Hand-written Pydantic models mirror every `$defs` entry in `schemas/agent_workflow_schema_bundle.json`. The schema bundle remains the canonical external contract; Pydantic models are the Python-side authority. A drift-detection test ensures they stay in sync.

## Module Structure

```
src/sdlc_control_plane/
    verification/
        __init__.py
        models.py          # Pydantic models for all $defs
    cli/
        __init__.py         # validate command
```

## Models (`verification/models.py`)

### Constrained String Types

The schema bundle defines four foundational constrained-string types used throughout all models. These become `Annotated` type aliases in Python:

| Schema Type | Python Type | Constraint |
|-------------|------------|------------|
| `NonEmptyString` | `Annotated[str, StringConstraints(min_length=1)]` | Non-empty |
| `Id` | `Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:-]+$")]` | Alphanumeric + `_.:-` |
| `Sha256` | `Annotated[str, StringConstraints(pattern=r"^[A-Fa-f0-9]{64}$")]` | 64 hex chars |
| `Timestamp` | `datetime` | Pydantic handles ISO 8601 natively |

### Enums (StrEnum)

`Severity`, `AuthorKind`, `ExecutorType`, `WorkflowState`, `ArtifactType`, `EvidenceType`, `VerificationMethod`, `VerifiedStatus` -- each mirrors the corresponding `enum` in the schema bundle.

Certificate-specific enums (e.g., `PremiseStatus`, `QualityAssertionStatus`, `CertificateType`, `ValidationStatus`) are defined as separate `StrEnum` types.

### Inheritance Strategy for `allOf` Composition

The schema bundle uses `allOf` extensively -- `PremiseClaim` extends `ClaimBase`, certificates extend `CertificateEnvelope`, etc. In Pydantic, this maps to class inheritance with one key constraint: `extra="forbid"` must only be set on **leaf models** (models that are not inherited from). Base models (`ClaimBase`, `CertificateEnvelope`, `FormalConclusion`) use the default `extra="ignore"` or no explicit config, and leaf models set `extra="forbid"`.

This ensures subclass fields are not rejected by the parent's config while still catching truly unexpected fields on the concrete types.

### Building Blocks (Pydantic BaseModel)

Leaf models use `model_config = ConfigDict(extra="forbid")`. Base models used in `allOf` composition do not set `extra="forbid"`.

| Model | Required Fields | Notes |
|-------|----------------|-------|
| `Actor` | `actor_id`, `author_kind`, `role` | `role` is its own enum |
| `Locator` | (none required) | All fields optional |
| `ArtifactRef` | `artifact_id`, `artifact_type` | |
| `EvidenceRef` | `evidence_id`, `evidence_type`, `artifact_ref` | |
| `VerificationRecord` | `status`, `method`, `verified_by`, `verified_at` | |
| `ClaimBase` | `claim_id`, `text`, `evidence_refs` | `evidence_refs` minItems=1 |
| `PremiseClaim` | ClaimBase fields + `status` | status: satisfied/missing/partial |
| `QualityAssertion` | ClaimBase fields + `status` | status: verified/failed/not_verified/partial |
| `IssueFinding` | `issue_id`, `description`, `severity` | Optional: `evidence_refs`, `verification`, `status` (open/accepted/remediated/withdrawn/escalated) |
| `CommandVerification` | `command_id`, `command`, `exit_code`, `status` | Optional: `summary`, `fresh`, `evidence_ref` (singular), `verification` |
| `FormalConclusion` | `status`, `derived_from_claim_ids` | status enum varies by certificate type |
| `GateEvaluation` | `gate_id`, `requirement`, `status` | |

### Certificate Envelope

`CertificateEnvelope` -- base model with fields shared by all certificates:
- `schema_version`, `certificate_id`, `certificate_type`, `workflow_run_id`, `issue_ref`, `produced_by`, `produced_at`, `source_artifacts`, `validation_status`
- Optional: `pr_ref`, `validation_notes`, `verified_claim_count`, `unverified_claim_count`

### Certificate Types (extend CertificateEnvelope)

| Model | Additional Required Fields | `certificate_type` const |
|-------|---------------------------|--------------------------|
| `TaskReviewCertificate` | `definition`, `premises`, `quality_assertions`, `verification_commands`, `formal_conclusion`, `issues` | `task_review` |
| `DesignDecisionCertificate` | `definition`, `decision_topic`, `comparison`, `formal_conclusion` | `design_decision` |
| `DeferredScopeCertificate` | `definition`, `deferred_work`, `tracking_issue`, `acceptance_criteria`, `roadmap_position`, `current_deliverable_consistency`, `evaluation`, `formal_conclusion` | `deferred_scope` |
| `ImpactAlignmentCertificate` | `definition`, `roadmap_impacts`, `open_issue_scan`, `documentation_impacts`, `dependency_graph`, `formal_conclusion` | `impact_alignment` |

Each certificate type constrains `formal_conclusion.status` to its own subset (e.g., task_review uses complete/not_complete).

### Other Top-Level Models

| Model | Notes |
|-------|-------|
| `DisputeObject` | Dispute against a certificate claim |
| `TransitionRequest` | Workflow state transition with gate evaluations |
| `RemediationLogEntry` | Single hash-chained log entry |
| `RemediationLog` | Container for remediation entries |
| `WorkflowEvent` | Instrumentation event for KPI measurement |
| `DesignComparison` | Used within DesignDecisionCertificate |
| `RoadmapPosition` | Used within DeferredScopeCertificate |
| `DeferredEvaluation` | Used within DeferredScopeCertificate |
| `IssueImpactAssessment` | Used within ImpactAlignmentCertificate |
| `DocumentationImpact` | Used within ImpactAlignmentCertificate |
| `DependencyGraph` | Required: `unblocked_issues`, `blocked_by_updates`, `new_issues` (all `list[ArtifactRef]`). Optional: `post_merge_actions` (`list[NonEmptyString]`) |

## Validation Logic

```python
CERTIFICATE_MODELS: dict[str, type[CertificateEnvelope]] = {
    "task_review": TaskReviewCertificate,
    "design_decision": DesignDecisionCertificate,
    "deferred_scope": DeferredScopeCertificate,
    "impact_alignment": ImpactAlignmentCertificate,
}

def validate_certificate(data: dict[str, Any]) -> CertificateEnvelope:
    """Validate a JSON dict as a certificate. Auto-detects type from certificate_type field.

    Raises KeyError if certificate_type is missing or not recognized.
    Raises ValidationError if data does not match the schema.
    """
    cert_type = data.get("certificate_type")
    if cert_type not in CERTIFICATE_MODELS:
        raise KeyError(f"Unknown or missing certificate_type: {cert_type!r}")
    return CERTIFICATE_MODELS[cert_type].model_validate(data)
```

## CLI (`sdlc validate`)

```
Usage: sdlc validate [OPTIONS] FILES...

Options:
  --type TEXT  Certificate type override (task_review, design_decision, etc.)
  --format     Output format: rich (default), json

Exit codes (highest wins when processing multiple files):
  0 = all files valid
  1 = validation errors
  2 = file not found / JSON parse error (takes priority over 1)
```

Uses Rich for formatted output:
- Green checkmark + filename for valid files
- Red X + filename + indented error list for invalid files

## Test Plan (Red/Green TDD)

### Test fixtures (`tests/fixtures/`)

Minimal valid JSON files for each certificate type, plus invalid variants:
- `valid_task_review.json`
- `valid_design_decision.json`
- `valid_deferred_scope.json`
- `valid_impact_alignment.json`
- `invalid_missing_fields.json`
- `invalid_bad_enum.json`
- `invalid_extra_fields.json`

### Unit tests (`tests/test_models.py`)

- Each valid fixture parses successfully into the correct model type
- Each invalid fixture raises `ValidationError` with expected error count/fields
- Enum coverage: all enum values accepted, invalid values rejected
- `validate_certificate()` dispatches to correct model based on `certificate_type`
- Unknown or missing `certificate_type` raises `KeyError`

### Drift detection (`tests/test_schema_drift.py`)

- Load the JSON Schema bundle
- For each `$defs` entry, compare against the corresponding Pydantic model's `.model_json_schema()`
- Verify: same required fields, same enum values, same field types
- This is structural equivalence, not byte-identical JSON (Pydantic's schema output format differs from hand-written JSON Schema)
- Note: drift tests require normalization (Pydantic uses `anyOf` for Optional, different `$defs` naming, etc.). Focus on comparing required fields, enum values, and field types rather than exact schema shape

### CLI tests (`tests/test_cli.py`)

- `sdlc validate valid_task_review.json` exits 0
- `sdlc validate invalid_missing_fields.json` exits 1
- `sdlc validate nonexistent.json` exits 2
- `sdlc validate --type task_review valid_task_review.json` exits 0
- Multiple files: mixed valid/invalid exits 1

## Out of Scope

- Referential validation (evidence refs resolve to real artifacts) -- S2
- Claim verification logic -- S5
- Camunda/workflow interaction -- S3+
- API endpoints -- later sessions
