"""Tests for verification models matching the JSON Schema bundle."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sdlc_control_plane.verification.models import (
    ActorRole,
    ArtifactType,
    AuthorKind,
    CertificateType,
    CommandVerificationStatus,
    EvidenceType,
    ExecutorType,
    GateStatus,
    Id,
    IssueFindingStatus,
    NonEmptyString,
    Severity,
    ValidationStatus,
    VerificationMethod,
    VerifiedStatus,
    WorkflowState,
)


class TestConstrainedTypes:
    def test_non_empty_string_rejects_empty(self) -> None:
        from pydantic import TypeAdapter

        ta = TypeAdapter(NonEmptyString)
        with pytest.raises(ValidationError):
            ta.validate_python("")

    def test_non_empty_string_accepts_value(self) -> None:
        from pydantic import TypeAdapter

        ta = TypeAdapter(NonEmptyString)
        assert ta.validate_python("hello") == "hello"

    def test_id_rejects_spaces(self) -> None:
        from pydantic import TypeAdapter

        ta = TypeAdapter(Id)
        with pytest.raises(ValidationError):
            ta.validate_python("has space")

    def test_id_accepts_valid(self) -> None:
        from pydantic import TypeAdapter

        ta = TypeAdapter(Id)
        assert ta.validate_python("cert-001.v2:latest") == "cert-001.v2:latest"


class TestEnums:
    def test_severity_values(self) -> None:
        assert set(Severity) == {"critical", "important", "minor", "info"}

    def test_author_kind_values(self) -> None:
        assert set(AuthorKind) == {"claude", "codex", "gemini", "human", "tool", "system"}

    def test_workflow_state_values(self) -> None:
        expected = {
            "pending",
            "triage",
            "design",
            "planning",
            "implementing",
            "simplify",
            "self_review",
            "certificate_review",
            "issues",
            "certified",
            "integration",
            "complete",
        }
        assert set(WorkflowState) == expected

    def test_artifact_type_values(self) -> None:
        assert len(ArtifactType) == 21

    def test_evidence_type_values(self) -> None:
        assert len(EvidenceType) == 16

    def test_verification_method_values(self) -> None:
        assert len(VerificationMethod) == 9

    def test_verified_status_values(self) -> None:
        assert set(VerifiedStatus) == {"verified", "failed", "not_checked", "inconclusive"}

    def test_executor_type_values(self) -> None:
        assert set(ExecutorType) == {"static", "tool", "llm", "human"}

    def test_certificate_type_values(self) -> None:
        assert set(CertificateType) == {
            "task_review",
            "design_decision",
            "deferred_scope",
            "impact_alignment",
        }

    def test_validation_status_values(self) -> None:
        assert set(ValidationStatus) == {
            "draft",
            "validated",
            "deficient",
            "clean",
            "superseded",
        }

    def test_actor_role_values(self) -> None:
        expected = {
            "implementer",
            "reviewer_a",
            "reviewer_b",
            "finder",
            "validator",
            "arbiter",
            "maintainer",
            "system",
        }
        assert set(ActorRole) == expected

    def test_invalid_enum_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            Severity("nonexistent")

    def test_issue_finding_status_values(self) -> None:
        assert set(IssueFindingStatus) == {
            "open",
            "accepted",
            "remediated",
            "withdrawn",
            "escalated",
        }

    def test_command_verification_status_values(self) -> None:
        assert set(CommandVerificationStatus) == {"passed", "failed", "not_run"}

    def test_gate_status_values(self) -> None:
        assert set(GateStatus) == {"passed", "failed", "waived", "not_evaluated"}
