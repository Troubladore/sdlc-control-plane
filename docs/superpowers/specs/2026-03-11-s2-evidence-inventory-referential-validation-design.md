# S2: Evidence Inventory + Referential Validation — Design Spec

> **Session:** 2 of 14
> **Date:** 2026-03-11
> **Status:** Draft
> **Audience:** Contributors, certificate-producing agents, validators
> **Prerequisite:** Familiarity with S1 (schema bundle as Pydantic models + CLI validator)
> **Acceptance criterion:** "Validator catches broken references" (design doc, S2)

## 1. Overview

Session 2 adds two capabilities to the SDLC control plane:

1. **Canonical evidence and artifact inventories** on the certificate envelope — a structural place for one-definition-per-ID semantics.
2. **Referential validation** — pure, deterministic checks that all internal cross-references in a certificate resolve, plus optional filesystem-backed locator checks.

These extend the existing `sdlc validate` command. After S2, a certificate that parses structurally but has dangling claim IDs, duplicate evidence, or missing file paths is no longer reported as valid.

## 2. Architecture

### 2.1 Validation Pipeline

`sdlc validate` becomes a layered pipeline. Each layer runs only if the previous layer passed:

```
1. Load JSON                          → exit 2 on I/O error
2. Pydantic structural validation     → exit 1 on schema error (translated to Diagnostics)
3. Referential validation (pure)      → exit 1 on errors
4. Filesystem locator checks (opt-in) → exit 1 on failures, exit 2 if --project-root unusable
```

Layers 3 and 4 are new. Layer 2 is unchanged in logic but its errors are now translated into the shared `Diagnostic` model at the CLI boundary.

### 2.2 CLI Contract

```
sdlc validate <files...> [--project-root PATH] [--type TYPE]
```

- `--project-root PATH` — enables filesystem locator checks. If provided and not a valid directory, exit 2.
- Exit codes unchanged: `0` = all checks passed (warnings allowed), `1` = validation errors, `2` = I/O/configuration errors.
- Multiple files: process all, exit with worst code.

### 2.3 Diagnostic Model

All validation results — structural, referential, and filesystem — are represented as `Diagnostic` objects:

```python
class Diagnostic(BaseModel):
    model_config = ConfigDict(frozen=True)

    severity: Literal["error", "warning"]
    category: Literal["structure", "reference", "filesystem"]
    code: str
    path: str            # JSON path, e.g. "premises[0].evidence_refs[1]"
    message: str
    related_path: str | None = None  # For duplicates: location of first definition
```

`Diagnostic` uses Pydantic `BaseModel` (not `@dataclass`) to stay consistent with the project convention that all data structures use Pydantic. `frozen=True` ensures immutability. Using `BaseModel` also gives free JSON serialization for future machine-readable output.

- Any error diagnostic causes exit 1.
- Warnings print but do not affect exit code.
- Output is grouped by category in deterministic order: `STRUCTURE`, `REFERENCE`, `FILESYSTEM`, then sorted by `path`, then `code`.

### 2.4 Library API

```python
# verification/referential.py
def validate_refs(certificate: CertificateEnvelope) -> list[Diagnostic]: ...

# verification/locator_fs.py
def validate_filesystem(certificate: CertificateEnvelope, project_root: Path) -> list[Diagnostic]: ...

# verification/diagnostics.py
def pydantic_errors_to_diagnostics(error: ValidationError, file_path: str) -> list[Diagnostic]: ...
```

The CLI composes these. Tests call them directly.

## 3. Canonical Evidence & Artifact Inventory

### 3.1 Model Changes

Two new optional fields on `CertificateEnvelope`:

```python
class CertificateEnvelope(BaseModel):
    # ... existing fields ...
    artifact_inventory: list[ArtifactRef] | None = None
    evidence_inventory: list[EvidenceRef] | None = None
```

### 3.2 Semantics

**Model level:** The fields are optional (`None` default) for backward compatibility. Pydantic does not reject certificates missing inventories.

**Convention level:** New certificates (S2+) should always include inventories. When inventories are present, they are the single source of truth for artifact and evidence definitions. When absent, the validator falls back to treating each inline occurrence as a definition, and duplicates remain errors.

This is a deliberate split: the Pydantic model is permissive (accepts legacy input), while referential validation adds convention-level rigor. The "required" expectation is enforced by documentation and by certificate-producing tooling (S6+), not by structural schema validation.

### 3.3 Inline References

S2 does not yet introduce lightweight `ArtifactUse` / `EvidenceUse` reference types. Inline occurrences remain full `ArtifactRef` / `EvidenceRef` objects. When inventories are present:

- Every `artifact_id` / `evidence_id` used inline must appear in the corresponding inventory.
- Inline definitions must be consistent with the canonical inventory entry (same `artifact_type`, `content_hash`, etc.).
- Unused inventory entries generate a warning.

