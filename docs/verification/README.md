# Verification & Evidence

> **Status:** Normative — authoritative for current behavior
> **Audience:** Certificate authors (human or LLM) and validator contributors
> **Reading order:** Start with project README.md, then this document

The Verification & Evidence bounded context owns evidence inventory, certificate validation, dispute handling, and rendered markdown.

## Components

| Component | Code | Docs |
|-----------|------|------|
| Data Models | `src/sdlc_control_plane/verification/models.py` | [Evidence Model](evidence-model.md) |
| Referential Validation | `src/sdlc_control_plane/verification/referential.py` | [Referential Validation](referential-validation.md) |
| Filesystem Checks | `src/sdlc_control_plane/verification/locator_fs.py` | [Referential Validation](referential-validation.md) |
| Diagnostics | `src/sdlc_control_plane/verification/diagnostics.py` | [Diagnostics](diagnostics.md) |

## Validation Pipeline

`sdlc validate` runs a layered pipeline:

1. **Load JSON** — exit 2 on I/O error
2. **Pydantic structural validation** — exit 1 on schema error
3. **Referential validation** (pure) — exit 1 on errors
4. **Filesystem locator checks** (opt-in via `--project-root`) — exit 1 on failures
