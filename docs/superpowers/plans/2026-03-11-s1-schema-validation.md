# Session 1: Schema Bundle as Pydantic Models + CLI Validator — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the JSON Schema bundle as type-safe Pydantic models and a CLI validator that accepts certificate JSON files.

**Architecture:** Hand-written Pydantic models in `verification/models.py` mirror every `$defs` entry in the schema bundle. A `validate_certificate()` dispatcher auto-detects certificate type. The CLI (`sdlc validate`) wraps this with Rich output and proper exit codes. Drift-detection tests keep models in sync with the canonical schema.

**Tech Stack:** Python 3.10+, Pydantic v2, Click, Rich, pytest

**Spec:** `docs/superpowers/specs/2026-03-11-s1-schema-validation-design.md`
**Schema:** `schemas/agent_workflow_schema_bundle.json`

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `src/sdlc_control_plane/verification/models.py` | All Pydantic models mirroring schema `$defs` |
| Modify | `src/sdlc_control_plane/cli/__init__.py` | Wire up `validate` command with file args, `--type`, Rich output |
| Create | `tests/fixtures/valid_task_review.json` | Minimal valid TaskReviewCertificate |
| Create | `tests/fixtures/valid_design_decision.json` | Minimal valid DesignDecisionCertificate |
| Create | `tests/fixtures/valid_deferred_scope.json` | Minimal valid DeferredScopeCertificate |
| Create | `tests/fixtures/valid_impact_alignment.json` | Minimal valid ImpactAlignmentCertificate |
| Create | `tests/fixtures/invalid_missing_fields.json` | Certificate with required fields missing |
| Create | `tests/fixtures/invalid_bad_enum.json` | Certificate with invalid enum value |
| Create | `tests/fixtures/invalid_extra_fields.json` | Certificate with unexpected extra field |
| Create | `tests/test_models.py` | Unit tests for models + validate_certificate() |
| Create | `tests/test_schema_drift.py` | Drift detection: Pydantic vs JSON Schema bundle |
| Create | `tests/test_cli.py` | CLI integration tests via Click test runner |

---

## Chunk 1: Constrained Types, Enums, and Foundation Models

### Task 1: Create feature branch

**Files:** (none)

- [ ] **Step 1: Create and switch to feature branch**

Run: `git checkout -b feat/s1-schema-validation`

- [ ] **Step 2: Verify clean state**

Run: `git status`
Expected: On branch `feat/s1-schema-validation`, nothing to commit

---

### Task 2: Constrained types and enums — red tests

**Files:**
- Create: `tests/test_models.py`
- Create: `src/sdlc_control_plane/verification/models.py` (empty initially)

- [ ] **Step 1: Write failing tests for constrained types and enums**

Create `tests/test_models.py`:

```python
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
            "pending", "triage", "design", "planning", "implementing",
            "simplify", "self_review", "certificate_review", "issues",
            "certified", "integration", "complete",
        }
        assert set(WorkflowState) == expected

    def test_artifact_type_values(self) -> None:
        assert len(ArtifactType) == 17

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
            "task_review", "design_decision", "deferred_scope", "impact_alignment",
        }

    def test_validation_status_values(self) -> None:
        assert set(ValidationStatus) == {
            "draft", "validated", "deficient", "clean", "superseded",
        }

    def test_actor_role_values(self) -> None:
        expected = {
            "implementer", "reviewer_a", "reviewer_b", "finder",
            "validator", "arbiter", "maintainer", "system",
        }
        assert set(ActorRole) == expected

    def test_invalid_enum_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            Severity("nonexistent")
```

- [ ] **Step 2: Create empty models file so import path exists**

Create `src/sdlc_control_plane/verification/models.py`:

```python
"""Pydantic models mirroring the JSON Schema bundle $defs."""
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py -x -v`
Expected: FAIL — ImportError (names not exported)

---

### Task 3: Constrained types and enums — green implementation

**Files:**
- Modify: `src/sdlc_control_plane/verification/models.py`

- [ ] **Step 1: Implement constrained types and all enums**

Write `src/sdlc_control_plane/verification/models.py`:

```python
"""Pydantic models mirroring the JSON Schema bundle $defs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import StringConstraints

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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -x -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/sdlc_control_plane/verification/models.py tests/test_models.py
git commit -m "feat(s1): add constrained types and enums for schema bundle"
```

---

### Task 4: Building block models — red tests

**Files:**
- Modify: `tests/test_models.py`

- [ ] **Step 1: Add failing tests for Actor, Locator, ArtifactRef, EvidenceRef, VerificationRecord**

Append to `tests/test_models.py`:

```python
from sdlc_control_plane.verification.models import (
    Actor,
    ArtifactRef,
    EvidenceRef,
    Locator,
    VerificationRecord,
)


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py::TestActor -x -v`
Expected: FAIL — ImportError

---

### Task 5: Building block models — green implementation

**Files:**
- Modify: `src/sdlc_control_plane/verification/models.py`

- [ ] **Step 1: Add Pydantic models for building blocks**

Append to `src/sdlc_control_plane/verification/models.py` (after enums):

```python
from pydantic import BaseModel, ConfigDict, Field


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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -x -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/sdlc_control_plane/verification/models.py tests/test_models.py
git commit -m "feat(s1): add building block models (Actor, Locator, ArtifactRef, EvidenceRef, VerificationRecord)"
```

---

### Task 6: Claim models and findings — red tests

**Files:**
- Modify: `tests/test_models.py`

- [ ] **Step 1: Add failing tests for ClaimBase, PremiseClaim, QualityAssertion, IssueFinding, CommandVerification, FormalConclusion, GateEvaluation**

Append to `tests/test_models.py`:

```python
from sdlc_control_plane.verification.models import (
    ClaimBase,
    CommandVerification,
    FormalConclusion,
    GateEvaluation,
    IssueFinding,
    PremiseClaim,
    QualityAssertion,
)


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
                claim_id="p1", text="x", evidence_refs=[], status="satisfied",
            )

    def test_rejects_extra_field(self) -> None:
        with pytest.raises(ValidationError):
            PremiseClaim(
                claim_id="p1", text="x",
                evidence_refs=[_make_evidence_ref()],
                status="satisfied", bogus="y",
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
            issue_id="i1", description="Bug", severity="critical", status="open",
        )
        assert f.status == IssueFindingStatus.OPEN


class TestCommandVerification:
    def test_valid(self) -> None:
        cv = CommandVerification(
            command_id="cmd-1", command="pytest", exit_code=0, status="passed",
        )
        assert cv.status == CommandVerificationStatus.PASSED

    def test_with_optional_singular_evidence_ref(self) -> None:
        cv = CommandVerification(
            command_id="cmd-1", command="pytest", exit_code=0, status="passed",
            evidence_ref=_make_evidence_ref(),
        )
        assert cv.evidence_ref is not None


class TestFormalConclusion:
    def test_valid(self) -> None:
        fc = FormalConclusion(
            status="complete", derived_from_claim_ids=["p1", "q1"],
        )
        assert fc.status == FormalConclusionStatus.COMPLETE

    def test_empty_derived_from_rejected(self) -> None:
        with pytest.raises(ValidationError):
            FormalConclusion(status="complete", derived_from_claim_ids=[])


class TestGateEvaluation:
    def test_valid(self) -> None:
        ge = GateEvaluation(
            gate_id="g1", requirement="Tests pass", status="passed",
        )
        assert ge.status == GateStatus.PASSED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py::TestPremiseClaim -x -v`
Expected: FAIL — ImportError

---

### Task 7: Claim models and findings — green implementation

**Files:**
- Modify: `src/sdlc_control_plane/verification/models.py`

- [ ] **Step 1: Add claim models, findings, conclusion, gate**

Append to `src/sdlc_control_plane/verification/models.py`:

```python
class ClaimBase(BaseModel):
    """Base for claims. Not leaf — no extra='forbid' here."""

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
    """Base conclusion. Not leaf — certificates constrain status further."""

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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -x -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/sdlc_control_plane/verification/models.py tests/test_models.py
git commit -m "feat(s1): add claim models, findings, conclusion, and gate evaluation"
```

---

## Chunk 2: Certificate Models and Remaining Top-Level Types

### Task 8: Certificate envelope and four certificate types — red tests

**Files:**
- Modify: `tests/test_models.py`
- Create: `tests/fixtures/valid_task_review.json`

- [ ] **Step 1: Create a minimal valid task review fixture**

Create `tests/fixtures/valid_task_review.json`:

```json
{
  "schema_version": "1.0.0",
  "certificate_id": "cert-001",
  "certificate_type": "task_review",
  "workflow_run_id": "run-001",
  "issue_ref": {
    "artifact_id": "issue-42",
    "artifact_type": "issue"
  },
  "produced_by": {
    "actor_id": "claude-1",
    "author_kind": "claude",
    "role": "reviewer_a"
  },
  "produced_at": "2026-03-11T00:00:00Z",
  "source_artifacts": [
    {"artifact_id": "src-1", "artifact_type": "file"}
  ],
  "validation_status": "validated",
  "definition": "Task is COMPLETE iff all spec requirements are satisfied.",
  "premises": [
    {
      "claim_id": "p1",
      "text": "All tests pass",
      "evidence_refs": [
        {
          "evidence_id": "ev-1",
          "evidence_type": "test_result",
          "artifact_ref": {"artifact_id": "art-1", "artifact_type": "command_output"}
        }
      ],
      "status": "satisfied"
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
          "artifact_ref": {"artifact_id": "art-2", "artifact_type": "command_output"}
        }
      ],
      "status": "verified"
    }
  ],
  "verification_commands": [
    {
      "command_id": "cmd-1",
      "command": "pytest",
      "exit_code": 0,
      "status": "passed"
    }
  ],
  "formal_conclusion": {
    "status": "complete",
    "derived_from_claim_ids": ["p1", "q1"]
  },
  "issues": []
}
```

- [ ] **Step 2: Add failing tests for certificate models**

Append to `tests/test_models.py`:

```python
import json
from pathlib import Path

from sdlc_control_plane.verification.models import (
    CertificateEnvelope,
    TaskReviewCertificate,
    validate_certificate,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestTaskReviewCertificate:
    def test_valid_from_fixture(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        cert = TaskReviewCertificate.model_validate(data)
        assert cert.certificate_type == CertificateType.TASK_REVIEW
        assert cert.formal_conclusion.status == FormalConclusionStatus.COMPLETE

    def test_rejects_wrong_conclusion_status(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["formal_conclusion"]["status"] = "justified"
        with pytest.raises(ValidationError):
            TaskReviewCertificate.model_validate(data)

    def test_rejects_extra_field(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        data["bogus_field"] = "x"
        with pytest.raises(ValidationError):
            TaskReviewCertificate.model_validate(data)


class TestValidateCertificate:
    def test_dispatches_task_review(self) -> None:
        data = json.loads((FIXTURES / "valid_task_review.json").read_text())
        cert = validate_certificate(data)
        assert isinstance(cert, TaskReviewCertificate)

    def test_unknown_type_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown or missing"):
            validate_certificate({"certificate_type": "bogus"})

    def test_missing_type_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown or missing"):
            validate_certificate({})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py::TestTaskReviewCertificate -x -v`
Expected: FAIL — ImportError

---

### Task 9: Certificate models — green implementation

**Files:**
- Modify: `src/sdlc_control_plane/verification/models.py`