Lightweight reference types (ID-only inline references) are a future refinement tracked separately.

### 3.4 Why Inventories on the Envelope

**Decision:** Canonical inventories live on `CertificateEnvelope`, not in a companion document.

**Rationale:**
- The validation architecture (Stage 0) already assumes evidence and artifact inventories exist before certificate production.
- The CLI validates single certificate files — a sidecar document would break single-artifact validation and add coordination problems.
- The repo's artifact-first, replayable design requires that a certificate be self-contained for validation purposes.
- Companion documents only make sense when inventories are shared across certificates in a workflow, which is not the current S2 scope.

## 4. Referential Check Inventory

### 4.1 Pure Checks (always run) — `referential.py`

| Code | Severity | Description |
|------|----------|-------------|
| `duplicate_claim_id` | error | Same `claim_id` on multiple `ClaimBase` nodes. All `ClaimBase` nodes share one document-wide namespace. `related_path` points to first definition. |
| `duplicate_evidence_id` | error | Same `evidence_id` on multiple `EvidenceRef` nodes. Duplicates mean duplicate *definitions*, not duplicate citations. `related_path` points to first definition. |
| `duplicate_artifact_id` | error | Same `artifact_id` on multiple `ArtifactRef` nodes. Same semantics as evidence. `related_path` points to first definition. |
| `missing_claim_ref` | error | ID in `formal_conclusion.derived_from_claim_ids` not found in any `ClaimBase` node in the document. |
| `missing_evidence_in_verification` | error | ID in `VerificationRecord.evidence_checked` not found in any `EvidenceRef.evidence_id` in the document. Matching is document-wide (consistent with the global namespace decision). |
| `empty_locator` | warning | `Locator` object exists but all fields are `None`. |
| `note_only_locator` | warning | `Locator` has only `note` set — no resolvable target (no path, URL, command, or commit SHA). Structurally populated but semantically unresolvable. |
| `invalid_line_range` | error | `start_line > end_line` on a `Locator`. This is an impossible span — malformed data, not stale state. |
| `absolute_path_not_allowed` | error | `Locator.path` is an absolute path. Paths must be relative to project root. |
| `path_escapes_project_root` | error | `Locator.path` normalizes outside project root (e.g. `../../etc/passwd`). This is a **lexical containment check against a synthetic root** — it validates the document's claim about path structure without needing `--project-root`. Algorithm: `PurePosixPath('/synthetic') / locator_path` is resolved; if the result does not start with `/synthetic/`, the check fails. The synthetic root is arbitrary; only the containment test matters. |

**Inventory-specific checks** (only when `artifact_inventory` / `evidence_inventory` are present):

| Code | Severity | Description |
|------|----------|-------------|
| `missing_artifact_from_inventory` | error | An `artifact_id` used inline but not in `artifact_inventory`. |
| `missing_evidence_from_inventory` | error | An `evidence_id` used inline but not in `evidence_inventory`. |
| `unused_artifact_inventory_entry` | warning | An `artifact_inventory` entry not referenced anywhere inline. |
| `unused_evidence_inventory_entry` | warning | An `evidence_inventory` entry not referenced anywhere inline. |
| `artifact_definition_mismatch` | error | Inline `ArtifactRef` has different `artifact_type`, `content_hash`, `uri`, or `locator` than the canonical inventory entry. `description` is excluded from comparison — it may vary in verbosity across inline occurrences without constituting a semantic mismatch. |
| `evidence_definition_mismatch` | error | Inline `EvidenceRef` has different `evidence_type`, `excerpt_hash`, `excerpt`, or `artifact_ref` than the canonical inventory entry. The full `artifact_ref` is compared because an evidence item pointing to a different artifact than the canonical entry is a semantic error. |

### 4.2 Claim Namespace Semantics

**Decision:** All `ClaimBase` nodes share one document-wide namespace.

**Rationale:**
- The process docs treat non-task certificates as having premise-like statements that directly support conclusions (e.g., Design Decision Certificate has `P1`, `P2`, then concludes "By D1...").
- The model already encodes `comparison.our_pattern`, `comparison.reference_pattern`, `comparison.divergence_reason`, and `current_deliverable_consistency` as `ClaimBase`-bearing fields.
- A global namespace is simpler, works naturally with a generic tree walk, and avoids surprising collisions where two claim-bearing nodes accidentally share an ID.
- For machine-generated certificates, global uniqueness is a reasonable constraint.

### 4.3 Duplicate ID Semantics

**Decision:** Duplicate IDs mean duplicate *definitions*, not duplicate citations.

