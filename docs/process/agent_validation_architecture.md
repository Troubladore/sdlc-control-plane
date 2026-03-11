# Agent Workflow Validation Architecture and KPI Plan

This document turns the Certificate-Driven Development and Development Lifecycle BPMN specs into an implementation-oriented validation architecture, with KPIs that can be measured phase by phase.

## Design Goal

Optimize for three things in this order:

1. **Truthfulness of workflow claims** - agents should not be able to claim completion without evidence.
2. **Auditability** - every certificate claim, dispute, remediation step, and transition should be reconstructable from source artifacts.
3. **Measured value** - every added guardrail should be evaluated for whether it improves correctness, yield, or economics rather than becoming process theater.

## Canonical Artifact Strategy

Authoritative records are machine-readable JSON. Human-readable markdown is rendered from those JSON objects.

Canonical artifact types:
- Task Review Certificate
- Design Decision Certificate
- Deferred Scope Certificate
- Impact Alignment Certificate
- Dispute Object
- Transition Request
- Remediation Log
- Workflow Event

## Validation Pipeline

### Stage 0. Evidence inventory build (deterministic)

Before any certificate is produced:
- collect file spans
- collect issue bodies and titles
- collect command outputs
- collect git commits and diffs
- assign stable artifact IDs and evidence IDs

Output:
- evidence inventory
- artifact inventory

Why:
- constrained decoding can then force agents to reference only valid evidence IDs
- validation later becomes deterministic and replayable

### Stage 1. Constrained artifact generation (LLM)

The agent explores and reasons semi-formally, but when it emits an authoritative artifact it must produce canonical JSON conforming to the schema bundle.

Rules:
- no free-form authoritative markdown
- no raw file:line strings unless they resolve to inventory-backed evidence refs
- enums only from schema-controlled vocabularies
- every claim must cite evidence refs

### Stage 2. Structural validation (deterministic)

Validate against JSON Schema:
- required fields present
- enums valid
- no unknown properties in strict objects
- correct field types and cardinality

If this fails:
- reject artifact
- emit workflow event with `status=fail`
- do not advance state

### Stage 3. Referential validation (deterministic)

Check that:
- all artifact IDs exist
- all evidence refs exist in the evidence inventory
- all issue refs resolve
- all command refs resolve to recorded command outputs
- all certificate IDs are unique
- all claim IDs are unique within a certificate

If this fails:
- reject artifact
- record missing or broken references as findings

### Stage 4. Claim verification (deterministic + supervised LLM)

For each claim in the certificate:
1. identify cited evidence
2. read or re-run the underlying source
3. verify the claim against the source
4. write a `verification` record

Required by certificate type:
- **Task Review**: re-run every verification command; re-read every file span
- **Design Decision**: re-read reference code and our code; verify comparison accuracy
- **Deferred Scope**: open the tracking issue; verify acceptance criteria and dependency placement
- **Impact Alignment**: for same-milestone issues, read the body; title-only scans are only allowed when clearly cross-domain and must be explicitly marked as such

No certificate can become `validated` without a verification record per claim.

### Stage 5. Certificate-specific rule evaluation (deterministic)

Apply business rules from the process specs.

#### Task Review pass rules
- every premise status is `satisfied`
- every quality assertion status is `verified`
- all required verification commands passed with fresh output
- no `critical` or `important` issues remain open

#### Design Decision pass rules
- comparison result is `matches` or `exceeds`
- if `diverges`, a divergence reason with evidence is mandatory
- final status must be `justified`

#### Deferred Scope pass rules
- tracking issue exists
- acceptance criteria not empty
- roadmap position valid
- current deliverable consistency supported
- final status must be `valid`

#### Impact Alignment pass rules
- every potentially affected open issue has an assessment
- same-milestone `none` claims require body-level verification
- every row has verification evidence
- impacted docs are updated or tracked explicitly
- post-merge actions enumerated
- final status must be `aligned`

### Stage 6. Competitive review and dispute handling (multi-model + deterministic arbiter checks)

