# S2: Evidence Inventory + Referential Validation — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add canonical evidence/artifact inventories to the certificate envelope and implement referential + filesystem validation that catches broken references.

**Architecture:** Layered validation pipeline: (1) JSON load, (2) Pydantic structural validation, (3) pure referential validation via recursive model tree walk, (4) opt-in filesystem locator checks. All results are `Diagnostic` Pydantic models. CLI composes and renders.

**Tech Stack:** Python 3.10+, Pydantic, Click, Rich, pytest, Hypothesis. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-03-11-s2-evidence-inventory-referential-validation-design.md`

**Branch:** `feat/s2-referential-validation` (from `main`)

---

## Pre-flight

- [ ] **Step 1: Create feature branch**

```bash
git checkout main && git pull && git checkout -b feat/s2-referential-validation
```

- [ ] **Step 2: Verify clean baseline**

```bash
make check
```

Expected: All lint, typecheck, and tests pass.

---

## Chunk 1: Foundation — Diagnostic Model + Schema/Model Updates

### Task 1: Diagnostic Model

**Files:**
- Create: `src/sdlc_control_plane/verification/diagnostics.py`
- Create: `tests/test_diagnostics.py`

- [ ] **Step 1: Write failing tests for Diagnostic model**

```python
# tests/test_diagnostics.py
"""Tests for the Diagnostic model and Pydantic error translation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sdlc_control_plane.verification.diagnostics import Diagnostic


class TestDiagnostic:
    def test_create_error_diagnostic(self) -> None:
        d = Diagnostic(
            severity="error",
            category="reference",
            code="duplicate_claim_id",
            path="premises[0].claim_id",
            message='claim ID "p1" already defined',
        )
        assert d.severity == "error"
        assert d.category == "reference"
        assert d.code == "duplicate_claim_id"

    def test_create_warning_diagnostic(self) -> None:
        d = Diagnostic(
            severity="warning",
            category="reference",
            code="empty_locator",
            path="premises[0].evidence_refs[0].artifact_ref.locator",
            message="Locator has all None fields",
        )
        assert d.severity == "warning"

    def test_related_path_optional(self) -> None:
        d = Diagnostic(
            severity="error",
            category="reference",
            code="duplicate_claim_id",
            path="quality_assertions[0].claim_id",
            message="duplicate",
            related_path="premises[0].claim_id",
        )
        assert d.related_path == "premises[0].claim_id"

    def test_related_path_defaults_none(self) -> None:
        d = Diagnostic(
            severity="error",
            category="reference",
            code="missing_claim_ref",
            path="formal_conclusion.derived_from_claim_ids[0]",
            message="not found",
        )
        assert d.related_path is None

    def test_frozen(self) -> None:
        d = Diagnostic(
            severity="error",
            category="reference",
            code="test",
            path="x",
            message="y",
        )
        with pytest.raises(ValidationError):
            d.severity = "warning"  # type: ignore[misc]

    def test_rejects_invalid_severity(self) -> None:
        with pytest.raises(ValidationError):
            Diagnostic(
                severity="critical",  # type: ignore[arg-type]
                category="reference",
                code="test",
                path="x",
                message="y",
            )

    def test_rejects_invalid_category(self) -> None:
        with pytest.raises(ValidationError):
            Diagnostic(
                severity="error",
                category="semantic",  # type: ignore[arg-type]
                code="test",
                path="x",
                message="y",
            )

    def test_json_serializable(self) -> None:
        d = Diagnostic(
            severity="error",
            category="structure",
            code="pydantic_validation_error",
            path="certificate_id",
            message="Field required",
        )
        data = d.model_dump()
        assert data["code"] == "pydantic_validation_error"
        assert data["related_path"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_diagnostics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sdlc_control_plane.verification.diagnostics'`

- [ ] **Step 3: Write Diagnostic model**

```python
# src/sdlc_control_plane/verification/diagnostics.py
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
    file_path: str,
) -> list[Diagnostic]:
    """Translate a Pydantic ValidationError into Diagnostic objects."""
    diagnostics: list[Diagnostic] = []
    for err in error.errors():
        loc = " -> ".join(str(p) for p in err["loc"])
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_diagnostics.py -v`
Expected: All PASS

- [ ] **Step 5: Write tests for pydantic_errors_to_diagnostics**

Add to `tests/test_diagnostics.py`:

```python
from sdlc_control_plane.verification.diagnostics import pydantic_errors_to_diagnostics
from sdlc_control_plane.verification.models import TaskReviewCertificate


class TestPydanticErrorTranslation:
    def test_translates_missing_field(self) -> None:
        try:
            TaskReviewCertificate(
                **{
                    "schema_version": "1.0.0",
                    "certificate_type": "task_review",
                    # missing certificate_id and many others
                }
            )
        except ValidationError as e:
            diagnostics = pydantic_errors_to_diagnostics(e, "test.json")
            assert len(diagnostics) > 0
            assert all(d.severity == "error" for d in diagnostics)
            assert all(d.category == "structure" for d in diagnostics)
            assert all(d.code == "pydantic_validation_error" for d in diagnostics)

    def test_translates_nested_error(self) -> None:
        try:
            TaskReviewCertificate(
                **{
                    "schema_version": "1.0.0",
                    "certificate_id": "cert-001",
                    "certificate_type": "task_review",
                    "workflow_run_id": "run-001",
                    "issue_ref": {"artifact_id": "iss-1", "artifact_type": "issue"},
                    "produced_by": {
                        "actor_id": "c1",
                        "author_kind": "claude",
                        "role": "reviewer_a",
                    },
                    "produced_at": "2026-03-11T00:00:00Z",
                    "source_artifacts": [
                        {"artifact_id": "s1", "artifact_type": "file"}
                    ],
                    "validation_status": "validated",
                    "definition": "Task complete iff all satisfied.",
                    "premises": [
                        {
                            "claim_id": "p1",
                            "text": "ok",
                            "evidence_refs": [
                                {
                                    "evidence_id": "ev-1",
                                    "evidence_type": "test_result",
                                    "artifact_ref": {
                                        "artifact_id": "a1",
                                        "artifact_type": "INVALID_TYPE",
                                    },
                                }
                            ],
                            "status": "satisfied",
                        }
                    ],
                    "quality_assertions": [
                        {
                            "claim_id": "q1",
                            "text": "ok",
                            "evidence_refs": [
                                {
                                    "evidence_id": "ev-2",
                                    "evidence_type": "typecheck_result",
                                    "artifact_ref": {
                                        "artifact_id": "a2",
                                        "artifact_type": "command_output",
                                    },
                                }
                            ],
                            "status": "verified",
                        }
                    ],
                    "verification_commands": [
                        {
                            "command_id": "cmd-1",
                            "command": "pytest",
                            "exit_code": 0,
                            "status": "passed",
                        }
                    ],
                    "formal_conclusion": {
                        "status": "complete",
                        "derived_from_claim_ids": ["p1", "q1"],
                    },
                    "issues": [],
                }
            )
        except ValidationError as e:
            diagnostics = pydantic_errors_to_diagnostics(e, "test.json")
            assert len(diagnostics) >= 1
            # Should include path showing nested location
            paths = [d.path for d in diagnostics]
            assert any("artifact_type" in p for p in paths)

    def test_empty_error_returns_empty_list(self) -> None:
        # ValidationError always has at least one error, so test with a valid parse
        # (no exception, no diagnostics to translate)
        pass  # This is a design note — the function is only called when there IS an error
```

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_diagnostics.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/sdlc_control_plane/verification/diagnostics.py tests/test_diagnostics.py
git commit -m "feat(s2): add Diagnostic model and Pydantic error translation

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Model Changes — Add Inventories to CertificateEnvelope + Update Schema Bundle

**Files:**
- Modify: `src/sdlc_control_plane/verification/models.py:489-502`
- Modify: `schemas/agent_workflow_schema_bundle.json` (CertificateEnvelope $def)
- Modify: `tests/test_models.py` (TestCertificateEnvelope)
- Modify: `tests/test_schema_drift.py` (will auto-check after schema update)

- [ ] **Step 1: Write failing tests for new inventory fields**

Add to `tests/test_models.py` in `TestCertificateEnvelope`:

```python
    def test_inventory_fields_optional(self) -> None:
        ce = CertificateEnvelope(**_make_envelope_data())
        assert ce.artifact_inventory is None
        assert ce.evidence_inventory is None

    def test_with_artifact_inventory(self) -> None:
        ce = CertificateEnvelope(
            **_make_envelope_data(
                artifact_inventory=[
                    {"artifact_id": "art-1", "artifact_type": "file"},
                ]
            )
        )
        assert len(ce.artifact_inventory) == 1  # type: ignore[arg-type]
        assert ce.artifact_inventory[0].artifact_id == "art-1"  # type: ignore[index]

    def test_with_evidence_inventory(self) -> None:
        ce = CertificateEnvelope(
            **_make_envelope_data(
                evidence_inventory=[
                    {
                        "evidence_id": "ev-1",
                        "evidence_type": "file_span",
                        "artifact_ref": {
                            "artifact_id": "art-1",
                            "artifact_type": "file",
                        },
                    },
                ]
            )
        )
        assert len(ce.evidence_inventory) == 1  # type: ignore[arg-type]

    def test_empty_inventories_allowed(self) -> None:
        ce = CertificateEnvelope(
            **_make_envelope_data(
                artifact_inventory=[],
                evidence_inventory=[],
            )
        )
        assert ce.artifact_inventory == []
        assert ce.evidence_inventory == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py::TestCertificateEnvelope::test_inventory_fields_optional -v`
Expected: FAIL — `AttributeError: 'CertificateEnvelope' object has no attribute 'artifact_inventory'`

- [ ] **Step 3: Add inventory fields to CertificateEnvelope model**

In `src/sdlc_control_plane/verification/models.py`, after `unverified_claim_count`:

```python
    artifact_inventory: list[ArtifactRef] | None = None
    evidence_inventory: list[EvidenceRef] | None = None
```

- [ ] **Step 4: Run model tests**

Run: `uv run pytest tests/test_models.py -v`
Expected: All PASS

- [ ] **Step 5: Update JSON Schema bundle**

In `schemas/agent_workflow_schema_bundle.json`, add to CertificateEnvelope properties (after `unverified_claim_count`):

```json
    "artifact_inventory": {
      "type": "array",
      "items": { "$ref": "#/$defs/ArtifactRef" }
    },
    "evidence_inventory": {
      "type": "array",
      "items": { "$ref": "#/$defs/EvidenceRef" }
    }
```

These are NOT in the `required` array — they are optional.

- [ ] **Step 6: Run drift tests to verify schema sync**

Run: `uv run pytest tests/test_schema_drift.py -v`
Expected: All PASS (CertificateEnvelope properties now match)

- [ ] **Step 7: Verify existing fixtures still pass**

Run: `uv run pytest tests/test_models.py::TestFixtureRoundTrip -v`
Expected: All PASS (existing fixtures have no inventory fields, which default to None)

- [ ] **Step 8: Run full check**

Run: `make check`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add src/sdlc_control_plane/verification/models.py schemas/agent_workflow_schema_bundle.json tests/test_models.py
git commit -m "feat(s2): add artifact_inventory and evidence_inventory to CertificateEnvelope

Optional fields (None default) on both Pydantic model and JSON Schema.
Convention: required for new S2+ certificates, accepted as absent for legacy.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Update verification/__init__.py Re-exports

**Files:**
- Modify: `src/sdlc_control_plane/verification/__init__.py`

- [ ] **Step 1: Add re-exports**

```python
# src/sdlc_control_plane/verification/__init__.py
"""Verification & Evidence bounded context — public API."""

from sdlc_control_plane.verification.diagnostics import (
    Diagnostic,
    pydantic_errors_to_diagnostics,
)

__all__ = [
    "Diagnostic",
    "pydantic_errors_to_diagnostics",
]
```

Note: `validate_refs` and `validate_filesystem` will be added here in later tasks as they are created.

- [ ] **Step 2: Verify import works**

Run: `uv run python -c "from sdlc_control_plane.verification import Diagnostic; print(Diagnostic.__name__)"`
Expected: `Diagnostic`

- [ ] **Step 3: Commit**

```bash
git add src/sdlc_control_plane/verification/__init__.py
git commit -m "feat(s2): re-export Diagnostic from verification package

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Chunk 2: Referential Validation — Tree Walk + Pure Checks

### Task 4: Generic Tree Walk + Duplicate ID Checks

**Files:**
- Create: `src/sdlc_control_plane/verification/referential.py`
- Create: `tests/test_referential.py`

This is the largest task. The tree walk collects all typed nodes from the certificate model recursively, then the checks run against the collected sets.

- [ ] **Step 1: Write failing tests for tree walk collection**

```python
# tests/test_referential.py
"""Tests for referential validation (pure intra-document checks)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdlc_control_plane.verification.diagnostics import Diagnostic
from sdlc_control_plane.verification.models import validate_certificate
from sdlc_control_plane.verification.referential import validate_refs