- [ ] **Step 1: Add CertificateEnvelope and all four certificate types**

Append to `src/sdlc_control_plane/verification/models.py`:

```python
from typing import Any, Literal


class DesignComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    our_pattern: ClaimBase
    reference_pattern: ClaimBase
    divergence_reason: ClaimBase | None = None
    reference_source: ReferenceSource | None = None
    match_status: DesignMatchStatus


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


class IssueImpactAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_ref: ArtifactRef
    impact_status: ImpactStatus
    impact_description: NonEmptyString | None = None
    action: NonEmptyString
    verification: VerificationRecord


class DocumentationImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_ref: ArtifactRef
    status: DocumentationImpactStatus
    description: NonEmptyString | None = None
    verification: VerificationRecord | None = None


class DependencyGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unblocked_issues: list[ArtifactRef]
    blocked_by_updates: list[ArtifactRef]
    new_issues: list[ArtifactRef]
    post_merge_actions: list[NonEmptyString] | None = None


# ---------------------------------------------------------------------------
# Certificate Envelope (base — not leaf)
# ---------------------------------------------------------------------------

class CertificateEnvelope(BaseModel):
    """Base for all certificates. Not leaf — subclasses set extra='forbid'."""

    schema_version: NonEmptyString
    certificate_id: Id
    certificate_type: CertificateType
    workflow_run_id: Id
    issue_ref: ArtifactRef
    pr_ref: ArtifactRef | None = None
    produced_by: Actor
    produced_at: Timestamp
    source_artifacts: list[ArtifactRef] = Field(min_length=1)
    validation_status: ValidationStatus
    validation_notes: NonEmptyString | None = None
    verified_claim_count: int | None = Field(default=None, ge=0)
    unverified_claim_count: int | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Concrete certificate types (leaf models)
# ---------------------------------------------------------------------------

class TaskReviewConclusion(FormalConclusion):
    model_config = ConfigDict(extra="forbid")
    status: Literal["complete", "not_complete"]  # type: ignore[assignment]


class TaskReviewCertificate(CertificateEnvelope):
    model_config = ConfigDict(extra="forbid")
    certificate_type: Literal["task_review"] = "task_review"  # type: ignore[assignment]

    definition: NonEmptyString
    premises: list[PremiseClaim] = Field(min_length=1)
    quality_assertions: list[QualityAssertion] = Field(min_length=1)
    verification_commands: list[CommandVerification] = Field(min_length=1)
    formal_conclusion: TaskReviewConclusion
    issues: list[IssueFinding]


class DesignDecisionConclusion(FormalConclusion):
    model_config = ConfigDict(extra="forbid")
    status: Literal["justified", "needs_revision"]  # type: ignore[assignment]


class DesignDecisionCertificate(CertificateEnvelope):
    model_config = ConfigDict(extra="forbid")
    certificate_type: Literal["design_decision"] = "design_decision"  # type: ignore[assignment]

    definition: NonEmptyString
    decision_topic: NonEmptyString
    comparison: DesignComparison
    formal_conclusion: DesignDecisionConclusion


class DeferredScopeConclusion(FormalConclusion):
    model_config = ConfigDict(extra="forbid")
    status: Literal["valid", "invalid"]  # type: ignore[assignment]


class DeferredScopeCertificate(CertificateEnvelope):
    model_config = ConfigDict(extra="forbid")
    certificate_type: Literal["deferred_scope"] = "deferred_scope"  # type: ignore[assignment]

    definition: NonEmptyString
    deferred_work: NonEmptyString
    tracking_issue: ArtifactRef
    acceptance_criteria: list[NonEmptyString] = Field(min_length=1)
    roadmap_position: RoadmapPosition
    current_deliverable_consistency: ClaimBase
    evaluation: DeferredEvaluation
    formal_conclusion: DeferredScopeConclusion


class ImpactAlignmentConclusion(FormalConclusion):
    model_config = ConfigDict(extra="forbid")
    status: Literal["aligned", "not_aligned"]  # type: ignore[assignment]


class ImpactAlignmentCertificate(CertificateEnvelope):
    model_config = ConfigDict(extra="forbid")
    certificate_type: Literal["impact_alignment"] = "impact_alignment"  # type: ignore[assignment]

    definition: NonEmptyString
    roadmap_impacts: list[IssueImpactAssessment]
    open_issue_scan: list[IssueImpactAssessment] = Field(min_length=1)
    documentation_impacts: list[DocumentationImpact]
    dependency_graph: DependencyGraph
    formal_conclusion: ImpactAlignmentConclusion


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
    """Validate a JSON dict as a certificate. Auto-detects type.

    Raises KeyError if certificate_type is missing or not recognized.
    Raises ValidationError if data does not match the schema.
    """
    cert_type = data.get("certificate_type")
    if cert_type not in CERTIFICATE_MODELS:
        raise KeyError(f"Unknown or missing certificate_type: {cert_type!r}")
    return CERTIFICATE_MODELS[cert_type].model_validate(data)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -x -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/sdlc_control_plane/verification/models.py tests/test_models.py tests/fixtures/valid_task_review.json
git commit -m "feat(s1): add certificate envelope, four certificate types, and validate_certificate()"
```

---

### Task 10: Remaining top-level models — red tests

**Files:**
- Modify: `tests/test_models.py`

- [ ] **Step 1: Add failing tests for DisputeObject, TransitionRequest, RemediationLogEntry, RemediationLog, WorkflowEvent**

Append to `tests/test_models.py`:

