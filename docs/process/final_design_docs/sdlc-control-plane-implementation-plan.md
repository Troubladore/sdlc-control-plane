# SDLC Control Plane Implementation Plan

## 1. Purpose

This plan scaffolds two deliverables in a way that is incremental, auditable, and measurable:

1. A rigorous review process for software delivery work, centered on evidence-backed certificates, validation, and gated workflow transitions.
2. A formal standards intake and placement process that lets principal architects add, modify, or retire standards without creating architectural chaos.

The plan is intentionally optimized for epistemic confidence, auditability, and controlled extensibility. It is not optimized for the fastest possible throughput. The working assumption is that compute is cheaper than architectural confusion, false confidence, or slow human argument loops.

## 2. What success looks like

At the end of the pilot, the organization should be able to demonstrate all of the following in one bounded slice of the SDLC:

- A real change can move from issue -> implementation -> self review -> certificate review -> PR integration with evidence-backed gates.
- No workflow state can advance on agent prose alone. Advancement requires verifier artifacts.
- New architect standards no longer arrive as ad hoc requests to edit BPMN. They enter through a formal intake process, are classified, assigned to the correct bounded context, and produce an explicit implementation decision.
- The system can tell whether added rigor is helping or creating process theatre by measuring quality, yield, human effort, and cost.

## 3. Pilot scope

The pilot focuses on one narrow but high-value part of the SDLC:

- Code implementation and review for a single pilot repository or product area.
- The certificate types already defined in the current design:
  - Task Review Certificate
  - Design Decision Certificate
  - Deferred Scope Certificate
  - Impact Alignment Certificate
- The standards intake process for rules that affect this pilot lane.

Out of scope for the pilot:

- Enterprise-wide rollout across all teams
- Full IT4IT coverage across every value stream
- Full microservice decomposition on day 1
- Large architecture refactors, full release management, or production operations control planes

## 4. Implementation principles

### 4.1 Optimize for confidence, not speed

The target outcome is a trustworthy externalized working memory for SDLC governance. The system must make it difficult to be wrong silently.

### 4.2 Boundaries first, services second

Use bounded contexts from the start, but begin implementation as a modular monolith plus Camunda where practical. Split into separate services only when the ownership, release cadence, audit boundary, or runtime profile justifies it.

### 4.3 Treat authoritative artifacts as machine-readable first

Canonical artifacts are JSON objects validated against schemas. Human-readable markdown is rendered from those canonical objects.

### 4.4 Agents propose; the control plane verifies

Agents may explore semi-formally, but binding assertions to the workflow must be schema-constrained, evidence-backed, and deterministically validated.

### 4.5 Every change to the system goes through the system

No direct edits to BPMN, DMN, policy code, certificate rules, or KPI definitions should be merged unless they are tied to an approved standards intake artifact.

## 5. Target bounded contexts for the pilot

The pilot should make these boundaries explicit even if several start as modules in one deployable:

1. Delivery Orchestration
   - Owns BPMN processes, timers, routing, escalation, and workflow transitions.
   - Technology anchor: Camunda 8.

2. Verification and Evidence
   - Owns evidence inventory, certificate validation, verification records, dispute objects, and rendered certificates.

3. Engineering Policy and Standards
   - Owns standards catalog, rule classification, applicability logic, and placement decisions.
   - Owns policy DMN tables.

4. Exception and Remediation
   - Owns waivers, compensating controls, deficiency lifecycle, and remediation ledger.

5. Measurement and Experimentation
   - Owns workflow event stream, KPI computation, dashboards, and version comparisons.

6. Engineering Context Profile
   - Minimal slice of the later context graph.
   - Owns repo profile, ownership metadata, subsystem tags, and applicability facts needed by policy decisions.

## 6. Formal process for absorbing new architect standards

This process is built first because it becomes the mechanism by which the rest of the system evolves.

### 6.1 Process name

Use this name consistently:

**Standards Change Intake and Placement Process (SCIPP)**

### 6.2 Required intake questions

Every proposal must answer these five questions before design work begins:

1. Is this rule an invariant, decision, orchestration rule, integration rule, or non-functional requirement?
2. Which bounded context owns the words in this rule?
3. What evidence artifact proves compliance?
4. What is the exception or waiver path?
5. What KPI should move if this is worth implementing?

