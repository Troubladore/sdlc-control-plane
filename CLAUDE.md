# sdlc-control-plane - Engineering Control Plane

**Reusable SDLC governance framework** with Camunda 8 orchestration, certificate-driven development, and competitive multi-model review.

## Project Philosophy

Build an **Engineering Control Plane**, not a giant monolithic SDLC workflow.

This system is optimized for (in order):
1. Epistemic confidence
2. Auditability and replayability
3. Controlled extensibility
4. Human working-memory offload
5. Measured value over process theatre
6. Throughput and latency only after the above are acceptable

The design assumes that false confidence in a change or a standard is far more expensive than extra compute or extra deterministic validation.

## Architecture

### Bounded Contexts (DDD)

| Context | Package | Owns |
|---------|---------|------|
| Verification & Evidence | `verification/` | Evidence inventory, certificates, validation, disputes, rendered markdown |
| Delivery Orchestration | `orchestration/` | BPMN processes, workflow instances, transition sequencing, timers, escalation |
| Engineering Policy & Standards | `policy/` | Standards catalog, rule classification, SCIPP, placement decisions, policy DMN |
| Exception & Remediation | `exceptions/` | Waivers, deficiencies, remediation ledger, compensating controls |
| Measurement & Experimentation | `measurement/` | Workflow events, KPI computation, dashboards, version comparisons |
| Engineering Context Profile | `context_profile/` | Repo profile, subsystem tags, ownership, sensitivity tier |

### What Camunda Owns vs. What It Doesn't

Camunda owns: process flow, human tasks, timers, escalation, transition sequencing, waiting and correlation.

Camunda does **not** own: semantic truth of certificate validity, standard applicability, waiver validity, or business/engineering invariants. Those belong to the domain services.

### Tech Stack

- **Python 3.10+** with `uv` for dependency management
- **Pydantic** for data models and configuration validation
- **Click** for CLI
- **JSON Schema** for artifact validation (schema bundle at `schemas/`)
- **Camunda 8** via REST/gRPC (decoupled -- bring your own cluster)
- **BPMN/DMN** assets in `processes/` and `dmn/`
- **pytest + hypothesis** for testing
- **ruff + mypy** for quality

### File Organization

```
src/sdlc_control_plane/
    verification/       # Evidence inventory, certificates, validation, disputes
    orchestration/      # Camunda/Zeebe client, workflow interaction
    policy/             # Standards catalog, SCIPP, placement decisions
    exceptions/         # Waivers, deficiencies, remediation ledger
    measurement/        # Workflow events, KPIs, dashboards
    context_profile/    # Repo profile, subsystem tags, ownership
    cli/                # CLI entry points

schemas/                # JSON Schema bundles (canonical artifact contracts)
processes/              # BPMN process models
dmn/                    # DMN decision tables
docs/
    process/            # Process specifications (certificate-driven dev, BPMN lifecycle)
    design/             # Design documents and specs
tests/
```

## Quality Standard

**Every assertion of completion must be backed by verifiable evidence.**

See `docs/process/certificate-driven-development.md` for:
- Task Review Certificates (spec compliance + code quality)
- Design Decision Certificates (match or exceed reference patterns)
- Deferred Scope Certificates (no "out of scope" without tracking)
- Impact Alignment Certificates (no silent drift from plans)

## Development Practices

### Python Conventions
- **Modern Python 3.10+** with full type hints
- **Pydantic models** for all data structures and configuration
- **Pure functions** where possible -- no side effects in validation logic
- **uv** for dependency management
- **pytest** with hypothesis for property-based testing
- **Rich** for CLI output

### Key Implementation Principles

1. **Bounded Context Isolation**: Each context owns its data model, invariants, and validation rules. Cross-context communication goes through well-defined interfaces.

2. **Artifact-First Development**: All authoritative artifacts (certificates, disputes, transitions, remediation entries) are JSON documents validated against the schema bundle.

3. **Gate-Based Transitions**: No workflow state advances on prose alone. Every transition requires a TransitionRequest, supporting artifacts, and deterministic gate evaluation.

4. **Evidence-Backed Claims**: Every binding claim in a certificate must cite evidence by stable ID. Title-only scanning is explicitly flagged.

5. **Constrained Decoding Boundary**: Use structured output for authoritative artifacts only. Exploratory reasoning is unconstrained.

