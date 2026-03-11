"""Tests for verification models matching the JSON Schema bundle."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sdlc_control_plane.verification.models import (
    Actor,
    ActorRole,
    ArtifactRef,
    ArtifactType,
    AuthorKind,
    CertificateType,
    CommandVerification,
    CommandVerificationStatus,
    EvidenceRef,
    EvidenceType,
    ExecutorType,
    FormalConclusion,
    FormalConclusionStatus,
    GateEvaluation,
    GateStatus,
    Id,
    IssueFinding,
    IssueFindingStatus,
    Locator,
    NonEmptyString,
    PremiseClaim,
    PremiseStatus,
    QualityAssertion,
    QualityAssertionStatus,
    Severity,
    ValidationStatus,
    VerificationMethod,
    VerificationRecord,
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


class TestActor:
    def test_valid_actor(self) -> None:
        a = Actor(actor_id="claude-1", author_kind="claude", role="reviewer_a")
        assert a.actor_id == "claude-1"

    def test_actor_rejects_extra_field(self) -> None:
        with pytest.raises(ValidationError):
            Actor(actor_id="a", author_kind="claude", role="reviewer_a", bogus="x")

    def test_actor_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            Actor(actor_id="a", author_kind="claude")  # type: ignore[call-arg]


class TestLocator:
    def test_empty_locator(self) -> None:
        loc = Locator()
        assert loc.path is None

    def test_locator_with_fields(self) -> None:
        loc = Locator(path="src/foo.py", start_line=1, end_line=10)
        assert loc.start_line == 1


class TestArtifactRef:
    def test_valid(self) -> None:
        ref = ArtifactRef(artifact_id="art-1", artifact_type="file")
        assert ref.artifact_type == ArtifactType.FILE

    def test_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            ArtifactRef(artifact_id="art-1")  # type: ignore[call-arg]


class TestEvidenceRef:
    def test_valid(self) -> None:
        ref = EvidenceRef(
            evidence_id="ev-1",
            evidence_type="file_span",
            artifact_ref=ArtifactRef(artifact_id="art-1", artifact_type="file"),
        )
        assert ref.evidence_type == EvidenceType.FILE_SPAN


class TestVerificationRecord:
    def test_valid(self) -> None:
        vr = VerificationRecord(
            status="verified",
            method="source_read",
            verified_by=Actor(actor_id="c1", author_kind="claude", role="reviewer_a"),
            verified_at="2026-03-11T00:00:00Z",
        )
        assert vr.status == VerifiedStatus.VERIFIED


def _make_evidence_ref() -> EvidenceRef:
    return EvidenceRef(
        evidence_id="ev-1",
        evidence_type="file_span",
        artifact_ref=ArtifactRef(artifact_id="art-1", artifact_type="file"),
    )


class TestPremiseClaim:
    def test_valid(self) -> None:
        pc = PremiseClaim(
            claim_id="p1",
            text="All tests pass",
            evidence_refs=[_make_evidence_ref()],
            status="satisfied",
        )
        assert pc.status == PremiseStatus.SATISFIED

    def test_empty_evidence_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PremiseClaim(
                claim_id="p1",
                text="x",
                evidence_refs=[],
                status="satisfied",
            )

    def test_rejects_extra_field(self) -> None:
        with pytest.raises(ValidationError):
            PremiseClaim(
                claim_id="p1",
                text="x",
                evidence_refs=[_make_evidence_ref()],
                status="satisfied",
                bogus="y",
            )


class TestQualityAssertion:
    def test_valid(self) -> None:
        qa = QualityAssertion(
            claim_id="q1",
            text="Code is type-safe",
            evidence_refs=[_make_evidence_ref()],
            status="verified",
        )
        assert qa.status == QualityAssertionStatus.VERIFIED


class TestIssueFinding:
    def test_valid_minimal(self) -> None:
        f = IssueFinding(issue_id="i1", description="Bug found", severity="minor")
        assert f.severity == Severity.MINOR

    def test_valid_with_optional_status(self) -> None:
        f = IssueFinding(
            issue_id="i1",
            description="Bug",
            severity="critical",
            status="open",
        )
        assert f.status == IssueFindingStatus.OPEN


class TestCommandVerification:
    def test_valid(self) -> None:
        cv = CommandVerification(
            command_id="cmd-1",
            command="pytest",
            exit_code=0,
            status="passed",
        )
        assert cv.status == CommandVerificationStatus.PASSED

    def test_with_optional_singular_evidence_ref(self) -> None:
        cv = CommandVerification(
            command_id="cmd-1",
            command="pytest",
            exit_code=0,
            status="passed",
            evidence_ref=_make_evidence_ref(),
        )
        assert cv.evidence_ref is not None


class TestFormalConclusion:
    def test_valid(self) -> None:
        fc = FormalConclusion(
            status="complete",
            derived_from_claim_ids=["p1", "q1"],
        )
        assert fc.status == FormalConclusionStatus.COMPLETE

    def test_empty_derived_from_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FormalConclusion(status="complete", derived_from_claim_ids=[])


class TestGateEvaluation:
    def test_valid(self) -> None:
        ge = GateEvaluation(
            gate_id="g1",
            requirement="Tests pass",
            status="passed",
        )
        assert ge.status == GateStatus.PASSED