The current embedded model has no separate "reference by ID" mechanism — each `EvidenceRef` / `ArtifactRef` occurrence is a full inline definition. The duplicate-ID checks enforce one-definition-per-ID-per-document. The canonical inventory (Section 3) provides the structural place for that single definition.

### 4.4 Filesystem Checks (only with `--project-root`) — `locator_fs.py`

| Code | Severity | Description |
|------|----------|-------------|
| `unresolvable_path` | error | `Locator.path` does not exist relative to `--project-root`. |
| `line_range_exceeds_file` | warning | `end_line` exceeds actual file line count. |
| `path_not_regular_file` | error | Resolved path exists but is a directory, when `start_line` or `end_line` are set. A directory with line-addressed locator fields is an invalid locator, not stale state. |

### 4.5 Structure Checks (Pydantic translation) — `diagnostics.py`

| Code | Severity | Description |
|------|----------|-------------|
| `pydantic_validation_error` | error | Translated from `ValidationError`. One diagnostic per Pydantic error, with JSON path. |

### 4.6 Total: 20 Check Codes

- 10 always-run referential
- 6 inventory-specific referential
- 3 filesystem
- 1 structural translation

## 5. Generic Tree Walk

The referential validator walks the full model tree **recursively** rather than per-certificate-type:

1. Collect all `ClaimBase` instances with their JSON paths.
2. Collect all `EvidenceRef` instances with their JSON paths.
3. Collect all `ArtifactRef` instances with their JSON paths — **including those nested inside `EvidenceRef.artifact_ref`**.
4. Collect all `Locator` instances with their JSON paths — **including those nested inside `ArtifactRef.locator` at any depth**.
5. Collect all `VerificationRecord` instances with their JSON paths.
6. Run checks against collected sets.

This ensures new certificate types get baseline referential coverage automatically. Per-type logic is only needed where a certificate type has specific structural rules (e.g., `TaskReviewCertificate` has `premises` and `quality_assertions` that contribute to the claim namespace).

### 5.1 Non-obvious Collection Sources

The tree walk must collect `EvidenceRef` and `ArtifactRef` from all model types that contain them, not just `ClaimBase` nodes. Key sources beyond claims:

| Model | Field | Type |
|-------|-------|------|
| `IssueFinding` | `evidence_refs`, `verification` | `list[EvidenceRef] \| None`, `VerificationRecord \| None` |
| `CommandVerification` | `evidence_ref` | `EvidenceRef \| None` (singular) |
| `IssueImpactAssessment` | `issue_ref`, `verification` | `ArtifactRef`, `VerificationRecord` |
| `DocumentationImpact` | `document_ref`, `verification` | `ArtifactRef`, `VerificationRecord \| None` |
| `GateEvaluation` | `verifier_artifacts` | `list[ArtifactRef] \| None` (artifacts, not evidence) |
| `CertificateEnvelope` | `issue_ref`, `pr_ref`, `source_artifacts` | `ArtifactRef` / `list[ArtifactRef]` |
| `RoadmapPosition` | `blocked_by`, `blocks` | `list[ArtifactRef]` |
| `DependencyGraph` | `unblocked_issues`, `blocked_by_updates`, `new_issues` | `list[ArtifactRef]` |

`IssueFinding` has `issue_id` (not `claim_id`) and is **not** a `ClaimBase` subclass — its IDs are not part of the claim namespace, but its evidence refs are collected for duplicate/inventory checks.

## 6. File Layout

### 6.1 Source Code

```
src/sdlc_control_plane/verification/
    models.py              # (modify) Add artifact_inventory, evidence_inventory to CertificateEnvelope
    diagnostics.py         # (new) Diagnostic model (Pydantic), pydantic_errors_to_diagnostics()
    referential.py         # (new) validate_refs() — pure intra-document checks + inventory checks
    locator_fs.py          # (new) validate_filesystem() — project-root-gated checks
    __init__.py            # (modify) re-export public API

src/sdlc_control_plane/cli/
    __init__.py            # (modify) extend validate with --project-root, compose layers, render diagnostics
```

### 6.2 Tests

```
tests/
    test_referential.py    # (new) Unit tests for validate_refs()
    test_locator_fs.py     # (new) Unit tests for validate_filesystem() using tmp_path
    test_diagnostics.py    # (new) Diagnostic model + Pydantic-to-Diagnostic translation
    test_cli.py            # (modify) Integration tests for --project-root and layered validation
    fixtures/
        broken_refs_*.json # (new) Certificates with referential errors
```

### 6.3 Key Design Decisions

- `referential.py` and `locator_fs.py` are separate modules — each has a clear single responsibility and can be tested/imported independently.
- `diagnostics.py` owns the `Diagnostic` model and the Pydantic error translation utility. It is a shared contract, not an orchestration layer.
- `locator_fs.py` (not `filesystem.py`) — the module specifically resolves `Locator` fields against the filesystem. When URL or git-based locator resolution is added later, the naming pattern is clear: `locator_url.py`, `locator_git.py`.
- No new dependencies — everything uses stdlib + Pydantic + Rich (already in deps).