```python
from sdlc_control_plane.verification.models import (
    DisputeObject,
    RemediationLog,
    RemediationLogEntry,
    TransitionRequest,
    WorkflowEvent,
)

ZERO_HASH = "0" * 64


class TestDisputeObject:
    def test_valid(self) -> None:
        d = DisputeObject(
            dispute_id="d-1",
            target_certificate_id="cert-001",
            target_claim_id="p1",
            filed_by=Actor(actor_id="c1", author_kind="claude", role="reviewer_b"),
            dispute_type="wrong_evidence",
            status="filed",
            rationale="Evidence does not support claim",
            source_refs=[_make_evidence_ref()],
        )
        assert d.dispute_type == DisputeType.WRONG_EVIDENCE


class TestTransitionRequest:
    def test_valid(self) -> None:
        tr = TransitionRequest(
            request_id="tr-1",
            workflow_run_id="run-001",
            from_state="implementing",
            to_state="self_review",
            requested_by=Actor(actor_id="c1", author_kind="claude", role="implementer"),
            required_artifacts=[ArtifactRef(artifact_id="a1", artifact_type="file")],
            gate_evaluations=[
                GateEvaluation(gate_id="g1", requirement="Tests pass", status="passed"),
            ],
            status="approved",
        )
        assert tr.from_state == WorkflowState.IMPLEMENTING


class TestRemediationLogEntry:
    def test_valid(self) -> None:
        e = RemediationLogEntry(
            sequence=1,
            timestamp="2026-03-11T00:00:00Z",
            author="claude",
            action="file",
            deficiency_id="def-1",
            content="Filed deficiency for missing test",
            prev_hash=ZERO_HASH,
            signature="sig-placeholder",
        )
        assert e.sequence == 1


class TestRemediationLog:
    def test_valid(self) -> None:
        log = RemediationLog(
            log_id="log-1",
            certificate_id="cert-001",
            certificate_status="deficient",
            entries=[],
        )
        assert log.certificate_status == RemediationLogStatus.DEFICIENT


class TestWorkflowEvent:
    def test_valid(self) -> None:
        we = WorkflowEvent(
            event_id="evt-1",
            run_id="run-001",
            orchestration_version="1.0",
            workflow_step="implement",
            executor_type="llm",
            status="pass",
            started_at="2026-03-11T00:00:00Z",
            ended_at="2026-03-11T00:01:00Z",
        )
        assert we.executor_type == ExecutorType.LLM
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py::TestDisputeObject -x -v`
Expected: FAIL — ImportError

---

### Task 11: Remaining top-level models — green implementation

**Files:**
- Modify: `src/sdlc_control_plane/verification/models.py`

- [ ] **Step 1: Add remaining models**

Append to `src/sdlc_control_plane/verification/models.py` (before the dispatch section):

```python
class DisputeObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dispute_id: Id
    target_certificate_id: Id
    target_claim_id: Id
    filed_by: Actor
    against_actor: Actor | None = None
    validator: Actor | None = None
    arbiter: Actor | None = None
    dispute_type: DisputeType
    status: DisputeStatus
    rationale: NonEmptyString
    source_refs: list[EvidenceRef] = Field(min_length=1)
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
    requested_at: Timestamp | None = None
    required_artifacts: list[ArtifactRef] = Field(min_length=1)
    gate_evaluations: list[GateEvaluation] = Field(min_length=1)
    status: TransitionRequestStatus
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
    open_deficiency_count: int | None = Field(default=None, ge=0)
    entries: list[RemediationLogEntry]


class WorkflowEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: Id
    run_id: Id
    parent_run_id: Id | None = None
    orchestration_version: NonEmptyString
    skills_hash: Sha256 | None = None
    policy_hash: Sha256 | None = None
    workflow_step: NonEmptyString
    state: WorkflowState | None = None
    executor_type: ExecutorType
    status: WorkflowEventStatus
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
    started_at: Timestamp
    ended_at: Timestamp
    duration_seconds: float | None = Field(default=None, ge=0)
    complexity_bucket: ComplexityBucket | None = None
    changed_loc: int | None = Field(default=None, ge=0)
    files_changed: int | None = Field(default=None, ge=0)
    tests_added: int | None = Field(default=None, ge=0)
    story_points: float | None = Field(default=None, ge=0)
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -x -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/sdlc_control_plane/verification/models.py tests/test_models.py
git commit -m "feat(s1): add dispute, transition, remediation, and workflow event models"
```

---

## Chunk 3: Remaining Fixtures, CLI, and Drift Detection

### Task 12: Create remaining valid fixtures

**Files:**
- Create: `tests/fixtures/valid_design_decision.json`
- Create: `tests/fixtures/valid_deferred_scope.json`
- Create: `tests/fixtures/valid_impact_alignment.json`
- Create: `tests/fixtures/invalid_missing_fields.json`
- Create: `tests/fixtures/invalid_bad_enum.json`
- Create: `tests/fixtures/invalid_extra_fields.json`

- [ ] **Step 1: Create valid_design_decision.json**

```json
{
  "schema_version": "1.0.0",
  "certificate_id": "cert-dd-001",
  "certificate_type": "design_decision",
  "workflow_run_id": "run-001",
  "issue_ref": {"artifact_id": "issue-10", "artifact_type": "issue"},
  "produced_by": {"actor_id": "claude-1", "author_kind": "claude", "role": "reviewer_a"},
  "produced_at": "2026-03-11T00:00:00Z",
  "source_artifacts": [{"artifact_id": "src-1", "artifact_type": "design_doc"}],
  "validation_status": "validated",
  "definition": "Design decision is JUSTIFIED iff it matches or exceeds reference patterns.",
  "decision_topic": "Schema validation approach",
  "comparison": {
    "our_pattern": {
      "claim_id": "op1",
      "text": "We use Pydantic models",
      "evidence_refs": [{"evidence_id": "ev-1", "evidence_type": "reference_code", "artifact_ref": {"artifact_id": "a1", "artifact_type": "file"}}]
    },
    "reference_pattern": {
      "claim_id": "rp1",
      "text": "inspect_ai uses Pydantic for structured output",
      "evidence_refs": [{"evidence_id": "ev-2", "evidence_type": "reference_code", "artifact_ref": {"artifact_id": "a2", "artifact_type": "reference_repo"}}]
    },
    "match_status": "matches"
  },
  "formal_conclusion": {
    "status": "justified",
    "derived_from_claim_ids": ["op1", "rp1"]
  }
}
```