Mode selection:
- competitive review for feature PRs, epic-level PRs, and process docs
- single reviewer for documentation-only or tiny hotfixes

Flow:
1. Reviewer A produces artifact
2. Reviewer B produces artifact
3. each reviews the other and emits Dispute Objects
4. arbiter verifies each dispute against sources
5. a merged final artifact is produced

Validation rules for disputes:
- dispute must target a real certificate and claim ID
- dispute must cite source refs
- validator and arbiter decisions are logged
- scoring and penalties are recorded as workflow events, not just prose

### Stage 7. Remediation ledger verification (deterministic)

When deficiencies exist:
- log entries are append-only
- sequence must increase monotonically
- `prev_hash` must match previous entry
- signature must verify against claimed author
- author must have authority for the action
- only original Finder can accept remediation

No certificate can become `clean` until:
- every accepted deficiency is remediated
- every remediation has Finder acceptance
- log chain verifies end-to-end

### Stage 8. Transition gatekeeping (deterministic)

Agents do not advance workflow state directly.
They submit a Transition Request.
The engine checks:
- required artifacts exist
- required gates passed
- verifier artifacts exist
- no blocking deficiencies remain

Then and only then can state change.

### Stage 9. Event emission and KPI computation (deterministic)

Every meaningful step emits a Workflow Event with:
- run_id
- orchestration_version
- workflow step/state
- executor type
- costs
- artifacts
- status
- timing

This is the measurement substrate.

## KPI Model

### Unit of work

Use three levels simultaneously:

1. **Run-level** - one end-to-end workflow run
2. **Issue-level** - one issue/task completed
3. **PR-level** - one PR merged

For economics, the north-star unit should be:
- **per issue/task completed** for implementation work
- **per PR merged** for integration outcomes

### Core KPIs

#### Economics
- CostPerSuccess
- CostPerAttempt
- CostOfFailures
- LLM Spend %
- Compute Spend %
- Human Spend %
- CostPerKLOC or complexity-normalized cost

#### Yield and reliability
- FirstPassYield (FPY)
- Avg retries per step
- Gate failure distribution
- p95 cycle time

#### Human burden
- HumanMinutesPerSuccess
- HumanTouchpointsPerSuccess
- Override / exception rate

#### Quality
- Post-merge defect rate
- Security / compliance findings
- Review churn

#### Determinism leverage
- Deterministic step coverage
- Deterministic verified cost / total cost
- Token avoidance rate
- MaintenanceCostPerSuccess

## New domain-specific KPIs for certificate-driven workflows

These are the most important additions to tell rigor from theater.

### Certificate quality KPIs
- **SchemaPassRate** = valid certificate JSON / certificates submitted
- **EvidenceBackedClaimRate** = claims with >=1 evidence ref / total claims
- **VerifiedClaimCoverage** = claims with verification record / total claims
- **BrokenReferenceRate** = invalid evidence refs / total evidence refs
- **MandatoryFieldMissRate** = missing required fields / certificates submitted

### Validation effectiveness KPIs
- **ValidationCatchRate** = claims changed or rejected during validation / total claims
- **FalseConfidenceEscapeRate** = post-merge defects attributable to claims that validation marked verified / successful outcomes
- **SameMilestoneIssueBodyReadRate** = same-milestone impact rows with body-level verification / same-milestone impact rows
- **TitleOnlyNoneRate** = impact rows marked none using title-only verification / total impact rows

### Competitive review KPIs
- **ValidDisputesPerCertificate**
- **FalseDisputeRate** = false disputes / total disputes
- **ArbiterOverturnRate**
- **MergedCertificateDelta** = claims in final artifact that came from only one reviewer / total final claims

### Remediation KPIs
- **MedianTimeToRemediateDeficiency**
- **OpenDeficiencyAgingP95**
- **AuthorityViolationBlocks** = blocked invalid accept/reject attempts
- **HashChainFailureRate**
- **EscalationRateToHuman**

### Transition integrity KPIs
- **ArtifactBackedTransitionRate** = approved transitions with all required verifier artifacts / approved transitions
- **InvalidTransitionRejectionRate**
- **WaiverRate**

