"""Tests for referential validation — all 16 check codes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from sdlc_control_plane.verification.models import (
    validate_certificate,
)
from sdlc_control_plane.verification.referential import validate_refs

if TYPE_CHECKING:
    from sdlc_control_plane.verification.diagnostics import Diagnostic
    from sdlc_control_plane.verification.models import CertificateEnvelope

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())  # type: ignore[no-any-return]


def _parse(data: dict[str, Any]) -> CertificateEnvelope:
    return validate_certificate(data)


def _codes(diags: list[Diagnostic]) -> list[str]:
    return [d.code for d in diags]


def _errors(diags: list[Diagnostic]) -> list[Diagnostic]:
    return [d for d in diags if d.severity == "error"]


def _warnings(diags: list[Diagnostic]) -> list[Diagnostic]:
    return [d for d in diags if d.severity == "warning"]


# ---------------------------------------------------------------------------
# Helpers for building inventory-enabled certificates
# ---------------------------------------------------------------------------


def _make_task_review_with_inventory() -> dict[str, Any]:
    """Build a valid task_review with artifact_inventory and evidence_inventory."""
    return {
        "schema_version": "1.0.0",
        "certificate_id": "cert-inv-001",
        "certificate_type": "task_review",
        "workflow_run_id": "run-001",
        "issue_ref": {"artifact_id": "issue-42", "artifact_type": "issue"},
        "produced_by": {
            "actor_id": "claude-1",
            "author_kind": "claude",
            "role": "reviewer_a",
        },
        "produced_at": "2026-03-11T00:00:00Z",
        "source_artifacts": [{"artifact_id": "src-1", "artifact_type": "file"}],
        "validation_status": "validated",
        "artifact_inventory": [
            {
                "artifact_id": "art-1",
                "artifact_type": "command_output",
                "description": "pytest output",
            },
            {
                "artifact_id": "art-2",
                "artifact_type": "command_output",
                "description": "mypy output",
            },
        ],
        "evidence_inventory": [
            {
                "evidence_id": "ev-1",
                "evidence_type": "test_result",
                "artifact_ref": {
                    "artifact_id": "art-1",
                    "artifact_type": "command_output",
                },
            },
            {
                "evidence_id": "ev-2",
                "evidence_type": "typecheck_result",
                "artifact_ref": {
                    "artifact_id": "art-2",
                    "artifact_type": "command_output",
                },
            },
        ],
        "definition": "Task is COMPLETE iff all spec requirements are satisfied.",
        "premises": [
            {
                "claim_id": "p1",
                "text": "All tests pass",
                "evidence_refs": [
                    {
                        "evidence_id": "ev-1",
                        "evidence_type": "test_result",
                        "artifact_ref": {
                            "artifact_id": "art-1",
                            "artifact_type": "command_output",
                        },
                    }
                ],
                "status": "satisfied",
            }
        ],
        "quality_assertions": [
            {
                "claim_id": "q1",
                "text": "Code is type-safe",
                "evidence_refs": [
                    {
                        "evidence_id": "ev-2",
                        "evidence_type": "typecheck_result",
                        "artifact_ref": {
                            "artifact_id": "art-2",
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


# =========================================================================
# Valid fixtures produce no errors
# =========================================================================


class TestValidCertificatePassesRefChecks:
    @pytest.mark.parametrize(
        "fixture",
        [
            "valid_task_review.json",
            "valid_design_decision.json",
            "valid_deferred_scope.json",
            "valid_impact_alignment.json",
        ],
    )
    def test_no_errors(self, fixture: str) -> None:
        cert = _parse(_load(fixture))
        diags = validate_refs(cert)
        errors = _errors(diags)
        assert errors == [], f"Unexpected errors: {errors}"


# =========================================================================
# duplicate_claim_id
# =========================================================================


class TestDuplicateClaimId:
    def test_duplicate_claim_id_detected(self) -> None:
        data = _load("valid_task_review.json")
        # Set quality_assertions[0].claim_id to same as premises[0].claim_id
        data["quality_assertions"][0]["claim_id"] = "p1"
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "duplicate_claim_id" in codes


# =========================================================================
# duplicate_evidence_id
# =========================================================================


class TestDuplicateEvidenceId:
    def test_duplicate_evidence_id_detected(self) -> None:
        data = _load("valid_task_review.json")
        # Set quality_assertions[0].evidence_refs[0].evidence_id to "ev-1"
        data["quality_assertions"][0]["evidence_refs"][0]["evidence_id"] = "ev-1"
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "duplicate_evidence_id" in codes


# =========================================================================
# duplicate_artifact_id
# =========================================================================


class TestDuplicateArtifactId:
    def test_duplicate_artifact_id_detected(self) -> None:
        data = _load("valid_task_review.json")
        # Set quality_assertions[0].evidence_refs[0].artifact_ref.artifact_id to "art-1"
        data["quality_assertions"][0]["evidence_refs"][0]["artifact_ref"][
            "artifact_id"
        ] = "art-1"
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "duplicate_artifact_id" in codes


# =========================================================================
# missing_claim_ref
# =========================================================================


class TestMissingClaimRef:
    def test_missing_claim_ref_detected(self) -> None:
        data = _load("valid_task_review.json")
        data["formal_conclusion"]["derived_from_claim_ids"].append("NONEXISTENT")
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "missing_claim_ref" in codes


# =========================================================================
# missing_evidence_in_verification
# =========================================================================


class TestMissingEvidenceInVerification:
    def test_missing_evidence_in_verification_detected(self) -> None:
        data = _load("valid_task_review.json")
        # Add a verification record to premises[0] that references a ghost evidence
        data["premises"][0]["verification"] = {
            "status": "verified",
            "method": "source_read",
            "verified_by": {
                "actor_id": "c1",
                "author_kind": "claude",
                "role": "reviewer_a",
            },
            "verified_at": "2026-03-11T00:00:00Z",
            "evidence_checked": ["ev-1", "GHOST"],
        }
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "missing_evidence_in_verification" in codes


# =========================================================================
# Locator checks
# =========================================================================


class TestLocatorChecks:
    def _make_with_locator(self, locator: dict[str, Any]) -> CertificateEnvelope:
        data = _load("valid_task_review.json")
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["locator"] = locator
        return _parse(data)

    def test_empty_locator(self) -> None:
        cert = self._make_with_locator({})
        diags = validate_refs(cert)
        codes = _codes(_warnings(diags))
        assert "empty_locator" in codes

    def test_note_only_locator(self) -> None:
        cert = self._make_with_locator({"note": "see above"})
        diags = validate_refs(cert)
        codes = _codes(_warnings(diags))
        assert "note_only_locator" in codes

    def test_invalid_line_range(self) -> None:
        cert = self._make_with_locator(
            {"path": "src/foo.py", "start_line": 50, "end_line": 10}
        )
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "invalid_line_range" in codes

    def test_absolute_posix_path(self) -> None:
        cert = self._make_with_locator({"path": "/etc/passwd"})
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "absolute_path_not_allowed" in codes

    def test_absolute_windows_drive(self) -> None:
        cert = self._make_with_locator({"path": "C:\\Users\\foo.py"})
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "absolute_path_not_allowed" in codes

    def test_absolute_windows_unc(self) -> None:
        cert = self._make_with_locator({"path": "\\\\server\\share"})
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "absolute_path_not_allowed" in codes

    def test_path_escapes_project_root(self) -> None:
        cert = self._make_with_locator({"path": "../../etc/passwd"})
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "path_escapes_project_root" in codes

    def test_safe_dotdot_path(self) -> None:
        """A path with internal .. that normalizes safely should NOT error."""
        cert = self._make_with_locator({"path": "src/../lib/foo.py"})
        diags = validate_refs(cert)
        error_codes = _codes(_errors(diags))
        assert "path_escapes_project_root" not in error_codes
        assert "absolute_path_not_allowed" not in error_codes

    def test_valid_relative_path(self) -> None:
        """A clean relative path should produce no locator errors."""
        cert = self._make_with_locator({"path": "src/foo.py"})
        diags = validate_refs(cert)
        locator_codes = [
            d.code
            for d in diags
            if d.code
            in {
                "empty_locator",
                "note_only_locator",
                "invalid_line_range",
                "absolute_path_not_allowed",
                "path_escapes_project_root",
            }
        ]
        assert locator_codes == []


# =========================================================================
# Inventory checks
# =========================================================================


class TestInventoryChecks:
    def test_valid_inventory_no_errors(self) -> None:
        data = _make_task_review_with_inventory()
        cert = _parse(data)
        diags = validate_refs(cert)
        errors = _errors(diags)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_missing_artifact_from_inventory(self) -> None:
        data = _make_task_review_with_inventory()
        # Reference art-99 which is not in inventory
        data["premises"][0]["evidence_refs"][0]["artifact_ref"][
            "artifact_id"
        ] = "art-99"
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "missing_artifact_from_inventory" in codes

    def test_missing_evidence_from_inventory(self) -> None:
        data = _make_task_review_with_inventory()
        # Reference ev-99 which is not in inventory
        data["premises"][0]["evidence_refs"][0]["evidence_id"] = "ev-99"
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "missing_evidence_from_inventory" in codes

    def test_unused_artifact_inventory_entry(self) -> None:
        data = _make_task_review_with_inventory()
        # Add an extra inventory entry that is not referenced
        data["artifact_inventory"].append(
            {
                "artifact_id": "art-unused",
                "artifact_type": "file",
                "description": "unused",
            }
        )
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_warnings(diags))
        assert "unused_artifact_inventory_entry" in codes

    def test_unused_evidence_inventory_entry(self) -> None:
        data = _make_task_review_with_inventory()
        data["evidence_inventory"].append(
            {
                "evidence_id": "ev-unused",
                "evidence_type": "test_result",
                "artifact_ref": {
                    "artifact_id": "art-1",
                    "artifact_type": "command_output",
                },
            }
        )
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_warnings(diags))
        assert "unused_evidence_inventory_entry" in codes

    def test_artifact_definition_mismatch(self) -> None:
        data = _make_task_review_with_inventory()
        # Inline ref has artifact_type "file" but inventory says "command_output"
        data["premises"][0]["evidence_refs"][0]["artifact_ref"]["artifact_type"] = "file"
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "artifact_definition_mismatch" in codes

    def test_evidence_definition_mismatch(self) -> None:
        data = _make_task_review_with_inventory()
        # Inline ref has evidence_type "command_output" but inventory says "test_result"
        data["premises"][0]["evidence_refs"][0]["evidence_type"] = "command_output"
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "evidence_definition_mismatch" in codes

    def test_duplicate_in_inventory_itself(self) -> None:
        data = _make_task_review_with_inventory()
        # Duplicate art-1 in the inventory
        data["artifact_inventory"].append(
            {
                "artifact_id": "art-1",
                "artifact_type": "command_output",
                "description": "duplicate",
            }
        )
        cert = _parse(data)
        diags = validate_refs(cert)
        codes = _codes(_errors(diags))
        assert "duplicate_artifact_id" in codes

    def test_inline_duplicates_allowed_with_inventory(self) -> None:
        """When inventories are present, inline refs may repeat the same ID."""
        data = _make_task_review_with_inventory()
        # Both premises and quality_assertions reference ev-1 with same artifact
        data["quality_assertions"][0]["evidence_refs"][0]["evidence_id"] = "ev-1"
        data["quality_assertions"][0]["evidence_refs"][0][
            "evidence_type"
        ] = "test_result"
        data["quality_assertions"][0]["evidence_refs"][0]["artifact_ref"] = {
            "artifact_id": "art-1",
            "artifact_type": "command_output",
        }
        cert = _parse(data)
        diags = validate_refs(cert)
        error_codes = _codes(_errors(diags))
        assert "duplicate_evidence_id" not in error_codes
        assert "duplicate_artifact_id" not in error_codes