- [ ] **Step 2: Create valid_deferred_scope.json**

```json
{
  "schema_version": "1.0.0",
  "certificate_id": "cert-ds-001",
  "certificate_type": "deferred_scope",
  "workflow_run_id": "run-001",
  "issue_ref": {"artifact_id": "issue-20", "artifact_type": "issue"},
  "produced_by": {"actor_id": "claude-1", "author_kind": "claude", "role": "reviewer_a"},
  "produced_at": "2026-03-11T00:00:00Z",
  "source_artifacts": [{"artifact_id": "src-1", "artifact_type": "plan_doc"}],
  "validation_status": "validated",
  "definition": "Deferral is VALID iff tracked with clear criteria and consistent state.",
  "deferred_work": "Referential validation of evidence refs",
  "tracking_issue": {"artifact_id": "issue-21", "artifact_type": "issue"},
  "acceptance_criteria": ["All evidence refs resolve to real artifacts"],
  "roadmap_position": {
    "milestone": "Session 2",
    "blocked_by": [],
    "blocks": [{"artifact_id": "issue-30", "artifact_type": "issue"}]
  },
  "current_deliverable_consistency": {
    "claim_id": "cc1",
    "text": "Current session works without referential validation",
    "evidence_refs": [{"evidence_id": "ev-1", "evidence_type": "test_result", "artifact_ref": {"artifact_id": "a1", "artifact_type": "command_output"}}]
  },
  "evaluation": {
    "tracked": true,
    "acceptance_criteria_clear": true,
    "roadmap_position_valid": true,
    "current_state_consistent": true
  },
  "formal_conclusion": {
    "status": "valid",
    "derived_from_claim_ids": ["cc1"]
  }
}
```

- [ ] **Step 3: Create valid_impact_alignment.json**

```json
{
  "schema_version": "1.0.0",
  "certificate_id": "cert-ia-001",
  "certificate_type": "impact_alignment",
  "workflow_run_id": "run-001",
  "issue_ref": {"artifact_id": "issue-40", "artifact_type": "issue"},
  "produced_by": {"actor_id": "claude-1", "author_kind": "claude", "role": "reviewer_a"},
  "produced_at": "2026-03-11T00:00:00Z",
  "source_artifacts": [{"artifact_id": "src-1", "artifact_type": "pull_request"}],
  "validation_status": "validated",
  "definition": "Change is ALIGNED iff no silent drift from plans.",
  "roadmap_impacts": [],
  "open_issue_scan": [
    {
      "issue_ref": {"artifact_id": "issue-41", "artifact_type": "issue"},
      "impact_status": "none",
      "action": "No action needed",
      "verification": {
        "status": "verified",
        "method": "source_read",
        "verified_by": {"actor_id": "c1", "author_kind": "claude", "role": "reviewer_a"},
        "verified_at": "2026-03-11T00:00:00Z"
      }
    }
  ],
  "documentation_impacts": [],
  "dependency_graph": {
    "unblocked_issues": [],
    "blocked_by_updates": [],
    "new_issues": []
  },
  "formal_conclusion": {
    "status": "aligned",
    "derived_from_claim_ids": ["issue-41"]
  }
}
```

- [ ] **Step 4: Create invalid fixture files**

`tests/fixtures/invalid_missing_fields.json`:
```json
{
  "schema_version": "1.0.0",
  "certificate_type": "task_review"
}
```

`tests/fixtures/invalid_bad_enum.json`:
```json
{
  "schema_version": "1.0.0",
  "certificate_id": "cert-001",
  "certificate_type": "task_review",
  "workflow_run_id": "run-001",
  "issue_ref": {"artifact_id": "issue-42", "artifact_type": "issue"},
  "produced_by": {"actor_id": "c1", "author_kind": "claude", "role": "reviewer_a"},
  "produced_at": "2026-03-11T00:00:00Z",
  "source_artifacts": [{"artifact_id": "s1", "artifact_type": "file"}],
  "validation_status": "INVALID_ENUM_VALUE",
  "definition": "x",
  "premises": [{"claim_id": "p1", "text": "x", "evidence_refs": [{"evidence_id": "e1", "evidence_type": "file_span", "artifact_ref": {"artifact_id": "a1", "artifact_type": "file"}}], "status": "satisfied"}],
  "quality_assertions": [{"claim_id": "q1", "text": "x", "evidence_refs": [{"evidence_id": "e2", "evidence_type": "file_span", "artifact_ref": {"artifact_id": "a2", "artifact_type": "file"}}], "status": "verified"}],
  "verification_commands": [{"command_id": "c1", "command": "pytest", "exit_code": 0, "status": "passed"}],
  "formal_conclusion": {"status": "complete", "derived_from_claim_ids": ["p1"]},
  "issues": []
}
```

