# SDLC Control Plane Technical Specification

## 1. Purpose

This specification defines a first implementation slice of an SDLC control plane that is optimized for confidence, auditability, and controlled evolution.

It is explicitly scoped to two deliverables:

1. **Rigorous Review Process**
   - Evidence-backed review for code delivery work
   - Certificate generation, validation, dispute handling, and gated transitions

2. **Standards Change Intake and Placement Process (SCIPP)**
   - Formal intake for new architect standards
   - Classification, bounded-context ownership, placement decision, exception path, and KPI hypothesis

This spec is an addendum and consolidation of the current certificate-driven development design, BPMN lifecycle design, validation and KPI design, and the DDD / bounded-context guidance discussed so far.

## 2. Optimization target

This system is optimized for the following, in this order:

1. Epistemic confidence
2. Auditability and replayability
3. Controlled extensibility
4. Human working-memory offload
5. Measured value over process theatre
6. Throughput and latency only after the above are acceptable

The design assumes that false confidence in a change or a standard is far more expensive than extra compute or extra deterministic validation.

## 3. Architectural stance

### 3.1 Core statement

Build an **Engineering Control Plane**, not a giant monolithic SDLC workflow.

### 3.2 Boundary statement

Use DDD bounded contexts to separate meaning and ownership. Use Camunda to orchestrate across those contexts. Use DMN for auditable decisions. Use domain services and deterministic validators to enforce invariants.

### 3.3 Implementation stance

Start as:

- Camunda as the orchestration runtime
- a modular monolith for the remaining bounded contexts where practical
- one event model and one schema discipline across all authoritative artifacts

Split into separate services only when justified by ownership, release cadence, audit boundary, or runtime needs.

## 4. In-scope business problem

The pilot solves two linked business problems:

### 4.1 Problem A - Rigorous review

The organization needs a way to prove that a change was implemented and reviewed to a defined quality bar, with explicit evidence for each binding claim.

### 4.2 Problem B - Architect standards intake

The organization needs a way to absorb new standards without turning every new request into a direct BPMN edit or an endless architecture debate. Every new rule needs a repeatable intake, classification, ownership, placement, exception model, and measurement hypothesis.

## 5. Control-plane invariants

These invariants apply to the pilot and should be enforced from the start.

1. No authoritative artifact is accepted without schema validation.
2. No binding claim is accepted without evidence references.
3. No workflow state transition occurs without required verifier artifacts.
4. No standards-affecting code change is merged without an approved Placement Decision Record.
5. No exception is valid without authority, expiry, and compensating controls.
6. No implemented standard is considered complete without a KPI hypothesis and observation window.
7. Every workflow step emits a WorkflowEvent record.

## 6. Bounded context map

This is the target logical decomposition for the pilot.

| Bounded context | Purpose | Owns | Initial deployment mode |
|---|---|---|---|
| Delivery Orchestration | Long-running workflow, task routing, escalation, gates | BPMN processes, workflow instances, transition orchestration | Camunda runtime |
| Verification and Evidence | Truthful artifact handling | evidence inventory, certificates, verification records, disputes, rendered markdown | module or service |
| Engineering Policy and Standards | Standard meaning and placement | standards catalog, applicability logic, placement decisions, policy DMN | module or service |
| Exception and Remediation | Controlled escape hatches | waivers, deficiencies, remediation ledger, compensating controls | module or service |
| Measurement and Experimentation | Outcome measurement | workflow events, KPI computation, dashboards, version comparisons | module or data pipeline |
| Engineering Context Profile | Facts about repos and change scope | repo profile, subsystem tags, ownership, sensitivity tier, architecture-impact facts | module |

### 6.1 What Camunda owns

Camunda owns:

- process flow
- human tasks
- timers
- escalation
- transition sequencing
- waiting and correlation

Camunda does **not** own:

- the semantic truth of whether a certificate is valid
- the semantic truth of whether a standard applies
- the semantic truth of whether a waiver is valid
- the semantic truth of business or engineering invariants

### 6.2 What services or modules own

The service or module for a bounded context owns:

- the data model for that context
- its invariants
- its validation rules
- its externally visible API and events
- any DMN tables written in that context's language

## 7. Rule placement model

Every proposed rule must be classified before implementation.

### 7.1 Canonical rule classes

| Rule class | Meaning | Default home |
|---|---|---|
| Invariant | a state that must never exist | domain service, deterministic validator, or policy-as-code |
| Decision | given facts, choose an outcome or requirement set | DMN owned by the relevant context |
| Orchestration rule | ordering, routing, who/when/escalation | BPMN in Delivery Orchestration |
| Integration rule | how systems communicate or synchronize | connector, adapter, or event handler |
| Non-functional requirement | cross-cutting quality or operational concern | platform control, CI policy, observability, or standards catalog |