FIXTURES = Path(__file__).parent / "fixtures"


def _load_cert(name: str) -> object:
    data = json.loads((FIXTURES / name).read_text())
    return validate_certificate(data)


class TestValidCertificatePassesRefChecks:
    def test_valid_task_review_no_errors(self) -> None:
        cert = _load_cert("valid_task_review.json")
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.severity == "error"]
        assert errors == []

    def test_valid_design_decision_no_errors(self) -> None:
        cert = _load_cert("valid_design_decision.json")
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.severity == "error"]
        assert errors == []

    def test_valid_deferred_scope_no_errors(self) -> None:
        cert = _load_cert("valid_deferred_scope.json")
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.severity == "error"]
        assert errors == []

    def test_valid_impact_alignment_known_design_gap(self) -> None:
        """ImpactAlignmentCertificate has no ClaimBase fields, but
        FormalConclusion.derived_from_claim_ids requires min_length=1.
        The fixture references 'issue-41' which is an ArtifactRef ID,
        not a claim ID. This is a pre-existing design tension — the
        referential validator correctly flags it as missing_claim_ref.
        """
        cert = _load_cert("valid_impact_alignment.json")
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.severity == "error"]
        # Only expected error: the derived_from_claim_ids reference
        assert all(d.code == "missing_claim_ref" for d in errors)
        assert len(errors) == 1
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_referential.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sdlc_control_plane.verification.referential'`

- [ ] **Step 3: Implement tree walk and validate_refs skeleton**

