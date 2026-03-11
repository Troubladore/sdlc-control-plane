"""Tests for verification models matching the JSON Schema bundle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from sdlc_control_plane.verification.models import (
    CERTIFICATE_MODELS,
    Actor,
    ActorRole,
    ArtifactRef,
    ArtifactType,
    AuthorKind,
    CertificateEnvelope,
    CertificateType,
    CommandVerification,
    CommandVerificationStatus,
    DeferredEvaluation,
    DeferredScopeCertificate,
    DeferredScopeConclusion,
    DependencyGraph,
    DesignComparison,
    DesignDecisionCertificate,
    DesignDecisionConclusion,
    DisputeObject,
    DocumentationImpact,
    EvidenceRef,
    EvidenceType,
    ExecutorType,
    FormalConclusion,
    FormalConclusionStatus,
    GateEvaluation,
    GateStatus,
    Id,
    ImpactAlignmentCertificate,
    ImpactAlignmentConclusion,
    IssueFinding,
    IssueFindingStatus,
    IssueImpactAssessment,
    Locator,
    NonEmptyString,
    PremiseClaim,
    PremiseStatus,
    QualityAssertion,
    QualityAssertionStatus,
    RemediationLog,
    RemediationLogEntry,
    RoadmapPosition,
    Severity,
    TaskReviewCertificate,
    TaskReviewConclusion,
    TransitionRequest,
    ValidationStatus,
    VerificationMethod,
    VerificationRecord,
    VerifiedStatus,
    WorkflowEvent,
    WorkflowState,
    validate_certificate,
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


# ---------------------------------------------------------------------------
# Helper models for certificates
# ---------------------------------------------------------------------------


def _make_claim_base_data() -> dict:
    return {
        "claim_id": "c1",
        "text": "Pattern X",
        "evidence_refs": [
            {
                "evidence_id": "ev-1",
                "evidence_type": "file_span",
                "artifact_ref": {"artifact_id": "art-1", "artifact_type": "file"},
            }
        ],
    }


class TestDesignComparison:
    def test_valid(self) -> None:
        dc = DesignComparison(
            our_pattern=_make_claim_base_data(),
            reference_pattern=_make_claim_base_data(),
            match_status="matches",
        )
        assert dc.match_status.value == "matches"

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            DesignComparison(
                our_pattern=_make_claim_base_data(),
                reference_pattern=_make_claim_base_data(),
                match_status="matches",
                bogus="x",
            )

    def test_with_optional_fields(self) -> None:
        dc = DesignComparison(
            our_pattern=_make_claim_base_data(),
            reference_pattern=_make_claim_base_data(),
            match_status="diverges",
            divergence_reason=_make_claim_base_data(),
            reference_source="inspect_ai",
        )
        assert dc.reference_source.value == "inspect_ai"


class TestRoadmapPosition:
    def test_valid(self) -> None:
        rp = RoadmapPosition(
            milestone="v1.0",
            blocked_by=[],
            blocks=[],
        )
        assert rp.milestone == "v1.0"

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            RoadmapPosition(milestone="v1", blocked_by=[], blocks=[], bogus="x")


class TestDeferredEvaluation:
    def test_valid(self) -> None:
        de = DeferredEvaluation(
            tracked=True,
            acceptance_criteria_clear=True,
            roadmap_position_valid=True,
            current_state_consistent=True,
        )
        assert de.tracked is True

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            DeferredEvaluation(
                tracked=True,
                acceptance_criteria_clear=True,
                roadmap_position_valid=True,
                current_state_consistent=True,
                bogus="x",
            )


class TestIssueImpactAssessment:
    def test_valid(self) -> None:
        iia = IssueImpactAssessment(
            issue_ref={"artifact_id": "iss-1", "artifact_type": "issue"},
            impact_status="none",
            action="No action needed",
            verification={
                "status": "verified",
                "method": "source_read",
                "verified_by": {
                    "actor_id": "c1",
                    "author_kind": "claude",
                    "role": "reviewer_a",
                },
                "verified_at": "2026-03-11T00:00:00Z",
            },
        )
        assert iia.impact_status.value == "none"

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            IssueImpactAssessment(
                issue_ref={"artifact_id": "iss-1", "artifact_type": "issue"},
                impact_status="none",
                action="x",
                verification={
                    "status": "verified",
                    "method": "source_read",
                    "verified_by": {
                        "actor_id": "c1",
                        "author_kind": "claude",
                        "role": "reviewer_a",
                    },
                    "verified_at": "2026-03-11T00:00:00Z",
                },
                bogus="x",
            )


class TestDocumentationImpact:
    def test_valid(self) -> None:
        di = DocumentationImpact(
            document_ref={"artifact_id": "doc-1", "artifact_type": "design_doc"},
            status="none",
        )
        assert di.status.value == "none"

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            DocumentationImpact(
                document_ref={"artifact_id": "d1", "artifact_type": "design_doc"},
                status="none",
                bogus="x",
            )


class TestDependencyGraph:
    def test_valid(self) -> None:
        dg = DependencyGraph(
            unblocked_issues=[],
            blocked_by_updates=[],
            new_issues=[],
        )
        assert dg.unblocked_issues == []

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            DependencyGraph(
                unblocked_issues=[],
                blocked_by_updates=[],
                new_issues=[],
                bogus="x",
            )

    def test_optional_post_merge_actions(self) -> None:
        dg = DependencyGraph(
            unblocked_issues=[],
            blocked_by_updates=[],
            new_issues=[],
            post_merge_actions=["Deploy docs"],
        )
        assert dg.post_merge_actions == ["Deploy docs"]


# ---------------------------------------------------------------------------
# Certificate Envelope
# ---------------------------------------------------------------------------


def _make_envelope_data(**overrides: object) -> dict:
    base = {
        "schema_version": "1.0.0",
        "certificate_id": "cert-001",
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
    }
    base.update(overrides)
    return base


class TestCertificateEnvelope:
    def test_valid(self) -> None:
        ce = CertificateEnvelope(**_make_envelope_data())
        assert ce.certificate_id == "cert-001"

    def test_missing_required(self) -> None:
        data = _make_envelope_data()
        del data["certificate_id"]
        with pytest.raises(ValidationError):
            CertificateEnvelope(**data)

    def test_empty_source_artifacts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CertificateEnvelope(**_make_envelope_data(source_artifacts=[]))

    def test_optional_claim_counts(self) -> None:
        ce = CertificateEnvelope(
            **_make_envelope_data(verified_claim_count=3, unverified_claim_count=0)
        )
        assert ce.verified_claim_count == 3

    def test_negative_claim_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CertificateEnvelope(**_make_envelope_data(verified_claim_count=-1))


# ---------------------------------------------------------------------------
# Typed conclusions
# ---------------------------------------------------------------------------


class TestTaskReviewConclusion:
    def test_valid_complete(self) -> None:
        c = TaskReviewConclusion(status="complete", derived_from_claim_ids=["p1"])
        assert c.status == "complete"

    def test_valid_not_complete(self) -> None:
        c = TaskReviewConclusion(status="not_complete", derived_from_claim_ids=["p1"])
        assert c.status == "not_complete"

    def test_rejects_wrong_status(self) -> None:
        with pytest.raises(ValidationError):
            TaskReviewConclusion(status="justified", derived_from_claim_ids=["p1"])


class TestDesignDecisionConclusion:
    def test_valid(self) -> None:
        c = DesignDecisionConclusion(status="justified", derived_from_claim_ids=["c1"])
        assert c.status == "justified"

    def test_rejects_wrong_status(self) -> None:
        with pytest.raises(ValidationError):
            DesignDecisionConclusion(status="complete", derived_from_claim_ids=["c1"])


class TestDeferredScopeConclusion:
    def test_valid(self) -> None:
        c = DeferredScopeConclusion(status="valid", derived_from_claim_ids=["c1"])
        assert c.status == "valid"

    def test_rejects_wrong_status(self) -> None:
        with pytest.raises(ValidationError):
            DeferredScopeConclusion(status="aligned", derived_from_claim_ids=["c1"])


class TestImpactAlignmentConclusion:
    def test_valid(self) -> None:
        c = ImpactAlignmentConclusion(status="aligned", derived_from_claim_ids=["c1"])
        assert c.status == "aligned"

    def test_rejects_wrong_status(self) -> None:
        with pytest.raises(ValidationError):
            ImpactAlignmentConclusion(status="complete", derived_from_claim_ids=["c1"])


# ---------------------------------------------------------------------------
# TaskReviewCertificate
# ---------------------------------------------------------------------------


def _make_task_review_data(**overrides: object) -> dict:
    base = _make_envelope_data(certificate_type="task_review")
    base.update(
        {
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
    )
    base.update(overrides)
    return base


class TestTaskReviewCertificate:
    def test_valid(self) -> None:
        cert = TaskReviewCertificate(**_make_task_review_data())
        assert cert.certificate_type == "task_review"
        assert cert.formal_conclusion.status == "complete"

    def test_rejects_extra_field(self) -> None:
        with pytest.raises(ValidationError):
            TaskReviewCertificate(**_make_task_review_data(bogus="x"))

    def test_empty_premises_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TaskReviewCertificate(**_make_task_review_data(premises=[]))

    def test_wrong_conclusion_status_rejected(self) -> None:
        data = _make_task_review_data()
        data["formal_conclusion"]["status"] = "justified"
        with pytest.raises(ValidationError):
            TaskReviewCertificate(**data)

    def test_wrong_certificate_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TaskReviewCertificate(**_make_task_review_data(certificate_type="design_decision"))


# ---------------------------------------------------------------------------
# DesignDecisionCertificate
# ---------------------------------------------------------------------------


def _make_design_decision_data(**overrides: object) -> dict:
    base = _make_envelope_data(certificate_type="design_decision")
    base.update(
        {
            "definition": "Design is justified if it matches or exceeds reference.",
            "decision_topic": "Use Pydantic for data models",
            "comparison": {
                "our_pattern": _make_claim_base_data(),
                "reference_pattern": _make_claim_base_data(),
                "match_status": "matches",
            },
            "formal_conclusion": {
                "status": "justified",
                "derived_from_claim_ids": ["c1"],
            },
        }
    )
    base.update(overrides)
    return base


class TestDesignDecisionCertificate:
    def test_valid(self) -> None:
        cert = DesignDecisionCertificate(**_make_design_decision_data())
        assert cert.certificate_type == "design_decision"

    def test_rejects_extra_field(self) -> None:
        with pytest.raises(ValidationError):
            DesignDecisionCertificate(**_make_design_decision_data(bogus="x"))


# ---------------------------------------------------------------------------
# DeferredScopeCertificate
# ---------------------------------------------------------------------------


def _make_deferred_scope_data(**overrides: object) -> dict:
    base = _make_envelope_data(certificate_type="deferred_scope")
    base.update(
        {
            "definition": "Deferral is valid if tracked and criteria are clear.",
            "deferred_work": "Integrate real LLM reviewers",
            "tracking_issue": {"artifact_id": "iss-99", "artifact_type": "issue"},
            "acceptance_criteria": ["LLM produces valid certificates"],
            "roadmap_position": {
                "milestone": "Session 13",
                "blocked_by": [],
                "blocks": [],
            },
            "current_deliverable_consistency": _make_claim_base_data(),
            "evaluation": {
                "tracked": True,
                "acceptance_criteria_clear": True,
                "roadmap_position_valid": True,
                "current_state_consistent": True,
            },
            "formal_conclusion": {
                "status": "valid",
                "derived_from_claim_ids": ["c1"],
            },
        }
    )
    base.update(overrides)
    return base


class TestDeferredScopeCertificate:
    def test_valid(self) -> None:
        cert = DeferredScopeCertificate(**_make_deferred_scope_data())
        assert cert.certificate_type == "deferred_scope"

    def test_rejects_extra_field(self) -> None:
        with pytest.raises(ValidationError):
            DeferredScopeCertificate(**_make_deferred_scope_data(bogus="x"))

    def test_empty_acceptance_criteria_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DeferredScopeCertificate(**_make_deferred_scope_data(acceptance_criteria=[]))


# ---------------------------------------------------------------------------
# ImpactAlignmentCertificate
# ---------------------------------------------------------------------------


def _make_impact_alignment_data(**overrides: object) -> dict:
    vr = {
        "status": "verified",
        "method": "source_read",
        "verified_by": {
            "actor_id": "c1",
            "author_kind": "claude",
            "role": "reviewer_a",
        },
        "verified_at": "2026-03-11T00:00:00Z",
    }
    base = _make_envelope_data(certificate_type="impact_alignment")
    base.update(
        {
            "definition": "Impact is aligned if no silent drift.",
            "roadmap_impacts": [],
            "open_issue_scan": [
                {
                    "issue_ref": {"artifact_id": "iss-1", "artifact_type": "issue"},
                    "impact_status": "none",
                    "action": "No action",
                    "verification": vr,
                }
            ],
            "documentation_impacts": [],
            "dependency_graph": {
                "unblocked_issues": [],
                "blocked_by_updates": [],
                "new_issues": [],
            },
            "formal_conclusion": {
                "status": "aligned",
                "derived_from_claim_ids": ["c1"],
            },
        }
    )
    base.update(overrides)
    return base


class TestImpactAlignmentCertificate:
    def test_valid(self) -> None:
        cert = ImpactAlignmentCertificate(**_make_impact_alignment_data())
        assert cert.certificate_type == "impact_alignment"

    def test_rejects_extra_field(self) -> None:
        with pytest.raises(ValidationError):
            ImpactAlignmentCertificate(**_make_impact_alignment_data(bogus="x"))

    def test_empty_open_issue_scan_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImpactAlignmentCertificate(**_make_impact_alignment_data(open_issue_scan=[]))


# ---------------------------------------------------------------------------
# DisputeObject
# ---------------------------------------------------------------------------


def _make_dispute_data(**overrides: object) -> dict:
    base = {
        "dispute_id": "disp-001",
        "target_certificate_id": "cert-001",
        "target_claim_id": "p1",
        "filed_by": {
            "actor_id": "claude-2",
            "author_kind": "claude",
            "role": "reviewer_b",
        },
        "dispute_type": "wrong_evidence",
        "status": "filed",
        "rationale": "Evidence does not support claim",
        "source_refs": [
            {
                "evidence_id": "ev-99",
                "evidence_type": "file_span",
                "artifact_ref": {"artifact_id": "art-99", "artifact_type": "file"},
            }
        ],
    }
    base.update(overrides)
    return base


class TestDisputeObject:
    def test_valid(self) -> None:
        d = DisputeObject(**_make_dispute_data())
        assert d.dispute_id == "disp-001"

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            DisputeObject(**_make_dispute_data(bogus="x"))

    def test_empty_source_refs_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DisputeObject(**_make_dispute_data(source_refs=[]))

    def test_optional_penalty_points(self) -> None:
        d = DisputeObject(**_make_dispute_data(penalty_points=5))
        assert d.penalty_points == 5


# ---------------------------------------------------------------------------
# TransitionRequest
# ---------------------------------------------------------------------------


def _make_transition_data(**overrides: object) -> dict:
    base = {
        "request_id": "tr-001",
        "workflow_run_id": "run-001",
        "from_state": "implementing",
        "to_state": "self_review",
        "requested_by": {
            "actor_id": "claude-1",
            "author_kind": "claude",
            "role": "implementer",
        },
        "required_artifacts": [{"artifact_id": "art-1", "artifact_type": "file"}],
        "gate_evaluations": [{"gate_id": "g1", "requirement": "Tests pass", "status": "passed"}],
        "status": "requested",
    }
    base.update(overrides)
    return base


class TestTransitionRequest:
    def test_valid(self) -> None:
        tr = TransitionRequest(**_make_transition_data())
        assert tr.from_state.value == "implementing"

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            TransitionRequest(**_make_transition_data(bogus="x"))

    def test_empty_gate_evaluations_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TransitionRequest(**_make_transition_data(gate_evaluations=[]))

    def test_empty_required_artifacts_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TransitionRequest(**_make_transition_data(required_artifacts=[]))


# ---------------------------------------------------------------------------
# RemediationLogEntry & RemediationLog
# ---------------------------------------------------------------------------

ZERO_HASH = "0" * 64


def _make_remediation_entry_data(**overrides: object) -> dict:
    base = {
        "sequence": 1,
        "timestamp": "2026-03-11T00:00:00Z",
        "author": "claude",
        "action": "file",
        "deficiency_id": "def-001",
        "content": "Filed deficiency for missing test",
        "prev_hash": ZERO_HASH,
        "signature": "sig-placeholder",
    }
    base.update(overrides)
    return base


class TestRemediationLogEntry:
    def test_valid(self) -> None:
        e = RemediationLogEntry(**_make_remediation_entry_data())
        assert e.sequence == 1

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            RemediationLogEntry(**_make_remediation_entry_data(bogus="x"))

    def test_sequence_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RemediationLogEntry(**_make_remediation_entry_data(sequence=0))

    def test_optional_booleans(self) -> None:
        e = RemediationLogEntry(
            **_make_remediation_entry_data(
                authority_verified=True,
                signature_verified=False,
                hash_chain_verified=True,
            )
        )
        assert e.authority_verified is True


class TestRemediationLog:
    def test_valid(self) -> None:
        rl = RemediationLog(
            log_id="log-001",
            certificate_id="cert-001",
            certificate_status="deficient",
            entries=[RemediationLogEntry(**_make_remediation_entry_data())],
        )
        assert rl.certificate_status.value == "deficient"

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            RemediationLog(
                log_id="log-001",
                certificate_id="cert-001",
                certificate_status="deficient",
                entries=[],
                bogus="x",
            )

    def test_optional_open_deficiency_count(self) -> None:
        rl = RemediationLog(
            log_id="log-001",
            certificate_id="cert-001",
            certificate_status="deficient",
            entries=[],
            open_deficiency_count=2,
        )
        assert rl.open_deficiency_count == 2


# ---------------------------------------------------------------------------
# WorkflowEvent
# ---------------------------------------------------------------------------


def _make_workflow_event_data(**overrides: object) -> dict:
    base = {
        "event_id": "evt-001",
        "run_id": "run-001",
        "orchestration_version": "0.1.0",
        "workflow_step": "implement",
        "executor_type": "llm",
        "status": "pass",
        "started_at": "2026-03-11T00:00:00Z",
        "ended_at": "2026-03-11T00:01:00Z",
    }
    base.update(overrides)
    return base


class TestWorkflowEvent:
    def test_valid(self) -> None:
        we = WorkflowEvent(**_make_workflow_event_data())
        assert we.event_id == "evt-001"

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowEvent(**_make_workflow_event_data(bogus="x"))

    def test_optional_cost_fields(self) -> None:
        we = WorkflowEvent(
            **_make_workflow_event_data(
                tokens_in=1000,
                tokens_out=500,
                llm_cost_usd=0.05,
                compute_seconds=10.5,
                duration_seconds=60.0,
                complexity_bucket="small",
                changed_loc=42,
                story_points=3.0,
            )
        )
        assert we.tokens_in == 1000
        assert we.llm_cost_usd == 0.05

    def test_negative_tokens_rejected(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowEvent(**_make_workflow_event_data(tokens_in=-1))


# ---------------------------------------------------------------------------
# validate_certificate dispatch
# ---------------------------------------------------------------------------


class TestValidateCertificate:
    def test_dispatches_task_review(self) -> None:
        cert = validate_certificate(_make_task_review_data())
        assert isinstance(cert, TaskReviewCertificate)

    def test_dispatches_design_decision(self) -> None:
        cert = validate_certificate(_make_design_decision_data())
        assert isinstance(cert, DesignDecisionCertificate)

    def test_dispatches_deferred_scope(self) -> None:
        cert = validate_certificate(_make_deferred_scope_data())
        assert isinstance(cert, DeferredScopeCertificate)

    def test_dispatches_impact_alignment(self) -> None:
        cert = validate_certificate(_make_impact_alignment_data())
        assert isinstance(cert, ImpactAlignmentCertificate)

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown"):
            validate_certificate({"certificate_type": "bogus"})

    def test_missing_type_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown"):
            validate_certificate({})

    def test_certificate_models_has_all_types(self) -> None:
        assert set(CERTIFICATE_MODELS.keys()) == {
            "task_review",
            "design_decision",
            "deferred_scope",
            "impact_alignment",
        }


# ---------------------------------------------------------------------------
# Fixture-based round-trip test
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures"


class TestFixtureRoundTrip:
    def test_valid_task_review_fixture(self) -> None:
        fixture_path = FIXTURE_DIR / "valid_task_review.json"
        data = json.loads(fixture_path.read_text())
        cert = validate_certificate(data)
        assert isinstance(cert, TaskReviewCertificate)
        assert cert.formal_conclusion.status == "complete"