### 7.2 Placement rules

Use this matrix when turning the five intake questions into implementation.

| If the rule says... | Implement primarily in... | Optional secondary home |
|---|---|---|
| "this must never be accepted" | Verification service or policy code | BPMN gate to surface failure |
| "if facts look like X, require Y" | DMN | BPMN to branch based on DMN output |
| "after A happens, request B and wait for C" | BPMN | DMN for branching logic |
| "all repo changes touching subsystem Q need control R" | policy DMN + standards catalog | CI policy or verification rule |
| "this evidence must exist before merge" | Verification service | BPMN gate |
| "this exception may be granted only by role Z for 14 days" | Exception service | BPMN task for approval workflow |
| "tool X must post result to system Y" | integration adapter | BPMN connector for orchestration |

### 7.3 FEEL usage rule

Use FEEL only for local decision expressions inside DMN or BPMN. Do not use FEEL as the only home of durable business meaning.

### 7.4 Microservice split rule

A bounded context may start as a module. Split it into a separate service only when at least one of these is true:

- it has a different owner team
- it needs an independent release cadence
- it serves multiple workflows or products and must be protected from orchestration changes
- it carries a distinct audit or compliance boundary
- it needs distinct runtime scaling or storage characteristics

## 8. Deliverable A - Rigorous Review Process specification

### 8.1 Purpose

Provide an evidence-backed, machine-checkable review process for a single pilot path in the SDLC.

### 8.2 Pilot workflow states

The pilot workflow should support at least these states:

- pending
- implementing
- self_review
- certificate_review
- certified
- integrated
- complete
- issues_rework

### 8.3 State transition principle

State transitions are never justified by agent prose alone.

Each transition requires:

- a TransitionRequest artifact
- the required supporting artifacts
- completed gate evaluations
- deterministic validation of the gate conditions

### 8.4 Required review artifacts

The pilot supports these artifact types:

- TaskReviewCertificate
- DesignDecisionCertificate
- DeferredScopeCertificate
- ImpactAlignmentCertificate
- DisputeObject
- TransitionRequest
- RemediationLog
- WorkflowEvent

These already exist in the current schema bundle and remain canonical.

### 8.5 Certificate semantics

#### Task Review Certificate

Purpose:
- prove task completion and code quality in one integrated pass

Must include:
- premises from spec or issue acceptance criteria
- quality assertions
- verification commands
- formal conclusion
- issues if present

#### Design Decision Certificate

Purpose:
- prove that a design choice is justified against reference patterns or documented superior divergence

#### Deferred Scope Certificate

Purpose:
- prove that deferral is explicit, tracked, consistent, and positioned in the dependency graph

#### Impact Alignment Certificate

Purpose:
- prove that the change does not silently drift from open issues, plans, roadmap, or documentation

### 8.6 Validation pipeline

The review process uses this pipeline.

1. Evidence inventory build
2. Constrained artifact generation
3. Structural validation
4. Referential validation
5. Claim verification
6. Certificate-specific rule evaluation
7. Optional dispute and arbiter flow
8. Transition gatekeeping
9. Workflow event emission

### 8.7 Evidence inventory

The Verification and Evidence context must build a stable evidence inventory before a certificate is accepted.

Minimum evidence sources:

- file spans
- issue titles and bodies
- command outputs
- commit references
- diff metadata
- document or plan references

Every evidence item must have a stable ID. Certificates cite IDs, not freehand references, whenever possible.

### 8.8 Constrained decoding boundary

Use constrained decoding for authoritative artifacts only.

Allowed constrained outputs:

- certificate JSON
- dispute JSON
- transition request JSON
- remediation entries

Not required for:

- exploratory reasoning
- brainstorming
- narrative analysis before a binding claim is made

### 8.9 Claim verification rules

Minimum verification rules for pilot review:

| Certificate type | Required verification |
|---|---|
| Task Review | re-run or inspect every verification command and re-read cited file spans |
| Design Decision | inspect both local and reference evidence cited |
| Deferred Scope | verify issue existence, acceptance criteria, and roadmap position |
| Impact Alignment | read issue bodies for same-milestone or nearby impacted issues; title-only scan is allowed only where explicitly justified |

### 8.10 Review-mode decision

A DMN table should choose single review vs competitive review.

Inputs:
- change risk
- architecture impact
- process docs touched
- size of change
- subsystem criticality

Outputs:
- review_mode = single or competitive
- arbiter_required = true or false

