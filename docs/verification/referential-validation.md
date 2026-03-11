# Referential Validation

> **Status:** Normative — authoritative for current behavior
> **Audience:** Certificate authors (human or LLM) and validator contributors
> **Reading order:** [docs/verification/README.md](README.md) → this document
> **Prerequisite:** Familiarity with the evidence model ([evidence-model.md](evidence-model.md))

Referential validation checks that all internal cross-references in a certificate resolve, and that structural invariants on locator paths hold. It is implemented as a pure function with no filesystem I/O.

## Check Inventory

### Always-Run Checks (10 codes)

These run on every certificate regardless of whether inventories are present.

| Code | Severity | Description |
|------|----------|-------------|
| `duplicate_claim_id` | error | Same `claim_id` on multiple `ClaimBase` nodes. All `ClaimBase` nodes share one document-wide namespace. `related_path` points to the first definition. |
| `duplicate_evidence_id` | error | Same `evidence_id` on multiple `EvidenceRef` nodes. Applies within inventories and within inline occurrences in legacy mode. `related_path` points to the first definition. |
| `duplicate_artifact_id` | error | Same `artifact_id` on multiple `ArtifactRef` nodes. Same semantics as evidence. `related_path` points to the first definition. |
| `missing_claim_ref` | error | An ID in `formal_conclusion.derived_from_claim_ids` not found in any `ClaimBase` node in the document. |
| `missing_evidence_in_verification` | error | An ID in `VerificationRecord.evidence_checked` not found in any `EvidenceRef.evidence_id` in the document. Matching is document-wide (uses the canonical inventory when present). |
| `empty_locator` | warning | A `Locator` object exists but all fields are `None`. |
| `note_only_locator` | warning | A `Locator` has only `note` set — no resolvable target (no path, URL, command, or commit SHA). Structurally populated but semantically unresolvable. |
| `invalid_line_range` | error | `start_line > end_line` on a `Locator`. An impossible span — malformed data, not stale state. |
| `absolute_path_not_allowed` | error | `Locator.path` is an absolute path. Locator paths must be POSIX-style relative paths. Rejects both POSIX absolute paths (starting with `/`) and Windows drive-qualified paths (matching `^[A-Za-z]:` or starting with `\\`). |
| `path_escapes_project_root` | error | `Locator.path` normalizes outside the project root. Lexical containment check using `posixpath.normpath()` — no filesystem I/O required. Example: `src/../../etc/passwd` normalizes to `../etc/passwd`, which starts with `..`, so the check fails. |

### Inventory-Specific Checks (6 codes)

These run only when `artifact_inventory` or `evidence_inventory` are present on the envelope.

| Code | Severity | Description |
|------|----------|-------------|
| `missing_artifact_from_inventory` | error | An `artifact_id` used inline but not present in `artifact_inventory`. |
| `missing_evidence_from_inventory` | error | An `evidence_id` used inline but not present in `evidence_inventory`. |
| `unused_artifact_inventory_entry` | warning | An `artifact_inventory` entry not referenced anywhere inline. |
| `unused_evidence_inventory_entry` | warning | An `evidence_inventory` entry not referenced anywhere inline. |
| `artifact_definition_mismatch` | error | An inline `ArtifactRef` has different `artifact_type`, `content_hash`, `uri`, or `locator` than the canonical inventory entry. `description` is excluded from comparison. |
| `evidence_definition_mismatch` | error | An inline `EvidenceRef` has different `evidence_type`, `excerpt_hash`, `excerpt`, or `artifact_ref` than the canonical inventory entry. |

### Filesystem Checks (3 codes)

These run only when `--project-root` is provided to `sdlc validate`. Implemented in `locator_fs.py`.

| Code | Severity | Description |
|------|----------|-------------|
| `unresolvable_path` | error | `Locator.path` does not exist relative to `--project-root`. |
| `line_range_exceeds_file` | warning | `end_line` exceeds the actual file line count. |
| `path_not_regular_file` | error | Resolved path exists but is a directory, and `start_line` or `end_line` are set. A directory with line-addressed locator fields is an invalid locator. |

### Structural Translation (1 code)

Pydantic validation errors are translated into diagnostics at the CLI boundary.

| Code | Severity | Description |
|------|----------|-------------|
| `pydantic_validation_error` | error | Translated from a Pydantic `ValidationError`. One diagnostic per Pydantic error, with JSON path. |

**Total: 20 check codes.**

## Severity Rationale

Errors block the validation pipeline (cause exit 1). Warnings are informative and do not affect the exit code.

**Always errors:** Broken references, impossible spans, path traversal, absolute paths, and field mismatches are structural or security problems — not stale state. A certificate that encodes an impossible span or a directory traversal is invalid, not just out of date.

**Always warnings:** Empty or note-only locators, line range exceeding file length, and unused inventory entries represent imprecision or staleness. They should be investigated but do not make the certificate's claims false.

## Generic Tree Walk

The referential validator walks the full model tree recursively rather than dispatching per certificate type. This ensures new certificate types get baseline referential coverage automatically without requiring per-type code changes.

Collection order:
1. All `ClaimBase` instances with their JSON paths.
2. All `EvidenceRef` instances with their JSON paths (including those nested inside `ClaimBase.evidence_refs`, `IssueFinding.evidence_refs`, `CommandVerification.evidence_ref`).
3. All `ArtifactRef` instances with their JSON paths (including those nested inside `EvidenceRef.artifact_ref`, `IssueImpactAssessment.issue_ref`, envelope fields, etc.).
4. All `Locator` instances with their JSON paths (including those nested inside `ArtifactRef.locator` at any depth).
5. All `VerificationRecord` instances with their JSON paths.

Key non-obvious collection sources include: `IssueFinding.evidence_refs`, `CommandVerification.evidence_ref`, `GateEvaluation.verifier_artifacts`, `CertificateEnvelope.issue_ref`/`pr_ref`/`source_artifacts`, `RoadmapPosition.blocked_by`/`blocks`, and `DependencyGraph` artifact lists.

## Examples

### Broken claim reference

```json
{
  "formal_conclusion": {
    "derived_from_claim_ids": ["P1", "P99"]
  }
}
```

If `P99` does not appear on any `ClaimBase` node:

```
REFERENCE
  error  missing_claim_ref  formal_conclusion.derived_from_claim_ids[1]
         Claim ID 'P99' not found in document
```

### Path escaping project root

```json
{
  "locator": {"path": "src/../../etc/passwd"}
}
```

```
REFERENCE
  error  path_escapes_project_root  premises[0].evidence_refs[0].artifact_ref.locator.path
         Path 'src/../../etc/passwd' normalizes to '../etc/passwd', which escapes project root
```

## Related

- Code: `src/sdlc_control_plane/verification/referential.py`
- Code: `src/sdlc_control_plane/verification/locator_fs.py`
- Decision: [Path Validation Semantics](../decisions/s2-path-validation-semantics.md)
- Decision: [Claim Namespace Semantics](../decisions/s2-claim-namespace-semantics.md)
- Decision: [Canonical Evidence Inventory](../decisions/s2-canonical-evidence-inventory.md)
