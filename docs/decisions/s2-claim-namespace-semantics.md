# Decision: Claim Namespace Semantics

> **Session:** S2 — Evidence Inventory + Referential Validation
> **Date:** 2026-03-11
> **Status:** Decided
> **Audience:** Contributors, certificate-producing agents, validator implementors
> **Reading order:** [docs/decisions/README.md](README.md) → this document

**Decision:** All `ClaimBase` nodes in a certificate share one document-wide namespace. A `claim_id` must be unique across every `ClaimBase`-bearing field, regardless of where in the document the node appears.

## Context and Requirements

S2 introduces a `duplicate_claim_id` check: if two `ClaimBase` nodes carry the same `claim_id`, that is an error. The question is which nodes participate in that namespace — only certain subtypes, or every `ClaimBase` node.

`ClaimBase` is used as the base for:
- `Premise` and `Assertion` (canonical claim nodes in `TaskReviewCertificate`, `DesignDecisionCertificate`)
- `IssueImpactAssessment` and `DocumentationImpact` (impact assessment rows, added to `ClaimBase` in S2)
- Potentially any future `ClaimBase` subclass added in later sessions

`FormalConclusion.derived_from_claim_ids` is a list of IDs that must resolve to `ClaimBase` nodes. Its validation depends on knowing the full population of claim IDs in the document.

## Options Evaluated

### Option 1: Canonical-claim-only namespace (Premise + Assertion only)

Only nodes explicitly typed as `Premise` or `Assertion` participate in the claim namespace. Other `ClaimBase` subclasses are excluded from duplicate checking and from `derived_from_claim_ids` resolution.

**Trade-offs:**
- Pro: Narrower scope — less surprising if subclasses have incidentally matching IDs.
- Con: Requires per-type special-casing in the tree walk and the `derived_from_claim_ids` resolver.
- Con: `IssueImpactAssessment` becomes a `ClaimBase` subclass in S2 (with `claim_id`), but its IDs would not be resolvable from `derived_from_claim_ids` — a model contradiction.
- Con: Process docs treat non-task certificates as having premise-like statements that directly support conclusions. Restricting the namespace contradicts that design.

### Option 2: All ClaimBase nodes share one namespace (chosen)

Every node that subclasses `ClaimBase` participates in the document-wide namespace. The `duplicate_claim_id` check applies across all of them. `derived_from_claim_ids` can reference any of them.

**Trade-offs:**
- Pro: Simple invariant: one namespace, one rule, no per-type logic.
- Pro: Works naturally with a generic recursive tree walk — no type dispatch needed.
- Pro: `IssueImpactAssessment.claim_id` is immediately resolvable from `derived_from_claim_ids`.
- Pro: Machine-generated certificates can enforce global uniqueness trivially (e.g., `claim_id` = `sha256(content)[:8]`).
- Con: Tighter constraint on certificate authors — IDs must be unique across the full document, not just within a section. In practice this is not a burden for machine-generated certificates and is a good discipline for human-authored ones.

## Chosen Approach: Option 2

All `ClaimBase` nodes share one document-wide namespace. The generic tree walk collects every `ClaimBase` instance regardless of its concrete type. `duplicate_claim_id` is checked against the full collected set. `derived_from_claim_ids` resolves against the same set.

This aligns with how the process docs describe non-task certificates (e.g., a Design Decision Certificate has `P1`, `P2` as premises, then concludes "By D1..."), and with the `IssueImpactAssessment` becoming a `ClaimBase` subclass.

## Related

- Code: `src/sdlc_control_plane/verification/referential.py` — `duplicate_claim_id` check, `missing_claim_ref` check
- Code: `src/sdlc_control_plane/verification/models.py` — `ClaimBase`, `IssueImpactAssessment`, `DocumentationImpact`
- Spec: `docs/superpowers/specs/2026-03-11-s2-evidence-inventory-referential-validation-design.md`, Sections 5.2, 6