Default pilot behavior:
- single review for most changes
- competitive review only for process docs, architecture-impacting changes, or other high-risk cases

### 8.11 Exception model

If review artifacts fail, the default path is rework.

If a waiver is allowed, it must include:

- waiver ID
- approving authority
- reason
- expiry
- compensating controls
- linked deficiency IDs

### 8.12 Non-negotiable acceptance tests for Deliverable A

1. If a certificate is malformed, schema validation fails and the workflow cannot advance.
2. If a certificate cites missing evidence, referential validation fails and the workflow cannot advance.
3. If a same-milestone issue is marked NONE without body-level verification, Impact Alignment fails.
4. If a TransitionRequest lacks required artifacts, the transition is rejected.
5. If a claim has no verification record when required, the certificate cannot become validated.

## 9. Deliverable B - Standards Change Intake and Placement Process specification

### 9.1 Purpose

Provide a formal process that absorbs new architect standards, turns them into owned artifacts, and routes them to the correct implementation home.

### 9.2 Process policy

A standards change is not a conversation. It is a governed change artifact.

Every new standard, modification, or retirement proposal must become an SCIPP instance.

### 9.3 SCIPP states

The process should support these states:

- draft
- submitted
- needs_info
- classified
- routed
- designed
- approved
- implemented
- verified
- observed
- closed
- rework

### 9.4 Required questions

SCIPP must enforce the following fields before a proposal can leave `submitted`:

1. rule class
2. owning bounded context
3. required evidence artifact
4. exception path
5. KPI hypothesis

### 9.5 SCIPP artifacts

#### 9.5.1 StandardChangeProposal

Purpose:
- capture the proposed standard and its intended business value

Minimum fields:

```json
{
  "proposal_id": "scp-001",
  "title": "Require threat model evidence for auth-impacting changes",
  "proposer": {"actor_id": "arch-17", "role": "principal_architect"},
  "standard_text": "Changes that materially affect authentication flows must include a threat model artifact.",
  "business_driver": "reduce late security review churn and escaped auth design defects",
  "rule_class": "decision",
  "candidate_owning_context": "engineering_policy_and_standards",
  "evidence_artifact_type": "threat_model_record",
  "exception_required": true,
  "exception_summary": "temporary waiver allowed for emergency hotfixes",
  "primary_kpi": "post_merge_security_findings",
  "status": "submitted"
}
```

#### 9.5.2 PlacementDecisionRecord

Purpose:
- record where the rule will live and why

Minimum fields:

```json
{
  "pdr_id": "pdr-001",
  "proposal_id": "scp-001",
  "final_rule_class": "decision",
  "owning_context": "engineering_policy_and_standards",
  "implementation_homes": [
    "standard_applicability.dmn",
    "verification_rule",
    "bpmn_gate"
  ],
  "rationale": "applicability is a policy decision; evidence enforcement is a verification invariant; workflow needs a gate",
  "exception_owner": "exception_and_remediation",
  "measurement_owner": "measurement_and_experimentation",
  "status": "approved"
}
```

#### 9.5.3 KPIHypothesis

Purpose:
- define how value will be measured

Minimum fields:

```json
{
  "hypothesis_id": "kh-001",
  "proposal_id": "scp-001",
  "primary_metric": "post_merge_security_findings",
  "expected_direction": "down",
  "guardrail_metrics": ["human_minutes_per_success", "review_churn"],
  "baseline_window_days": 30,
  "observation_window_days": 45,
  "success_threshold": "20_percent_reduction_without_more_than_10_percent_human_time_increase"
}
```

#### 9.5.4 ExceptionModel

Purpose:
- define waiverability and compensating controls

Minimum fields:

```json
{
  "exception_model_id": "em-001",
  "proposal_id": "scp-001",
  "waiverable": true,
  "waiver_authority": "security_architecture_owner",
  "max_duration_days": 14,
  "compensating_controls": ["manual_security_review"],
  "expiry_behavior": "revert_to_required",
  "evidence_required": ["waiver_reason", "approver_identity"]
}
```

### 9.6 Placement decision workflow

Use this sequence:

1. Proposer submits SCP.
2. Intake steward checks completeness.
3. Policy owner classifies rule class.
4. Candidate owning context is confirmed.
5. Evidence owner defines proof artifact.
6. Exception owner defines waiver path.
7. Measurement owner approves KPI hypothesis.
8. PDR is approved.
9. Implementation change set is created.
10. Post-implementation review decides keep, revise, or retire.

### 9.7 Rule placement decision support

A small DMN table may provide a recommended placement. Human approval is still required.