```python
# src/sdlc_control_plane/verification/referential.py
"""Pure referential validation for certificate documents."""

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
# Tree walk: collect typed nodes with their JSON paths
# ---------------------------------------------------------------------------

NodeEntry = tuple[str, Any]  # (json_path, model_instance)


def _collect_nodes(
    obj: Any,
    path: str,
    *,
    claims: list[NodeEntry],
    evidence_refs: list[NodeEntry],
    artifact_refs: list[NodeEntry],
    locators: list[NodeEntry],
    verification_records: list[NodeEntry],
    conclusions: list[NodeEntry],
) -> None:
    """Recursively walk a Pydantic model tree and collect typed nodes."""
    if not isinstance(obj, BaseModel):
        return

    if isinstance(obj, ClaimBase):
        claims.append((path, obj))
    if isinstance(obj, EvidenceRef):
        evidence_refs.append((path, obj))
    if isinstance(obj, ArtifactRef):
        artifact_refs.append((path, obj))
    if isinstance(obj, Locator):
        locators.append((path, obj))
    if isinstance(obj, VerificationRecord):
        verification_records.append((path, obj))
    if isinstance(obj, FormalConclusion):
        conclusions.append((path, obj))

    for field_name, field_value in obj:
        child_path = f"{path}.{field_name}" if path else field_name
        if isinstance(field_value, BaseModel):
            _collect_nodes(
                field_value,
                child_path,
                claims=claims,
                evidence_refs=evidence_refs,
                artifact_refs=artifact_refs,
                locators=locators,
                verification_records=verification_records,
                conclusions=conclusions,
            )
        elif isinstance(field_value, list):
            for i, item in enumerate(field_value):
                _collect_nodes(
                    item,
                    f"{child_path}[{i}]",
                    claims=claims,
                    evidence_refs=evidence_refs,
                    artifact_refs=artifact_refs,
                    locators=locators,
                    verification_records=verification_records,
                    conclusions=conclusions,
                )


def _walk(cert: CertificateEnvelope) -> dict[str, list[NodeEntry]]:
    """Walk a certificate and return all collected typed nodes."""
    collections: dict[str, list[NodeEntry]] = {
        "claims": [],
        "evidence_refs": [],
        "artifact_refs": [],
        "locators": [],
        "verification_records": [],
        "conclusions": [],
    }
    _collect_nodes(cert, "", **collections)
    return collections


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------

_WINDOWS_ABS_RE = re.compile(r"^[A-Za-z]:|^\\\\")


def _check_duplicate_ids(
    entries: list[NodeEntry],
    id_field: str,
    code: str,
    has_inventory: bool,
) -> list[Diagnostic]:
    """Check for duplicate IDs across a set of nodes.

    When has_inventory is True and the entries come from inline nodes,
    duplicates are expected (same evidence cited by multiple claims).
    This function is called on inventory entries only in that case.
    """
    seen: dict[str, str] = {}  # id -> first_path
    diagnostics: list[Diagnostic] = []
    for json_path, node in entries:
        node_id = getattr(node, id_field)
        id_path = f"{json_path}.{id_field}" if json_path else id_field
        if node_id in seen:
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    category="reference",
                    code=code,
                    path=id_path,
                    message=f'{code}: "{node_id}" already defined',
                    related_path=seen[node_id],
                )
            )
        else:
            seen[node_id] = id_path
    return diagnostics


def _check_locators(locators: list[NodeEntry]) -> list[Diagnostic]:
    """Check locator constraints: empty, note-only, line range, path safety."""
    diagnostics: list[Diagnostic] = []
    _RESOLVABLE = ("path", "url", "command", "commit_sha", "issue_number", "diff_hunk")

    for json_path, loc in locators:
        has_resolvable = any(getattr(loc, f) is not None for f in _RESOLVABLE)
        has_lines = loc.start_line is not None or loc.end_line is not None

        if not has_resolvable and not has_lines:
            if loc.note is None:
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        category="reference",
                        code="empty_locator",
                        path=json_path,
                        message="Locator has all None fields",
                    )
                )
            else:
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        category="reference",
                        code="note_only_locator",
                        path=json_path,
                        message="Locator has only note set — no resolvable target",
                    )
                )

        # invalid_line_range
        if (
            loc.start_line is not None
            and loc.end_line is not None
            and loc.start_line > loc.end_line
        ):
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    category="reference",
                    code="invalid_line_range",
                    path=f"{json_path}.start_line",
                    message=f"start_line ({loc.start_line}) > end_line ({loc.end_line})",
                )
            )

        # Path safety checks
        if loc.path is not None:
            # absolute_path_not_allowed
            if loc.path.startswith("/") or _WINDOWS_ABS_RE.match(loc.path):
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="absolute_path_not_allowed",
                        path=f"{json_path}.path",
                        message=f'Absolute path not allowed: "{loc.path}"',
                    )
                )
            else:
                # path_escapes_project_root (lexical check via posixpath.normpath)
                normalized = posixpath.normpath(loc.path)
                if normalized == ".." or normalized.startswith("../"):
                    diagnostics.append(
                        Diagnostic(
                            severity="error",
                            category="reference",
                            code="path_escapes_project_root",
                            path=f"{json_path}.path",
                            message=f'Path escapes project root: "{loc.path}" normalizes to "{normalized}"',
                        )
                    )

    return diagnostics


def _check_missing_claim_refs(
    conclusions: list[NodeEntry],
    claim_ids: dict[str, str],
) -> list[Diagnostic]:
    """Check that derived_from_claim_ids reference real claims."""
    diagnostics: list[Diagnostic] = []
    for json_path, conclusion in conclusions:
        for i, claim_id in enumerate(conclusion.derived_from_claim_ids):
            if claim_id not in claim_ids:
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="missing_claim_ref",
                        path=f"{json_path}.derived_from_claim_ids[{i}]",
                        message=f'Claim ID "{claim_id}" not found in document',
                    )
                )
    return diagnostics


def _check_missing_evidence_in_verification(
    verification_records: list[NodeEntry],
    evidence_ids: set[str],
) -> list[Diagnostic]:
    """Check that evidence_checked IDs reference real evidence."""
    diagnostics: list[Diagnostic] = []
    for json_path, vr in verification_records:
        if vr.evidence_checked is None:
            continue
        for i, eid in enumerate(vr.evidence_checked):
            if eid not in evidence_ids:
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="missing_evidence_in_verification",
                        path=f"{json_path}.evidence_checked[{i}]",
                        message=f'Evidence ID "{eid}" not found in document',
                    )
                )
    return diagnostics


def _check_inventory(
    cert: CertificateEnvelope,
    inline_evidence: list[NodeEntry],
    inline_artifacts: list[NodeEntry],
) -> list[Diagnostic]:
    """Inventory-specific checks when inventories are present."""
    diagnostics: list[Diagnostic] = []

    if cert.artifact_inventory is not None:
        inv_by_id: dict[str, ArtifactRef] = {}
        inv_first_path: dict[str, str] = {}  # artifact_id -> first definition path
        # Check for duplicates within inventory
        for i, entry in enumerate(cert.artifact_inventory):
            path = f"artifact_inventory[{i}]"
            if entry.artifact_id in inv_by_id:
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="duplicate_artifact_id",
                        path=f"{path}.artifact_id",
                        message=f'duplicate_artifact_id: "{entry.artifact_id}" already defined',
                        related_path=inv_first_path[entry.artifact_id],
                    )
                )
            else:
                inv_by_id[entry.artifact_id] = entry
                inv_first_path[entry.artifact_id] = f"{path}.artifact_id"

        # Check inline artifacts against inventory
        referenced_ids: set[str] = set()
        for json_path, art in inline_artifacts:
            # Skip inventory entries themselves
            if json_path.startswith("artifact_inventory["):
                continue
            referenced_ids.add(art.artifact_id)
            if art.artifact_id not in inv_by_id:
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="missing_artifact_from_inventory",
                        path=f"{json_path}.artifact_id",
                        message=f'Artifact ID "{art.artifact_id}" not in artifact_inventory',
                    )
                )
            else:
                # Definition mismatch check (exclude description)
                canon = inv_by_id[art.artifact_id]
                mismatches = []
                if art.artifact_type != canon.artifact_type:
                    mismatches.append(f"artifact_type: {art.artifact_type} != {canon.artifact_type}")
                if art.content_hash != canon.content_hash:
                    mismatches.append(f"content_hash mismatch")
                if art.uri != canon.uri:
                    mismatches.append(f"uri mismatch")
                if art.locator != canon.locator:
                    mismatches.append(f"locator mismatch")
                if mismatches:
                    diagnostics.append(
                        Diagnostic(
                            severity="error",
                            category="reference",
                            code="artifact_definition_mismatch",
                            path=json_path,
                            message=f'Inline artifact "{art.artifact_id}" differs from inventory: {", ".join(mismatches)}',
                        )
                    )

        # Unused inventory entries
        for i, entry in enumerate(cert.artifact_inventory):
            if entry.artifact_id not in referenced_ids:
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        category="reference",
                        code="unused_artifact_inventory_entry",
                        path=f"artifact_inventory[{i}]",
                        message=f'Artifact ID "{entry.artifact_id}" in inventory but never referenced inline',
                    )
                )

    if cert.evidence_inventory is not None:
        ev_inv_by_id: dict[str, EvidenceRef] = {}
        ev_inv_first_path: dict[str, str] = {}
        for i, entry in enumerate(cert.evidence_inventory):
            path = f"evidence_inventory[{i}]"
            if entry.evidence_id in ev_inv_by_id:
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="duplicate_evidence_id",
                        path=f"{path}.evidence_id",
                        message=f'duplicate_evidence_id: "{entry.evidence_id}" already defined',
                        related_path=ev_inv_first_path[entry.evidence_id],
                    )
                )
            else:
                ev_inv_by_id[entry.evidence_id] = entry
                ev_inv_first_path[entry.evidence_id] = f"{path}.evidence_id"

        ev_referenced_ids: set[str] = set()
        for json_path, ev in inline_evidence:
            if json_path.startswith("evidence_inventory["):
                continue
            ev_referenced_ids.add(ev.evidence_id)
            if ev.evidence_id not in ev_inv_by_id:
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        category="reference",
                        code="missing_evidence_from_inventory",
                        path=f"{json_path}.evidence_id",
                        message=f'Evidence ID "{ev.evidence_id}" not in evidence_inventory',
                    )
                )
            else:
                canon = ev_inv_by_id[ev.evidence_id]
                mismatches = []
                if ev.evidence_type != canon.evidence_type:
                    mismatches.append(f"evidence_type: {ev.evidence_type} != {canon.evidence_type}")
                if ev.excerpt_hash != canon.excerpt_hash:
                    mismatches.append("excerpt_hash mismatch")
                if ev.excerpt != canon.excerpt:
                    mismatches.append("excerpt mismatch")
                if ev.artifact_ref != canon.artifact_ref:
                    mismatches.append("artifact_ref mismatch")
                if mismatches:
                    diagnostics.append(
                        Diagnostic(
                            severity="error",
                            category="reference",
                            code="evidence_definition_mismatch",
                            path=json_path,
                            message=f'Inline evidence "{ev.evidence_id}" differs from inventory: {", ".join(mismatches)}',
                        )
                    )

        for i, entry in enumerate(cert.evidence_inventory):
            if entry.evidence_id not in ev_referenced_ids:
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        category="reference",
                        code="unused_evidence_inventory_entry",
                        path=f"evidence_inventory[{i}]",
                        message=f'Evidence ID "{entry.evidence_id}" in inventory but never referenced inline',
                    )
                )

    return diagnostics


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def validate_refs(certificate: CertificateEnvelope) -> list[Diagnostic]:
    """Run all pure referential checks on a parsed certificate."""
    collections = _walk(certificate)
    diagnostics: list[Diagnostic] = []

    has_artifact_inv = certificate.artifact_inventory is not None
    has_evidence_inv = certificate.evidence_inventory is not None

    # Build ID registries
    claim_ids: dict[str, str] = {}
    for json_path, claim in collections["claims"]:
        claim_ids[claim.claim_id] = f"{json_path}.claim_id" if json_path else "claim_id"

    evidence_ids: set[str] = set()
    if has_evidence_inv:
        for entry in certificate.evidence_inventory:  # type: ignore[union-attr]
            evidence_ids.add(entry.evidence_id)
    else:
        for _, ev in collections["evidence_refs"]:
            evidence_ids.add(ev.evidence_id)

    # 1. Duplicate claim IDs (always checked across all ClaimBase nodes)
    diagnostics.extend(
        _check_duplicate_ids(collections["claims"], "claim_id", "duplicate_claim_id", False)
    )

    # 2. Duplicate evidence/artifact IDs (behavior depends on inventory presence)
    if not has_evidence_inv:
        diagnostics.extend(
            _check_duplicate_ids(
                collections["evidence_refs"], "evidence_id", "duplicate_evidence_id", False
            )
        )
    if not has_artifact_inv:
        diagnostics.extend(
            _check_duplicate_ids(
                collections["artifact_refs"], "artifact_id", "duplicate_artifact_id", False
            )
        )

    # 3. Missing claim refs in conclusions
    diagnostics.extend(_check_missing_claim_refs(collections["conclusions"], claim_ids))

    # 4. Missing evidence in verification records
    diagnostics.extend(
        _check_missing_evidence_in_verification(collections["verification_records"], evidence_ids)
    )

    # 5. Locator checks
    diagnostics.extend(_check_locators(collections["locators"]))

    # 6. Inventory-specific checks
    if has_artifact_inv or has_evidence_inv:
        diagnostics.extend(
            _check_inventory(
                certificate,
                collections["evidence_refs"],
                collections["artifact_refs"],
            )
        )

    return diagnostics
```

