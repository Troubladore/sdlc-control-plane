"""Pydantic models mirroring the JSON Schema bundle $defs."""

from __future__ import annotations

import sys
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:

    class StrEnum(str, Enum):
        """Backport of StrEnum for Python < 3.11."""


from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# ---------------------------------------------------------------------------
# Constrained string types
# ---------------------------------------------------------------------------

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]
Id = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:-]+$")]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[A-Fa-f0-9]{64}$")]
Timestamp = datetime


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Severity(StrEnum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    MINOR = "minor"
    INFO = "info"


class AuthorKind(StrEnum):
    CLAUDE = "claude"
    CODEX = "codex"
    GEMINI = "gemini"
    HUMAN = "human"
    TOOL = "tool"
    SYSTEM = "system"


class ExecutorType(StrEnum):
    STATIC = "static"
    TOOL = "tool"
    LLM = "llm"
    HUMAN = "human"


class WorkflowState(StrEnum):
    PENDING = "pending"
    TRIAGE = "triage"
    DESIGN = "design"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    SIMPLIFY = "simplify"
    SELF_REVIEW = "self_review"
    CERTIFICATE_REVIEW = "certificate_review"
    ISSUES = "issues"
    CERTIFIED = "certified"
    INTEGRATION = "integration"
    COMPLETE = "complete"


class ArtifactType(StrEnum):
    CERTIFICATE = "certificate"
    CERTIFICATE_MARKDOWN = "certificate_markdown"
    FILE = "file"
    FILE_SPAN = "file_span"
    ISSUE = "issue"
    ISSUE_BODY = "issue_body"
    ISSUE_TITLE = "issue_title"
    COMMAND_OUTPUT = "command_output"
    JUNIT_XML = "junit_xml"
    COVERAGE_REPORT = "coverage_report"
    SARIF = "sarif"
    GIT_COMMIT = "git_commit"
    GIT_DIFF = "git_diff"
    PULL_REQUEST = "pull_request"
    ROADMAP_DOC = "roadmap_doc"
    DESIGN_DOC = "design_doc"
    PLAN_DOC = "plan_doc"
    REFERENCE_REPO = "reference_repo"
    RENDERED_OUTPUT = "rendered_output"
    WORKFLOW_EVENT = "workflow_event"
    REMEDIATION_LOG = "remediation_log"


class EvidenceType(StrEnum):
    FILE_SPAN = "file_span"
    ISSUE_BODY = "issue_body"
    ISSUE_TITLE = "issue_title"
    COMMAND_OUTPUT = "command_output"
    COMMAND_RERUN = "command_rerun"
    TEST_RESULT = "test_result"
    LINT_RESULT = "lint_result"
    TYPECHECK_RESULT = "typecheck_result"
    COMMIT = "commit"
    DIFF_HUNK = "diff_hunk"
    ROADMAP_ENTRY = "roadmap_entry"
    DOCUMENTATION_PAGE = "documentation_page"
    REFERENCE_CODE = "reference_code"
    LOG_ENTRY = "log_entry"
    SIGNATURE_CHECK = "signature_check"
    HASH_CHECK = "hash_check"


class VerificationMethod(StrEnum):
    SOURCE_READ = "source_read"
    COMMAND_RERUN = "command_rerun"
    TITLE_SCAN = "title_scan"
    ISSUE_BODY_READ = "issue_body_read"
    DIFF_REVIEW = "diff_review"
    SIGNATURE_CHECK = "signature_check"
    HASH_CHAIN_CHECK = "hash_chain_check"
    CROSS_MODEL_REVIEW = "cross_model_review"
    HUMAN_REVIEW = "human_review"


class VerifiedStatus(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    NOT_CHECKED = "not_checked"
    INCONCLUSIVE = "inconclusive"


class CertificateType(StrEnum):
    TASK_REVIEW = "task_review"
    DESIGN_DECISION = "design_decision"
    DEFERRED_SCOPE = "deferred_scope"
    IMPACT_ALIGNMENT = "impact_alignment"


class ValidationStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    DEFICIENT = "deficient"
    CLEAN = "clean"
    SUPERSEDED = "superseded"


class ActorRole(StrEnum):
    IMPLEMENTER = "implementer"
    REVIEWER_A = "reviewer_a"
    REVIEWER_B = "reviewer_b"
    FINDER = "finder"
    VALIDATOR = "validator"
    ARBITER = "arbiter"
    MAINTAINER = "maintainer"
    SYSTEM = "system"


class PremiseStatus(StrEnum):
    SATISFIED = "satisfied"
    MISSING = "missing"
    PARTIAL = "partial"


class QualityAssertionStatus(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    NOT_VERIFIED = "not_verified"
    PARTIAL = "partial"


class IssueFindingStatus(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"
    REMEDIATED = "remediated"
    WITHDRAWN = "withdrawn"
    ESCALATED = "escalated"


class CommandVerificationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not_run"


class GateStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    WAIVED = "waived"
    NOT_EVALUATED = "not_evaluated"


class FormalConclusionStatus(StrEnum):
    COMPLETE = "complete"
    NOT_COMPLETE = "not_complete"
    JUSTIFIED = "justified"
    NEEDS_REVISION = "needs_revision"
    VALID = "valid"
    INVALID = "invalid"
    ALIGNED = "aligned"
    NOT_ALIGNED = "not_aligned"


class DisputeType(StrEnum):
    WRONG_DEPENDENCY = "wrong_dependency"
    WRONG_SCOPE = "wrong_scope"
    WRONG_EVIDENCE = "wrong_evidence"
    MISSING_VERIFICATION = "missing_verification"
    MISSING_CLAIM = "missing_claim"
    INVALID_COMPARISON = "invalid_comparison"
    INVALID_DEFERRAL = "invalid_deferral"
    INVALID_NONE_CLAIM = "invalid_none_claim"
    STATE_TRANSITION_VIOLATION = "state_transition_violation"
    OTHER = "other"


class DisputeStatus(StrEnum):
    FILED = "filed"
    CONFIRMED_BY_VALIDATOR = "confirmed_by_validator"
    DISPUTED_BY_VALIDATOR = "disputed_by_validator"
    UPHELD = "upheld"
    OVERTURNED = "overturned"
    WITHDRAWN = "withdrawn"
    INCONCLUSIVE = "inconclusive"
    ESCALATED = "escalated"


class TransitionRequestStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class RemediationAction(StrEnum):
    FILE = "file"
    CONFIRM = "confirm"
    DISPUTE = "dispute"
    EVIDENCE = "evidence"
    ACCEPT = "accept"
    REJECT = "reject"
    ARBITRATE = "arbitrate"
    REBUTTAL = "rebuttal"
    WITHDRAW = "withdraw"
    ESCALATE = "escalate"


class RemediationLogStatus(StrEnum):
    DEFICIENT = "deficient"
    CLEAN = "clean"


class WorkflowEventStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


class ComplexityBucket(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    UNKNOWN = "unknown"


class DesignMatchStatus(StrEnum):
    MATCHES = "matches"
    EXCEEDS = "exceeds"
    DIVERGES = "diverges"


class ReferenceSource(StrEnum):
    INSPECT_AI = "inspect_ai"
    MTEB = "mteb"
    PYTHON_STDLIB = "python_stdlib"
    OTHER = "other"


class ImpactStatus(StrEnum):
    NONE = "none"
    IMPACTED = "impacted"
    UNCERTAIN = "uncertain"


class DocumentationImpactStatus(StrEnum):
    NONE = "none"
    UPDATED = "updated"
    FOLLOW_UP_REQUIRED = "follow_up_required"


# ---------------------------------------------------------------------------
# Building block models
# ---------------------------------------------------------------------------


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: Id
    author_kind: AuthorKind
    role: ActorRole
    display_name: NonEmptyString | None = None
    model_family: NonEmptyString | None = None
    version: NonEmptyString | None = None


class Locator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: NonEmptyString | None = None
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    issue_number: int | None = Field(default=None, ge=1)
    url: str | None = None
    command: NonEmptyString | None = None
    commit_sha: Annotated[str, StringConstraints(pattern=r"^[A-Fa-f0-9]{7,40}$")] | None = None
    diff_hunk: NonEmptyString | None = None
    note: NonEmptyString | None = None


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: Id
    artifact_type: ArtifactType
    uri: str | None = None
    content_hash: Sha256 | None = None
    locator: Locator | None = None
    description: NonEmptyString | None = None


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: Id
    evidence_type: EvidenceType
    artifact_ref: ArtifactRef
    excerpt_hash: Sha256 | None = None
    excerpt: NonEmptyString | None = None
    candidate_inventory_id: Id | None = None


class VerificationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: VerifiedStatus
    method: VerificationMethod
    verified_by: Actor
    verified_at: Timestamp
    evidence_checked: list[Id] | None = None
    notes: NonEmptyString | None = None


# ---------------------------------------------------------------------------
# Claim and finding models
# ---------------------------------------------------------------------------


class ClaimBase(BaseModel):
    """Base for claims. Not leaf -- no extra='forbid' here."""

    claim_id: Id
    text: NonEmptyString
    evidence_refs: list[EvidenceRef] = Field(min_length=1)
    verification: VerificationRecord | None = None
    notes: NonEmptyString | None = None


class PremiseClaim(ClaimBase):
    model_config = ConfigDict(extra="forbid")

    status: PremiseStatus


class QualityAssertion(ClaimBase):
    model_config = ConfigDict(extra="forbid")

    status: QualityAssertionStatus


class IssueFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: Id
    description: NonEmptyString
    severity: Severity
    evidence_refs: list[EvidenceRef] | None = None
    verification: VerificationRecord | None = None
    status: IssueFindingStatus | None = None


class CommandVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: Id
    command: NonEmptyString
    summary: NonEmptyString | None = None
    exit_code: int = Field(ge=0)
    status: CommandVerificationStatus
    fresh: bool | None = None
    evidence_ref: EvidenceRef | None = None
    verification: VerificationRecord | None = None


class FormalConclusion(BaseModel):
    """Base conclusion. Not leaf -- certificates constrain status further."""

    status: FormalConclusionStatus
    summary: NonEmptyString | None = None
    derived_from_claim_ids: list[Id] = Field(min_length=1)


class GateEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_id: Id
    requirement: NonEmptyString
    status: GateStatus
    verifier_artifacts: list[ArtifactRef] | None = None
    notes: NonEmptyString | None = None


# ---------------------------------------------------------------------------
# Helper models for certificates
# ---------------------------------------------------------------------------


class DesignComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    our_pattern: ClaimBase
    reference_pattern: ClaimBase
    match_status: DesignMatchStatus
    divergence_reason: ClaimBase | None = None
    reference_source: ReferenceSource | None = None


class RoadmapPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    milestone: NonEmptyString
    blocked_by: list[ArtifactRef]
    blocks: list[ArtifactRef]


class DeferredEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tracked: bool
    acceptance_criteria_clear: bool
    roadmap_position_valid: bool
    current_state_consistent: bool


class IssueImpactAssessment(ClaimBase):
    model_config = ConfigDict(extra="forbid")

    issue_ref: ArtifactRef
    impact_status: ImpactStatus
    action: NonEmptyString
    verification: VerificationRecord  # Override: required (was optional on ClaimBase)
    impact_description: NonEmptyString | None = None


class DocumentationImpact(ClaimBase):
    model_config = ConfigDict(extra="forbid")

    document_ref: ArtifactRef
    status: DocumentationImpactStatus
    description: NonEmptyString | None = None
    verification: VerificationRecord | None = None  # Stays optional


class DependencyGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unblocked_issues: list[ArtifactRef]
    blocked_by_updates: list[ArtifactRef]
    new_issues: list[ArtifactRef]
    post_merge_actions: list[NonEmptyString] | None = None


# ---------------------------------------------------------------------------
# Certificate Envelope (base for all certificates — NOT leaf)
# ---------------------------------------------------------------------------


class CertificateEnvelope(BaseModel):
    schema_version: NonEmptyString
    certificate_id: Id
    certificate_type: CertificateType
    workflow_run_id: Id
    issue_ref: ArtifactRef
    produced_by: Actor
    produced_at: Timestamp
    source_artifacts: list[ArtifactRef] = Field(min_length=1)
    validation_status: ValidationStatus
    pr_ref: ArtifactRef | None = None
    validation_notes: NonEmptyString | None = None
    verified_claim_count: int | None = Field(default=None, ge=0)
    unverified_claim_count: int | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Typed conclusions (constrained status subsets)
# ---------------------------------------------------------------------------


class TaskReviewConclusion(FormalConclusion):
    model_config = ConfigDict(extra="forbid")

    status: Literal["complete", "not_complete"]  # type: ignore[assignment]


class DesignDecisionConclusion(FormalConclusion):
    model_config = ConfigDict(extra="forbid")

    status: Literal["justified", "needs_revision"]  # type: ignore[assignment]


class DeferredScopeConclusion(FormalConclusion):
    model_config = ConfigDict(extra="forbid")

    status: Literal["valid", "invalid"]  # type: ignore[assignment]


class ImpactAlignmentConclusion(FormalConclusion):
    model_config = ConfigDict(extra="forbid")

    status: Literal["aligned", "not_aligned"]  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Four certificate types
# ---------------------------------------------------------------------------


class TaskReviewCertificate(CertificateEnvelope):
    model_config = ConfigDict(extra="forbid")

    certificate_type: Literal["task_review"]  # type: ignore[assignment]
    definition: NonEmptyString
    premises: list[PremiseClaim] = Field(min_length=1)
    quality_assertions: list[QualityAssertion] = Field(min_length=1)
    verification_commands: list[CommandVerification] = Field(min_length=1)
    formal_conclusion: TaskReviewConclusion
    issues: list[IssueFinding]


class DesignDecisionCertificate(CertificateEnvelope):
    model_config = ConfigDict(extra="forbid")

    certificate_type: Literal["design_decision"]  # type: ignore[assignment]
    definition: NonEmptyString
    decision_topic: NonEmptyString
    comparison: DesignComparison
    formal_conclusion: DesignDecisionConclusion


class DeferredScopeCertificate(CertificateEnvelope):
    model_config = ConfigDict(extra="forbid")

    certificate_type: Literal["deferred_scope"]  # type: ignore[assignment]
    definition: NonEmptyString
    deferred_work: NonEmptyString
    tracking_issue: ArtifactRef
    acceptance_criteria: list[NonEmptyString] = Field(min_length=1)
    roadmap_position: RoadmapPosition
    current_deliverable_consistency: ClaimBase
    evaluation: DeferredEvaluation
    formal_conclusion: DeferredScopeConclusion


class ImpactAlignmentCertificate(CertificateEnvelope):
    model_config = ConfigDict(extra="forbid")

    certificate_type: Literal["impact_alignment"]  # type: ignore[assignment]
    definition: NonEmptyString
    roadmap_impacts: list[IssueImpactAssessment]
    open_issue_scan: list[IssueImpactAssessment] = Field(min_length=1)
    documentation_impacts: list[DocumentationImpact]
    dependency_graph: DependencyGraph
    formal_conclusion: ImpactAlignmentConclusion


# ---------------------------------------------------------------------------
# Remaining top-level models
# ---------------------------------------------------------------------------


class DisputeObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dispute_id: Id
    target_certificate_id: Id
    target_claim_id: Id
    filed_by: Actor
    dispute_type: DisputeType
    status: DisputeStatus
    rationale: NonEmptyString
    source_refs: list[EvidenceRef] = Field(min_length=1)
    against_actor: Actor | None = None
    validator: Actor | None = None
    arbiter: Actor | None = None
    proposed_fix: NonEmptyString | None = None
    arbiter_ruling: NonEmptyString | None = None
    penalty_points: int | None = None


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: Id
    workflow_run_id: Id
    from_state: WorkflowState
    to_state: WorkflowState
    requested_by: Actor
    required_artifacts: list[ArtifactRef] = Field(min_length=1)
    gate_evaluations: list[GateEvaluation] = Field(min_length=1)
    status: TransitionRequestStatus
    requested_at: Timestamp | None = None
    decided_by: Actor | None = None
    decision_notes: NonEmptyString | None = None


class RemediationLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    timestamp: Timestamp
    author: AuthorKind
    action: RemediationAction
    deficiency_id: Id
    content: NonEmptyString
    prev_hash: Sha256
    signature: NonEmptyString
    content_hash: Sha256 | None = None
    authority_verified: bool | None = None
    signature_verified: bool | None = None
    hash_chain_verified: bool | None = None


class RemediationLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    log_id: Id
    certificate_id: Id
    certificate_status: RemediationLogStatus
    entries: list[RemediationLogEntry]
    open_deficiency_count: int | None = Field(default=None, ge=0)


class WorkflowEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: Id
    run_id: Id
    orchestration_version: NonEmptyString
    workflow_step: NonEmptyString
    executor_type: ExecutorType
    status: WorkflowEventStatus
    started_at: Timestamp
    ended_at: Timestamp
    parent_run_id: Id | None = None
    skills_hash: Sha256 | None = None
    policy_hash: Sha256 | None = None
    state: WorkflowState | None = None
    exit_code: int | None = None
    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    llm_cost_usd: float | None = Field(default=None, ge=0)
    compute_seconds: float | None = Field(default=None, ge=0)
    ci_minutes_est: float | None = Field(default=None, ge=0)
    compute_cost_usd: float | None = Field(default=None, ge=0)
    human_minutes: float | None = Field(default=None, ge=0)
    human_cost_usd: float | None = Field(default=None, ge=0)
    artifacts: list[ArtifactRef] | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    complexity_bucket: ComplexityBucket | None = None
    changed_loc: int | None = Field(default=None, ge=0)
    files_changed: int | None = Field(default=None, ge=0)
    tests_added: int | None = Field(default=None, ge=0)
    story_points: float | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

CERTIFICATE_MODELS: dict[str, type[CertificateEnvelope]] = {
    "task_review": TaskReviewCertificate,
    "design_decision": DesignDecisionCertificate,
    "deferred_scope": DeferredScopeCertificate,
    "impact_alignment": ImpactAlignmentCertificate,
}


def validate_certificate(data: dict[str, Any]) -> CertificateEnvelope:
    """Dispatch to the correct certificate model based on certificate_type."""
    cert_type = data.get("certificate_type")
    if cert_type not in CERTIFICATE_MODELS:
        raise KeyError(f"Unknown or missing certificate_type: {cert_type!r}")
    return CERTIFICATE_MODELS[cert_type].model_validate(data)
