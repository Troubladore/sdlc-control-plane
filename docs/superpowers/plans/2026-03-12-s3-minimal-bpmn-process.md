# S3: Minimal BPMN Process (Happy Path) — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy a minimal 6-phase BPMN process to Camunda and prove the happy path completes via Operate.

**Architecture:** Hand-authored BPMN XML with 6 sequential service tasks (Triage -> Design -> Planning -> Implement -> Review -> Integrate). Thin pyzeebe-based facade in `orchestration/` with lazy conditional imports. `SyncZeebeClient` for deploy/start operations; `asyncio.run()` wrapping `ZeebeWorker` for job completion only.

**Tech Stack:** Python 3.10+, pyzeebe 4.x, Pydantic, BPMN 2.0 XML, httpx (dev), Camunda 8.8 CI cluster

**Spec:** `docs/superpowers/specs/2026-03-11-s3-minimal-bpmn-process-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `processes/issue-lifecycle.bpmn` | BPMN 2.0 process model — 6 sequential service tasks |
| Create | `src/sdlc_control_plane/orchestration/config.py` | `ZeebeConfig` Pydantic model, `from_env()` classmethod |
| Create | `src/sdlc_control_plane/orchestration/client.py` | `ZeebeClient` facade — deploy, start, run_worker |
| Modify | `src/sdlc_control_plane/orchestration/__init__.py` | Re-export `ZeebeConfig`, `ZeebeClient` |
| Create | `tests/test_orchestration_config.py` | Unit tests for ZeebeConfig |
| Create | `tests/test_orchestration_client.py` | Unit tests for ZeebeClient (mocked pyzeebe) |
| Create | `tests/test_bpmn.py` | Unit tests for BPMN artifact correctness |
| Create | `tests/test_workflow_integration.py` | Integration test — full happy path against CI cluster |
| Modify | `tests/conftest.py` | Integration fixtures (zeebe_available, cleanup) |
| Modify | `pyproject.toml` | Add `httpx` dev dep, register `integration` marker |
| Modify | `Makefile` | Add `test-integration` target |
| Modify | `.env.example` | Add CI cluster comment |

---

## Chunk 1: Project Configuration and BPMN Artifact

### Task 1: Project Configuration Updates

**Files:**
- Modify: `pyproject.toml`
- Modify: `Makefile`
- Modify: `.env.example`

- [ ] **Step 1: Add `httpx` to dev dependencies and register integration marker**

In `pyproject.toml`, add `httpx` to `[project.optional-dependencies].dev` and
add the `integration` marker to pytest config:

```toml
# In [project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "hypothesis>=6.90",
    "mypy>=1.8",
    "ruff>=0.3",
    "httpx>=0.27",
]

# In [tool.pytest.ini_options] — add markers and default deselection:
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
markers = ["integration: requires live Camunda cluster"]
addopts = "-m 'not integration'"
```

The `addopts = "-m 'not integration'"` line ensures `make test` (and bare
`pytest`) never collects integration tests. Integration tests run only via
the explicit `make test-integration` target which passes `-m integration`.

- [ ] **Step 2: Add `test-integration` Makefile target**

Add to `Makefile` after the existing `check` target:

Also update the `.PHONY` line at the top of the Makefile to include `test-integration`:

```makefile
.PHONY: test test-all lint typecheck check fmt test-integration
```

Then add the target after the existing `check` target:

```makefile
test-integration:
	uv run pytest -m integration -v
```

- [ ] **Step 3: Add CI cluster comment to `.env.example`**

Add a comment block to `.env.example`:

```bash
# Camunda 8 connection (decoupled -- bring your own cluster)
ZEEBE_GRPC=localhost:26500
ZEEBE_REST=http://localhost:8088
CAMUNDA_OPERATE_URL=http://localhost:8088

# CI cluster (for automated tests, no auth required):
# ZEEBE_GRPC=localhost:36500
# ZEEBE_REST=http://localhost:18088
# CAMUNDA_OPERATE_URL=http://localhost:18088

# LLM reviewer APIs (Session 13 -- mock reviewers until then)
# OPENAI_API_KEY=sk-...
# GOOGLE_API_KEY=...
```

- [ ] **Step 4: Sync dependencies (both dev and camunda extras)**

Run: `uv sync --extra dev --extra camunda`
Expected: httpx and pyzeebe installed, lock file updated.
Both extras are needed: `dev` for test tooling (httpx, pytest, etc.) and
`camunda` for pyzeebe (required by `ZeebeClient` and integration tests).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml Makefile .env.example uv.lock
git commit -m "build: add httpx dev dep, integration marker, test-integration target"
```

---

### Task 2: BPMN Process Model

**Files:**
- Create: `processes/issue-lifecycle.bpmn`
- Create: `tests/test_bpmn.py`