`tests/fixtures/invalid_extra_fields.json`:
```json
{
  "schema_version": "1.0.0",
  "certificate_id": "cert-001",
  "certificate_type": "task_review",
  "workflow_run_id": "run-001",
  "issue_ref": {"artifact_id": "issue-42", "artifact_type": "issue"},
  "produced_by": {"actor_id": "c1", "author_kind": "claude", "role": "reviewer_a"},
  "produced_at": "2026-03-11T00:00:00Z",
  "source_artifacts": [{"artifact_id": "s1", "artifact_type": "file"}],
  "validation_status": "validated",
  "definition": "x",
  "premises": [{"claim_id": "p1", "text": "x", "evidence_refs": [{"evidence_id": "e1", "evidence_type": "file_span", "artifact_ref": {"artifact_id": "a1", "artifact_type": "file"}}], "status": "satisfied"}],
  "quality_assertions": [{"claim_id": "q1", "text": "x", "evidence_refs": [{"evidence_id": "e2", "evidence_type": "file_span", "artifact_ref": {"artifact_id": "a2", "artifact_type": "file"}}], "status": "verified"}],
  "verification_commands": [{"command_id": "c1", "command": "pytest", "exit_code": 0, "status": "passed"}],
  "formal_conclusion": {"status": "complete", "derived_from_claim_ids": ["p1"]},
  "issues": [],
  "unexpected_extra_field": "should cause validation error"
}
```

- [ ] **Step 5: Commit fixtures**

```bash
git add tests/fixtures/
git commit -m "test(s1): add certificate fixtures for validation testing"
```

---

### Task 13: Fixture validation tests — red then green

**Files:**
- Modify: `tests/test_models.py`

- [ ] **Step 1: Add tests for remaining fixtures and invalid cases**

Append to `tests/test_models.py`:

```python
from sdlc_control_plane.verification.models import (
    DesignDecisionCertificate,
    DeferredScopeCertificate,
    ImpactAlignmentCertificate,
)


class TestDesignDecisionCertificate:
    def test_valid_from_fixture(self) -> None:
        data = json.loads((FIXTURES / "valid_design_decision.json").read_text())
        cert = DesignDecisionCertificate.model_validate(data)
        assert cert.certificate_type == CertificateType.DESIGN_DECISION


class TestDeferredScopeCertificate:
    def test_valid_from_fixture(self) -> None:
        data = json.loads((FIXTURES / "valid_deferred_scope.json").read_text())
        cert = DeferredScopeCertificate.model_validate(data)
        assert cert.certificate_type == CertificateType.DEFERRED_SCOPE


class TestImpactAlignmentCertificate:
    def test_valid_from_fixture(self) -> None:
        data = json.loads((FIXTURES / "valid_impact_alignment.json").read_text())
        cert = ImpactAlignmentCertificate.model_validate(data)
        assert cert.certificate_type == CertificateType.IMPACT_ALIGNMENT


class TestInvalidCertificates:
    def test_missing_fields_rejected(self) -> None:
        data = json.loads((FIXTURES / "invalid_missing_fields.json").read_text())
        with pytest.raises(ValidationError):
            TaskReviewCertificate.model_validate(data)

    def test_bad_enum_rejected(self) -> None:
        data = json.loads((FIXTURES / "invalid_bad_enum.json").read_text())
        with pytest.raises(ValidationError):
            TaskReviewCertificate.model_validate(data)

    def test_extra_field_rejected(self) -> None:
        data = json.loads((FIXTURES / "invalid_extra_fields.json").read_text())
        with pytest.raises(ValidationError):
            TaskReviewCertificate.model_validate(data)

    def test_validate_certificate_dispatches_all_types(self) -> None:
        for fixture_name, expected_type in [
            ("valid_task_review.json", TaskReviewCertificate),
            ("valid_design_decision.json", DesignDecisionCertificate),
            ("valid_deferred_scope.json", DeferredScopeCertificate),
            ("valid_impact_alignment.json", ImpactAlignmentCertificate),
        ]:
            data = json.loads((FIXTURES / fixture_name).read_text())
            cert = validate_certificate(data)
            assert isinstance(cert, expected_type), f"Failed for {fixture_name}"
```

- [ ] **Step 2: Run tests to verify they pass** (models already exist from previous tasks)

Run: `uv run pytest tests/test_models.py -x -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_models.py
git commit -m "test(s1): add fixture-based validation tests for all certificate types"
```

---

### Task 14: CLI implementation — red tests