## 7. Documentation

### 7.1 Documentation Additions

S2 adds structured documentation layers following the progressive discovery pattern from `grounding-measure-core`:

**`docs/decisions/`** — Design decisions as first-class artifacts (rationale/history, informative):

```
docs/decisions/
    README.md                              # Decision index table
    s2-canonical-evidence-inventory.md     # Why inventories on envelope, not sidecar
    s2-claim-namespace-semantics.md        # Why all ClaimBase nodes share one namespace
    s2-diagnostic-model.md                 # Why machine-readable diagnostics from day one
    s2-path-validation-semantics.md        # Lexical containment vs filesystem resolution
```

Each decision doc follows a standard format:
- Session/issue reference, date, status
- One-sentence decision summary
- Context and requirements
- 2-3 options evaluated with trade-offs
- Chosen approach and rationale
- Links to related docs and code

**`docs/verification/`** — Component documentation mirroring code structure (normative for current behavior):

```
docs/verification/
    README.md                    # Component overview, progressive discovery entry
    evidence-model.md            # Canonical inventory pattern, ID semantics, inline references
    referential-validation.md    # Check inventory, severity rationale, examples
    diagnostics.md               # Diagnostic model, category/code taxonomy, CLI rendering
```

### 7.2 Documentation Norms

Each doc category has a normative status:

| Category | Status | Meaning |
|----------|--------|---------|
| `docs/verification/` | Normative | Authoritative for current behavior |
| `docs/decisions/` | Informative | Rationale and history — explains *why* |
| `docs/design/` | Informative | Broader system design |
| `docs/process/` | Normative | Workflow and process rules |

Each major doc includes audience and reading-order headers:

```markdown
> **Audience:** Certificate authors (human or LLM) and validator contributors
> **Reading order:** Start with README.md -> docs/verification/README.md -> this doc
> **Prerequisite:** Familiarity with the Pydantic model layer (verification/models.py)
```

### 7.3 Updates to Existing Docs

- **`README.md`**: Add documentation threading table (Architecture, Decisions, Process, Implementation entry points).
- **`CLAUDE.md`**: Add `docs/decisions/README.md` and `docs/verification/README.md` to Reference Documents section.

## 8. Out of Scope

Explicitly deferred from S2:

| Item | Reason | Tracked |
|------|--------|---------|
| Lightweight `ArtifactUse` / `EvidenceUse` reference types | Model refinement after inventory pattern is proven | Future issue |
| `Locator.url` resolution | Network I/O, not local validation | S5+ |
| `Locator.commit_sha` existence | Requires git, not local validation | S5+ |
| `Locator.issue_number` resolution | Requires GitHub API | S5+ |
| `content_hash` / `excerpt_hash` verification | Deeper verification, S5 scope | S5 |
| Cross-certificate referential validation | Requires persistent inventory across runs | Future issue (C) |
| Orphan evidence detection | Needs research — embedded model makes orphans ill-defined | Future issue |
| Verification completeness checks | S5 claim verification engine concern | S5 |
| Evidence inventory builder | Certificate production tooling, not validation | S6+ |
| `--format json` CLI output | Defer until real automation consumer exists; library API is machine-readable | Future |

## 9. Testing Strategy

- **Red/Green TDD** — write failing tests first, then implement to pass.
- **Unit tests** for `validate_refs()` covering each check code with positive and negative cases.
- **Unit tests** for `validate_filesystem()` using `tmp_path` fixtures.
- **Unit tests** for `pydantic_errors_to_diagnostics()` translation.
- **Integration tests** in `test_cli.py` for end-to-end pipeline behavior, exit codes, and output formatting.
- **Property-based tests** with Hypothesis where applicable (e.g., path containment properties).
- **Existing fixtures** remain valid — they must continue passing with the new validation layers.
- Run `/simplify` after each major coding chunk and before PR creation.

## 10. Acceptance Criteria

1. `sdlc validate valid_certificate.json` passes structural + referential checks (exit 0).
2. `sdlc validate broken_refs.json` catches and reports all broken references (exit 1).
3. `sdlc validate cert.json --project-root .` catches missing file paths (exit 1).
4. Diagnostics are machine-readable at the library API level (`Diagnostic` Pydantic model with consistent codes, paths, and categories). CLI output is human-formatted; `--format json` is deferred.
5. Output is grouped by category in deterministic order.
6. All existing tests continue passing.
7. `make check` passes (lint + type check + tests).
8. Documentation layers are in place with decision docs and component docs.
9. GitHub issues created for deferred items (cross-certificate validation, orphan evidence research).