### Testing Strategy
- **Unit tests** for validation logic, schema compliance, hash chain integrity
- **Integration tests** for Camunda workflow interaction
- **Property-based tests** with Hypothesis for mathematical properties (scoring, hash chains)
- **Smoke tests** to verify CLI and basic functionality

### Camunda Connection

This repo does **not** manage the Camunda engine. It connects via environment variables:
```
ZEEBE_GRPC=localhost:26500
ZEEBE_REST=http://localhost:8088
CAMUNDA_OPERATE_URL=http://localhost:8088
```

See `.env.example` for the full set.

The local Camunda 8.8 cluster runs from `~/repos/camunda/` (Docker Compose, separate repo).

## Quick Development Commands

```bash
# Install dependencies
uv sync --extra dev

# Run tests
make test          # Quick tests
make test-all      # All tests with coverage
make check         # Lint + type check + tests

# Format
make fmt

# CLI
uv run sdlc --help
uv run sdlc validate  # (Session 1)
```

## Implementation Roadmap

The system is built incrementally across 14 sessions, each optimized for bounded cognitive load:

| Session | Focus | Key Deliverable |
|---------|-------|-----------------|
| 0 | Repo skeleton + docs migration | `uv run pytest` passes |
| 1 | Schema bundle as Python package + CLI validator | `sdlc validate certificate.json` |
| 2 | Evidence inventory + referential validation | Broken refs caught |
| 3 | Minimal BPMN process (happy path) | Workflow completes in Operate |
| 4 | TransitionRequest gating + WorkflowEvent emission | Invalid transitions blocked |
| 5 | Claim verification engine | Certificates verified claim-by-claim |
| 6 | Mock reviewer protocol | Mock reviewer produces valid certificates |
| 7 | Competitive review (two reviewers + cross-validation) | Disputes filed |
| 8 | Arbiter + scoring + leaderboard | Leaderboard updates |
| 9 | Remediation ledger (hash-chained, signed) | Tamper detection works |
| 10 | SCIPP workflow (standards intake + placement) | Proposals routed correctly |
| 11 | GitHub webhook integration | Issue assignment triggers workflow |
| 12 | KPI dashboard + measurement | Dashboard shows run data |
| 13 | Real LLM reviewer integration (Codex + Gemini) | Live competitive review |

Full design: `docs/design/2026-03-10-issue-114-sdlc-control-plane-design.md`

## Claude Workflow Guidelines

### Branching & Merging Strategy

**Branch Hierarchy:**
- `main` -- Production-ready, stable releases only
- Feature branches for individual sessions/tasks

**Branch Naming:**
- Features: `feat/s{N}-{short-description}` (e.g., `feat/s1-schema-validation`)
- Fixes: `fix/s{N}-{short-description}`

**Branch Flow:**
1. Feature branches branch from `main`
2. Feature PRs target `main`
3. Squash merge after review

### Development Standards
- **Conventional commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:` prefixes
- **All commits must be signed**
- **Test everything**: Run `make check` before committing
- **Handle optional deps**: Camunda imports (`pyzeebe`) are always conditional
- **Co-author**: Include `Co-Authored-By: Claude <noreply@anthropic.com>` in commits

### Workflow for Each Session
1. Create feature branch from `main`: `git checkout -b feat/s{N}-description`
2. Implement changes following the session scope
3. Run `make check` -- all must pass
4. Commit with conventional commit message
5. Push and create PR: `gh pr create --base main`
6. Request review -- do NOT close issues or merge

### Code Quality Requirements
- **Full type annotations** (Python 3.10+ style)
- **Pydantic models** for all data structures
- **Pure validation functions** -- no side effects
- **Statistical rigor** where applicable (scoring, KPIs)

## Reference Documents

- `docs/process/certificate-driven-development.md` -- Certificate templates and state machine
- `docs/process/development-lifecycle-bpmn.md` -- Full BPMN lifecycle specification
- `docs/process/agent_validation_architecture.md` -- 9-stage validation pipeline and KPIs
- `docs/process/final_design_docs/sdlc-control-plane-technical-spec.md` -- DDD bounded contexts, rule placement, SCIPP
- `docs/process/final_design_docs/sdlc-control-plane-implementation-plan.md` -- 5-phase roadmap
- `schemas/agent_workflow_schema_bundle.json` -- Canonical JSON Schema bundle
