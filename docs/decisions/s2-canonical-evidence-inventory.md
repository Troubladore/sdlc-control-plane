# Decision: Canonical Evidence Inventory Location

> **Session:** S2 — Evidence Inventory + Referential Validation
> **Date:** 2026-03-11
> **Status:** Decided
> **Audience:** Contributors, certificate-producing agents, schema designers
> **Reading order:** [docs/decisions/README.md](README.md) → this document

**Decision:** Canonical artifact and evidence inventories live on the `CertificateEnvelope`, not in a companion document or external registry.

## Context and Requirements

S2 introduces one-definition-per-ID semantics: every `artifact_id` and `evidence_id` used in a certificate must have a single canonical definition. A location must be chosen for those definitions.

Requirements:
- The `sdlc validate` CLI validates a single certificate file at a time.
- Certificates must be replayable and self-contained for audit purposes.
- The referential validator must be a pure function (no I/O, no external state).
- Backward compatibility with S1 certificates (which have no inventories) must be preserved.

## Options Evaluated

### Option A: Sidecar companion document

A separate file (e.g., `my-cert.evidence.json`) provides the inventory. The validator loads both files together.

**Trade-offs:**
- Pro: Inventories can be shared across multiple certificates in a workflow run.
- Con: Breaks single-artifact validation — the CLI would need coordination logic to find the sidecar.
- Con: Makes the certificate non-self-contained; replay requires locating the companion file.
- Con: Adds a new artifact type with its own schema, tooling, and lifecycle.
- Con: Referential validation would require I/O, defeating the pure-function design.

### Option B: Envelope fields (chosen)

Two optional fields on `CertificateEnvelope`:

```python
artifact_inventory: list[ArtifactRef] | None = None
evidence_inventory: list[EvidenceRef] | None = None
```

**Trade-offs:**
- Pro: Certificate is self-contained — validate with a single file path.
- Pro: Referential validator remains a pure function over the parsed model.
- Pro: Optional fields preserve backward compatibility with S1 certificates.
- Pro: Aligns with the repo's artifact-first, replayable design principle.
- Con: Inventories cannot be shared across certificates (deferred to a future cross-certificate validation feature).

### Option C: External registry

A persistent store (database or index file) holds canonical definitions. Certificates reference IDs only.

**Trade-offs:**
- Pro: True normalization; no duplication across certificates.
- Con: Requires persistent infrastructure, which is out of scope for S2.
- Con: Validation depends on external state — breaks pure-function and replay requirements.
- Con: Significantly higher complexity for the current scope.

## Chosen Approach: Option B

Inventories live on the `CertificateEnvelope` as optional fields. The fields are optional at the model level (Pydantic accepts certificates without them) to preserve backward compatibility. When present, they are the authoritative definitions — all inline occurrences are treated as references that must match the inventory.

The "required for new certificates" expectation is enforced by documentation and by certificate-producing tooling (S6+), not by structural schema validation. This is a deliberate split between Pydantic-level permissiveness (accepting legacy input) and referential validation (enforcing S2+ conventions).

Cross-certificate inventory sharing is tracked as a future issue.

## Related

- Code: `src/sdlc_control_plane/verification/models.py` — `CertificateEnvelope.artifact_inventory`, `evidence_inventory`
- Code: `src/sdlc_control_plane/verification/referential.py` — inventory-specific check codes
- Spec: `docs/superpowers/specs/2026-03-11-s2-evidence-inventory-referential-validation-design.md`, Section 4