Inputs:
- rule class
- object of control (artifact, workflow state, codebase property, team behavior)
- whether the rule requires durable truth protection
- whether the rule requires routing or waiting behavior
- whether the rule requires runtime integration

Outputs:
- primary home
- secondary home
- owning bounded context
- default exception owner

### 9.8 Enforcement rules for Deliverable B

1. A PR that modifies BPMN, DMN, standards catalog, validation rules, or control-plane code must reference an approved PDR.
2. A PDR cannot be approved without a KPI hypothesis and exception model.
3. A proposal cannot be marked implemented until the owning context confirms the change and the Measurement context records the observation window.
4. A proposal cannot be closed until a Post-Implementation Review is recorded.

### 9.9 Non-negotiable acceptance tests for Deliverable B

1. A proposal missing one of the five required questions is routed to `needs_info`.
2. A proposal classified as an invariant cannot be satisfied by BPMN alone.
3. A standards-related PR without a linked PDR is rejected by CI.
4. A standard without a KPI hypothesis cannot be marked approved.
5. A standard without an exception model cannot be marked implemented unless explicitly non-waiverable.

## 10. Shared platform components

### 10.1 Canonical schema bundle

The current schema bundle remains the base. Extend it with a second bundle or merged bundle for SCIPP artifacts.

Base artifact families already defined:
- certificate artifacts
- disputes
- transition requests
- remediation log
- workflow events

New artifact families required:
- StandardChangeProposal
- PlacementDecisionRecord
- KPIHypothesis
- ExceptionModel
- StandardsApplicabilityRule
- PostImplementationReview

### 10.2 Evidence storage

Need at least:
- relational store for metadata and status
- object store for logs and rendered artifacts
- immutable IDs for evidence and artifacts

### 10.3 Event stream

Every major action emits a WorkflowEvent or StandardsEvent.

Minimum event types:
- ReviewRunStarted
- EvidenceInventoryBuilt
- CertificateSubmitted
- CertificateValidated
- TransitionRequested
- TransitionApproved
- StandardProposalSubmitted
- StandardProposalClassified
- PlacementDecisionApproved
- StandardImplemented
- StandardObserved
- WaiverGranted
- RemediationAccepted

### 10.4 Engineering Context Profile

For the pilot, the context profile can stay simple.

Minimum facts:
- repo ID
- service or subsystem tags
- owner team
- sensitivity tier
- architecture impact flag
- process-doc-touched flag
- change class

These facts feed DMN and KPI segmentation.

## 11. BPMN, DMN, and service ownership

### 11.1 BPMN processes

The pilot should define at least two BPMN process models:

1. `rigorous_review_demo.bpmn`
2. `standards_change_intake_and_placement.bpmn`

### 11.2 DMN decisions

The pilot should define at least these DMN tables:

1. `required_certificates_by_change_profile.dmn`
2. `review_mode_selection.dmn`
3. `standard_placement_suggester.dmn`
4. `standard_applicability_by_repo_profile.dmn`

Ownership:
- orchestration-facing DMN belongs with Delivery Orchestration if it uses orchestration language
- policy-facing DMN belongs with Engineering Policy and Standards if it uses policy language

### 11.3 Service or module responsibilities

#### Verification and Evidence

Suggested API surface:
- `POST /evidence-inventories`
- `POST /certificates/{type}`
- `POST /certificates/{id}/validate`
- `POST /disputes`
- `POST /transition-requests`
- `GET /artifacts/{id}`

#### Engineering Policy and Standards

Suggested API surface:
- `POST /standard-proposals`
- `POST /placement-decisions`
- `GET /standards/{id}`
- `POST /standards/{id}/evaluate-applicability`
- `POST /post-implementation-reviews`

#### Exception and Remediation

Suggested API surface:
- `POST /waivers`
- `POST /deficiencies`
- `POST /remediation-entries`
- `POST /deficiencies/{id}/accept`

#### Measurement and Experimentation

Suggested API surface:
- `POST /workflow-events`
- `GET /kpis`
- `GET /version-comparisons`

## 12. Constrained decoding usage specification

### 12.1 Principle

Constrained decoding is used to make authoritative artifacts valid and referentially sound. It is not relied on as the primary source of semantic correctness.

### 12.2 Where to use it

Use constrained decoding for:
- certificates
- disputes
- transition requests
- remediation entries
- standard proposals
- placement decisions

### 12.3 What to constrain

At minimum constrain:
- JSON structure
- enum values
- claim IDs
- artifact IDs
- evidence IDs
- certificate types
- workflow states

### 12.4 What not to promise

Constrained decoding guarantees structural validity and valid references. It does not guarantee that a cited artifact actually supports the claim. That is the role of claim verification.

