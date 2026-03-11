"""Referential validator — pure checks for cross-reference integrity.

Walks a CertificateEnvelope tree collecting typed nodes, then runs
16 check codes covering duplicate IDs, missing refs, locator quality,
and inventory consistency.
"""

from __future__ import annotations

import posixpath
import re
from typing import Any

from pydantic import BaseModel

from sdlc_control_plane.verification.diagnostics import Diagnostic
from sdlc_control_plane.verification.models import (
    ArtifactRef,
    CertificateEnvelope,
    ClaimBase,
    EvidenceRef,
    FormalConclusion,
    Locator,
    VerificationRecord,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RESOLVABLE = ("path", "url", "command", "commit_sha", "issue_number", "diff_hunk")
_WINDOWS_ABS_RE = re.compile(r"^[A-Za-z]:|^\\\\")

# Fields on ArtifactRef to compare for definition mismatch (exclude description).
_ARTIFACT_CMP_FIELDS = ("artifact_type", "content_hash", "uri")
# Fields on EvidenceRef to compare for definition mismatch.
_EVIDENCE_CMP_FIELDS = ("evidence_type", "excerpt_hash", "excerpt")


# ---------------------------------------------------------------------------
# Generic recursive tree walk
# ---------------------------------------------------------------------------

# The types we want to collect, mapped to their expected base class.
_COLLECT_TYPES: tuple[type[BaseModel], ...] = (
    ClaimBase,
    EvidenceRef,
    ArtifactRef,
    Locator,
    VerificationRecord,
    FormalConclusion,
)


def _walk(
    obj: Any,  # noqa: ANN401
    path: str,
) -> list[tuple[str, BaseModel]]:
    """Recursively walk a Pydantic model tree, collecting typed nodes with JSON paths."""
    results: list[tuple[str, BaseModel]] = []
    if isinstance(obj, BaseModel):
        for target_type in _COLLECT_TYPES:
            if isinstance(obj, target_type):
                results.append((path, obj))
                break  # only record once per node (most-specific match first)
        for field_name in obj.__class__.model_fields:
            value = getattr(obj, field_name)
            child_path = f"{path}.{field_name}" if path else field_name
            results.extend(_walk(value, child_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            results.extend(_walk(item, f"{path}[{i}]"))
    return results


# ---------------------------------------------------------------------------
# Check: duplicate_claim_id
# ---------------------------------------------------------------------------


def _check_duplicate_claims(
    nodes: list[tuple[str, BaseModel]],
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    seen: dict[str, str] = {}  # claim_id -> first path
    for json_path, node in nodes:
        if isinstance(node, ClaimBase):
            cid = node.claim_id
            if cid in seen:
                diags.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="duplicate_claim_id",
                        path=json_path,
                        message=f"Duplicate claim_id {cid!r}",
                        related_path=seen[cid],
                    )
                )
            else:
                seen[cid] = json_path
    return diags


# ---------------------------------------------------------------------------
# Check: duplicate_evidence_id / duplicate_artifact_id (legacy — no inventory)
# ---------------------------------------------------------------------------


def _check_duplicate_evidence_legacy(
    nodes: list[tuple[str, BaseModel]],
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    seen: dict[str, str] = {}
    for json_path, node in nodes:
        if isinstance(node, EvidenceRef):
            eid = node.evidence_id
            if eid in seen:
                diags.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="duplicate_evidence_id",
                        path=json_path,
                        message=f"Duplicate evidence_id {eid!r}",
                        related_path=seen[eid],
                    )
                )
            else:
                seen[eid] = json_path
    return diags


def _is_evidence_artifact(path: str) -> bool:
    """Return True if this ArtifactRef path is inside an evidence chain.

    Evidence-chain artifacts are nested inside EvidenceRef (.artifact_ref suffix)
    as opposed to structural ArtifactRefs (issue_ref, source_artifacts, pr_ref,
    tracking_issue, blocked_by, blocks, etc.) which may legitimately reuse IDs.
    """
    return ".artifact_ref" in path or path.endswith(".artifact_ref")


def _check_duplicate_artifact_legacy(
    nodes: list[tuple[str, BaseModel]],
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    seen: dict[str, str] = {}
    for json_path, node in nodes:
        if isinstance(node, ArtifactRef) and _is_evidence_artifact(json_path):
            aid = node.artifact_id
            if aid in seen:
                diags.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="duplicate_artifact_id",
                        path=json_path,
                        message=f"Duplicate artifact_id {aid!r}",
                        related_path=seen[aid],
                    )
                )
            else:
                seen[aid] = json_path
    return diags


# ---------------------------------------------------------------------------
# Check: missing_claim_ref
# ---------------------------------------------------------------------------