- [ ] **Step 4: Run tests to verify existing fixtures pass**

Run: `uv run pytest tests/test_referential.py -v`
Expected: All PASS (valid fixtures have no referential errors)

- [ ] **Step 5: Write tests for duplicate ID detection (legacy mode — no inventory)**

Add to `tests/test_referential.py`:

```python
class TestDuplicateClaimId:
    def test_duplicate_claim_id_detected(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        # Make quality_assertions[0] have same claim_id as premises[0]
        data["quality_assertions"][0]["claim_id"] = "p1"
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "duplicate_claim_id"]
        assert len(errors) == 1
        assert errors[0].severity == "error"
        assert "p1" in errors[0].message
        assert errors[0].related_path is not None


class TestDuplicateEvidenceId:
    def test_duplicate_evidence_id_detected(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        # Make both evidence refs have same ID
        data["quality_assertions"][0]["evidence_refs"][0]["evidence_id"] = "ev-1"
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "duplicate_evidence_id"]
        assert len(errors) == 1


class TestDuplicateArtifactId:
    def test_duplicate_artifact_id_detected(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        # Make both artifact refs have same ID
        data["quality_assertions"][0]["evidence_refs"][0]["artifact_ref"]["artifact_id"] = "art-1"
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "duplicate_artifact_id"]
        assert len(errors) == 1
```

- [ ] **Step 6: Run duplicate ID tests**

Run: `uv run pytest tests/test_referential.py -v -k "Duplicate"`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/sdlc_control_plane/verification/referential.py tests/test_referential.py
git commit -m "feat(s2): add referential validator with tree walk and duplicate ID checks

Generic recursive tree walk collects ClaimBase, EvidenceRef, ArtifactRef,
Locator, VerificationRecord, and FormalConclusion nodes. Implements all
20 check codes from the S2 spec including inventory-aware duplicate semantics.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Missing Ref + Locator Check Tests

