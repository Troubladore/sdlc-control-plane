# Decision: Sync/Async Strategy for Zeebe Client

> **Session:** S3 — Minimal BPMN Process (Happy Path)
> **Date:** 2026-03-12
> **Status:** Decided
> **Audience:** Contributors, Camunda integration implementors
> **Reading order:** [docs/decisions/README.md](README.md) → this document

**Decision:** Use `SyncZeebeClient` for deploy/start operations and `asyncio.run()` wrapping `ZeebeWorker` for job completion.

## Context and Requirements

pyzeebe 4.x provides three execution surfaces:

| Class | Interface | Use case |
|-------|-----------|----------|
| `ZeebeClient` | `async` | Request-response gRPC (deploy, create instance) |
| `SyncZeebeClient` | Sync wrapper over `ZeebeClient` | Same, callable from sync code |
| `ZeebeWorker` | `async` only | Long-running job subscription loop |

The CLI is synchronous (Click). The S3 scope requires: deploy a BPMN, start a process instance, complete a job, and confirm the instance reached an end state. The question is which execution model to use for each operation.

## Options Evaluated

### Option A: All async with `pytest-asyncio`

Use `ZeebeClient` everywhere, mark all tests `@pytest.mark.asyncio`, add `pytest-asyncio` as a dev dependency.

**Trade-offs:**
- Pro: Uniform async model throughout.
- Con: Adds a test dependency that complicates the test surface for non-Camunda tests.
- Con: The Click CLI must still wrap everything in `asyncio.run()` at the entry point.
- Con: Overly broad — most operations are simple request-response calls that don't benefit from async.

### Option B: All sync via `SyncZeebeClient`

Use `SyncZeebeClient` for all operations. Avoid async entirely.

**Trade-offs:**
- Pro: Simple, no event loop management.
- Con: `ZeebeWorker` has no sync equivalent in pyzeebe 4.x — this option cannot support job workers at all.
- Con: Defers the async question without resolving it, blocking any worker-based workflows.

### Option C: Hybrid — `SyncZeebeClient` for request-response, `asyncio.run()` for worker (chosen)

`deploy_process()` and `create_instance()` use `SyncZeebeClient`. `run_worker()` constructs a fresh `ZeebeWorker` with its own gRPC channel and wraps it in `asyncio.run()`.

**Trade-offs:**
- Pro: `SyncZeebeClient` is natural for the CLI's synchronous call sites.
- Pro: `asyncio.run()` is the correct boundary for `ZeebeWorker` — it starts a fresh event loop, runs to completion, and exits cleanly.
- Pro: No new test dependencies; async integration tests use `asyncio.run()` directly or a thin sync wrapper.
- Con: The `run_worker()` path creates a separate gRPC channel — it cannot share the channel used by `SyncZeebeClient` across event loop boundaries.
- Con: Slightly more explicit channel lifecycle management required.

## Chosen Approach: Option C

`deploy_process()` and `create_instance()` are simple request-response operations — `SyncZeebeClient` handles them naturally from a sync CLI context. `run_worker()` requires `ZeebeWorker`, which is async-only; it runs under `asyncio.run()` with a fresh channel, isolated from the sync client's channel. Channel isolation across event loop boundaries is a pyzeebe/gRPC requirement, not a workaround.

If the project later adopts a fully async CLI entry point (e.g., `asyncio.run(main())`), the hybrid can be collapsed into uniform `ZeebeClient` usage. That refactor is deferred until there is a demonstrated need.

## Related

- Code: `src/sdlc_control_plane/orchestration/client.py` — `ZeebeClient` wrapper, `run_worker()`
- pyzeebe docs: `SyncZeebeClient`, `ZeebeWorker`
- Session scope: S3 happy-path integration test in `tests/integration/test_s3_happy_path.py`
