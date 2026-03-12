# Decision: pyzeebe Handler `**kwargs` Pattern

> **Session:** S3 — Minimal BPMN Process (Happy Path)
> **Date:** 2026-03-12
> **Status:** Decided
> **Audience:** Contributors, Camunda integration implementors
> **Reading order:** [docs/decisions/README.md](README.md) → this document

**Decision:** pyzeebe task handlers use `**kwargs: Any` instead of `job: Job` parameter annotation.

## Context and Requirements

S3 adds a `ZeebeClient` wrapper that registers job workers via pyzeebe 4.x. pyzeebe's decorator (`@worker.task`) inspects handler parameters at registration time to determine which job variables to inject into the handler call. This introspection uses `inspect.signature()` and checks parameter annotations.

The project uses `from __future__ import annotations` (PEP 563) in all modules for forward-reference support. PEP 563 turns all type hints into strings at runtime — annotations are not evaluated until explicitly requested.

## Options Evaluated

### Option A: `job: Job` annotation (rejected)

```python
from pyzeebe.job.job import Job

async def handler(job: Job) -> dict:
    job_type = job.type
    ...
```

pyzeebe's `parameter_tools.get_parameters_from_function` checks `param.annotation == Job` (identity comparison against the class object). With PEP 563, `param.annotation` is the string `"Job"` (or the internal `"_Job"`), not the class. The identity check fails silently and the handler is called with zero positional arguments, raising `TypeError` at runtime.

**Trade-offs:**
- Pro: Explicit type annotation on the handler.
- Con: Silently broken under PEP 563 — no warning at registration, crash on first job.
- Con: Requires removing `from __future__ import annotations` from `client.py` while the rest of the project keeps it.

### Option B: `**kwargs: Any` (chosen)

```python
async def handler(**kwargs: Any) -> dict:
    job_type = job_type_name  # captured from outer closure
    ...
```

pyzeebe treats `**kwargs` as "accept all job variables as keyword arguments." No annotation introspection is required. The job type is captured from the enclosing `register_handler` closure variable rather than read from a `Job` object.

**Trade-offs:**
- Pro: Correct under PEP 563 — no annotation introspection at all.
- Pro: Consistent with the project-wide `from __future__ import annotations` convention.
- Pro: Handler receives all job variables as a plain dict — straightforward to forward.
- Con: Loses static type safety on individual handler parameters.
- Con: Job metadata fields (beyond `type`) require an alternate access path if needed in future.

### Option C: Remove `from __future__ import annotations` from `client.py`

Keep `job: Job` annotation but remove the future import from the one file where it causes a problem.

**Trade-offs:**
- Pro: Preserves annotation type safety.
- Con: Inconsistent with the project convention — every other module uses PEP 563.
- Con: Forward references in `client.py` would then require string quoting manually.
- Con: Hides the root incompatibility rather than addressing it.

## Chosen Approach: Option B

Use `**kwargs: Any` in all pyzeebe task handlers. Job type is captured from the closure variable in `register_handler`, not from `job.type`. This is the only approach that is correct under PEP 563 without creating per-file import inconsistency.

This is a pyzeebe 4.x + PEP 563 incompatibility. If pyzeebe adds `get_type_hints()`-based introspection in a future release, this decision can be revisited.

## Related

- Code: `src/sdlc_control_plane/orchestration/client.py` — `register_handler()`, handler closure
- Upstream: pyzeebe `pyzeebe/utils/parameter_tools.py` — `get_parameters_from_function()`
- PEP 563: https://peps.python.org/pep-0563/
