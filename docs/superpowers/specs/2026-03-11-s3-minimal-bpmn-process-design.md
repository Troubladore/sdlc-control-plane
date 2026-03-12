# S3: Minimal BPMN Process (Happy Path) — Design Spec

> Session 3 of the SDLC Control Plane implementation roadmap.
> Goal: Deploy a minimal BPMN process to Camunda and prove the full 6-phase
> happy path completes via Operate.

---

## 1. Scope

### In Scope

- Hand-authored BPMN 2.0 process model for the issue lifecycle happy path
- Thin pyzeebe-based orchestration facade with conditional imports
- ZeebeConfig Pydantic model matching the repo's `.env.example` contract
- Unit tests for config, client facade, and BPMN artifact correctness
- Integration tests proving workflow completion against the live Camunda cluster

### Out of Scope (deferred to later sessions)

- Transition gating / gate evaluation (S4)
- WorkflowEvent emission (S4)
- User tasks, embedded subprocesses, timers, escalation
- Competitive review / dispute handling (S7-S8)
- Certificate semantics in Camunda
- Remediation loops (S9)

---

## 2. BPMN Process Model

**File:** `processes/issue-lifecycle.bpmn`

**Process ID:** `issue-lifecycle`

**Shape:** Single sequential process with 6 service tasks.

```
StartEvent_1
  -> Activity_triage    (job type: "triage")
  -> Activity_design    (job type: "design")
  -> Activity_planning  (job type: "planning")
  -> Activity_implement (job type: "implement")
  -> Activity_review    (job type: "review")
  -> Activity_integrate (job type: "integrate")
  -> EndEvent_1
```

### Design Decisions

- **All phases are service tasks in S3.** The lifecycle spec maps some phases to
  user tasks and embedded subprocesses, but S3 needs a fully automatable happy
  path driven by job workers. The richer task types are S4+ evolution.

- **Static BPMN element IDs.** Element IDs identify nodes in the process
  definition, not runtime instances. `issue_id` belongs in process variables,
  not element IDs. IDs follow the `Activity_{phase}` convention aligned with
  Section 10 of the lifecycle spec.

- **Zeebe extension namespace required.** The BPMN XML must include the Zeebe
  extension namespace (`zeebe:taskDefinition`) for each service task so the
  process is executable, not just structurally valid.

### Process Variables (at start)

| Variable | Type | Description |
|----------|------|-------------|
| `issue_id` | string | Identifier for the issue being processed |
| `issue_type` | string | Issue type (e.g., "Implementation", "Contract") |

Minimal set for S3. Later sessions extend with `milestone`, `assignee_role`,
`epic_branch`, etc. per Section 10 of the lifecycle spec.

---

## 3. Orchestration Module

### File Structure

```
src/sdlc_control_plane/orchestration/
    __init__.py     # Re-exports ZeebeConfig, ZeebeClient
    config.py       # ZeebeConfig Pydantic model
    client.py       # ZeebeClient facade over pyzeebe
```

### `config.py` — ZeebeConfig

A plain `pydantic.BaseModel` with a `from_env()` classmethod that reads
`os.environ`. Not `pydantic-settings.BaseSettings` (that package is not a
project dependency).

| Field | Type | Default | Env Var | Notes |
|-------|------|---------|---------|-------|
| `zeebe_grpc` | `str` | `"localhost:26500"` | `ZEEBE_GRPC` | host:port, NOT a URL |
| `zeebe_rest` | `str` | `"http://localhost:8088"` | `ZEEBE_REST` | HTTP URL |
| `camunda_operate_url` | `str` | `"http://localhost:8088"` | `CAMUNDA_OPERATE_URL` | HTTP URL |

Validation:
- `zeebe_rest` and `camunda_operate_url` must start with `http://` or `https://`
- `zeebe_grpc` is validated as `host:port` format (no scheme)

#### Cluster Authentication

The local infrastructure has two Camunda clusters:
- **Main cluster** (ports 26500/8088): requires authentication (returns 401
  on unauthenticated REST calls). Used for interactive development.
- **CI cluster** (ports 36500/18088): unauthenticated (`unprotectedApi: true`).
  Designed for automated testing.

S3 integration tests target the **CI cluster**. The test fixtures use env
vars to connect, defaulting to CI cluster ports. The `.env.example` defaults
remain pointed at the main cluster (for interactive CLI use), but integration
test fixtures override with CI cluster values.

Auth support (for the main cluster) is deferred — not needed for S3.

### `client.py` — ZeebeClient

The `pyzeebe` dependency is checked lazily, not at module import time. The
module itself imports cleanly even without the `camunda` extra installed.
The dependency check happens when `ZeebeClient` is **constructed** — if
`pyzeebe` is not available, the constructor raises `ImportError` with:
`"pyzeebe is required. Install with: uv sync --extra camunda"`

This keeps the `orchestration` package importable for tests, docs, and
type checking on machines without `pyzeebe` installed. Only actual use
of the Zeebe client triggers the dependency requirement.

**Constructor:** `ZeebeClient(config: ZeebeConfig)`

#### Async Strategy

pyzeebe 4.x provides both `ZeebeClient` (async) and `SyncZeebeClient`
(sync wrapper). `ZeebeWorker` is async-only — there is no sync equivalent.

Our facade uses **`SyncZeebeClient`** for `deploy_process` and
`create_instance` (simple request-response operations that don't need
async). For `run_worker`, which requires the async `ZeebeWorker`, the
facade wraps the worker loop in `asyncio.run()`.