### 6.3 Mandatory artifacts

Each SCIPP instance must produce these artifacts:

- Standard Change Proposal (SCP)
- Placement Decision Record (PDR)
- KPI Hypothesis
- Exception Model
- Implementation Change Set
- Post-Implementation Review

### 6.4 Enforcement rule

A PR that changes BPMN, DMN, standards catalog, certificate schemas, validation logic, or control-plane services must reference an approved PDR ID. CI should reject the PR if that reference is missing.

## 7. Phased roadmap

The roadmap below is designed so that the pilot becomes useful early, while keeping later expansion paths open.

---

## Phase 0 - Charter, boundaries, and baseline

### Objective

Establish the architecture and measurement frame before building automation.

### Build

- Confirm pilot repository or product area.
- Confirm pilot workflow scope: issue -> implementation -> review -> PR integration.
- Publish the bounded context map.
- Publish the rule placement matrix.
- Define the workflow event schema and baseline KPI pack.
- Baseline the last 10 to 20 comparable changes if data exists.
- Stand up SCIPP as a lightweight process first, even if initial execution is partly manual.

### Deliverables

- Architecture charter
- Bounded context map
- Rule placement matrix
- Baseline KPI dashboard definition
- SCIPP template pack

### Exit criteria

- Every new standards request is captured as an SCP.
- The pilot team agrees on owners for each bounded context.
- Baseline metrics exist for current review flow.

### KPIs to watch

- ProposalCompletenessRate
- Baseline FirstPassYield
- Baseline HumanMinutesPerSuccess
- Baseline ReviewChurn
- Baseline PostMergeDefectRate

### Notes

Do not automate aggressively in this phase. The main goal is to create the vocabulary and decision rights that will prevent chaos later.

---

## Phase 1 - Canonical artifact contracts and intake workflow

### Objective

Turn both deliverables into machine-checkable artifacts before wiring complex behavior.

### Build

#### For rigorous review

- Adopt the current certificate schema bundle as the canonical artifact set.
- Render markdown certificates from canonical JSON.
- Define evidence inventory IDs and artifact IDs.
- Define TransitionRequest and WorkflowEvent as mandatory primitives.

#### For architect intake

- Add schema definitions for:
  - StandardChangeProposal
  - PlacementDecisionRecord
  - KPIHypothesis
  - ExceptionModel
  - StandardsApplicabilityRule
- Implement SCIPP as a workflow with states:
  - Draft
  - Submitted
  - Needs Info
  - Classified
  - Routed
  - Designed
  - Approved
  - Implemented
  - Verified
  - Observed
  - Closed or Rework
- Implement a simple standards catalog.

### Deliverables

- Canonical JSON and markdown rendering for pilot artifacts
- Schema validation for certificates and intake artifacts
- SCIPP workflow definition v1
- Standards catalog v1

### Exit criteria

- A certificate can be submitted and rejected on schema failure.
- An architect proposal can be submitted and rejected if the five required questions are unanswered.
- Markdown is no longer the source of truth.

### KPIs to watch

- SchemaPassRate
- MandatoryFieldMissRate
- ProposalSchemaPassRate
- ProposalCompletenessRate
- EvidenceBackedClaimRate

### Notes

This phase removes malformed artifacts. It does not yet prove semantic correctness.

---

## Phase 2 - Pilot review workflow in Camunda

### Objective

Make the original rigorous review process executable for one real path through the SDLC.

### Build

- Implement the pilot BPMN process in Camunda for:
  - Pending
  - Implementing
  - Self Review
  - Certificate Review
  - Certified
  - Integrated
  - Complete
  - Issues / Rework loop
- Connect Git provider and CI artifacts to the evidence inventory.
- Implement structural validation and referential validation.
- Require TransitionRequest artifacts for state changes.
- Gate state advancement on verifier artifacts rather than agent assertions.
- Support these certificate types in the pilot:
  - Task Review Certificate
  - Design Decision Certificate
  - Deferred Scope Certificate
  - Impact Alignment Certificate

### Deliverables

