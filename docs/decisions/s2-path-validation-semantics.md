# Decision: Path Validation Semantics

> **Session:** S2 — Evidence Inventory + Referential Validation
> **Date:** 2026-03-11
> **Status:** Decided
> **Audience:** Contributors, validator implementors, security reviewers
> **Reading order:** [docs/decisions/README.md](README.md) → this document

**Decision:** Path safety (containment within project root) is validated as a pure lexical check in `referential.py`, independent of `--project-root`. Filesystem existence checks are separated into `locator_fs.py` and only run when `--project-root` is provided.

## Context and Requirements

`Locator.path` fields in certificates express file locations. Two concerns arise:

1. **Safety:** A path like `../../etc/passwd` in a certificate is a malformed claim — no valid development artifact lives outside the project root. This should be flagged regardless of whether the certificate is being validated against a real filesystem.
2. **Existence:** A path may be syntactically valid but point to a file that doesn't exist on the current machine. This requires I/O.

The question is how to split these two concerns across the validation pipeline.

## Options Evaluated

### Option A: Require --project-root for all path checks

No path validation runs unless `--project-root` is provided. Both safety and existence checks are gated on it.

**Trade-offs:**
- Pro: Simple model — path checks are always filesystem-backed.
- Con: A certificate with `../../etc/passwd` in a `Locator.path` passes referential validation silently unless the user provides `--project-root`.
- Con: Makes path safety dependent on runtime configuration, not certificate content. A certificate that encodes a directory traversal attack is "valid" without the flag.
- Con: Undermines the pure-function design of `referential.py` — it would need to be parameterized with optional I/O.

### Option B: Split pure/lexical from filesystem checks (chosen)

- `referential.py` (always runs): lexical checks — `absolute_path_not_allowed`, `path_escapes_project_root`, `invalid_line_range`.
- `locator_fs.py` (opt-in via `--project-root`): filesystem checks — `unresolvable_path`, `line_range_exceeds_file`, `path_not_regular_file`.

The lexical containment check uses `posixpath.normpath()` without any filesystem access:

```python
normalized = posixpath.normpath(path)
if normalized.startswith("..") or normalized == "..":
    # path_escapes_project_root
```

**Trade-offs:**
- Pro: `referential.py` remains a pure function — no I/O, no configuration, fully testable in isolation.
- Pro: Directory traversal attempts in certificates are caught without needing `--project-root`.
- Pro: Clear module responsibility: `referential.py` = structural/logical checks; `locator_fs.py` = I/O checks.
- Pro: The naming pattern extends naturally: `locator_url.py`, `locator_git.py` for future locator types.
- Con: Two modules instead of one. In practice, the split makes each module simpler and more testable.

### Option C: Skip path safety entirely

Trust certificate authors not to include path traversal sequences. Only check existence when `--project-root` is provided.

**Trade-offs:**
- Pro: Minimal implementation.
- Con: A `Locator.path` of `../../etc/passwd` is silently accepted. This is not just a stale-path situation — it is a structurally invalid certificate claim.
- Con: Inconsistent with the project's principle that certificates encode verifiable claims. A path that escapes the project root is not a valid claim about project content.

## Chosen Approach: Option B

The lexical containment check (`path_escapes_project_root`) runs as part of the always-on pure referential validation, using only `posixpath.normpath()` — no filesystem I/O. Absolute paths (`absolute_path_not_allowed`) are similarly rejected in the pure layer.

Filesystem existence and line-count checks run only when `--project-root` is provided, in the separate `locator_fs.py` module.

This split ensures that structurally invalid paths (directory traversal, absolute paths) are always caught, while existence checks remain opt-in.

## Related

- Code: `src/sdlc_control_plane/verification/referential.py` — `absolute_path_not_allowed`, `path_escapes_project_root`, `invalid_line_range`
- Code: `src/sdlc_control_plane/verification/locator_fs.py` — `unresolvable_path`, `line_range_exceeds_file`, `path_not_regular_file`
- Docs: [docs/verification/referential-validation.md](../verification/referential-validation.md) — full check inventory
- Spec: `docs/superpowers/specs/2026-03-11-s2-evidence-inventory-referential-validation-design.md`, Sections 5.1, 5.4