**Files:**
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli.py`:

```python
"""Tests for the sdlc validate CLI command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sdlc_control_plane.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


class TestValidateCLI:
    def setup_method(self) -> None:
        self.runner = CliRunner()

    def test_valid_file_exits_0(self) -> None:
        result = self.runner.invoke(main, ["validate", str(FIXTURES / "valid_task_review.json")])
        assert result.exit_code == 0

    def test_invalid_file_exits_1(self) -> None:
        result = self.runner.invoke(main, ["validate", str(FIXTURES / "invalid_missing_fields.json")])
        assert result.exit_code == 1

    def test_nonexistent_file_exits_2(self) -> None:
        result = self.runner.invoke(main, ["validate", "/tmp/nonexistent_cert.json"])
        assert result.exit_code == 2

    def test_type_override(self) -> None:
        result = self.runner.invoke(
            main, ["validate", "--type", "task_review", str(FIXTURES / "valid_task_review.json")]
        )
        assert result.exit_code == 0

    def test_multiple_files_mixed(self) -> None:
        result = self.runner.invoke(
            main,
            [
                "validate",
                str(FIXTURES / "valid_task_review.json"),
                str(FIXTURES / "invalid_missing_fields.json"),
            ],
        )
        assert result.exit_code == 1

    def test_file_error_priority_over_validation_error(self) -> None:
        result = self.runner.invoke(
            main,
            [
                "validate",
                str(FIXTURES / "invalid_missing_fields.json"),
                "/tmp/nonexistent_cert.json",
            ],
        )
        assert result.exit_code == 2

    def test_valid_output_contains_filename(self) -> None:
        result = self.runner.invoke(main, ["validate", str(FIXTURES / "valid_task_review.json")])
        assert "valid_task_review.json" in result.output

    def test_invalid_output_contains_error_detail(self) -> None:
        result = self.runner.invoke(main, ["validate", str(FIXTURES / "invalid_missing_fields.json")])
        assert result.exit_code == 1
        assert "missing" in result.output.lower() or "required" in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -x -v`
Expected: FAIL — the current `validate` command takes no arguments

---

### Task 15: CLI implementation — green

**Files:**
- Modify: `src/sdlc_control_plane/cli/__init__.py`

- [ ] **Step 1: Replace the validate command stub with full implementation**

Write `src/sdlc_control_plane/cli/__init__.py`:

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

from sdlc_control_plane.verification.models import (
    CERTIFICATE_MODELS,
    validate_certificate,
)

console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """SDLC Control Plane -- certificate-driven development governance."""


@main.command()
@click.argument("files", nargs=-1, required=True, type=click.Path())
@click.option("--type", "cert_type", default=None, help="Certificate type override.")
def validate(files: tuple[str, ...], cert_type: str | None) -> None:
    """Validate certificate artifacts against the schema bundle."""
    exit_code = 0

    for file_path_str in files:
        file_path = Path(file_path_str)

        # File access errors
        if not file_path.exists():
            console.print(f"[red]✗[/red] {file_path} — file not found")
            exit_code = max(exit_code, 2)
            continue

        try:
            data: dict[str, Any] = json.loads(file_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            console.print(f"[red]✗[/red] {file_path} — {e}")
            exit_code = max(exit_code, 2)
            continue

        # Apply type override if given
        if cert_type is not None:
            data["certificate_type"] = cert_type

        # Validate
        try:
            validate_certificate(data)
            console.print(f"[green]✓[/green] {file_path}")
        except KeyError as e:
            console.print(f"[red]✗[/red] {file_path} — {e}")
            exit_code = max(exit_code, 1)
        except ValidationError as e:
            console.print(f"[red]✗[/red] {file_path}")
            for error in e.errors():
                loc = " → ".join(str(p) for p in error["loc"])
                console.print(f"    {loc}: {error['msg']}")
            exit_code = max(exit_code, 1)

    sys.exit(exit_code)
```

- [ ] **Step 2: Run CLI tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -x -v`
Expected: All tests PASS

- [ ] **Step 3: Run all tests**

Run: `uv run pytest -x -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/sdlc_control_plane/cli/__init__.py tests/test_cli.py
git commit -m "feat(s1): implement sdlc validate CLI with Rich output and exit codes"
```

---

### Task 16: Schema drift detection — red tests

**Files:**
- Create: `tests/test_schema_drift.py`

- [ ] **Step 1: Write drift detection tests**

Create `tests/test_schema_drift.py`:

```python
"""Drift detection: verify Pydantic models stay in sync with the JSON Schema bundle.

Compares structural properties (required fields, enum values, field presence)
rather than exact JSON Schema output, since Pydantic v2 generates schemas
in a different format than hand-written JSON Schema.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sdlc_control_plane.verification import models

SCHEMA_BUNDLE = json.loads(
    (Path(__file__).parent.parent / "schemas" / "agent_workflow_schema_bundle.json").read_text()
)
DEFS: dict[str, Any] = SCHEMA_BUNDLE["$defs"]

# Map from schema $defs name to Pydantic model class
MODEL_MAP: dict[str, type] = {
    "Actor": models.Actor,
    "Locator": models.Locator,
    "ArtifactRef": models.ArtifactRef,
    "EvidenceRef": models.EvidenceRef,
    "VerificationRecord": models.VerificationRecord,
    "ClaimBase": models.ClaimBase,
    "PremiseClaim": models.PremiseClaim,
    "QualityAssertion": models.QualityAssertion,
    "IssueFinding": models.IssueFinding,
    "CommandVerification": models.CommandVerification,
    "FormalConclusion": models.FormalConclusion,
    "GateEvaluation": models.GateEvaluation,
    "CertificateEnvelope": models.CertificateEnvelope,
    "TaskReviewCertificate": models.TaskReviewCertificate,
    "DesignDecisionCertificate": models.DesignDecisionCertificate,
    "DeferredScopeCertificate": models.DeferredScopeCertificate,
    "ImpactAlignmentCertificate": models.ImpactAlignmentCertificate,
    "DisputeObject": models.DisputeObject,
    "TransitionRequest": models.TransitionRequest,
    "RemediationLogEntry": models.RemediationLogEntry,
    "RemediationLog": models.RemediationLog,
    "WorkflowEvent": models.WorkflowEvent,
    "DesignComparison": models.DesignComparison,
    "RoadmapPosition": models.RoadmapPosition,
    "DeferredEvaluation": models.DeferredEvaluation,
    "IssueImpactAssessment": models.IssueImpactAssessment,
    "DocumentationImpact": models.DocumentationImpact,
}

# Enum-only $defs (no "required" to check, just enum values)
ENUM_MAP: dict[str, type] = {
    "Severity": models.Severity,
    "AuthorKind": models.AuthorKind,
    "ExecutorType": models.ExecutorType,
    "WorkflowState": models.WorkflowState,
    "ArtifactType": models.ArtifactType,
    "EvidenceType": models.EvidenceType,
    "VerificationMethod": models.VerificationMethod,
    "VerifiedStatus": models.VerifiedStatus,
}


def _collect_required(schema_def: dict[str, Any]) -> set[str]:
    """Collect all required fields from a schema def, following allOf."""
    required: set[str] = set()
    if "required" in schema_def:
        required.update(schema_def["required"])
    for item in schema_def.get("allOf", []):
        if "required" in item:
            required.update(item["required"])
        # Follow $ref to collect parent required fields
        if "$ref" in item:
            ref_name = item["$ref"].split("/")[-1]
            if ref_name in DEFS:
                required.update(_collect_required(DEFS[ref_name]))
    return required