Important: the worker creates a **separate** `grpc.aio.Channel` inside
`asyncio.run()` — it cannot share the `SyncZeebeClient`'s channel across
event loop boundaries.

S3 does **not** support being called from within an already-running event
loop. If that becomes necessary in later sessions, the facade can expose
async variants alongside the sync API.

**Methods:**

#### `deploy_process(bpmn_path: Path) -> DeploymentResult`
Deploy a BPMN file to Zeebe. Returns deployment metadata (process definition
key). Internally delegates to pyzeebe's `deploy_resource()`.

#### `create_instance(process_id: str, variables: dict) -> InstanceResult`
Start a workflow instance. Returns instance key. Internally delegates to
pyzeebe's `run_process()`.

#### `run_worker(job_type: str, handler: Callable | None = None, timeout: float = 30.0) -> list[str]`
Register a worker for the given job type. Behavior:
- Processes jobs of the given type until no more matching work remains or
  `timeout` seconds elapse, then returns.
- If `handler` is `None`, auto-completes each job (S3 happy path).
- If `handler` is provided, calls it with the job variables.
- Returns a list of completed job types (for order verification in tests).
- Deterministic for the sequential S3 process: each job type appears exactly
  once per instance.

#### Multi-Phase Worker Orchestration

The S3 integration test needs to complete all 6 sequential job types. The
six-phase orchestration logic lives in the **integration test layer**, not
in the public `ZeebeClient` API. The test registers all 6 task handlers on
a single `ZeebeWorker` instance (via `run_worker`), runs the worker until
all 6 have fired or timeout is reached, and each handler appends its job
type to a shared completion list for order verification.

The public `ZeebeClient` API stays minimal: `deploy_process`,
`create_instance`, `run_worker`. No `run_happy_path` convenience method
on the client — that would be a test-shaped method on the library surface.

**Result types:** `DeploymentResult` and `InstanceResult` are simple Pydantic
models (or dataclasses) holding the key fields returned by Zeebe.

---

## 4. Testing Strategy

### Unit Tests (`make test`)

#### `tests/test_orchestration_config.py`
- `ZeebeConfig.from_env()` reads env vars correctly
- Defaults applied when env vars are absent
- Validation rejects malformed values (e.g., `zeebe_rest` without `http://`)
- `zeebe_grpc` accepts `host:port` format without scheme

#### `tests/test_orchestration_client.py`
- Clear `ImportError` message when `pyzeebe` is not installed
- Successful `ZeebeClient` construction when `pyzeebe` is available (mocked)
- Facade methods exist and delegate correctly (mock pyzeebe, don't test its internals)

#### `tests/test_bpmn.py`
- BPMN file exists at `processes/issue-lifecycle.bpmn`
- XML is well-formed
- Process ID is `issue-lifecycle`
- Contains exactly 6 activity elements, all are service tasks
- Each service task has a Zeebe `taskDefinition` with the correct job type
- Job types are exactly: `triage`, `design`, `planning`, `implement`, `review`, `integrate`
- Sequence flows connect: StartEvent_1 -> 6 tasks in order -> EndEvent_1
- Zeebe extension namespace is declared

### Integration Tests (`make test-integration`, `@pytest.mark.integration`)

#### `tests/test_workflow_integration.py`
1. Deploy `processes/issue-lifecycle.bpmn` to Zeebe (CI cluster)
2. Start instance with `{issue_id: "TEST-1", issue_type: "Implementation"}`
3. Workers record observed job completion order, then auto-complete
4. Assert observed order equals `["triage", "design", "planning", "implement", "review", "integrate"]`
5. Assert instance reached completed state via Camunda REST API
   (`POST /v2/process-instances/search` with filter on `processInstanceKey`).
   Uses polling with retry (up to 10s, 1s intervals) to account for
   Elasticsearch indexing delay between Zeebe completion and search
   API reflecting the state.

#### `tests/conftest.py` — Integration Fixtures
- `zeebe_available` fixture: checks both Zeebe gRPC reachability (CI cluster,
  default `localhost:36500`) AND Camunda REST API reachability (CI cluster,
  default `http://localhost:18088`). Skips gracefully if either is unavailable.
- CI cluster connection defaults are hardcoded in the fixture but overridable
  via `ZEEBE_GRPC` and `CAMUNDA_OPERATE_URL` env vars.
- Cleanup fixture: best-effort cancel of test instances on teardown. Does not
  fail if instance already completed or is gone.

### Configuration Additions

**`pyproject.toml`:**
```toml
[tool.pytest.ini_options]
markers = ["integration: requires live Camunda cluster"]
```

**`Makefile`:**
```makefile
test-integration:
	uv run pytest -m integration -v
```

---

## 5. Dependencies

No new required dependencies. `pyzeebe>=4.0` is already in the `[camunda]`
optional extra.

Add to `[dev]` extras:
- `httpx>=0.27` — for Camunda REST API queries in integration tests
  (completion state polling).

`pytest-asyncio` is **not** added for S3. The sync facade wraps all async
internally via `asyncio.run()`, so tests are plain synchronous pytest.

Integration tests are collected by `make test` but gracefully skipped via
the `zeebe_available` fixture when the Camunda cluster is unreachable. No
change to the default `make test` target is required.

---

## 6. Success Criterion

> "Workflow completes in Operate"

Proven by: integration test that deploys `issue-lifecycle.bpmn`, starts an
instance, drives all 6 phases via workers, records the completion order, and
verifies the instance reached completed state through the Operate REST API.