- Pilot BPMN flow in Camunda
- Transition gatekeeper
- Evidence inventory builder
- Certificate submission and validation API
- Git and CI adapters

### Exit criteria

- One real feature branch can go end to end through the pilot workflow.
- Invalid transitions are blocked.
- Broken references are blocked.
- All workflow steps emit WorkflowEvent records.

### KPIs to watch

- ArtifactBackedTransitionRate
- InvalidTransitionRejectionRate
- BrokenReferenceRate
- DeterministicStepCoverage
- GateFailureDistribution
- FirstPassYield by gate

### Notes

Expect short-term yield to dip. The workflow will start catching failures that were previously invisible.

---

## Phase 3 - Claim verification and rule placement engine

### Objective

Raise the pilot from structurally valid to semantically defensible, and make architect standards routable into the correct implementation layer.

### Build

#### For rigorous review

- Implement claim-by-claim verification records.
- Re-run verification commands where required.
- Enforce certificate-type specific validation rules.
- Require Verified coverage for all binding claims.

#### For architect intake

- Implement the PDR workflow step.
- Add a placement decision matrix with these canonical homes:
  - invariant -> domain service / policy code / deterministic validator
  - decision -> DMN owned by the correct bounded context
  - orchestration rule -> BPMN in Delivery Orchestration
  - integration rule -> connector or event handler
  - non-functional requirement -> platform control, CI policy, or observability standard
- Add a small DMN table that suggests likely placement based on rule type and target scope.
- Route at least two real architect rules through SCIPP and place them into the correct components.

### Deliverables

- Verification engine v1
- Placement Decision Record workflow
- Rule placement DMN v1
- Two implemented standards that arrived through SCIPP

### Exit criteria

- No certificate can pass without verification records for its required claims.
- No architect proposal can skip placement and jump directly into Camunda or service code.
- At least two real standards have gone through classification, placement, implementation, and measurement setup.

### KPIs to watch

- VerifiedClaimCoverage
- ValidationCatchRate
- PlacementLeadTime
- PlacementReworkRate
- SameMilestoneIssueBodyReadRate
- TitleOnlyNoneRate
- HumanMinutesPerSuccess

### Notes

This is the phase where false confidence should start dropping if the design is working.

---

## Phase 4 - Exception, remediation, and KPI dashboards

### Objective

Complete the control loop: every standard and every deficiency must have a formal escape hatch and a measurable outcome.

### Build

- Implement waiver and exception records.
- Implement remediation ledger with separation of duty.
- Require every SCIPP proposal to define its exception path.
- Require every implemented standard to define its KPI hypothesis and observation window.
- Build dashboards for the pilot.
- Add post-implementation review to SCIPP.

### Deliverables

- Exception and Remediation module
- Remediation log and verification
- KPI dashboard v1
- SCIPP observation and review stage

### Exit criteria

- Deficiencies cannot be silently closed without accepted remediation evidence.
- Every implemented standard has a KPI hypothesis and measurement window.
- Dashboards show both delivery and governance metrics.

### KPIs to watch

- MedianTimeToRemediateDeficiency
- OpenDeficiencyAgingP95
- AuthorityViolationBlocks
- WaiverRate
- CostPerSuccess
- HumanMinutesPerSuccess
- ReviewChurn
- PostMergeDefectRate

### Notes

This phase is where the organization can start distinguishing real control gains from process theatre.

---

## Phase 5 - Selective competitive review and scale decision

### Objective

Add higher-cost controls only where the evidence says they are worth it.

### Build

- Add competitive dual-review mode for high-risk or high-impact changes only.
- Add dispute objects and arbiter handling.
- Add benchmark replay across orchestration versions.
- Decide whether any bounded contexts should split into separate services.

### Deliverables

- Competitive review mode for selected workflows
- Dispute handling flow
- Version comparison reports
- Service split decision memo

### Exit criteria

- Competitive review is enabled only where it produces measurable value.
- The organization has a clear decision on which modules remain together and which split.

### KPIs to watch

- ValidDisputesPerCertificate
- FalseDisputeRate
- ArbiterOverturnRate
- ReviewChurn
- CostPerSuccess by orchestration version
- PostMergeDefectRate by orchestration version

