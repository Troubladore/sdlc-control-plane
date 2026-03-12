# Delivery Orchestration

> **Status:** Normative — authoritative for current behavior
> **Audience:** Contributors working on Camunda/Zeebe integration
> **Reading order:** Start with project README.md, then this document

The Delivery Orchestration bounded context owns the thin facade over pyzeebe for Camunda 8 interaction: BPMN process deployment, workflow instance creation, and connection configuration.

## Components

| Component | Code | Responsibility |
|-----------|------|----------------|
| Configuration | `src/sdlc_control_plane/orchestration/config.py` | `ZeebeConfig` — reads env vars, validates connection parameters |
| Client | `src/sdlc_control_plane/orchestration/client.py` | `ZeebeClient` — deploy processes, create instances, result types |

### ZeebeConfig

`ZeebeConfig` is a Pydantic settings model that reads from environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZEEBE_GRPC` | `localhost:26500` | Zeebe gRPC gateway address |
| `ZEEBE_REST` | `http://localhost:8088` | Zeebe REST API base URL |
| `CAMUNDA_OPERATE_URL` | `http://localhost:8088` | Camunda Operate UI/API URL |

### ZeebeClient

`ZeebeClient` wraps `pyzeebe` and exposes two operations:

- `deploy_process(bpmn_path)` → `DeploymentResult` — deploys a BPMN file to the connected Zeebe instance
- `create_instance(process_id, variables)` → `InstanceResult` — starts a workflow instance by process ID

**Result types:**

- `DeploymentResult` — holds `process_definition_key`, `bpmn_process_id`, `version`, and `resource_name`
- `InstanceResult` — holds `process_instance_key`, `bpmn_process_id`, `version`, and `process_definition_key`

Both are Pydantic models; all fields are set from the Zeebe API response.

## BPMN Process

`processes/issue-lifecycle.bpmn` is the happy-path issue lifecycle process. It contains 6 sequential service tasks:

1. `validate-certificate` — validate the submitted certificate artifact
2. `assign-reviewers` — select and assign two independent reviewers
3. `run-review` — execute parallel review (competitive multi-model)
4. `cross-validate` — reviewers cross-validate each other's certificates
5. `resolve-disputes` — arbiter resolves any filed disputes
6. `emit-workflow-event` — emit a `WorkflowEvent` to the measurement context

The process is deployed via `ZeebeClient.deploy_process("processes/issue-lifecycle.bpmn")`.

## Connection

Copy `.env.example` to `.env` and set the three variables:

```bash
ZEEBE_GRPC=localhost:26500
ZEEBE_REST=http://localhost:8088
CAMUNDA_OPERATE_URL=http://localhost:8088
```

The local Camunda 8 full-stack cluster runs from `~/repos/camunda/` (Docker Compose). A separate CI cluster is available at `localhost:36500` (gRPC) and `localhost:18088` (REST).

`pyzeebe` is an optional dependency. The client import is always conditional so the rest of the package loads without it:

```python
try:
    from pyzeebe import ZeebeClient as _ZeebeClient
except ImportError:
    _ZeebeClient = None  # type: ignore[assignment,misc]
```

## Testing

Unit tests mock the pyzeebe layer entirely — no live cluster required:

```bash
make test        # includes orchestration unit tests
make check       # lint + type check + unit tests
```

Integration tests require a live Zeebe instance:

```bash
make test-integration  # Integration tests (requires live Camunda cluster)
```

Integration tests deploy `processes/issue-lifecycle.bpmn` and verify that `create_instance` returns a valid `InstanceResult`.

## Current Limitations

- **No auth support** — `ZeebeConfig` does not model OAuth credentials or TLS certificates; the client connects to an unsecured gRPC endpoint only.
- **No secure channels** — TLS for the gRPC channel is not wired in; production use against a secured cluster requires manual `pyzeebe` configuration.
- **Workers create separate channels** — if job workers are added in a future session, each worker opens its own channel rather than sharing the client channel.
