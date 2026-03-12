# Decision: Integration Tests Target CI Cluster

> **Session:** S3 — Minimal BPMN Process (Happy Path)
> **Date:** 2026-03-12
> **Status:** Decided
> **Audience:** Contributors, CI pipeline operators
> **Reading order:** [docs/decisions/README.md](README.md) → this document

**Decision:** S3 integration tests target the CI cluster (ports 36500/18088), not the main cluster. Auth support is deferred.

## Context and Requirements

The local Camunda 8.8 stack (at `~/repos/camunda/`) runs two clusters:

| Cluster | Zeebe gRPC | REST | Auth |
|---------|-----------|------|------|
| Main | 26500 | 8088 | Required (returns 401 on unauthenticated REST calls) |
| CI | 36500 | 18088 | None (`unprotectedApi: true`) |

S3 integration tests need to deploy BPMN, start instances, and query process state via the REST API. Implementing OAuth2/Basic auth for the main cluster is out of scope for S3.

## Options Evaluated

### Option A: Target main cluster, implement auth

Add authentication support (Bearer token or Basic auth) to the Camunda REST client before running integration tests.

**Trade-offs:**
- Pro: Tests run against the same cluster used interactively.
- Con: Auth implementation is non-trivial scope that belongs in a later session.
- Con: Credentials in test fixtures create a secret-management concern.
- Con: Blocks S3 tests on auth infrastructure rather than on BPMN correctness.

### Option B: Target CI cluster (chosen)

Integration tests default to the CI cluster (`ZEEBE_GRPC=localhost:36500`, `ZEEBE_REST=http://localhost:18088`). No auth headers required. Test fixtures set these defaults; they are overridable via environment variables.

**Trade-offs:**
- Pro: Tests run immediately without auth credentials.
- Pro: CI cluster is purpose-built for automated testing — isolated from interactive work on the main cluster.
- Pro: Ports are overridable, so tests can target any cluster when auth is added later.
- Con: Tests do not exercise the auth code path (deferred to a future session).
- Con: Developer must remember to start both clusters when running integration tests.

### Option C: Mock the Camunda client entirely

Replace the Zeebe client with a mock in integration tests; no live cluster required.

**Trade-offs:**
- Pro: No external dependency.
- Con: Defeats the purpose of integration tests — BPMN deployment and execution fidelity are exactly what S3 must verify.

## Chosen Approach: Option B

S3 integration tests target the CI cluster. The `.env.example` defaults remain pointed at the main cluster (26500/8088) for interactive use. Test fixtures default to CI cluster ports and read `ZEEBE_GRPC_TEST` / `ZEEBE_REST_TEST` env vars so the target is overridable in any environment.

### Implementation Note: `processInstanceKey` Must Be a String

When querying `/v2/process-instances/search` via the Camunda REST API, the `processInstanceKey` filter value must be passed as a **string**, not an integer. Passing an integer returns HTTP 400. pyzeebe returns the key as a Python `int`; callers must convert with `str(key)` before including it in the filter payload.

## Related

- Code: `tests/integration/test_s3_happy_path.py` — CI cluster fixtures, `str(key)` conversion
- Code: `src/sdlc_control_plane/orchestration/client.py` — REST query helpers
- Config: `.env.example` — main cluster defaults for interactive use
- Infrastructure: `~/repos/camunda/` — Docker Compose stack with both clusters
