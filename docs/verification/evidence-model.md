# Evidence Model

> **Status:** Normative — authoritative for current behavior
> **Audience:** Certificate authors (human or LLM) and validator contributors
> **Reading order:** [docs/verification/README.md](README.md) → this document
> **Prerequisite:** Familiarity with the Pydantic model layer (`src/sdlc_control_plane/verification/models.py`)

## Canonical Inventory Pattern

S2 introduces optional inventory fields on `CertificateEnvelope`:

```python
class CertificateEnvelope(BaseModel):
    artifact_inventory: list[ArtifactRef] | None = None
    evidence_inventory: list[EvidenceRef] | None = None
```

When inventories are present, they are the **single source of truth** for artifact and evidence definitions. All inline occurrences of `ArtifactRef` and `EvidenceRef` are treated as references that must match the inventory.

When inventories are absent (legacy mode), every inline occurrence is treated as a definition, and the duplicate-ID checks apply across all inline occurrences.

## ID Semantics

### One-definition-per-ID

Every `artifact_id` and `evidence_id` must have exactly one canonical definition within a document. Duplicate definitions are always errors.

**When inventories are present:**
- The inventory entries are the definitions.
- Inline occurrences are references/citations — the same ID may appear in both the inventory and inline (expected, not an error).
- Two inventory entries with the same ID is always an error.

**When inventories are absent (legacy mode):**
- Every inline occurrence is treated as a definition.
- The same ID appearing on two different inline nodes is an error.

### Claim ID Namespace

All `ClaimBase` nodes — regardless of concrete type — share one document-wide namespace. `claim_id` must be unique across `Premise`, `Assertion`, `IssueImpactAssessment`, `DocumentationImpact`, and any future `ClaimBase` subclasses. See [docs/decisions/s2-claim-namespace-semantics.md](../decisions/s2-claim-namespace-semantics.md) for the rationale.

## Inline References

S2 does not yet introduce lightweight reference types (ID-only inline nodes). Inline occurrences remain full `ArtifactRef` / `EvidenceRef` objects. When inventories are present, inline fields must be consistent with the canonical inventory entry:

- For `ArtifactRef`: `artifact_type`, `content_hash`, `uri`, and `locator` must match. `description` is excluded — it may vary in verbosity.
- For `EvidenceRef`: `evidence_type`, `excerpt_hash`, `excerpt`, and `artifact_ref` must match. The full `artifact_ref` is compared because an evidence item pointing to a different artifact is a semantic error.

## Inventory vs Legacy Mode

| Behavior | Inventory present | Legacy mode (no inventory) |
|----------|-------------------|---------------------------|
| Duplicate `artifact_id` in inventory | Error | N/A |
| Duplicate `artifact_id` inline | Permitted (same ref used by multiple claims) | Error |
| `artifact_id` inline but not in inventory | Error (`missing_artifact_from_inventory`) | N/A |
| Unused inventory entry | Warning | N/A |
| Inline fields differ from inventory | Error (`artifact_definition_mismatch`) | N/A |

The same table applies symmetrically for `evidence_id` / `EvidenceRef`.

## Related

- Code: `src/sdlc_control_plane/verification/models.py`
- Decision: [Canonical Evidence Inventory](../decisions/s2-canonical-evidence-inventory.md)
- Decision: [Claim Namespace Semantics](../decisions/s2-claim-namespace-semantics.md)