### Notes

Competitive review should remain scoped until it proves it reduces escaped defects or human burden enough to justify the cost.

---

## 8. Implementation backlog by workstream

### Workstream A - Process and governance

- Define pilot workflow charter
- Publish bounded context map
- Publish rule placement matrix
- Implement SCIPP workflow
- Define approval rights and escalation path

### Workstream B - Verification and evidence

- Adopt existing schema bundle
- Add new standards-intake schemas
- Build evidence inventory
- Build structural validation
- Build referential validation
- Build claim verification
- Build markdown rendering

### Workstream C - Orchestration and decisioning

- Implement pilot review BPMN
- Implement standards intake BPMN
- Implement placement DMN
- Implement certificate-requirements DMN
- Implement competitive-review-required DMN

### Workstream D - Platform and integrations

- Git provider integration
- CI log and artifact ingestion
- Identity and role mapping
- Object storage for evidence
- Event emission plumbing

### Workstream E - Measurement and dashboards

- WorkflowEvent ingestion
- KPI computation jobs
- Baseline vs current comparisons
- Dashboard slices for quality, cost, yield, and governance

## 9. Roles and decision rights

### Required named owners

- Pilot Product Owner
- Delivery Orchestration Owner
- Verification and Evidence Owner
- Engineering Policy and Standards Owner
- Exception and Remediation Owner
- Measurement Owner
- Repo Owner / Service Owner for the pilot codebase
- Architect Intake Steward

### Decision rights

- Process path and task routing -> Delivery Orchestration Owner
- Policy meaning and applicability -> Engineering Policy and Standards Owner
- Certificate semantics and verifier artifacts -> Verification and Evidence Owner
- Waiver and remediation semantics -> Exception and Remediation Owner
- KPI definitions and success thresholds -> Measurement Owner
- Final escalations -> governance council or designated authority

## 10. Demonstration scenarios

Use these two scenarios as the first public demonstrations.

### Demo A - Rigorous review path

1. A pilot feature issue enters the workflow.
2. Implementation happens on a branch.
3. The agent or engineer produces canonical certificates.
4. The control plane validates structure, references, and claims.
5. Camunda blocks any transition without verifier artifacts.
6. The PR is created only after Impact Alignment is validated.
7. Dashboard shows the run, its cost, and where verification caught issues.

### Demo B - Principal architect proposes a new rule

1. Architect submits an SCP.
2. SCIPP forces answers to the five questions.
3. The rule is classified and routed.
4. The PDR shows where the rule belongs:
   - service invariant
   - DMN decision
   - BPMN flow rule
   - CI / platform policy
   - integration adapter
5. The implementation change references the PDR.
6. Post-implementation review checks whether the chosen KPI moved.

## 11. Exit gate for pilot completion

The pilot is complete only if all of the following are true:

- A real review flow runs end to end with evidence-backed state gates.
- At least two real architect standards were absorbed through SCIPP and placed without design chaos.
- The system can identify whether added controls improved quality, yield, or human burden.
- There is a clear decision on which modules stay together and which will later split into standalone services.

## 12. What not to do

Avoid these failure modes during implementation:

- Do not start by dumping every architect rule into BPMN.
- Do not make markdown the source of truth.
- Do not equate schema validity with semantic correctness.
- Do not split into many services before the bounded contexts and event contracts are stable.
- Do not add controls without defining the evidence artifact and KPI hypothesis.
- Do not let emergency exceptions become the normal path.

## 13. Recommended first 90-day sequence

A practical first sequence for the pilot:

- Weeks 1-2: Phase 0 complete
- Weeks 3-5: Phase 1 complete
- Weeks 6-9: Phase 2 complete
- Weeks 10-13: Phase 3 complete
- Weeks 14-16: Phase 4 partial, enough for dashboard and exception basics

Phase 5 should only begin after the pilot already demonstrates value on the first two deliverables.

## 14. Source lineage for this plan

This plan synthesizes the current certificate-driven development design, the BPMN lifecycle design, the validation and KPI design, the DDD and business-process boundary guidance, the semi-formal reasoning paper, and the EY article on connecting coding agents to engineering standards and compliance context.