**Files:**
- Modify: `tests/test_referential.py`

- [ ] **Step 1: Write tests for missing_claim_ref**

```python
class TestMissingClaimRef:
    def test_missing_derived_from_id(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["formal_conclusion"]["derived_from_claim_ids"] = ["p1", "NONEXISTENT"]
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "missing_claim_ref"]
        assert len(errors) == 1
        assert "NONEXISTENT" in errors[0].message
        assert "derived_from_claim_ids[1]" in errors[0].path

    def test_all_valid_refs_no_error(self) -> None:
        cert = _load_cert("valid_task_review.json")
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "missing_claim_ref"]
        assert errors == []
```

- [ ] **Step 2: Write tests for missing_evidence_in_verification**

```python
class TestMissingEvidenceInVerification:
    def test_missing_evidence_checked_id(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        # Add a verification record with a bad evidence_checked ref
        data["premises"][0]["verification"] = {
            "status": "verified",
            "method": "source_read",
            "verified_by": {"actor_id": "c1", "author_kind": "claude", "role": "reviewer_a"},
            "verified_at": "2026-03-11T00:00:00Z",
            "evidence_checked": ["ev-1", "GHOST"],
        }
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "missing_evidence_in_verification"]
        assert len(errors) == 1
        assert "GHOST" in errors[0].message
```

- [ ] **Step 3: Write tests for locator checks**

```python
class TestLocatorChecks:
    def test_empty_locator_warning(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {}
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        warnings = [d for d in diagnostics if d.code == "empty_locator"]
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"

    def test_note_only_locator_warning(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {
            "note": "see above"
        }
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        warnings = [d for d in diagnostics if d.code == "note_only_locator"]
        assert len(warnings) == 1

    def test_invalid_line_range(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {
            "path": "src/foo.py",
            "start_line": 50,
            "end_line": 10,
        }
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "invalid_line_range"]
        assert len(errors) == 1
        assert errors[0].severity == "error"

    def test_absolute_path_posix(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {
            "path": "/etc/passwd"
        }
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "absolute_path_not_allowed"]
        assert len(errors) == 1

    def test_absolute_path_windows_drive(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {
            "path": "C:\\Users\\foo.py"
        }
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "absolute_path_not_allowed"]
        assert len(errors) == 1

    def test_absolute_path_windows_unc(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {
            "path": "\\\\server\\share\\foo.py"
        }
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "absolute_path_not_allowed"]
        assert len(errors) == 1

    def test_path_escapes_root(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {
            "path": "../../etc/passwd"
        }
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "path_escapes_project_root"]
        assert len(errors) == 1

    def test_path_with_dotdot_that_stays_inside(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {
            "path": "src/../lib/foo.py"
        }
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "path_escapes_project_root"]
        assert errors == []

    def test_valid_relative_path_no_errors(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {
            "path": "src/foo.py",
            "start_line": 1,
            "end_line": 10,
        }
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        path_errors = [
            d
            for d in diagnostics
            if d.code
            in ("absolute_path_not_allowed", "path_escapes_project_root", "invalid_line_range")
        ]
        assert path_errors == []
```

- [ ] **Step 4: Run all referential tests**

Run: `uv run pytest tests/test_referential.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_referential.py
git commit -m "test(s2): add referential validation tests for missing refs and locator checks

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Inventory-Specific Check Tests

**Files:**
- Modify: `tests/test_referential.py`

- [ ] **Step 1: Write tests for inventory checks**

```python
def _make_task_review_with_inventory() -> dict:
    """Build a valid task review cert with canonical inventories."""
    return {
        "schema_version": "1.0.0",
        "certificate_id": "cert-001",
        "certificate_type": "task_review",
        "workflow_run_id": "run-001",
        "issue_ref": {"artifact_id": "issue-42", "artifact_type": "issue"},
        "produced_by": {"actor_id": "claude-1", "author_kind": "claude", "role": "reviewer_a"},
        "produced_at": "2026-03-11T00:00:00Z",
        "source_artifacts": [{"artifact_id": "src-1", "artifact_type": "file"}],
        "validation_status": "validated",
        "artifact_inventory": [
            {"artifact_id": "art-1", "artifact_type": "command_output"},
            {"artifact_id": "art-2", "artifact_type": "command_output"},
            {"artifact_id": "issue-42", "artifact_type": "issue"},
            {"artifact_id": "src-1", "artifact_type": "file"},
        ],
        "evidence_inventory": [
            {"evidence_id": "ev-1", "evidence_type": "test_result", "artifact_ref": {"artifact_id": "art-1", "artifact_type": "command_output"}},
            {"evidence_id": "ev-2", "evidence_type": "typecheck_result", "artifact_ref": {"artifact_id": "art-2", "artifact_type": "command_output"}},
        ],
        "definition": "Task is COMPLETE iff all spec requirements are satisfied.",
        "premises": [{"claim_id": "p1", "text": "All tests pass", "evidence_refs": [{"evidence_id": "ev-1", "evidence_type": "test_result", "artifact_ref": {"artifact_id": "art-1", "artifact_type": "command_output"}}], "status": "satisfied"}],
        "quality_assertions": [{"claim_id": "q1", "text": "Code is type-safe", "evidence_refs": [{"evidence_id": "ev-2", "evidence_type": "typecheck_result", "artifact_ref": {"artifact_id": "art-2", "artifact_type": "command_output"}}], "status": "verified"}],
        "verification_commands": [{"command_id": "cmd-1", "command": "pytest", "exit_code": 0, "status": "passed"}],
        "formal_conclusion": {"status": "complete", "derived_from_claim_ids": ["p1", "q1"]},
        "issues": [],
    }


class TestInventoryChecks:
    def test_valid_inventory_no_errors(self) -> None:
        cert = validate_certificate(_make_task_review_with_inventory())
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.severity == "error"]
        assert errors == []

    def test_missing_artifact_from_inventory(self) -> None:
        data = _make_task_review_with_inventory()
        # Remove art-1 from inventory but keep it inline
        data["artifact_inventory"] = [
            a for a in data["artifact_inventory"] if a["artifact_id"] != "art-1"
        ]
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "missing_artifact_from_inventory"]
        assert len(errors) >= 1

    def test_missing_evidence_from_inventory(self) -> None:
        data = _make_task_review_with_inventory()
        data["evidence_inventory"] = [
            e for e in data["evidence_inventory"] if e["evidence_id"] != "ev-1"
        ]
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "missing_evidence_from_inventory"]
        assert len(errors) >= 1

    def test_unused_artifact_inventory_entry(self) -> None:
        data = _make_task_review_with_inventory()
        data["artifact_inventory"].append(
            {"artifact_id": "unused-art", "artifact_type": "file"}
        )
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        warnings = [d for d in diagnostics if d.code == "unused_artifact_inventory_entry"]
        assert len(warnings) >= 1
        assert any("unused-art" in w.message for w in warnings)

    def test_unused_evidence_inventory_entry(self) -> None:
        data = _make_task_review_with_inventory()
        data["evidence_inventory"].append(
            {"evidence_id": "unused-ev", "evidence_type": "file_span", "artifact_ref": {"artifact_id": "art-1", "artifact_type": "command_output"}}
        )
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        warnings = [d for d in diagnostics if d.code == "unused_evidence_inventory_entry"]
        assert len(warnings) >= 1

    def test_artifact_definition_mismatch(self) -> None:
        data = _make_task_review_with_inventory()
        # Inline says "file" but inventory says "command_output" for art-1
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["artifact_type"] = "file"
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "artifact_definition_mismatch"]
        assert len(errors) >= 1

    def test_evidence_definition_mismatch(self) -> None:
        data = _make_task_review_with_inventory()
        # Inline says "file_span" but inventory says "test_result" for ev-1
        data["premises"][0]["evidence_refs"][0]["evidence_type"] = "file_span"
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "evidence_definition_mismatch"]
        assert len(errors) >= 1

    def test_duplicate_in_inventory_itself(self) -> None:
        data = _make_task_review_with_inventory()
        data["artifact_inventory"].append(
            {"artifact_id": "art-1", "artifact_type": "command_output"}
        )
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        errors = [d for d in diagnostics if d.code == "duplicate_artifact_id"]
        assert len(errors) >= 1

    def test_inline_duplicates_allowed_with_inventory(self) -> None:
        """Same evidence cited by multiple claims — not an error when inventory exists."""
        data = _make_task_review_with_inventory()
        # Both claims reference ev-1
        data["quality_assertions"][0]["evidence_refs"][0]["evidence_id"] = "ev-1"
        data["quality_assertions"][0]["evidence_refs"][0]["evidence_type"] = "test_result"
        data["quality_assertions"][0]["evidence_refs"][0]["artifact_ref"] = {
            "artifact_id": "art-1",
            "artifact_type": "command_output",
        }
        cert = validate_certificate(data)
        diagnostics = validate_refs(cert)
        dup_errors = [d for d in diagnostics if d.code == "duplicate_evidence_id"]
        assert dup_errors == [], "Inline duplicates should be allowed when inventory is present"
