# sdlc-control-plane

A reusable SDLC governance framework that provides evidence-backed, machine-checkable review for software delivery work.

Built on [Camunda 8](https://camunda.com/) for workflow orchestration, with certificate-driven development, competitive multi-model review, and tamper-proof audit trails.

## Why This Exists

Most code review is a trust exercise. A reviewer says "looks good" and everyone moves on. When things go wrong, there's no evidence trail to replay -- just a green checkmark and a prayer.

This project replaces trust with **verifiable evidence**. Every claim of completion -- "tests pass," "design matches spec," "no scope drift" -- must cite machine-checkable evidence. State transitions in the development lifecycle are gated by deterministic validation, not prose.

The system also introduces **competitive multi-model review**: two independent AI reviewers produce certificates in parallel, cross-validate each other's claims, and an arbiter resolves disputes. A scoring system with asymmetric penalties (catching real errors is rewarded; filing false disputes is penalized 3x) creates an incentive structure that rewards thoroughness over rubber-stamping.

### Research Context

This work operationalizes ideas from semi-formal reasoning in agentic code analysis (Ugare & Chandra, 2026), which shows that requiring explicit premises, evidence traces, and formal conclusions improves code analysis accuracy by 10+ percentage points. The framework extends this insight from individual analysis sessions to the full SDLC lifecycle, treating the development process itself as a system that can be measured and governed.

## Architecture

The system is built as an **Engineering Control Plane** using DDD bounded contexts:

| Context | Purpose |
|---------|---------|
| **Verification & Evidence** | Evidence inventory, certificate validation, dispute handling |
| **Delivery Orchestration** | BPMN workflow, state transitions, timers, escalation |
| **Engineering Policy & Standards** | Standards catalog, rule classification, intake process |
| **Exception & Remediation** | Waivers, deficiency tracking, hash-chained remediation ledger |
| **Measurement & Experimentation** | Workflow events, KPI computation, outcome dashboards |
| **Engineering Context Profile** | Repo metadata, subsystem tags, sensitivity tiers |

Camunda orchestrates across contexts. Domain services own semantic truth. DMN tables handle auditable decisions. This separation means rules live where they belong -- not everything gets stuffed into BPMN.

## Certificate Types

| Certificate | Proves |
|------------|--------|
| **Task Review** | Task completion and code quality, with cited evidence for every claim |
| **Design Decision** | Design choice is justified against reference patterns |
| **Deferred Scope** | Deferral is explicit, tracked, and positioned in the dependency graph |
| **Impact Alignment** | Change doesn't silently drift from open issues, plans, or docs |

## Key Design Decisions

- **Decoupled from Camunda engine lifecycle** -- bring your own cluster (SaaS or self-hosted)
- **Protocol-first LLM integration** -- reviewer interface is defined by contract, not by specific model
- **Python-first** -- the bottleneck is LLM round-trips, not compute
- **Append-only remediation ledger** -- hash-chained, signed, tamper-evident
- **Artifact-first** -- all authoritative documents are JSON validated against a canonical schema bundle

## Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for dependency management
- A Camunda 8 cluster (for workflow sessions; not needed for schema validation)

### Install

```bash
git clone https://github.com/Troubladore/sdlc-control-plane.git
cd sdlc-control-plane
uv sync --extra dev
```

### Run Tests

```bash
make check    # lint + type check + tests
make test     # just tests
```

### CLI

```bash
uv run sdlc --help
uv run sdlc validate    # Validate certificate artifacts (Session 1+)
```

### Connect to Camunda

Copy `.env.example` to `.env` and point to your cluster:

```bash
cp .env.example .env
# Edit ZEEBE_GRPC, ZEEBE_REST, CAMUNDA_OPERATE_URL
```

## Project Structure

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
    process/            # Process specifications
    design/             # Design documents
```

## Documentation

- [Certificate-Driven Development](docs/process/certificate-driven-development.md) -- process definition and certificate templates
- [Development Lifecycle BPMN](docs/process/development-lifecycle-bpmn.md) -- full workflow specification
- [Validation Architecture](docs/process/agent_validation_architecture.md) -- 9-stage pipeline and KPI model
- [Technical Specification](docs/process/final_design_docs/sdlc-control-plane-technical-spec.md) -- DDD contexts, rule placement, SCIPP
- [Implementation Plan](docs/process/final_design_docs/sdlc-control-plane-implementation-plan.md) -- phased roadmap
- [Design Doc](docs/design/2026-03-10-issue-114-sdlc-control-plane-design.md) -- repository and session design

## License

MIT
