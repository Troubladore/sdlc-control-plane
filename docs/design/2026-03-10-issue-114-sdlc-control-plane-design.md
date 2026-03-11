# SDLC Control Plane — Repository & Implementation Design

> Design doc for Issue #114 (D.11): Camunda State Engine for Certificate-Driven Development
> Approved: 2026-03-10

## Decision: Separate Repository

The SDLC control plane is infrastructure and process tooling, not grounding measurement code.
It gets its own published repository: `eruditis/sdlc-control-plane`.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repository | `eruditis/sdlc-control-plane` | Matches "Engineering Control Plane" language in specs |
| Language | Python-first | Bottleneck is LLM round-trips, not compute. One toolchain for approachability. |
| Camunda coupling | Decoupled — env vars point to external cluster | Control plane doesn't own engine lifecycle |
| LLM integration | Protocol-first with mock reviewers | Prove orchestration, gating, validation before adding LLM variance |
| Audience | Reusable framework with research narrative in docs | Configurable for other teams; research angle is first-class documentation |
| Phasing | Thin vertical slice, then widen | Optimize for cognitive load per session, not demo milestones |

## Architecture Overview

### Bounded Contexts (from technical spec)

| Context | Owns | Initial Form |
|---------|------|--------------|
| Verification & Evidence | Evidence inventory, certificates, validation, disputes | Python module |
| Delivery Orchestration | BPMN processes, timers, routing, transitions | Camunda + Python Zeebe client |
| Engineering Policy & Standards | Standards catalog, rule classification, SCIPP | Python module |
| Exception & Remediation | Waivers, deficiencies, remediation ledger | Python module |
| Measurement & Experimentation | Workflow events, KPIs, dashboards | Python module |
| Engineering Context Profile | Repo profile, subsystem tags, ownership | Python module |

### Tech Stack

- Python 3.10+ with `uv` for dependency management
- Pydantic for data models (generated from JSON Schema bundle)
- FastAPI for service APIs (when needed)
- `pyzeebe` or Zeebe REST API for Camunda interaction
- pytest + hypothesis for testing
- ruff + mypy for quality
- GitHub Actions for CI

### Relationship to Existing Repos

- `eruditis/sdlc-control-plane` — This repo. All control plane code, BPMN/DMN models, schemas, services.
- `~/repos/camunda/` — Unchanged. Docker Compose for Camunda 8 engine. Referenced in deployment docs.
- `~/repos/demo-camunda/` — Unchanged. Model governance tooling (linting, deploy canary). May share patterns.
- `eruditis/grounding-measure-core` — Source of the process design docs. Docs migrate to new repo.

## Implementation Phases (Cognitive-Load Optimized)

Each session is one bounded chunk. Every session ends with something that runs and passes tests.

### Session 0: Repo Skeleton
- Create GitHub repo `eruditis/sdlc-control-plane`
- Migrate all process docs from grounding-measure-core
- Python project structure with `uv`, pytest, ruff, mypy
- CLAUDE.md with project conventions
- CI workflow
- **Ends with:** `uv run pytest` passes

### Session 1: Schema Bundle as Python Package
- Pydantic models from JSON Schema bundle
- CLI: `sdlc validate certificate.json`
- Structural validation (required fields, enums, types)
- **Ends with:** CLI validates/rejects certificate files

### Session 2: Evidence Inventory + Referential Validation
- Evidence inventory builder (file spans, issues, commands)
- Stable artifact/evidence IDs
- Referential validation (all refs resolve)
- **Ends with:** Validator catches broken references

### Session 3: Minimal BPMN Process (Happy Path)
- BPMN process model for single-reviewer happy path
- Zeebe client to start/complete workflow instances
- Deploy to local Camunda
- **Ends with:** Workflow completes in Operate

### Session 4: Transition Gating + Event Emission
- TransitionRequest as mandatory primitive
- Gate evaluation (required artifacts present)
- WorkflowEvent emission on every step
- **Ends with:** Invalid transitions blocked

### Session 5: Claim Verification Engine
- Per-claim verification records
- Command re-run verification
- Source-read verification
- Certificate-type-specific rules
- **Ends with:** Certificates verified claim-by-claim

### Session 6: Mock Reviewer Protocol
- Reviewer interface definition
- Mock reviewer implementation (produces valid certificates)
- Single review mode wired into BPMN
- **Ends with:** Mock reviewer produces schema-valid certificates

### Session 7: Competitive Review
- Parallel reviewer dispatch in BPMN
- Cross-validation subprocess
- Dispute object production
- **Ends with:** Two mock reviewers, disputes filed

### Session 8: Arbiter + Scoring + Leaderboard
- Arbiter subprocess (dispute resolution)
- Incentive scoring engine (+100/+200/+300/-600/-100)
- Leaderboard persistence
- Certificate merge from best claims
- **Ends with:** Leaderboard updates after review cycle

### Session 9: Remediation Ledger
- Append-only log with hash chain
- Signed entries (author verification)
- Separation of duty (Finder acceptance)
- Tamper detection
- Timer events (24hr warning, 48hr escalation)
- **Ends with:** Tampered log detected and rejected

### Session 10: SCIPP Workflow
- Standards Change Intake BPMN process
- Five required intake questions enforcement
- Placement Decision Record workflow
- DMN tables for rule placement
- **Ends with:** Architect proposals routed correctly

### Session 11: GitHub Webhook Integration
- Webhook handler for issue/PR events
- Issue assignment triggers workflow start
- PR events feed into integration phase
- **Ends with:** Issue assignment triggers workflow

### Session 12: KPI Dashboard + Measurement
- WorkflowEvent aggregation
- Core KPI computation (CostPerSuccess, FPY, etc.)
- Dashboard (minimal, data-driven)
- Version comparison reports
- **Ends with:** Dashboard shows real run data

### Session 13: Real LLM Reviewer Integration
- Codex/GPT API as Reviewer A
- Gemini API as Reviewer B
- Structured output parsing for certificate production
- Prompt engineering for cross-validation
- **Ends with:** Live competitive review with real models

## Documents to Migrate

From `grounding-measure-core/docs/process/`:
- `development-lifecycle-bpmn.md`
- `certificate-driven-development.md`
- `agent_validation_architecture.md`
- `final_design_docs/sdlc-control-plane-technical-spec.md`
- `final_design_docs/sdlc-control-plane-implementation-plan.md`
- `agent_validation_design_inputs/agent_workflow_schema_bundle.json`
- `agent_validation_design_inputs/development-lifecycle-bpmn.numbered.txt`
- `agent_validation_design_inputs/certificate-driven-development.numbered.txt`

## Source Lineage

This design synthesizes:
- Issue #114 (D.11) acceptance criteria
- SDLC Control Plane Technical Specification
- SDLC Control Plane Implementation Plan
- Agent Workflow Validation Architecture and KPI Plan
- Certificate-Driven Development process definition
- Development Lifecycle BPMN process definition
- Agent Workflow Schema Bundle (JSON Schema)