def _check_missing_claim_refs(
    nodes: list[tuple[str, BaseModel]],
    claim_ids: set[str],
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for json_path, node in nodes:
        if isinstance(node, FormalConclusion):
            for ref_id in node.derived_from_claim_ids:
                if ref_id not in claim_ids:
                    diags.append(
                        Diagnostic(
                            severity="error",
                            category="reference",
                            code="missing_claim_ref",
                            path=json_path,
                            message=f"derived_from_claim_ids references unknown claim {ref_id!r}",
                        )
                    )
    return diags


# ---------------------------------------------------------------------------
# Check: missing_evidence_in_verification
# ---------------------------------------------------------------------------


def _check_missing_evidence_in_verification(
    nodes: list[tuple[str, BaseModel]],
    evidence_ids: set[str],
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for json_path, node in nodes:
        if isinstance(node, VerificationRecord) and node.evidence_checked:
            for eid in node.evidence_checked:
                if eid not in evidence_ids:
                    diags.append(
                        Diagnostic(
                            severity="error",
                            category="reference",
                            code="missing_evidence_in_verification",
                            path=json_path,
                            message=f"evidence_checked references unknown evidence {eid!r}",
                        )
                    )
    return diags


# ---------------------------------------------------------------------------
# Check: locator checks
# ---------------------------------------------------------------------------


def _check_locators(
    nodes: list[tuple[str, BaseModel]],
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for json_path, node in nodes:
        if not isinstance(node, Locator):
            continue

        has_resolvable = any(getattr(node, f) is not None for f in _RESOLVABLE)

        # empty_locator: all fields are None
        all_none = all(
            getattr(node, f) is None for f in node.__class__.model_fields
        )
        if all_none:
            diags.append(
                Diagnostic(
                    severity="warning",
                    category="reference",
                    code="empty_locator",
                    path=json_path,
                    message="Locator has no fields set",
                )
            )
            continue

        # note_only_locator: only note is set
        if not has_resolvable and node.note is not None:
            diags.append(
                Diagnostic(
                    severity="warning",
                    category="reference",
                    code="note_only_locator",
                    path=json_path,
                    message="Locator has only 'note' set — no resolvable reference",
                )
            )

        # invalid_line_range
        if (
            node.start_line is not None
            and node.end_line is not None
            and node.start_line > node.end_line
        ):
            diags.append(
                Diagnostic(
                    severity="error",
                    category="reference",
                    code="invalid_line_range",
                    path=json_path,
                    message=f"start_line ({node.start_line}) > end_line ({node.end_line})",
                )
            )

        # Path checks
        if node.path is not None:
            p = node.path

            # absolute_path_not_allowed: POSIX absolute or Windows absolute
            if p.startswith("/") or _WINDOWS_ABS_RE.match(p):
                diags.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="absolute_path_not_allowed",
                        path=json_path,
                        message=f"Absolute path not allowed: {p!r}",
                    )
                )
            else:
                # path_escapes_project_root
                normalized = posixpath.normpath(p)
                if normalized.startswith(".."):
                    diags.append(
                        Diagnostic(
                            severity="error",
                            category="reference",
                            code="path_escapes_project_root",
                            path=json_path,
                            message=f"Path escapes project root: {p!r}",
                        )
                    )

    return diags


# ---------------------------------------------------------------------------
# Inventory-specific checks
# ---------------------------------------------------------------------------


def _check_inventory(
    cert: CertificateEnvelope,
    nodes: list[tuple[str, BaseModel]],
) -> list[Diagnostic]:
    """Run inventory-specific checks when inventories are present."""
    diags: list[Diagnostic] = []

    art_inv = cert.artifact_inventory
    ev_inv = cert.evidence_inventory

    if art_inv is None and ev_inv is None:
        return diags

    # Build inventory lookup dicts
    art_inv_ids: dict[str, ArtifactRef] = {}
    ev_inv_ids: dict[str, EvidenceRef] = {}

    # Check duplicates within inventory itself
    if art_inv is not None:
        inv_first_path: dict[str, str] = {}
        for i, aref in enumerate(art_inv):
            ipath = f"artifact_inventory[{i}]"
            if aref.artifact_id in inv_first_path:
                diags.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="duplicate_artifact_id",
                        path=ipath,
                        message=f"Duplicate artifact_id {aref.artifact_id!r} in inventory",
                        related_path=inv_first_path[aref.artifact_id],
                    )
                )
            else:
                inv_first_path[aref.artifact_id] = ipath
                art_inv_ids[aref.artifact_id] = aref

    if ev_inv is not None:
        inv_first_path_ev: dict[str, str] = {}
        for i, eref in enumerate(ev_inv):
            ipath = f"evidence_inventory[{i}]"
            if eref.evidence_id in inv_first_path_ev:
                diags.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="duplicate_evidence_id",
                        path=ipath,
                        message=f"Duplicate evidence_id {eref.evidence_id!r} in inventory",
                        related_path=inv_first_path_ev[eref.evidence_id],
                    )
                )
            else:
                inv_first_path_ev[eref.evidence_id] = ipath
                ev_inv_ids[eref.evidence_id] = eref

    # Collect inline (non-inventory) refs
    inline_artifact_ids: set[str] = set()
    inline_evidence_ids: set[str] = set()

    for json_path, node in nodes:
        # Skip inventory entries themselves
        if json_path.startswith("artifact_inventory[") or json_path.startswith(
            "evidence_inventory["
        ):
            continue

        if (
            isinstance(node, ArtifactRef)
            and art_inv is not None
            and _is_evidence_artifact(json_path)
        ):
            aid = node.artifact_id
            inline_artifact_ids.add(aid)
            if aid not in art_inv_ids:
                diags.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="missing_artifact_from_inventory",
                        path=json_path,
                        message=f"Artifact {aid!r} not found in artifact_inventory",
                    )
                )
            else:
                # artifact_definition_mismatch
                canonical = art_inv_ids[aid]
                mismatches: list[str] = []
                for field in _ARTIFACT_CMP_FIELDS:
                    inline_val = getattr(node, field)
                    canon_val = getattr(canonical, field)
                    if inline_val != canon_val:
                        mismatches.append(field)
                if node.locator != canonical.locator:
                    mismatches.append("locator")
                if mismatches:
                    diags.append(
                        Diagnostic(
                            severity="error",
                            category="reference",
                            code="artifact_definition_mismatch",
                            path=json_path,
                            message=(
                                f"Artifact {aid!r} differs from inventory"
                                f" on: {', '.join(mismatches)}"
                            ),
                        )
                    )

        if isinstance(node, EvidenceRef) and ev_inv is not None:
            eid = node.evidence_id
            inline_evidence_ids.add(eid)
            if eid not in ev_inv_ids:
                diags.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="missing_evidence_from_inventory",
                        path=json_path,
                        message=f"Evidence {eid!r} not found in evidence_inventory",
                    )
                )
            else:
                # evidence_definition_mismatch
                ev_canonical = ev_inv_ids[eid]
                mismatches_ev: list[str] = []
                for field in _EVIDENCE_CMP_FIELDS:
                    inline_val = getattr(node, field)
                    canon_val = getattr(ev_canonical, field)
                    if inline_val != canon_val:
                        mismatches_ev.append(field)
                if node.artifact_ref != ev_canonical.artifact_ref:
                    mismatches_ev.append("artifact_ref")
                if mismatches_ev:
                    diags.append(
                        Diagnostic(
                            severity="error",
                            category="reference",
                            code="evidence_definition_mismatch",
                            path=json_path,
                            message=(
                                f"Evidence {eid!r} differs from inventory"
                                f" on: {', '.join(mismatches_ev)}"
                            ),
                        )
                    )

    # unused_artifact_inventory_entry
    if art_inv is not None:
        for i, aref in enumerate(art_inv):
            if aref.artifact_id not in inline_artifact_ids:
                diags.append(
                    Diagnostic(
                        severity="warning",
                        category="reference",
                        code="unused_artifact_inventory_entry",
                        path=f"artifact_inventory[{i}]",
                        message=(
                            f"Artifact {aref.artifact_id!r} declared in"
                            " inventory but never referenced inline"
                        ),
                    )
                )

    # unused_evidence_inventory_entry
    if ev_inv is not None:
        for i, eref in enumerate(ev_inv):
            if eref.evidence_id not in inline_evidence_ids:
                diags.append(
                    Diagnostic(
                        severity="warning",
                        category="reference",
                        code="unused_evidence_inventory_entry",
                        path=f"evidence_inventory[{i}]",
                        message=(
                            f"Evidence {eref.evidence_id!r} declared in"
                            " inventory but never referenced inline"
                        ),
                    )
                )

    return diags


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def validate_refs(certificate: CertificateEnvelope) -> list[Diagnostic]:
    """Run all referential checks on a parsed certificate.

    Returns a list of Diagnostic objects (errors and warnings).
    """
    nodes = _walk(certificate, "")
    diags: list[Diagnostic] = []

    has_inventory = (
        certificate.artifact_inventory is not None
        or certificate.evidence_inventory is not None
    )

    # --- Always-run checks ---

    # Duplicate claim IDs (document-wide namespace always)
    diags.extend(_check_duplicate_claims(nodes))

    # Duplicate evidence / artifact IDs — only in legacy (no-inventory) mode
    if not has_inventory:
        diags.extend(_check_duplicate_evidence_legacy(nodes))
        diags.extend(_check_duplicate_artifact_legacy(nodes))

    # Collect known IDs for ref resolution
    claim_ids: set[str] = set()
    evidence_ids: set[str] = set()
    for _, node in nodes:
        if isinstance(node, ClaimBase):
            claim_ids.add(node.claim_id)
        if isinstance(node, EvidenceRef):
            evidence_ids.add(node.evidence_id)

    # Missing claim refs in formal conclusions
    diags.extend(_check_missing_claim_refs(nodes, claim_ids))

    # Missing evidence in verification records
    diags.extend(_check_missing_evidence_in_verification(nodes, evidence_ids))

    # Locator quality checks
    diags.extend(_check_locators(nodes))

    # --- Inventory-specific checks ---
    if has_inventory:
        diags.extend(_check_inventory(certificate, nodes))

    return diags