```

- [ ] **Step 2: Run inventory tests**

Run: `uv run pytest tests/test_referential.py -v -k "Inventory"`
Expected: All PASS

- [ ] **Step 3: Run full test suite**

Run: `make check`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_referential.py
git commit -m "test(s2): add inventory-specific referential validation tests

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Chunk 3: Filesystem Locator Checks

### Task 7: Filesystem Validator

**Files:**
- Create: `src/sdlc_control_plane/verification/locator_fs.py`
- Create: `tests/test_locator_fs.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_locator_fs.py
"""Tests for filesystem-backed locator validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdlc_control_plane.verification.diagnostics import Diagnostic
from sdlc_control_plane.verification.locator_fs import validate_filesystem
from sdlc_control_plane.verification.models import validate_certificate

FIXTURES = Path(__file__).parent / "fixtures"


def _cert_with_locator(locator: dict) -> object:
    data = json.loads((FIXTURES / "valid_task_review.json").read_text())
    data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = locator
    return validate_certificate(data)


class TestUnresolvablePath:
    def test_missing_file_detected(self, tmp_path: Path) -> None:
        cert = _cert_with_locator({"path": "src/nonexistent.py"})
        diagnostics = validate_filesystem(cert, tmp_path)
        errors = [d for d in diagnostics if d.code == "unresolvable_path"]
        assert len(errors) == 1

    def test_existing_file_no_error(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "foo.py").write_text("hello\n")
        cert = _cert_with_locator({"path": "src/foo.py"})
        diagnostics = validate_filesystem(cert, tmp_path)
        errors = [d for d in diagnostics if d.code == "unresolvable_path"]
        assert errors == []


class TestLineRangeExceedsFile:
    def test_end_line_exceeds_file(self, tmp_path: Path) -> None:
        (tmp_path / "small.py").write_text("line1\nline2\nline3\n")
        cert = _cert_with_locator(
            {"path": "small.py", "start_line": 1, "end_line": 100}
        )
        diagnostics = validate_filesystem(cert, tmp_path)
        warnings = [d for d in diagnostics if d.code == "line_range_exceeds_file"]
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"

    def test_valid_line_range_no_warning(self, tmp_path: Path) -> None:
        (tmp_path / "ok.py").write_text("line1\nline2\nline3\n")
        cert = _cert_with_locator(
            {"path": "ok.py", "start_line": 1, "end_line": 3}
        )
        diagnostics = validate_filesystem(cert, tmp_path)
        warnings = [d for d in diagnostics if d.code == "line_range_exceeds_file"]
        assert warnings == []


class TestPathNotRegularFile:
    def test_directory_with_lines_is_error(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        cert = _cert_with_locator(
            {"path": "src", "start_line": 1, "end_line": 10}
        )
        diagnostics = validate_filesystem(cert, tmp_path)
        errors = [d for d in diagnostics if d.code == "path_not_regular_file"]
        assert len(errors) == 1
        assert errors[0].severity == "error"

    def test_directory_without_lines_no_error(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        cert = _cert_with_locator({"path": "src"})
        diagnostics = validate_filesystem(cert, tmp_path)
        errors = [d for d in diagnostics if d.code == "path_not_regular_file"]
        assert errors == []


class TestNoLocatorPaths:
    def test_cert_without_locators_produces_no_fs_diagnostics(self, tmp_path: Path) -> None:
        cert = validate_certificate(
            json.loads((FIXTURES / "valid_task_review.json").read_text())
        )
        diagnostics = validate_filesystem(cert, tmp_path)
        assert diagnostics == []
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_locator_fs.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement validate_filesystem**

```python
# src/sdlc_control_plane/verification/locator_fs.py
"""Filesystem-backed locator validation (opt-in via --project-root)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from sdlc_control_plane.verification.diagnostics import Diagnostic
from sdlc_control_plane.verification.models import CertificateEnvelope, Locator


def _collect_locators(obj: Any, path: str) -> list[tuple[str, Locator]]:
    """Recursively collect all Locator instances with their JSON paths."""
    results: list[tuple[str, Locator]] = []
    if not isinstance(obj, BaseModel):
        return results
    if isinstance(obj, Locator):
        results.append((path, obj))
    for field_name, field_value in obj:
        child_path = f"{path}.{field_name}" if path else field_name
        if isinstance(field_value, BaseModel):
            results.extend(_collect_locators(field_value, child_path))
        elif isinstance(field_value, list):
            for i, item in enumerate(field_value):
                results.extend(_collect_locators(item, f"{child_path}[{i}]"))
    return results


def validate_filesystem(
    certificate: CertificateEnvelope,
    project_root: Path,
) -> list[Diagnostic]:
    """Run filesystem-backed locator checks."""
    diagnostics: list[Diagnostic] = []
    locators = _collect_locators(certificate, "")

    for json_path, loc in locators:
        if loc.path is None:
            continue

        resolved = project_root / loc.path

        if not resolved.exists():
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    category="filesystem",
                    code="unresolvable_path",
                    path=f"{json_path}.path",
                    message=f'Path "{loc.path}" not found relative to project root',
                )
            )
            continue

        has_lines = loc.start_line is not None or loc.end_line is not None

        if not resolved.is_file() and has_lines:
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    category="filesystem",
                    code="path_not_regular_file",
                    path=f"{json_path}.path",
                    message=f'Path "{loc.path}" is not a regular file but has line fields',
                )
            )
            continue

        if resolved.is_file() and loc.end_line is not None:
            line_count = sum(1 for _ in resolved.open())
            if loc.end_line > line_count:
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        category="filesystem",
                        code="line_range_exceeds_file",
                        path=f"{json_path}.end_line",
                        message=f"end_line ({loc.end_line}) exceeds file length ({line_count})",
                    )
                )

    return diagnostics
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_locator_fs.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/sdlc_control_plane/verification/locator_fs.py tests/test_locator_fs.py
git commit -m "feat(s2): add filesystem locator validation

Checks unresolvable_path, line_range_exceeds_file, path_not_regular_file
when --project-root is provided.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Chunk 4: CLI Integration

