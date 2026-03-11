"""Tests for Diagnostic model and Pydantic error translation utilities."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sdlc_control_plane.verification.diagnostics import (
    Diagnostic,
    pydantic_errors_to_diagnostics,
)
from sdlc_control_plane.verification.models import TaskReviewCertificate


class TestDiagnosticModel:
    def test_create_error_diagnostic(self) -> None:
        d = Diagnostic(
            severity="error",
            category="structure",
            code="missing_field",
            path="premises[0].claim_id",
            message="Field required",
        )
        assert d.severity == "error"
        assert d.category == "structure"
        assert d.code == "missing_field"
        assert d.path == "premises[0].claim_id"
        assert d.message == "Field required"
        assert d.related_path is None

    def test_create_warning_diagnostic(self) -> None:
        d = Diagnostic(
            severity="warning",
            category="reference",
            code="broken_ref",
            path="evidence_refs[0].artifact_ref",
            message="Referenced artifact not found in inventory",
        )
        assert d.severity == "warning"
        assert d.category == "reference"

    def test_related_path_defaults_to_none(self) -> None:
        d = Diagnostic(
            severity="error",
            category="filesystem",
            code="file_not_found",
            path="source_artifacts[0].uri",
            message="File does not exist",
        )
        assert d.related_path is None

    def test_related_path_can_be_set_explicitly(self) -> None:
        d = Diagnostic(
            severity="warning",
            category="reference",
            code="cross_ref",
            path="premises[0].evidence_refs[0].artifact_ref.artifact_id",
            message="Artifact ID referenced but not declared",
            related_path="source_artifacts[2].artifact_id",
        )
        assert d.related_path == "source_artifacts[2].artifact_id"

    def test_model_is_frozen_raises_on_assignment(self) -> None:
        d = Diagnostic(
            severity="error",
            category="structure",
            code="err",
            path="x",
            message="msg",
        )
        with pytest.raises(ValidationError):
            d.severity = "warning"  # type: ignore[misc]

    def test_rejects_invalid_severity(self) -> None:
        with pytest.raises(ValidationError):
            Diagnostic(
                severity="critical",  # type: ignore[arg-type]
                category="structure",
                code="err",
                path="x",
                message="msg",
            )

    def test_rejects_invalid_category(self) -> None:
        with pytest.raises(ValidationError):
            Diagnostic(
                severity="error",
                category="semantic",  # type: ignore[arg-type]
                code="err",
                path="x",
                message="msg",
            )

    def test_json_serializable_via_model_dump(self) -> None:
        import json

        d = Diagnostic(
            severity="warning",
            category="filesystem",
            code="missing_file",
            path="source_artifacts[0].uri",
            message="File not on disk",
            related_path="some/other/path",
        )
        data = d.model_dump()
        # Should be serialisable to JSON without error
        serialised = json.dumps(data)
        parsed = json.loads(serialised)
        assert parsed["severity"] == "warning"
        assert parsed["category"] == "filesystem"
        assert parsed["related_path"] == "some/other/path"


class TestPydanticErrorsToDiagnostics:
    def _make_validation_error(self) -> ValidationError:
        """Trigger a ValidationError from TaskReviewCertificate with missing fields."""
        with pytest.raises(ValidationError) as exc_info:
            TaskReviewCertificate.model_validate({})
        return exc_info.value

    def test_translates_missing_field_errors(self) -> None:
        error = self._make_validation_error()
        diagnostics = pydantic_errors_to_diagnostics(error)
        assert len(diagnostics) > 0

    def test_all_diagnostics_have_correct_severity_category_code(self) -> None:
        error = self._make_validation_error()
        diagnostics = pydantic_errors_to_diagnostics(error)
        for d in diagnostics:
            assert d.severity == "error"
            assert d.category == "structure"
            assert d.code == "pydantic_validation_error"

    def test_message_contains_pydantic_error_text(self) -> None:
        error = self._make_validation_error()
        diagnostics = pydantic_errors_to_diagnostics(error)
        # At least one diagnostic should contain "Field required"
        messages = [d.message for d in diagnostics]
        assert any("Field required" in m for m in messages)

    def test_nested_errors_produce_dot_bracket_paths(self) -> None:
        """Nested errors must use dot/bracket style, not ' -> ' separators."""
        # Build a payload that triggers nested validation errors
        # premises[0] requires fields; force a nested error by providing
        # a partial premises entry missing required sub-fields
        payload: dict = {
            "schema_version": "1.0",
            "certificate_id": "cert-001",
            "certificate_type": "task_review",
            "workflow_run_id": "run-001",
            "issue_ref": {
                "artifact_id": "issue-001",
                "artifact_type": "issue",
            },
            "produced_by": {
                "actor_id": "claude-1",
                "author_kind": "claude",
                "role": "implementer",
            },
            "produced_at": "2026-01-01T00:00:00Z",
            "source_artifacts": [
                {"artifact_id": "art-001", "artifact_type": "file"}
            ],
            "validation_status": "draft",
            "definition": "Test certificate",
            "premises": [
                {
                    "claim_id": "p-001",
                    "text": "Some premise",
                    "status": "satisfied",
                    # evidence_refs missing -> nested validation error
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-001",
                            "evidence_type": "file_span",
                            # artifact_ref missing required fields
                            "artifact_ref": {
                                # artifact_id missing
                                "artifact_type": "file",
                            },
                        }
                    ],
                }
            ],
            "quality_assertions": [
                {
                    "claim_id": "qa-001",
                    "text": "Quality assertion",
                    "status": "verified",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-002",
                            "evidence_type": "test_result",
                            "artifact_ref": {
                                "artifact_id": "art-002",
                                "artifact_type": "junit_xml",
                            },
                        }
                    ],
                }
            ],
            "verification_commands": [
                {
                    "command_id": "cmd-001",
                    "command": "make check",
                    "exit_code": 0,
                    "status": "passed",
                }
            ],
            "formal_conclusion": {
                "status": "complete",
                "derived_from_claim_ids": ["p-001"],
            },
            "issues": [],
        }

        with pytest.raises(ValidationError) as exc_info:
            TaskReviewCertificate.model_validate(payload)

        diagnostics = pydantic_errors_to_diagnostics(exc_info.value)
        paths = [d.path for d in diagnostics]

        # There must be no " -> " separators in any path
        for path in paths:
            assert " -> " not in path, f"Path uses ' -> ' separator: {path!r}"

        # At least one path should use dot or bracket notation for nesting
        nested_paths = [p for p in paths if "." in p or "[" in p]
        assert len(nested_paths) > 0, (
            f"Expected at least one nested dot/bracket path, got: {paths}"
        )

        # Specifically, the path for the missing artifact_id should be
        # premises[0].evidence_refs[0].artifact_ref.artifact_id
        assert any(
            "premises[0]" in p for p in paths
        ), f"Expected 'premises[0]' in paths, got: {paths}"