- [ ] **Step 1: Write failing tests for the BPMN artifact**

Create `tests/test_bpmn.py`:

```python
"""Tests for the BPMN process model artifact."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

BPMN_PATH = Path(__file__).resolve().parent.parent / "processes" / "issue-lifecycle.bpmn"

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
ZEEBE_NS = "http://camunda.org/schema/zeebe/1.0"

EXPECTED_PHASES = ["triage", "design", "planning", "implement", "review", "integrate"]


def test_bpmn_file_exists() -> None:
    assert BPMN_PATH.exists(), f"BPMN file not found at {BPMN_PATH}"


def test_bpmn_well_formed_xml() -> None:
    ET.parse(BPMN_PATH)  # Raises ParseError if malformed


def test_bpmn_process_id() -> None:
    tree = ET.parse(BPMN_PATH)
    root = tree.getroot()
    ns = {"bpmn": BPMN_NS}
    processes = root.findall("bpmn:process", ns)
    assert len(processes) == 1
    assert processes[0].get("id") == "issue-lifecycle"
    assert processes[0].get("isExecutable") == "true"


def test_bpmn_zeebe_namespace_declared() -> None:
    text = BPMN_PATH.read_text()
    assert ZEEBE_NS in text, "Zeebe extension namespace not declared"


def test_bpmn_six_service_tasks() -> None:
    tree = ET.parse(BPMN_PATH)
    root = tree.getroot()
    ns = {"bpmn": BPMN_NS}
    process = root.find("bpmn:process", ns)
    assert process is not None
    tasks = process.findall("bpmn:serviceTask", ns)
    assert len(tasks) == 6, f"Expected 6 service tasks, got {len(tasks)}"


def test_bpmn_task_ids() -> None:
    tree = ET.parse(BPMN_PATH)
    root = tree.getroot()
    ns = {"bpmn": BPMN_NS}
    process = root.find("bpmn:process", ns)
    assert process is not None
    tasks = process.findall("bpmn:serviceTask", ns)
    task_ids = [t.get("id") for t in tasks]
    expected_ids = [f"Activity_{phase}" for phase in EXPECTED_PHASES]
    assert task_ids == expected_ids


def test_bpmn_job_types() -> None:
    tree = ET.parse(BPMN_PATH)
    root = tree.getroot()
    ns = {"bpmn": BPMN_NS, "zeebe": ZEEBE_NS}
    process = root.find("bpmn:process", ns)
    assert process is not None
    tasks = process.findall("bpmn:serviceTask", ns)
    job_types: list[str] = []
    for task in tasks:
        ext = task.find("bpmn:extensionElements", ns)
        assert ext is not None, f"No extensionElements on {task.get('id')}"
        td = ext.find("zeebe:taskDefinition", ns)
        assert td is not None, f"No zeebe:taskDefinition on {task.get('id')}"
        jt = td.get("type")
        assert jt is not None
        job_types.append(jt)
    assert job_types == EXPECTED_PHASES


def test_bpmn_sequence_flow_connectivity() -> None:
    """Verify start -> 6 tasks in order -> end via sequence flows."""
    tree = ET.parse(BPMN_PATH)
    root = tree.getroot()
    ns = {"bpmn": BPMN_NS}
    process = root.find("bpmn:process", ns)
    assert process is not None

    # Build adjacency from sequence flows
    flows: dict[str, str] = {}
    for sf in process.findall("bpmn:sequenceFlow", ns):
        src = sf.get("sourceRef")
        tgt = sf.get("targetRef")
        assert src is not None and tgt is not None
        flows[src] = tgt

    # Walk the chain: StartEvent_1 -> ... -> EndEvent_1
    expected_chain = (
        ["StartEvent_1"]
        + [f"Activity_{p}" for p in EXPECTED_PHASES]
        + ["EndEvent_1"]
    )
    for i in range(len(expected_chain) - 1):
        src = expected_chain[i]
        assert src in flows, f"No outgoing flow from {src}"
        assert flows[src] == expected_chain[i + 1], (
            f"Expected {src} -> {expected_chain[i + 1]}, got {src} -> {flows[src]}"
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bpmn.py -v`
Expected: FAIL — `processes/issue-lifecycle.bpmn` does not exist

- [ ] **Step 3: Create the BPMN process model**