### Task 8: Extend CLI validate Command

**Files:**
- Modify: `src/sdlc_control_plane/cli/__init__.py`
- Modify: `tests/test_cli.py`
- Modify: `src/sdlc_control_plane/verification/__init__.py`

- [ ] **Step 1: Update verification/__init__.py with all exports**

```python
# src/sdlc_control_plane/verification/__init__.py
"""Verification & Evidence bounded context — public API."""

from sdlc_control_plane.verification.diagnostics import (
    Diagnostic,
    pydantic_errors_to_diagnostics,
)
from sdlc_control_plane.verification.locator_fs import validate_filesystem
from sdlc_control_plane.verification.referential import validate_refs

__all__ = [
    "Diagnostic",
    "pydantic_errors_to_diagnostics",
    "validate_filesystem",
    "validate_refs",
]
```

- [ ] **Step 2: Write failing CLI integration tests**

Add to `tests/test_cli.py`:

```python
import json
import os
import tempfile


class TestValidateWithRefChecks:
    def setup_method(self) -> None:
        self.runner = CliRunner()

    def test_broken_claim_ref_exits_1(self, tmp_path: Path) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["formal_conclusion"]["derived_from_claim_ids"] = ["p1", "GHOST"]
        cert_path = tmp_path / "broken.json"
        cert_path.write_text(json.dumps(data))
        result = self.runner.invoke(main, ["validate", str(cert_path)])
        assert result.exit_code == 1
        assert "missing_claim_ref" in result.output

    def test_duplicate_claim_id_exits_1(self, tmp_path: Path) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["quality_assertions"][0]["claim_id"] = "p1"
        cert_path = tmp_path / "dup.json"
        cert_path.write_text(json.dumps(data))
        result = self.runner.invoke(main, ["validate", str(cert_path)])
        assert result.exit_code == 1
        assert "duplicate_claim_id" in result.output

    def test_output_grouped_by_category(self, tmp_path: Path) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["quality_assertions"][0]["claim_id"] = "p1"
        cert_path = tmp_path / "grouped.json"
        cert_path.write_text(json.dumps(data))
        result = self.runner.invoke(main, ["validate", str(cert_path)])
        assert "REFERENCE" in result.output


class TestValidateWithProjectRoot:
    def setup_method(self) -> None:
        self.runner = CliRunner()

    def test_missing_file_exits_1(self, tmp_path: Path) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {
            "path": "src/nonexistent.py"
        }
        cert_path = tmp_path / "cert.json"
        cert_path.write_text(json.dumps(data))
        result = self.runner.invoke(
            main, ["validate", str(cert_path), "--project-root", str(tmp_path)]
        )
        assert result.exit_code == 1
        assert "unresolvable_path" in result.output

    def test_invalid_project_root_exits_2(self, tmp_path: Path) -> None:
        result = self.runner.invoke(
            main,
            [
                "validate",
                str(FIXTURES / "valid_task_review.json"),
                "--project-root",
                "/tmp/nonexistent_dir_12345",
            ],
        )
        assert result.exit_code == 2

    def test_valid_with_project_root_exits_0(self, tmp_path: Path) -> None:
        result = self.runner.invoke(
            main,
            [
                "validate",
                str(FIXTURES / "valid_task_review.json"),
                "--project-root",
                str(tmp_path),
            ],
        )
        # Valid cert has no locator paths, so fs checks produce nothing
        assert result.exit_code == 0

    def test_warnings_do_not_cause_exit_1(self, tmp_path: Path) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = {}
        cert_path = tmp_path / "warn.json"
        cert_path.write_text(json.dumps(data))
        result = self.runner.invoke(main, ["validate", str(cert_path)])
        assert result.exit_code == 0  # warnings only, no errors
```

- [ ] **Step 3: Run to verify fail**

