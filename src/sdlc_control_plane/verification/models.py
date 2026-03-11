"""Pydantic models mirroring the JSON Schema bundle $defs."""

from __future__ import annotations

import sys
from datetime import datetime
from enum import Enum
from typing import Annotated

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