Create `processes/issue-lifecycle.bpmn`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                  xmlns:zeebe="http://camunda.org/schema/zeebe/1.0"
                  id="Definitions_1"
                  targetNamespace="http://bpmn.io/schema/bpmn"
                  exporter="sdlc-control-plane"
                  exporterVersion="0.1.0">

  <bpmn:process id="issue-lifecycle" name="Issue Lifecycle" isExecutable="true">

    <bpmn:startEvent id="StartEvent_1" name="Issue Assigned">
      <bpmn:outgoing>Flow_start_triage</bpmn:outgoing>
    </bpmn:startEvent>

    <bpmn:serviceTask id="Activity_triage" name="Triage">
      <bpmn:extensionElements>
        <zeebe:taskDefinition type="triage" />
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_start_triage</bpmn:incoming>
      <bpmn:outgoing>Flow_triage_design</bpmn:outgoing>
    </bpmn:serviceTask>

    <bpmn:serviceTask id="Activity_design" name="Design">
      <bpmn:extensionElements>
        <zeebe:taskDefinition type="design" />
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_triage_design</bpmn:incoming>
      <bpmn:outgoing>Flow_design_planning</bpmn:outgoing>
    </bpmn:serviceTask>

    <bpmn:serviceTask id="Activity_planning" name="Planning">
      <bpmn:extensionElements>
        <zeebe:taskDefinition type="planning" />
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_design_planning</bpmn:incoming>
      <bpmn:outgoing>Flow_planning_implement</bpmn:outgoing>
    </bpmn:serviceTask>

    <bpmn:serviceTask id="Activity_implement" name="Implement">
      <bpmn:extensionElements>
        <zeebe:taskDefinition type="implement" />
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_planning_implement</bpmn:incoming>
      <bpmn:outgoing>Flow_implement_review</bpmn:outgoing>
    </bpmn:serviceTask>

    <bpmn:serviceTask id="Activity_review" name="Review">
      <bpmn:extensionElements>
        <zeebe:taskDefinition type="review" />
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_implement_review</bpmn:incoming>
      <bpmn:outgoing>Flow_review_integrate</bpmn:outgoing>
    </bpmn:serviceTask>

    <bpmn:serviceTask id="Activity_integrate" name="Integrate">
      <bpmn:extensionElements>
        <zeebe:taskDefinition type="integrate" />
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_review_integrate</bpmn:incoming>
      <bpmn:outgoing>Flow_integrate_end</bpmn:outgoing>
    </bpmn:serviceTask>

    <bpmn:endEvent id="EndEvent_1" name="Issue Complete">
      <bpmn:incoming>Flow_integrate_end</bpmn:incoming>
    </bpmn:endEvent>

    <bpmn:sequenceFlow id="Flow_start_triage" sourceRef="StartEvent_1" targetRef="Activity_triage" />
    <bpmn:sequenceFlow id="Flow_triage_design" sourceRef="Activity_triage" targetRef="Activity_design" />
    <bpmn:sequenceFlow id="Flow_design_planning" sourceRef="Activity_design" targetRef="Activity_planning" />
    <bpmn:sequenceFlow id="Flow_planning_implement" sourceRef="Activity_planning" targetRef="Activity_implement" />
    <bpmn:sequenceFlow id="Flow_implement_review" sourceRef="Activity_implement" targetRef="Activity_review" />
    <bpmn:sequenceFlow id="Flow_review_integrate" sourceRef="Activity_review" targetRef="Activity_integrate" />
    <bpmn:sequenceFlow id="Flow_integrate_end" sourceRef="Activity_integrate" targetRef="EndEvent_1" />

  </bpmn:process>

</bpmn:definitions>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_bpmn.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `uv run pytest -x -q`
Expected: All existing tests + new BPMN tests pass

- [ ] **Step 6: Commit**

```bash
git add processes/issue-lifecycle.bpmn tests/test_bpmn.py
git commit -m "feat(s3): add BPMN issue-lifecycle process model with unit tests"
```

---

## Chunk 2: Orchestration Config and Client

### Task 3: ZeebeConfig

**Files:**
- Create: `src/sdlc_control_plane/orchestration/config.py`
- Create: `tests/test_orchestration_config.py`

- [ ] **Step 1: Write failing tests for ZeebeConfig**

Create `tests/test_orchestration_config.py`:

```python
"""Tests for orchestration configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from sdlc_control_plane.orchestration.config import ZeebeConfig


class TestZeebeConfigDefaults:
    def test_defaults(self) -> None:
        config = ZeebeConfig()
        assert config.zeebe_grpc == "localhost:26500"
        assert config.zeebe_rest == "http://localhost:8088"
        assert config.camunda_operate_url == "http://localhost:8088"

    def test_custom_values(self) -> None:
        config = ZeebeConfig(
            zeebe_grpc="myhost:26500",
            zeebe_rest="http://myhost:8088",
            camunda_operate_url="http://myhost:8088",
        )
        assert config.zeebe_grpc == "myhost:26500"
        assert config.zeebe_rest == "http://myhost:8088"


class TestZeebeConfigFromEnv:
    def test_reads_env_vars(self) -> None:
        env = {
            "ZEEBE_GRPC": "remotehost:26500",
            "ZEEBE_REST": "http://remotehost:8088",
            "CAMUNDA_OPERATE_URL": "http://remotehost:9090",
        }
        with patch.dict(os.environ, env, clear=False):
            config = ZeebeConfig.from_env()
        assert config.zeebe_grpc == "remotehost:26500"
        assert config.zeebe_rest == "http://remotehost:8088"
        assert config.camunda_operate_url == "http://remotehost:9090"

    def test_uses_defaults_when_env_absent(self) -> None:
        env_keys = ["ZEEBE_GRPC", "ZEEBE_REST", "CAMUNDA_OPERATE_URL"]
        cleaned = {k: v for k, v in os.environ.items() if k not in env_keys}
        with patch.dict(os.environ, cleaned, clear=True):
            config = ZeebeConfig.from_env()
        assert config.zeebe_grpc == "localhost:26500"

    def test_partial_env(self) -> None:
        with patch.dict(os.environ, {"ZEEBE_GRPC": "custom:9999"}, clear=False):
            config = ZeebeConfig.from_env()
        assert config.zeebe_grpc == "custom:9999"
        assert config.zeebe_rest == "http://localhost:8088"


class TestZeebeConfigValidation:
    def test_zeebe_rest_requires_http_scheme(self) -> None:
        with pytest.raises(ValidationError, match="zeebe_rest"):
            ZeebeConfig(zeebe_rest="localhost:8088")

    def test_camunda_operate_url_requires_http_scheme(self) -> None:
        with pytest.raises(ValidationError, match="camunda_operate_url"):
            ZeebeConfig(camunda_operate_url="localhost:8088")

    def test_zeebe_rest_accepts_https(self) -> None:
        config = ZeebeConfig(zeebe_rest="https://secure:8088")
        assert config.zeebe_rest == "https://secure:8088"

    def test_zeebe_grpc_rejects_http_scheme(self) -> None:
        with pytest.raises(ValidationError, match="zeebe_grpc"):
            ZeebeConfig(zeebe_grpc="http://localhost:26500")

    def test_zeebe_grpc_accepts_host_port(self) -> None:
        config = ZeebeConfig(zeebe_grpc="myhost:26500")
        assert config.zeebe_grpc == "myhost:26500"

    def test_zeebe_grpc_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            ZeebeConfig(zeebe_grpc="")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_orchestration_config.py -v`
Expected: FAIL — `config.py` module does not exist

- [ ] **Step 3: Implement ZeebeConfig**

Create `src/sdlc_control_plane/orchestration/config.py`:

```python
"""Zeebe/Camunda connection configuration."""

from __future__ import annotations

import os

from pydantic import BaseModel, field_validator


class ZeebeConfig(BaseModel):
    """Connection settings for Zeebe and Camunda services.

    Use ``from_env()`` to load from environment variables.
    """

    zeebe_grpc: str = "localhost:26500"
    zeebe_rest: str = "http://localhost:8088"
    camunda_operate_url: str = "http://localhost:8088"

    @field_validator("zeebe_grpc")
    @classmethod
    def _validate_grpc_address(cls, v: str) -> str:
        if not v:
            raise ValueError("zeebe_grpc must not be empty")
        if v.startswith(("http://", "https://")):
            raise ValueError(
                "zeebe_grpc must be host:port without scheme, got: " + v
            )
        return v

    @field_validator("zeebe_rest", "camunda_operate_url")
    @classmethod
    def _validate_http_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("must start with http:// or https://, got: " + v)
        return v

    @classmethod
    def from_env(cls) -> ZeebeConfig:
        """Create config from environment variables with defaults."""
        kwargs: dict[str, str] = {}
        env_map = {
            "ZEEBE_GRPC": "zeebe_grpc",
            "ZEEBE_REST": "zeebe_rest",
            "CAMUNDA_OPERATE_URL": "camunda_operate_url",
        }
        for env_key, field_name in env_map.items():
            val = os.environ.get(env_key)
            if val is not None:
                kwargs[field_name] = val
        return cls(**kwargs)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_orchestration_config.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/sdlc_control_plane/orchestration/config.py tests/test_orchestration_config.py
git commit -m "feat(s3): add ZeebeConfig with env var loading and validation"
```

---

### Task 4: ZeebeClient Facade

**Files:**
- Create: `src/sdlc_control_plane/orchestration/client.py`
- Modify: `src/sdlc_control_plane/orchestration/__init__.py`
- Create: `tests/test_orchestration_client.py`

- [ ] **Step 1: Write failing tests for ZeebeClient**

Create `tests/test_orchestration_client.py`:

```python
"""Tests for orchestration client facade."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from sdlc_control_plane.orchestration.config import ZeebeConfig


class TestConditionalImport:
    def test_module_imports_without_pyzeebe(self) -> None:
        """The orchestration.client module should import cleanly even
        when pyzeebe is not installed."""
        # Force-remove pyzeebe from sys.modules for this test
        saved = {}
        to_remove = [k for k in sys.modules if k.startswith("pyzeebe")]
        for k in to_remove:
            saved[k] = sys.modules.pop(k)

        try:
            with patch.dict(sys.modules, {"pyzeebe": None, "pyzeebe.channel": None}):
                # Re-import to test the conditional path
                import importlib
                import sdlc_control_plane.orchestration.client as mod

                importlib.reload(mod)
                # Module should load fine
                assert hasattr(mod, "ZeebeClient")
        finally:
            sys.modules.update(saved)

    def test_constructor_raises_without_pyzeebe(self) -> None:
        """ZeebeClient() should raise ImportError with install instructions."""
        saved = {}
        to_remove = [k for k in sys.modules if k.startswith("pyzeebe")]
        for k in to_remove:
            saved[k] = sys.modules.pop(k)

        try:
            with patch.dict(
                sys.modules, {"pyzeebe": None, "pyzeebe.channel": None}
            ):
                import importlib
                import sdlc_control_plane.orchestration.client as mod

                importlib.reload(mod)
                config = ZeebeConfig()
                with pytest.raises(ImportError, match="uv sync --extra camunda"):
                    mod.ZeebeClient(config)
        finally:
            sys.modules.update(saved)


class TestZeebeClientWithMockedPyzeebe:
    @pytest.fixture()
    def client(self) -> MagicMock:
        """Create a ZeebeClient with mocked pyzeebe."""
        from sdlc_control_plane.orchestration.client import ZeebeClient

        config = ZeebeConfig(zeebe_grpc="localhost:36500")
        with patch(
            "sdlc_control_plane.orchestration.client.create_insecure_channel"
        ) as mock_channel:
            mock_channel.return_value = MagicMock()
            zclient = ZeebeClient(config)
        return zclient

    def test_construction_succeeds(self, client: MagicMock) -> None:
        assert client is not None

    def test_has_deploy_process(self, client: MagicMock) -> None:
        assert hasattr(client, "deploy_process")
        assert callable(client.deploy_process)

    def test_has_create_instance(self, client: MagicMock) -> None:
        assert hasattr(client, "create_instance")
        assert callable(client.create_instance)

    def test_has_run_worker(self, client: MagicMock) -> None:
        assert hasattr(client, "run_worker")
        assert callable(client.run_worker)


class TestDeployProcess:
    def test_deploy_delegates_to_pyzeebe(self) -> None:
        from sdlc_control_plane.orchestration.client import (
            DeploymentResult,
            ZeebeClient,
        )

        config = ZeebeConfig(zeebe_grpc="localhost:36500")
        mock_response = MagicMock()
        mock_response.deployments = [
            MagicMock(
                bpmn_process_id="issue-lifecycle",
                version=1,
                process_definition_key=12345,
            )
        ]

        with patch(
            "sdlc_control_plane.orchestration.client.create_insecure_channel"
        ):
            client = ZeebeClient(config)

        client._sync_client = MagicMock()
        client._sync_client.deploy_resource.return_value = mock_response

        result = client.deploy_process(Path("test.bpmn"))
        assert isinstance(result, DeploymentResult)
        assert result.process_id == "issue-lifecycle"
        assert result.version == 1
        assert result.process_definition_key == 12345


class TestCreateInstance:
    def test_create_instance_delegates_to_pyzeebe(self) -> None:
        from sdlc_control_plane.orchestration.client import (
            InstanceResult,
            ZeebeClient,
        )

        config = ZeebeConfig(zeebe_grpc="localhost:36500")
        mock_response = MagicMock()
        mock_response.process_instance_key = 99999
        mock_response.process_definition_key = 12345

        with patch(
            "sdlc_control_plane.orchestration.client.create_insecure_channel"
        ):
            client = ZeebeClient(config)

        client._sync_client = MagicMock()
        client._sync_client.run_process.return_value = mock_response

        result = client.create_instance(
            "issue-lifecycle", {"issue_id": "TEST-1"}
        )
        assert isinstance(result, InstanceResult)
        assert result.process_instance_key == 99999
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_orchestration_client.py -v`
Expected: FAIL — `client.py` does not exist

- [ ] **Step 3: Implement ZeebeClient facade**

Create `src/sdlc_control_plane/orchestration/client.py`:

```python
"""Thin facade over pyzeebe for Camunda/Zeebe interaction."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from sdlc_control_plane.orchestration.config import ZeebeConfig

# Lazy imports — module loads cleanly without pyzeebe installed.
# The dependency is checked at ZeebeClient construction time.
try:
    from pyzeebe import Job as _Job
    from pyzeebe import SyncZeebeClient as _SyncZeebeClient
    from pyzeebe import ZeebeWorker as _ZeebeWorker
    from pyzeebe.channel import create_insecure_channel

    _PYZEEBE_AVAILABLE = True
except ImportError:
    _PYZEEBE_AVAILABLE = False

    # Provide stubs so the module can be imported for type checking
    create_insecure_channel = None  # type: ignore[assignment]


@dataclass(frozen=True)
class DeploymentResult:
    """Result of deploying a BPMN process to Zeebe."""

    process_id: str
    version: int
    process_definition_key: int


@dataclass(frozen=True)
class InstanceResult:
    """Result of starting a process instance."""

    process_instance_key: int
    process_definition_key: int


class ZeebeClient:
    """Synchronous facade over pyzeebe for Zeebe interaction.

    Requires the ``camunda`` extra to be installed. If pyzeebe is not
    available, the constructor raises ``ImportError`` with install
    instructions.
    """

    def __init__(self, config: ZeebeConfig) -> None:
        if not _PYZEEBE_AVAILABLE:
            raise ImportError(
                "pyzeebe is required. Install with: uv sync --extra camunda"
            )
        self._config = config
        self._channel = create_insecure_channel(
            grpc_address=config.zeebe_grpc
        )
        self._sync_client = _SyncZeebeClient(grpc_channel=self._channel)

    def deploy_process(self, bpmn_path: Path) -> DeploymentResult:
        """Deploy a BPMN file to Zeebe."""
        response = self._sync_client.deploy_resource(str(bpmn_path))
        proc = response.deployments[0]
        return DeploymentResult(
            process_id=proc.bpmn_process_id,
            version=proc.version,
            process_definition_key=proc.process_definition_key,
        )

    def create_instance(
        self, process_id: str, variables: dict[str, Any] | None = None
    ) -> InstanceResult:
        """Start a workflow instance."""
        response = self._sync_client.run_process(
            bpmn_process_id=process_id, variables=variables
        )
        return InstanceResult(
            process_instance_key=response.process_instance_key,
            process_definition_key=response.process_definition_key,
        )

    def run_worker(
        self,
        job_type: str,
        handler: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
        timeout: float = 30.0,
        max_jobs: int = 1,
    ) -> list[str]:
        """Run a worker that processes jobs of the given type.

        Lifecycle: activates and completes up to ``max_jobs`` jobs of the
        given type, then stops. If fewer than ``max_jobs`` arrive before
        ``timeout`` seconds, returns with whatever was completed.

        Args:
            job_type: Zeebe job type to handle.
            handler: Called with job variables dict. Return dict is
                merged into output variables. If None, jobs are
                auto-completed with no output.
            timeout: Max seconds to wait for jobs.
            max_jobs: Stop after completing this many jobs. Default 1.

        Returns:
            List of completed job types (for order verification).

        Note: pyzeebe auto-calls set_success_status() after the
        handler returns -- do NOT call it manually.
        """
        completed: list[str] = []

        async def _run() -> list[str]:
            # Create a fresh channel for the worker's event loop.
            # Cannot share the SyncZeebeClient's channel across
            # event loop boundaries.
            channel = create_insecure_channel(
                grpc_address=self._config.zeebe_grpc
            )
            worker = _ZeebeWorker(grpc_channel=channel)

            @worker.task(task_type=job_type)
            async def _handle(job: _Job) -> dict[str, Any]:
                result: dict[str, Any] = {}
                if handler is not None:
                    out = handler(job.variables)
                    if out is not None:
                        result = out
                completed.append(job.type)
                return result

            worker_task = asyncio.create_task(worker.work())
            try:
                deadline = asyncio.get_event_loop().time() + timeout
                while len(completed) < max_jobs:
                    if asyncio.get_event_loop().time() > deadline:
                        break
                    await asyncio.sleep(0.2)
            finally:
                await worker.stop()
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass
            return completed

        asyncio.run(_run())
        return completed
```

- [ ] **Step 4: Update `orchestration/__init__.py` with re-exports**

Replace the empty `src/sdlc_control_plane/orchestration/__init__.py` with:

```python
"""Delivery Orchestration — Camunda/Zeebe client and workflow interaction."""

from sdlc_control_plane.orchestration.client import (
    DeploymentResult,
    InstanceResult,
    ZeebeClient,
)
from sdlc_control_plane.orchestration.config import ZeebeConfig

__all__ = [
    "DeploymentResult",
    "InstanceResult",
    "ZeebeClient",
    "ZeebeConfig",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_orchestration_client.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest -x -q`
Expected: All tests pass (existing + new config + client + BPMN)

- [ ] **Step 7: Run lint and type checks**