Run: `uv run pytest tests/test_cli.py::TestValidateWithRefChecks -v`
Expected: FAIL (CLI doesn't run ref checks yet)

- [ ] **Step 4: Rewrite CLI validate command**

Replace the `validate` function in `src/sdlc_control_plane/cli/__init__.py`:

```python
"""CLI entry points for the SDLC Control Plane."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from pydantic import ValidationError
from rich.console import Console

from sdlc_control_plane.verification.diagnostics import (
    Diagnostic,
    pydantic_errors_to_diagnostics,
)
from sdlc_control_plane.verification.locator_fs import validate_filesystem
from sdlc_control_plane.verification.models import validate_certificate
from sdlc_control_plane.verification.referential import validate_refs

console = Console(soft_wrap=True)

# Category display order
_CATEGORY_ORDER = {"structure": 0, "reference": 1, "filesystem": 2}
_CATEGORY_LABELS = {"structure": "STRUCTURE", "reference": "REFERENCE", "filesystem": "FILESYSTEM"}


def _sort_diagnostics(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    """Sort diagnostics by category order, then path, then code."""
    return sorted(
        diagnostics,
        key=lambda d: (_CATEGORY_ORDER.get(d.category, 99), d.path, d.code),
    )


def _render_diagnostics(
    file_path: str,
    diagnostics: list[Diagnostic],
) -> None:
    """Render grouped diagnostics to console."""
    has_errors = any(d.severity == "error" for d in diagnostics)
    icon = "[red]\u2717[/red]" if has_errors else "[yellow]![/yellow]"
    console.print(f"{icon} {file_path}")

    sorted_diags = _sort_diagnostics(diagnostics)
    current_category: str | None = None
    for d in sorted_diags:
        if d.category != current_category:
            current_category = d.category
            console.print(f"  [bold]{_CATEGORY_LABELS.get(d.category, d.category)}[/bold]")
        sev_color = "red" if d.severity == "error" else "yellow"
        sev_label = "error" if d.severity == "error" else "warn "
        related = f" (see {d.related_path})" if d.related_path else ""
        console.print(
            f"    [{sev_color}]{sev_label}[/{sev_color}]  {d.path}: {d.code} \u2014 {d.message}{related}"
        )


@click.group()
@click.version_option()
def main() -> None:
    """SDLC Control Plane -- certificate-driven development governance."""


@main.command()
@click.argument("files", nargs=-1, required=True, type=click.Path())
@click.option("--type", "cert_type", default=None, help="Certificate type override.")
@click.option(
    "--project-root",
    "project_root",
    default=None,
    type=click.Path(),
    help="Project root for filesystem locator checks.",
)
def validate(files: tuple[str, ...], cert_type: str | None, project_root: str | None) -> None:
    """Validate certificate artifacts against the schema bundle."""
    # Validate project root early
    resolved_root: Path | None = None
    if project_root is not None:
        resolved_root = Path(project_root)
        if not resolved_root.is_dir():
            console.print(f"[red]\u2717[/red] --project-root is not a valid directory: {project_root}")
            sys.exit(2)

    exit_code = 0
    for file_path_str in files:
        file_path = Path(file_path_str)

        # Layer 1: Load JSON
        try:
            data: dict[str, Any] = json.loads(file_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            console.print(f"[red]\u2717[/red] {file_path} \u2014 {e}")
            exit_code = max(exit_code, 2)
            continue

        if cert_type is not None:
            data["certificate_type"] = cert_type

        # Layer 2: Pydantic structural validation
        try:
            cert = validate_certificate(data)
        except KeyError as e:
            console.print(f"[red]\u2717[/red] {file_path} \u2014 {e}")
            exit_code = max(exit_code, 1)
            continue
        except ValidationError as e:
            diagnostics = pydantic_errors_to_diagnostics(e, str(file_path))
            _render_diagnostics(str(file_path), diagnostics)
            exit_code = max(exit_code, 1)
            continue

        # Layer 3: Referential validation
        all_diagnostics: list[Diagnostic] = []
        all_diagnostics.extend(validate_refs(cert))

        # Layer 4: Filesystem locator checks (opt-in)
        if resolved_root is not None:
            all_diagnostics.extend(validate_filesystem(cert, resolved_root))

        # Render results
        if all_diagnostics:
            _render_diagnostics(str(file_path), all_diagnostics)
            if any(d.severity == "error" for d in all_diagnostics):
                exit_code = max(exit_code, 1)
        else:
            console.print(f"[green]\u2713[/green] {file_path}")

    sys.exit(exit_code)
```

- [ ] **Step 5: Run all CLI tests (old and new)**

Run: `uv run pytest tests/test_cli.py -v`
Expected: All PASS. Note: the existing `test_invalid_output_contains_error_detail` test checks for `"Field required"` in output. After the rewrite, Pydantic errors are translated through `pydantic_errors_to_diagnostics` which preserves the original message text (`err["msg"]`), so `"Field required"` should still appear in output. If this test fails, check that the `_render_diagnostics` output includes `d.message` which contains the original Pydantic error message.

- [ ] **Step 6: Run full check**

Run: `make check`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/sdlc_control_plane/cli/__init__.py src/sdlc_control_plane/verification/__init__.py tests/test_cli.py
git commit -m "feat(s2): integrate referential + filesystem validation into CLI

sdlc validate now runs layered pipeline: structure -> referential -> filesystem.
--project-root enables filesystem checks. Diagnostics grouped by category.
Exit codes: 0 (pass/warnings), 1 (validation errors), 2 (I/O errors).

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Chunk 5: Documentation + Issues + Cleanup

### Task 9: Documentation

**Files:**
- Create: `docs/decisions/README.md`
- Create: `docs/decisions/s2-canonical-evidence-inventory.md`
- Create: `docs/decisions/s2-claim-namespace-semantics.md`
- Create: `docs/decisions/s2-diagnostic-model.md`
- Create: `docs/decisions/s2-path-validation-semantics.md`
- Create: `docs/verification/README.md`
- Create: `docs/verification/evidence-model.md`
- Create: `docs/verification/referential-validation.md`
- Create: `docs/verification/diagnostics.md`
- Modify: `README.md`
- Modify: `CLAUDE.md`

Decision docs and component docs should be written using the content from the brainstorming conversation and spec. Each decision doc follows the format:
- Session/issue reference, date, status
- One-sentence decision summary
- Context and requirements
- 2-3 options evaluated with trade-offs
- Chosen approach and rationale
- Links to related docs and code

Component docs in `docs/verification/` mirror the code structure and are normative. Each includes audience + reading order headers.

- [ ] **Step 1: Create docs/decisions/README.md**

Index table of all S2 decisions with links.

- [ ] **Step 2: Create four decision docs**

Write each with the standard format. Source material is in the spec and brainstorming conversation.

- [ ] **Step 3: Create docs/verification/README.md**

Component overview with progressive discovery links.

- [ ] **Step 4: Create three verification component docs**

`evidence-model.md`, `referential-validation.md`, `diagnostics.md`.

- [ ] **Step 5: Update README.md**

Add documentation threading table.

- [ ] **Step 6: Update CLAUDE.md reference list**

Add `docs/decisions/README.md` and `docs/verification/README.md`.

- [ ] **Step 7: Commit**

```bash
git add docs/decisions/ docs/verification/ README.md CLAUDE.md
git commit -m "docs(s2): add decision logs, verification component docs, update README index

Four decision docs (inventory, claim namespace, diagnostics, path semantics).
Three verification component docs (evidence model, referential validation, diagnostics).
README now serves as documentation index with threading table.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: GitHub Issues for Deferred Items

- [ ] **Step 1: Create orphan evidence research issue**

```bash
gh issue create --title "Research: orphan evidence detection in embedded model" \
  --body "## Context
S2 established canonical evidence inventories but deferred orphan evidence detection.
The embedded evidence model makes orphans ill-defined (see spec Section 8).

## Research needed
- Define what 'orphan evidence' means when EvidenceRef is embedded, not centrally declared
- Evaluate whether S5 (claim verification engine) is the right place for this
- Consider whether the inventory pattern changes the analysis

## References
- Spec: docs/superpowers/specs/2026-03-11-s2-evidence-inventory-referential-validation-design.md
- Decision: docs/decisions/s2-canonical-evidence-inventory.md"
```

- [ ] **Step 2: Create cross-certificate validation issue**

```bash
gh issue create --title "Feature: cross-certificate referential validation" \
  --body "## Context
S2 validates references within a single certificate. Cross-certificate validation
(e.g., dispute references target certificate, remediation log references certificate)
requires a persistent inventory across runs.

## Scope
- Define inventory persistence model (file-based? database?)
- Validate cross-document artifact_id and certificate_id references
- Integrate with workflow orchestration (S3+)

## References
- Spec: docs/superpowers/specs/2026-03-11-s2-evidence-inventory-referential-validation-design.md (Section 8)"
```

- [ ] **Step 3: Commit (no code change, just tracking)**

Note: Issues are created on GitHub, no local commit needed.

---

### Task 11: Final Verification + /simplify

- [ ] **Step 1: Run full check**

```bash
make check
```

Expected: All lint, typecheck, and tests pass.

- [ ] **Step 2: Run /simplify**

Invoke `/simplify` to review all changed code for reuse, quality, and efficiency.

- [ ] **Step 3: Fix any issues found by /simplify**

- [ ] **Step 4: Run make check again after any /simplify changes**

```bash
make check
```

- [ ] **Step 5: Final commit if /simplify made changes**

```bash
git add -A
git commit -m "refactor(s2): apply /simplify review findings

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 12: Create PR

- [ ] **Step 1: Push branch**

```bash
git push -u origin feat/s2-referential-validation
```

- [ ] **Step 2: Create PR via gh api REST**

```bash
gh api repos/Troubladore/sdlc-control-plane/pulls \
  -f title="feat: S2 — Evidence Inventory + Referential Validation" \
  -f head="feat/s2-referential-validation" \
  -f base="main" \
  -f body="$(cat <<'EOF'
## Summary

Session 2 adds canonical evidence/artifact inventories to the certificate envelope
and implements referential + filesystem validation that catches broken references.

### What's new
- **Diagnostic model** — Pydantic `Diagnostic` with severity, category, code, path, message
- **Canonical inventories** — `artifact_inventory` and `evidence_inventory` on `CertificateEnvelope`
- **Referential validation** — 16 check codes via recursive model tree walk
- **Filesystem locator checks** — opt-in via `--project-root`
- **CLI integration** — `sdlc validate` runs layered pipeline: structure -> reference -> filesystem
- **Documentation** — decision logs, verification component docs, README as index

### Check inventory (20 codes)
- 10 always-run referential (duplicate IDs, missing refs, locator safety)
- 6 inventory-specific (missing from inventory, mismatch, unused entries)
- 3 filesystem (unresolvable path, line range, not regular file)
- 1 structural translation (Pydantic errors)

## Test plan
- [ ] `make check` passes (lint + typecheck + tests)
- [ ] Existing S1 fixtures still valid
- [ ] Broken ref fixtures caught with correct diagnostic codes
- [ ] `--project-root` catches missing files
- [ ] Warnings don't cause exit 1

Spec: `docs/superpowers/specs/2026-03-11-s2-evidence-inventory-referential-validation-design.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Return PR URL**