## Phase-by-phase rollout and expected signals

### Phase 1 - Canonical certificate JSON + schema validation

Implement:
- schema bundle
- constrained certificate emission
- markdown rendering from canonical JSON

Measure:
- SchemaPassRate
- MandatoryFieldMissRate
- EvidenceBackedClaimRate
- Gate failure distribution at certificate submission

What should move:
- structural errors should drop sharply
- markdown inconsistency should disappear

What should *not* be claimed yet:
- improved semantic correctness; this phase mainly removes malformed artifacts

### Phase 2 - Evidence inventory + transition gating

Implement:
- stable artifact/evidence IDs
- transition requests
- verifier-artifact requirement for state changes
- workflow events

Measure:
- ArtifactBackedTransitionRate
- BrokenReferenceRate
- InvalidTransitionRejectionRate
- DeterministicStepCoverage
- FirstPassYield by gate

Expected pattern:
- short-term FPY may fall because invalid transitions are now blocked
- long-term manual cleanup should drop

### Phase 3 - Claim-by-claim validation + Verified annotations

Implement:
- claim verification records
- certificate-specific validation rules
- mandatory verification for all claims

Measure:
- VerifiedClaimCoverage
- ValidationCatchRate
- SameMilestoneIssueBodyReadRate
- TitleOnlyNoneRate
- HumanMinutesPerSuccess

Expected pattern:
- validation catches rise first
- later post-merge defects and review churn should fall

### Phase 4 - Competitive review + dispute engine

Implement:
- dual reviewer mode
- dispute objects
- arbiter resolution
- reviewer scoring

Measure:
- ValidDisputesPerCertificate
- FalseDisputeRate
- ArbiterOverturnRate
- ReviewChurn
- PostMergeDefectRate
- HumanTouchpointsPerSuccess

Expected pattern:
- may increase cost and cycle time at first
- keep only if valid catches materially reduce escaped defects or human review load

### Phase 5 - Remediation ledger + chain of custody

Implement:
- append-only remediation log
- signature verification
- hash-chain verification
- separation-of-duty enforcement
- stale deficiency timers

Measure:
- MedianTimeToRemediateDeficiency
- OpenDeficiencyAgingP95
- AuthorityViolationBlocks
- HashChainFailureRate
- EscalationRateToHuman

Expected pattern:
- auditability improves immediately
- engineering economics improve only if remediation loops become clearer and shorter

### Phase 6 - Version comparison and optimization

Implement:
- benchmark corpus replay
- online stratified comparisons where safe
- dashboarding

Measure:
- CostPerSuccess
- FPY
- HumanMinutesPerSuccess
- p95 CycleTime
- PostMergeDefectRate
- DeterministicStepCoverage
- MaintenanceCostPerSuccess

Decision rule:
- keep a phase only if it improves quality or reduces human burden enough to justify added compute/maintenance

## Anti-theater decision framework

A control is **valuable** if it does one or more of these:
- blocks invalid state transitions deterministically
- increases verified claim coverage
- catches semantic errors before merge
- reduces post-merge defects
- reduces human review effort
- makes audit reconstruction materially easier

A control is probably **theater** if it:
- only increases documentation volume
- does not change transition behavior
- does not emit measurable verifier artifacts
- increases cost and human burden without improving catch rates or escaped-defect rates

## Minimal dashboard

Build these first:
- Cost waterfall per success
- Failure distribution by gate
- VerifiedClaimCoverage over time
- ValidationCatchRate by certificate type
- FalseDisputeRate vs ValidDisputesPerCertificate
- MedianTimeToRemediateDeficiency
- CostPerSuccess by orchestration_version
- PostMergeDefectRate by orchestration_version

## Recommended implementation order

1. Ship canonical JSON schemas and schema validation first.
2. Add evidence inventory + transition gating second.
3. Add claim verification and verified annotations third.
4. Add competitive review only where stakes justify it.
5. Add remediation ledger before broad rollout if auditability is a hard requirement.
6. Compare orchestration versions using benchmark replay and stratified production comparisons.