Run: `uv run ruff check src/sdlc_control_plane/orchestration/ tests/test_orchestration_config.py tests/test_orchestration_client.py tests/test_bpmn.py`
Run: `uv run mypy src/sdlc_control_plane/orchestration/`
Expected: No errors

- [ ] **Step 8: Commit**

```bash
git add src/sdlc_control_plane/orchestration/ tests/test_orchestration_client.py
git commit -m "feat(s3): add ZeebeClient facade with deploy, start, and worker support"
```

---

## Chunk 3: Integration Tests

### Task 5: Integration Test Infrastructure

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Read existing conftest.py**

Check `tests/conftest.py` for any existing fixtures to avoid conflicts.

- [ ] **Step 2: Add integration fixtures**

Add to `tests/conftest.py` (or create if it doesn't exist):

```python
"""Shared test fixtures."""

from __future__ import annotations

import os
import socket
from typing import Generator

import pytest

# CI cluster defaults (unauthenticated, for automated testing)
CI_ZEEBE_GRPC = "localhost:36500"
CI_CAMUNDA_REST = "http://localhost:18088"


def _check_tcp(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _check_http(url: str, timeout: float = 2.0) -> bool:
    """Check if an HTTP endpoint returns a non-error response."""
    try:
        import httpx

        resp = httpx.get(f"{url}/v2/topology", timeout=timeout)
        return resp.status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="session")
def zeebe_grpc_address() -> str:
    """Zeebe gRPC address for integration tests."""
    return os.environ.get("ZEEBE_GRPC", CI_ZEEBE_GRPC)


@pytest.fixture(scope="session")
def camunda_rest_url() -> str:
    """Camunda REST API base URL for integration tests.

    In Camunda 8.8's consolidated image, the Zeebe REST API and
    Operate share the same base URL. We use ZEEBE_REST (not
    CAMUNDA_OPERATE_URL) because the /v2/process-instances/search
    endpoint is part of the Zeebe REST API, not Operate's UI API.
    The env var fallback chain: ZEEBE_REST -> CI cluster default.
    """
    return os.environ.get("ZEEBE_REST", CI_CAMUNDA_REST)


@pytest.fixture(scope="session")
def zeebe_available(zeebe_grpc_address: str, camunda_rest_url: str) -> None:
    """Skip test if the Camunda CI cluster is not reachable.

    Checks both Zeebe gRPC and the Camunda REST API.
    """
    host, port_str = zeebe_grpc_address.rsplit(":", 1)
    if not _check_tcp(host, int(port_str)):
        pytest.skip(
            f"Zeebe gRPC not reachable at {zeebe_grpc_address}"
        )
    if not _check_http(camunda_rest_url):
        pytest.skip(
            f"Camunda REST API not reachable at {camunda_rest_url}"
        )


@pytest.fixture()
def instance_cleanup(zeebe_grpc_address: str) -> Generator[list[int], None, None]:
    """Best-effort cancel of test process instances on teardown.

    Append instance keys to the yielded list during the test.
    On teardown, attempts to cancel each. Does not fail if already
    completed or gone.
    """
    keys: list[int] = []
    yield keys
    if not keys:
        return
    try:
        from pyzeebe import SyncZeebeClient
        from pyzeebe.channel import create_insecure_channel

        channel = create_insecure_channel(grpc_address=zeebe_grpc_address)
        client = SyncZeebeClient(grpc_channel=channel)
        for key in keys:
            try:
                client.cancel_process_instance(key)
            except Exception:
                pass  # Already completed or gone
    except ImportError:
        pass
```

- [ ] **Step 3: Verify fixtures don't break existing tests**

Run: `uv run pytest -x -q`
Expected: All existing tests still pass

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test(s3): add integration fixtures for Camunda CI cluster"
```

---

### Task 6: Integration Test — Happy Path

**Files:**
- Create: `tests/test_workflow_integration.py`

- [ ] **Step 1: Write the integration test**

Create `tests/test_workflow_integration.py`:

```python
"""Integration test: issue-lifecycle happy path against live Camunda cluster.

Requires the Camunda CI cluster to be running (docker-compose-ci.yaml).
Skipped automatically if the cluster is not reachable.

Tests the full public facade: deploy_process, create_instance, run_worker.
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest

from sdlc_control_plane.orchestration.client import ZeebeClient
from sdlc_control_plane.orchestration.config import ZeebeConfig

BPMN_PATH = Path(__file__).resolve().parent.parent / "processes" / "issue-lifecycle.bpmn"

EXPECTED_PHASES = ["triage", "design", "planning", "implement", "review", "integrate"]


@pytest.fixture()
def zeebe_client(
    zeebe_available: None, zeebe_grpc_address: str
) -> ZeebeClient:
    """Create a ZeebeClient connected to the CI cluster."""
    config = ZeebeConfig(zeebe_grpc=zeebe_grpc_address)
    return ZeebeClient(config)


@pytest.fixture()
def _deploy_process(zeebe_client: ZeebeClient) -> None:
    """Deploy the issue-lifecycle BPMN to Zeebe."""
    zeebe_client.deploy_process(BPMN_PATH)


def _poll_instance_completed(
    rest_url: str,
    instance_key: int,
    timeout: float = 10.0,
    interval: float = 1.0,
) -> str:
    """Poll Camunda REST API until instance reaches a terminal state.

    Uses ``zeebe_rest`` (the Zeebe REST API), not Operate. In the
    consolidated Camunda 8.8 image both are the same endpoint, but
    semantically this is querying the Zeebe-backed process instance
    search, not the Operate UI API.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = httpx.post(
            f"{rest_url}/v2/process-instances/search",
            json={
                "filter": {"processInstanceKey": instance_key},
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            if items:
                state = items[0].get("state", "")
                if state in ("COMPLETED", "CANCELED", "TERMINATED"):
                    return state
        time.sleep(interval)
    raise TimeoutError(
        f"Instance {instance_key} did not reach terminal state within {timeout}s"
    )


@pytest.mark.integration
class TestIssueLifecycleHappyPath:
    def test_workflow_completes_all_phases(
        self,
        zeebe_client: ZeebeClient,
        camunda_rest_url: str,
        instance_cleanup: list[int],
        _deploy_process: None,
    ) -> None:
        """Deploy, start, drive all 6 phases via facade, verify completion.

        Uses ZeebeClient.run_worker() for each phase sequentially.
        The process is sequential, so each phase's job only becomes
        available after the previous one completes.
        """
        # Start instance via facade
        result = zeebe_client.create_instance(
            "issue-lifecycle",
            {"issue_id": "TEST-1", "issue_type": "Implementation"},
        )
        instance_key = result.process_instance_key
        assert instance_key > 0
        instance_cleanup.append(instance_key)

        # Drive all 6 phases sequentially through the facade.
        # Each run_worker call processes exactly 1 job of the given
        # type, then returns. The process is sequential so each
        # phase's job only appears after the prior one completes.
        completed: list[str] = []
        for phase in EXPECTED_PHASES:
            result_types = zeebe_client.run_worker(
                job_type=phase, timeout=10.0, max_jobs=1
            )
            completed.extend(result_types)

        # Assert ordering
        assert completed == EXPECTED_PHASES, (
            f"Expected {EXPECTED_PHASES}, got {completed}"
        )

        # Assert completed state via Camunda REST API.
        # Uses camunda_rest_url which points to the Zeebe REST API
        # on the CI cluster (localhost:18088). The /v2/ endpoints are
        # served by the consolidated Camunda image, not a separate
        # Operate instance.
        state = _poll_instance_completed(camunda_rest_url, instance_key)
        assert state == "COMPLETED", f"Expected COMPLETED, got {state}"
```

- [ ] **Step 2: Run integration test against CI cluster**

Run: `uv run pytest tests/test_workflow_integration.py -v -m integration`
Expected: 1 test PASS (if CI cluster is running) or SKIP (if not)

- [ ] **Step 3: Verify default test suite skips integration tests gracefully**

Run: `uv run pytest -x -q`
Expected: All tests pass; integration test either runs and passes or is
skipped with "Zeebe gRPC not reachable" message

- [ ] **Step 4: Commit**

```bash
git add tests/test_workflow_integration.py
git commit -m "test(s3): add integration test for issue-lifecycle happy path"
```

---

## Chunk 4: Final Verification

### Task 7: Full Suite Verification and Cleanup

- [ ] **Step 1: Run full quality check**

Run: `make check`
Expected: lint + typecheck + tests all pass

- [ ] **Step 2: Run integration tests**

Run: `make test-integration`
Expected: Happy path test passes against CI cluster

- [ ] **Step 3: Verify the BPMN process in Operate (manual check)**

Open `http://localhost:18088` in browser or use:

```bash
curl -s http://localhost:18088/v2/process-definitions/search \
  -X POST -H 'Content-Type: application/json' \
  -d '{"filter":{"bpmnProcessId":"issue-lifecycle"}}' | python3 -m json.tool
```

Expected: The `issue-lifecycle` process definition appears (version will
increment on each deploy — the important thing is the definition exists
and has the correct `bpmnProcessId`).

- [ ] **Step 4: Fix any issues found, re-run checks**

If any failures: fix, re-run `make check` and `make test-integration`.

- [ ] **Step 5: Final commit if any cleanup was needed**

```bash
git add -u
git commit -m "refactor(s3): address lint/type/test findings"
```