### 12.5 Reasoning mode split

Use two modes:

1. Semi-formal exploration mode
   - open reasoning with explicit premises and evidence gathering
2. Binding artifact mode
   - schema-constrained output only

The system should switch to binding artifact mode whenever an agent is about to assert something that affects state transitions, waivers, or official records.

## 13. Measurement specification

### 13.1 Minimum KPI pack

These KPIs should exist before broad rollout:

- CostPerSuccess
- FirstPassYield
- HumanMinutesPerSuccess
- GateFailureDistribution
- ReviewChurn
- PostMergeDefectRate
- SchemaPassRate
- EvidenceBackedClaimRate
- VerifiedClaimCoverage
- ArtifactBackedTransitionRate
- ProposalCompletenessRate
- PlacementLeadTime
- PlacementReworkRate

### 13.2 KPI interpretation rule

A control is valuable only if it improves one or more of these without unacceptable guardrail regressions:

- verified correctness
- escaped-defect rate
- review churn
- human minutes
- transition integrity
- auditability

A control is probably theatre if it mainly adds paperwork without changing transition behavior, catch rate, or real outcomes.

### 13.3 Observation windows

For SCIPP changes, define both:
- baseline window
- observation window

Do not claim success for a new standard without comparing before vs after over comparable work.

## 14. Repository and deployment layout

A practical v1 layout:

```text
/control-plane
  /processes
    rigorous_review_demo.bpmn
    standards_change_intake_and_placement.bpmn
  /dmn
    required_certificates_by_change_profile.dmn
    review_mode_selection.dmn
    standard_placement_suggester.dmn
    standard_applicability_by_repo_profile.dmn
  /schemas
    agent_workflow_schema_bundle.json
    standards_intake_schema_bundle.json
  /services
    verification
    policy
    exceptions
    measurement
    context_profile
  /renderers
  /dashboards
  /docs
```

Deployment recommendation for pilot:
- Camunda deployed separately
- one application deployable for control-plane modules
- one relational database
- one object store or durable artifact store
- one dashboarding stack

## 15. Worked example

Use this example to test the full design.

### Example standard

"Changes that materially affect authentication flows must include a threat model artifact before PR integration."

### SCIPP answers

1. Rule class
   - decision plus evidence requirement
2. Owning bounded context
   - Engineering Policy and Standards owns applicability language
3. Evidence artifact
   - threat_model_record
4. Exception path
   - 14-day waiver with manual security review as compensating control
5. KPI
   - reduce post-merge security findings and security review churn

### Placement decision

- Policy DMN decides whether the change profile requires a threat model.
- Verification service enforces that the required artifact exists and is valid.
- BPMN introduces a gate before PR integration.
- Exception service handles hotfix waivers.
- Measurement tracks whether the new rule reduces real defects or simply adds cost.

This example demonstrates why the rule should not live in Camunda alone.

## 16. IT4IT alignment

This pilot aligns to IT4IT as follows:

- Strategy to Portfolio
  - standards backlog, prioritization, and control roadmap
- Requirement to Deploy
  - rigorous review workflow and policy application to changes
- Detect to Correct
  - remediation, post-merge defects, waiver expiry, and policy feedback loops

This keeps the pilot grounded in a familiar enterprise operating model while using DDD for internal boundary discipline.

## 17. Security, audit, and separation of duty

Minimum controls for the pilot:

- immutable artifact IDs
- policy and process versioning in source control
- recorded approver identities for waivers and PDRs
- separation of duty for remediation acceptance
- versioned DMN and BPMN deployments
- correlation IDs across workflow instance, change request, and artifact set

## 18. Acceptance criteria for the full pilot

The pilot is acceptable only if all of these are true:

1. A real review run can be replayed from evidence inventory, artifacts, and workflow events.
2. At least one bad certificate is automatically blocked for a real reason.
3. At least one real architect standard is routed to a service or policy layer instead of being stuffed into BPMN.
4. A standards-related code change cannot merge without a PDR.
5. Dashboards can show whether the new controls improved or worsened outcomes.

## 19. Deferred items

Do not treat these as v1 requirements unless the pilot proves the basics first:

- full multi-repo engineering context graph
- enterprise-wide standards catalog
- broad competitive review on all changes
- broad service decomposition
- advanced risk scoring and machine learning

## 20. Source lineage

This specification synthesizes these inputs:

- Certificate-Driven Development
- Development Lifecycle BPMN design
- Validation architecture and KPI design
- BDD / DDD and business-process boundary guidance
- Semi-formal reasoning guidance from the agentic code reasoning paper
- EY article on connecting agents to engineering standards, repositories, and compliance context