def _collect_properties(schema_def: dict[str, Any]) -> set[str]:
    """Collect all property names from a schema def, following allOf."""
    props: set[str] = set()
    if "properties" in schema_def:
        props.update(schema_def["properties"].keys())
    for item in schema_def.get("allOf", []):
        if "properties" in item:
            props.update(item["properties"].keys())
        if "$ref" in item:
            ref_name = item["$ref"].split("/")[-1]
            if ref_name in DEFS:
                props.update(_collect_properties(DEFS[ref_name]))
    return props


def _get_pydantic_fields(model_cls: type) -> set[str]:
    """Get all field names from a Pydantic model including inherited."""
    if hasattr(model_cls, "model_fields"):
        return set(model_cls.model_fields.keys())
    return set()


def _get_pydantic_required(model_cls: type) -> set[str]:
    """Get required field names from a Pydantic model."""
    if hasattr(model_cls, "model_fields"):
        return {
            name
            for name, field in model_cls.model_fields.items()
            if field.is_required()
        }
    return set()


class TestEnumDrift:
    @pytest.mark.parametrize("name,enum_cls", list(ENUM_MAP.items()))
    def test_enum_values_match(self, name: str, enum_cls: type) -> None:
        schema_values = set(DEFS[name]["enum"])
        pydantic_values = {e.value for e in enum_cls}  # type: ignore[attr-defined]
        assert schema_values == pydantic_values, (
            f"Enum {name} drift: schema={schema_values - pydantic_values}, "
            f"pydantic={pydantic_values - schema_values}"
        )


class TestModelDrift:
    @pytest.mark.parametrize("name,model_cls", list(MODEL_MAP.items()))
    def test_required_fields_match(self, name: str, model_cls: type) -> None:
        schema_required = _collect_required(DEFS[name])
        pydantic_required = _get_pydantic_required(model_cls)
        assert schema_required == pydantic_required, (
            f"Model {name} required drift: "
            f"schema_only={schema_required - pydantic_required}, "
            f"pydantic_only={pydantic_required - schema_required}"
        )

    @pytest.mark.parametrize("name,model_cls", list(MODEL_MAP.items()))
    def test_property_names_match(self, name: str, model_cls: type) -> None:
        schema_props = _collect_properties(DEFS[name])
        pydantic_fields = _get_pydantic_fields(model_cls)
        assert schema_props == pydantic_fields, (
            f"Model {name} property drift: "
            f"schema_only={schema_props - pydantic_fields}, "
            f"pydantic_only={pydantic_fields - schema_props}"
        )


class TestAllDefsHaveModels:
    def test_every_schema_def_has_model_or_enum(self) -> None:
        """Every $defs entry should map to either a model or enum."""
        # These are constrained string types handled as Annotated aliases
        STRING_TYPES = {"NonEmptyString", "Id", "Sha256", "Timestamp"}
        covered = set(MODEL_MAP) | set(ENUM_MAP) | STRING_TYPES
        schema_defs = set(DEFS.keys())
        uncovered = schema_defs - covered
        assert not uncovered, f"Schema $defs without Pydantic mapping: {uncovered}"
```

- [ ] **Step 2: Run tests to verify they fail** (if any model mismatch exists) **or pass** (if models are correct)

Run: `uv run pytest tests/test_schema_drift.py -x -v`
Expected: Likely some failures from drift — fix in next step

---

### Task 17: Fix any drift detected

**Files:**
- Modify: `src/sdlc_control_plane/verification/models.py` (if needed)
- Modify: `tests/test_schema_drift.py` (if needed)

- [ ] **Step 1: Analyze drift failures and fix models or tests**

Review each failure:
- Missing fields: add to model
- Extra fields: remove from model or add to schema map
- Required mismatch: adjust default values

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest -x -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/sdlc_control_plane/verification/models.py tests/test_schema_drift.py
git commit -m "test(s1): add schema drift detection and fix any mismatches"
```

---

### Task 18: Lint, type check, and final quality pass

**Files:** (none new)

- [ ] **Step 1: Run ruff**

Run: `uv run ruff check src/ tests/`
Fix any issues found.

- [ ] **Step 2: Run ruff format**

Run: `uv run ruff format src/ tests/`

- [ ] **Step 3: Run mypy**

Run: `uv run mypy src/`
Fix any type errors found.

- [ ] **Step 4: Run full check suite**

Run: `make check`
Expected: All lint, typecheck, and tests pass

- [ ] **Step 5: Commit any fixes**

```bash
git add -u
git commit -m "refactor(s1): fix lint and type issues"
```

---

### Task 19: Manual smoke test

- [ ] **Step 1: Test CLI with valid file**

Run: `uv run sdlc validate tests/fixtures/valid_task_review.json`
Expected: Green checkmark, exit code 0

- [ ] **Step 2: Test CLI with invalid file**

Run: `uv run sdlc validate tests/fixtures/invalid_missing_fields.json`
Expected: Red X with error details, exit code 1

- [ ] **Step 3: Test CLI with nonexistent file**

Run: `uv run sdlc validate /tmp/nonexistent.json`
Expected: Red X "file not found", exit code 2

- [ ] **Step 4: Test CLI with --type override**

Run: `uv run sdlc validate --type design_decision tests/fixtures/valid_design_decision.json`
Expected: Green checkmark, exit code 0

---

### Task 20: Final commit and PR readiness

- [ ] **Step 1: Run `make check` one final time**

Run: `make check`
Expected: All pass

- [ ] **Step 2: Review git log**

Run: `git log --oneline feat/s1-schema-validation`
Expected: Clean conventional commit history

- [ ] **Step 3: Push branch**

Run: `git push -u origin feat/s1-schema-validation`
