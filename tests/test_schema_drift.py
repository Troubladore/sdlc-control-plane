"""Drift detection: verify Pydantic models stay in sync with the JSON Schema bundle."""

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

# ---------------------------------------------------------------------------
# Mapping: schema $defs name -> Pydantic model class
# ---------------------------------------------------------------------------

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

# Constrained string types that don't have a model class
STRING_TYPES = {"NonEmptyString", "Id", "Sha256", "Timestamp"}


# ---------------------------------------------------------------------------
# Helpers to collect schema info from $defs (handling allOf composition)
# ---------------------------------------------------------------------------


def _collect_from_schema(
    schema_def: dict[str, Any],
    key: str,
    extract: Any = None,
) -> set[str]:
    """Collect field names from a schema def, following allOf and $ref.

    For 'required': collects the list values directly.
    For 'properties': collects the dict keys.
    """
    if extract is None:
        extract = dict.keys if key == "properties" else list.__iter__

    result: set[str] = set()
    if key in schema_def:
        val = schema_def[key]
        result.update(val.keys() if isinstance(val, dict) else val)
    for item in schema_def.get("allOf", []):
        if key in item:
            val = item[key]
            result.update(val.keys() if isinstance(val, dict) else val)
        if "$ref" in item:
            ref_name = item["$ref"].split("/")[-1]
            if ref_name in DEFS:
                result.update(_collect_from_schema(DEFS[ref_name], key))
    return result


def _get_pydantic_fields(model_cls: type) -> set[str]:
    """Get all field names from a Pydantic model."""
    if hasattr(model_cls, "model_fields"):
        return set(model_cls.model_fields.keys())
    return set()


def _get_pydantic_required(model_cls: type) -> set[str]:
    """Get required field names from a Pydantic model."""
    if hasattr(model_cls, "model_fields"):
        return {name for name, field in model_cls.model_fields.items() if field.is_required()}
    return set()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEnumDrift:
    @pytest.mark.parametrize("name,enum_cls", list(ENUM_MAP.items()))
    def test_enum_values_match(self, name: str, enum_cls: type) -> None:
        schema_values = set(DEFS[name]["enum"])
        pydantic_values = {e.value for e in enum_cls}  # type: ignore[var-annotated]
        assert schema_values == pydantic_values, (
            f"Enum {name} drift: schema={schema_values - pydantic_values}, "
            f"pydantic={pydantic_values - schema_values}"
        )


class TestModelDrift:
    @pytest.mark.parametrize("name,model_cls", list(MODEL_MAP.items()))
    def test_required_fields_match(self, name: str, model_cls: type) -> None:
        schema_required = _collect_from_schema(DEFS[name], "required")
        pydantic_required = _get_pydantic_required(model_cls)
        assert schema_required == pydantic_required, (
            f"Model {name} required drift: "
            f"schema_only={schema_required - pydantic_required}, "
            f"pydantic_only={pydantic_required - schema_required}"
        )

    @pytest.mark.parametrize("name,model_cls", list(MODEL_MAP.items()))
    def test_property_names_match(self, name: str, model_cls: type) -> None:
        schema_props = _collect_from_schema(DEFS[name], "properties")
        pydantic_fields = _get_pydantic_fields(model_cls)
        assert schema_props == pydantic_fields, (
            f"Model {name} property drift: "
            f"schema_only={schema_props - pydantic_fields}, "
            f"pydantic_only={pydantic_fields - schema_props}"
        )


class TestAllDefsHaveModels:
    def test_every_schema_def_has_model_or_enum(self) -> None:
        covered = set(MODEL_MAP) | set(ENUM_MAP) | STRING_TYPES
        schema_defs = set(DEFS.keys())
        uncovered = schema_defs - covered
        assert not uncovered, f"Schema $defs without Pydantic mapping: {uncovered}"
