# Development Lifecycle — Camunda Process Definition

> Companion to [Certificate-Driven Development](certificate-driven-development.md).
> This document defines the executable process model for implementation in
> Camunda (BPMN 2.0). Certificate templates are defined in the companion doc;
> this doc defines when, where, and how they are produced and evaluated.

---

## 1. Process Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ISSUE LIFECYCLE                                  │
│                                                                         │
│  Triage ──→ Design ──→ Plan ──→ Implement ──→ Review ──→ Integrate     │
│    │          │         │          │             │           │          │
│    ▼          ▼         ▼          ▼             ▼           ▼          │
│  Backlog   Design    Plan       Feature       PR on       Merged to    │
│  Board     Doc       Doc        Branch        Epic        Epic/Main    │
│            + DDCs    + Tasks    + Code        + TRC                    │
│                                + Tests       + DSCs                    │
│                                + Certs                                 │
└─────────────────────────────────────────────────────────────────────────┘

DDC = Design Decision Certificate
TRC = Task Review Certificate
DSC = Deferred Scope Certificate
```

---

## 2. Roles

| Role | Shorthand | Responsibilities |
|------|-----------|-----------------|
| **Architect** | A | Domain knowledge, contracts, spikes, design decisions, PR review |
| **Lead Engineer** | L | Execution, TDD, implementation, documentation |
| **Reviewer** | R | Certificate evaluation (may be A, L, or external) |

Both A and L may implement. Role labels on issues indicate primary ownership.

---

## 3. Process Phases

### Phase 1: Triage

**Trigger:** New issue created or identified from roadmap.

**Activities:**
1. Assign to milestone (MS1–MS5 or Decoupled Backlog)
2. Set labels: Type, Role, Priority
3. Verify dependency graph (blocked-by / blocks)
4. Set Sequence field on project board

**Gate → Phase 2:**
- Issue has milestone, labels, and dependencies documented
- Issue is not blocked by incomplete upstream work

**Artifacts:** GitHub issue with structured fields.

---

### Phase 2: Design (for Contract/Spike/Architecture issues)

**Trigger:** Issue moves to "In Progress" for Contract or Spike type.

**Subprocess: Brainstorming**
```
Explore Context ──→ Clarifying Questions ──→ Propose Approaches
      │                    │                       │
      ▼                    ▼                       ▼
  Read issue,         One question           2-3 options with
  codebase,           at a time,             trade-offs and
  reference repos     understand intent      recommendation
                                                   │
                                                   ▼
                                          Present Design ──→ Approval
                                                   │
                                                   ▼
                                          Design Decision Certificates
```

**Decision Framework:**
For each design choice, evaluate through these lenses (priority order):
1. **Quality is job 1** — prefer more work for a more professional result
2. **Clean, approachable, professional, comprehensible** — how it looks to adopters
3. **Inspect-sibling feel** — match Inspect AI patterns exactly
4. **Researcher delight** — least surprise, one pattern to learn
5. **Dog-food our own mechanisms** — built-in and third-party use same paths
6. **Explicit over magic** — ceremony that communicates intent over hidden behavior

**Gate → Phase 3:**
- Design document saved to `docs/plans/YYYY-MM-DD-issue-NNN-<topic>-design.md`
- Design Decision Certificates produced for each architectural choice
- User has approved the design

**Artifacts:**
- Design document (committed)
- Design Decision Certificates (in design doc or separate)

---

### Phase 3: Planning

**Trigger:** Design approved (or skip Phase 2 for Implementation issues).

**Activities:**
1. Write implementation plan with bite-sized tasks (2-5 min each)
2. Each task specifies: files, TDD steps (red/green), exact commands, commit message
3. Save to `docs/plans/YYYY-MM-DD-issue-NNN-<topic>-plan.md`

**Plan Document Structure:**
```
# [Feature] Implementation Plan

> For Claude: REQUIRED SUB-SKILL: Use executing-plans

Goal: [one sentence]
Architecture: [2-3 sentences]
Tech Stack: [key technologies]

### Task N: [Component Name]
Files: [create/modify/test paths]
Step 1: Write failing test [code]
Step 2: Run test, verify FAIL [command + expected output]
Step 3: Write minimal implementation [code]
Step 4: Run test, verify PASS [command + expected output]
Step 5: Commit [exact message]
```

**Gate → Phase 4:**
- Plan document committed
- All tasks have explicit TDD steps
- User has chosen execution approach (subagent-driven or parallel session)

**Artifacts:**
- Implementation plan (committed)

---

### Phase 4: Implementation

**Trigger:** Plan approved.

**Subprocess: Per-Task Cycle**
```
                    ┌──────────────────────────────┐
                    │     PER-TASK CYCLE            │
                    │                               │
                    │  Write Failing Test (RED)     │
                    │         │                     │
                    │         ▼                     │
                    │  Verify Test Fails            │
                    │  (show output)                │
                    │         │                     │
                    │         ▼                     │
                    │  Write Minimal Code (GREEN)   │
                    │         │                     │
                    │         ▼                     │
                    │  Verify Test Passes           │
                    │  (show output)                │
                    │         │                     │
                    │         ▼                     │
                    │  Refactor (stay green)        │
                    │         │                     │
                    │         ▼                     │
                    │  Commit (conventional msg)    │
                    │         │                     │
                    │         ▼                     │
                    │  Self-Review                  │
                    │  - Completeness               │
                    │  - Quality                    │
                    │  - Discipline (YAGNI)         │
                    │  - Test coverage              │
                    │         │                     │
                    │         ▼                     │
                    │  Next Task or Phase 4b        │
                    └──────────────────────────────┘
```

**TDD Iron Law:** No production code without a failing test first. If code was
written before the test, delete it and start over.

**Branching:**
- Feature branch from current epic: `feat/ms{N}-{description}`
- All commits signed
- Conventional commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`

**Gate → Phase 4b (Simplify):**
- All plan tasks completed
- All tests pass (fresh output)
- All commits on feature branch

---

### Phase 4b: Simplify

**Trigger:** All implementation tasks complete.

**Activities (three parallel review agents):**

| Agent | Focus | Looks For |
|-------|-------|-----------|
| Code Reuse | Existing utilities | Duplicated functionality, missed reuse |
| Code Quality | Hacky patterns | Redundant state, copy-paste, leaky abstractions |
| Efficiency | Unnecessary work | Hot-path bloat, double registration, N+1 |

**For every finding:**
1. Fix it directly, OR
2. Produce a Deferred Scope Certificate with tracking issue

**"Pre-existing" is not an excuse.** Fix it or track it.

**Gate → Phase 5:**
- All findings addressed (fixed or certified-deferred)
- Lint clean: `uv run ruff check`
- Type clean: `uv run mypy`
- Tests pass: `uv run pytest`
- All outputs shown fresh, not claimed from memory

---

### Phase 5: Certificate Review

**Trigger:** Simplify complete.

**This is a single integrated pass** — not a separate spec review + quality
review + certificate check. One pass, one certificate.

**Produce: Task Review Certificate**
```
TASK REVIEW CERTIFICATE

DEFINITIONS:
D1: Task is COMPLETE iff all spec requirements are satisfied
    AND code quality meets project standards.

PREMISES (from issue acceptance criteria):
P1: [requirement] → Evidence: [file:line] → [SATISFIED/MISSING]
...

CODE QUALITY ASSERTIONS:
Q1: TDD verified → Evidence: [commit SHAs: red, green]
Q2: No regressions → Evidence: [pytest output]
Q3: Follows codebase patterns → Evidence: [file:line comparison]
Q4: YAGNI → Evidence: [diff scope vs spec scope]
Q5: Exceeds reference (Inspect AI) where applicable → Evidence: [comparison]

VERIFICATION COMMANDS:
V1: uv run pytest → [N passed, M skipped, exit 0]
V2: uv run ruff check → [All checks passed]
V3: uv run mypy → [Success: no issues found]

FORMAL CONCLUSION:
By D1, since P1..PN are [SATISFIED] and Q1..QN are [VERIFIED],
task is [COMPLETE/NOT COMPLETE].

ISSUES: [none / list with severity]
```

**Produce: Design Decision Certificates** (if design choices were made)

**Produce: Deferred Scope Certificates** (if any work was deferred)

**Gate → Phase 6 (if COMPLETE):**
- Task Review Certificate: all premises SATISFIED
- All Design Decision Certificates: JUSTIFIED
- All Deferred Scope Certificates: VALID
- No Critical or Important issues unresolved

**Gate → Phase 4 (if NOT COMPLETE):**
- Certificate identifies specific issues
- Loop back to Implementation with explicit items

---

### Phase 6: Integration

**Trigger:** Certificate Review passes.

**Activities:**
1. Produce Impact Alignment Certificate (scan ALL open issues, roadmap, docs)
2. **Validate** Impact Alignment Certificate (see Certificate Validation below)
3. Push feature branch
4. Create PR targeting epic branch (not main)
5. PR body includes or links to all certificates (Task Review, Design Decision, Deferred Scope, Impact Alignment)
6. Request review

**PR Structure:**
```markdown
## Summary
- [2-3 bullets]

## Certificates
- Task Review Certificate: [link or inline]
- Design Decision Certificates: [link or inline]
- Deferred Scope Certificates: [link or inline, with issue refs]
- Impact Alignment Certificate: [link or inline]

## Test Plan
- [ ] [verification steps]

Closes #N
```

**Gate → Complete:**
- PR reviewed and approved by maintainer
- Maintainer squash-merges (their prerogative)
- Feature branch deleted
- Issue closed by maintainer

**Post-merge:**
- Execute post-merge actions from Impact Alignment Certificate (e.g., comment on roadmap issue)
- Update project board
- Update issue map in project memory
- Sync epic branch if needed

---

## 4. Certificate Validation

> Producing a certificate without validating it is the same as not having one.

Every certificate must pass through a validation step after production. This
is where hand-waving and lazy claims get caught. The validation step is NOT
optional — it is a gate in the process.

### The Validation Protocol

```
FOR EACH claim in the certificate:

1. IDENTIFY the evidence cited (file:line, issue #, command output)
2. GO TO the source — read the actual file, issue body, or output
3. VERIFY the claim matches what the source actually says
4. RECORD what you verified in a "Verified" column or annotation

If ANY claim fails verification:
  → Fix the certificate
  → Re-validate the fixed claim
  → Document what was wrong and how it was caught
```

### Why This Step Exists

During PR #113 (the first PR under this process), the Impact Alignment
Certificate was produced and committed without validation. When challenged,
re-reading the actual issue bodies revealed 3 errors:

| Original Claim | Actual Evidence | Error Type |
|----------------|-----------------|------------|
| #89 "partially unblocked, needs #104" | Issue body says blocked by #81 + #86. #81 is CLOSED. | **Wrong dependency** — didn't read the issue |
| #72 "RELATED — mirrors our entry-point pattern" | Issue is about Inspect *task* entry points, not embedder entry points | **Wrong scope** — assumed from title, didn't read body |
| All rows lacked verification evidence | No "Verified" column | **No audit trail** — claims were unverifiable |

These errors were caught ONLY because someone asked "did we validate?"
Without the validation step, incorrect claims ship as fact.

### Certificate Types and Their Validation Focus

| Certificate | Key Validation Focus |
|-------------|---------------------|
| Task Review | Re-run every verification command. Re-read every file:line cited. |
| Design Decision | Re-read the reference source code cited. Verify the comparison is accurate. |
| Deferred Scope | Open the tracking issue URL. Verify acceptance criteria match what's claimed. |
| Impact Alignment | **Read the body of every issue claimed as NONE/impacted.** Title-scanning is insufficient. |

### The Impact Alignment Trap

Impact Alignment Certificates are the most vulnerable to lazy production
because they involve scanning many issues. The temptation is to scan titles
and write "NONE" for everything that doesn't obviously match. This is
exactly the failure mode that semi-formal certificates are designed to prevent.

**Required evidence for "NONE" impact claims:**
- For issues in the same milestone: read the issue body
- For issues in adjacent milestones that touch the same subsystem: read the issue body
- For issues clearly in a different domain (titles confirm): title-level scan acceptable, noted as "Titles confirm scope"
- For issues where you're uncertain: read the issue body

**The "Verified" column is mandatory.** Every row must state what was examined.

### Competitive Multi-Model Review

Certificate validation is performed by **two independent LLM reviewers**
(different model families) who competitively produce and cross-validate
certificates. A third model serves as final arbiter.

**Roles:**

| Role | Model | Responsibility |
|------|-------|----------------|
| Reviewer A | OpenAI Codex | Independently produce certificate, then validate Reviewer B's |
| Reviewer B | Google Gemini | Independently produce certificate, then validate Reviewer A's |
| Arbiter | Claude Code | Final judge — verifies disputed claims from both reviewers |

**Process:**

```
┌──────────────────────────────────────────────────────────┐
│               COMPETITIVE REVIEW CYCLE                    │
│                                                           │
│  1. PRODUCE (parallel)                                    │
│     Reviewer A ──→ Certificate A                          │
│     Reviewer B ──→ Certificate B                          │
│                                                           │
│  2. CROSS-VALIDATE (parallel)                             │
│     Reviewer A reads Certificate B ──→ Dispute Report A   │
│     Reviewer B reads Certificate A ──→ Dispute Report B   │
│                                                           │
│  3. ARBITRATE (sequential)                                │
│     Arbiter (Claude Code):                                │
│       - For each dispute: verify against source           │
│       - Determine: Valid catch / False dispute             │
│       - Score both reviewers                              │
│                                                           │
│  4. MERGE                                                 │
│     Produce final certificate from best claims of both    │
│     with all disputes resolved                            │
└──────────────────────────────────────────────────────────┘
```

**Incentive Structure:**

| Event | Token Reward | Notes |
|-------|-------------|-------|
| Producing a certificate with zero disputes | +100 | Clean work |
| Catching a genuine error in other reviewer's certificate | +200 | Bug bounty |
| Catching a false "NONE" claim (lazy title-scanning) | +300 | Highest-value catch |
| Filing a false dispute (claim was actually correct) | **-600** | Triple penalty — discourages gaming |
| Missing an error that the other reviewer caught | -100 | Incentivizes thoroughness |

The **triple penalty** for false disputes is critical. Without it, reviewers
are incentivized to dispute everything hoping to score bounties. The penalty
must exceed the reward by enough to make frivolous disputes costly.

**Leaderboard:**

Maintained as a persistent artifact in `docs/process/reviewer-leaderboard.md`:

```markdown
# Certificate Review Leaderboard

| Reviewer | Certificates | Clean (0 disputes) | Bugs Caught | False Disputes | Score |
|----------|-------------|---------------------|-------------|----------------|-------|
| Codex    | 5           | 3                   | 4           | 1              | +1100 |
| Gemini   | 5           | 2                   | 2           | 0              | +600  |

## Dispute Log

| PR | Dispute | Filed By | Ruling | Detail |
|----|---------|----------|--------|--------|
| #113 | #89 dependency claim | Gemini | VALID catch | Codex said "needs #104", issue says #81 |
| #113 | Q3 pattern claim | Codex | FALSE dispute (-600) | Gemini's claim was correct per file:line |
```

**Arbiter Protocol:**

When Claude Code arbitrates a dispute:

1. Read the disputed claim from both certificates
2. Go to the cited source (file, issue, command output)
3. Determine which reviewer's claim matches the source
4. If ambiguous: flag as INCONCLUSIVE (no reward, no penalty for either)
5. Record ruling with evidence in the dispute log

**When to use competitive review vs. single review:**

| Scenario | Review Mode |
|----------|------------|
| Feature PR (new code) | Competitive — both models review |
| Documentation-only PR | Single reviewer sufficient |
| Hotfix (< 20 lines changed) | Single reviewer sufficient |
| Epic-level PR (large scope) | Competitive — mandatory |
| Any PR touching process docs | Competitive — mandatory |

### Remediation Protocol — Chain of Custody

When a certificate identifies deficiencies, those deficiencies must be
tracked through a structured remediation cycle with **separation of duty**.
The model that filed the deficiency is the only authority that can accept
the remediation. The implementer cannot mark their own fix as accepted.

**Roles in remediation:**

| Role | Who | Responsibility |
|------|-----|----------------|
| **Implementer** | Claude Code | Writes code, produces initial certificates, provides remediation evidence |
| **Finder** | Codex or Gemini (whoever filed) | Owns the deficiency. Must accept or reject remediation evidence. |
| **Validator** | The other reviewer (not the finder) | Cross-validates the deficiency claim. Confirms or disputes. |
| **Arbiter** | Claude Code (wearing arbiter hat) | Breaks ties between Finder and Validator. Cannot arbitrate own implementation. |
| **Human** | Project maintainer | Final escalation when all models deadlock. |

**Deficiency lifecycle:**

```
1. FILED
   Finder identifies deficiency in certificate.
   Validator cross-checks.
       │
       ├── Validator CONFIRMS → deficiency ACCEPTED
       │   Finder owns acceptance authority.
       │
       └── Validator DISPUTES → goes to Arbiter
           │
           ├── Arbiter UPHOLDS → deficiency ACCEPTED
           │   Finder owns acceptance authority.
           │
           └── Arbiter OVERTURNS → Finder gets ONE rebuttal
               │
               ├── Rebuttal CONVINCES (Validator + Arbiter agree) →
               │   deficiency WITHDRAWN, no penalty
               │
               └── Rebuttal FAILS →
                   Finder must WITHDRAW claim.
                   False dispute penalty applied (-600).

2. ACCEPTED
   Implementer provides remediation evidence.
   Evidence must include:
     - What was done (commit SHA, file:line diff)
     - Proof it resolves the issue (test output, re-read of source)
       │
       ├── Finder ACCEPTS evidence → deficiency REMEDIATED
       │
       └── Finder REJECTS evidence (with reason) →
           Implementer must provide new evidence.
           If Implementer believes rejection is unfair → Arbiter rules.
           If Arbiter + Implementer + Finder deadlock → ESCALATE TO HUMAN.

3. REMEDIATED
   Deficiency is closed. Certificate status updated.
   When all deficiencies reach REMEDIATED → certificate is CLEAN.

4. ESCALATED
   Human arbitrates. Human's decision is final.
   Recorded in remediation log with human's reasoning.
```

**Remediation Log structure** (appended to the certificate that found issues):

```
REMEDIATION LOG

Certificate Status: [DEFICIENT (N open) / CLEAN (all remediated)]

R1: [Claim ID from certificate]
  Filed by: [Codex/Gemini]
  Cross-validated by: [Gemini/Codex] — [CONFIRMED/DISPUTED]
  Arbiter ruling: [N/A / UPHELD / OVERTURNED]
  Deficiency: [description of what was wrong]
  Status: [ACCEPTED / REMEDIATED / WITHDRAWN / ESCALATED]

  Remediation evidence (if ACCEPTED → REMEDIATED):
    Action: [commit SHA] [file:line description]
    Proof: [test output / re-read evidence]
    Accepted by: [Finder model name] on [date]

  Rebuttal (if OVERTURNED → rebuttal attempted):
    Finder's argument: [text]
    Ruling: [CONVINCES / FAILS]
    Penalty applied: [YES -600 / NO]

R2: ...
```

**The certificate cannot reach CLEAN status until:**
- Every ACCEPTED deficiency has REMEDIATED status
- Every remediation has been accepted by the original Finder
- The Remediation Log is committed with all evidence

**Tamper-proof log requirement:**

The Remediation Log is an **append-only, signed ledger**. No entry can be
modified or deleted after it is written. This prevents a model from
rewriting history, forging another model's acceptance, or silently
removing a deficiency.

Properties (detailed design in #114):

1. **Append-only:** New entries are appended. Prior entries are immutable.
   No edits, no deletions, no reordering. Like a write-ahead log or a
   blockchain — forward-only.

2. **Signed entries:** Each log entry is signed by the model that authored
   it. A Finder's acceptance entry must be signed by the Finder. An
   Implementer's evidence entry must be signed by the Implementer.
   Signatures must be verifiable by any party.

3. **Hash-chained:** Each entry includes a hash of the previous entry,
   forming a tamper-evident chain. Inserting, removing, or modifying an
   entry breaks the chain. Any participant can verify integrity by
   replaying the hash chain.

4. **Entry structure:**
   ```
   ENTRY {
     sequence: int              # Monotonically increasing
     timestamp: ISO-8601
     author: enum               # "codex" | "gemini" | "claude" | "human"
     action: enum               # "file" | "confirm" | "dispute" | "evidence"
                                # | "accept" | "reject" | "arbitrate"
                                # | "rebuttal" | "withdraw" | "escalate"
     deficiency_id: string
     content: string            # The claim, evidence, or ruling
     prev_hash: string          # SHA-256 of previous entry
     signature: string          # Model-specific signature of this entry
   }
   ```

5. **Verification:** Before accepting any log entry, the receiving party
   MUST verify: (a) the `prev_hash` chains correctly, (b) the `signature`
   matches the claimed `author`, (c) the `author` has authority for the
   `action` (e.g., only Finder can `accept`).

6. **Storage:** The log is committed to git as part of the certificate
   file. Git's own SHA integrity provides a secondary tamper-evidence
   layer, but the hash chain is the primary mechanism (survives
   cherry-picks, rebases, and non-git transports).

The exact signing mechanism (API-key-derived HMAC, asymmetric keys per
model, or Camunda-managed tokens) is a design decision for the #114
implementation. The requirement here is the **property**: no model can
forge another model's entries or alter the history.

**Anti-patterns:**

| Pattern | Problem | Fix |
|---------|---------|-----|
| Implementer marks own deficiency as remediated | No separation of duty | Finder must accept; signature enforced |
| "Fixed in commit X" with no proof | Claim without evidence | Must include test output or re-verification |
| Finder rubber-stamps all remediations | Lazy acceptance | Arbiter spot-checks acceptance quality |
| Model rewrites prior log entry | History tampering | Hash chain breaks; detected on verification |
| Model forges another model's signature | Identity spoofing | Signature verification rejects entry |
| Endless dispute loop | Process deadlock | Max one rebuttal, then human escalation |
| Deficiency left in ACCEPTED forever | Forgotten work | Timer event: 24hr warning, 48hr escalation |

---

## 5. Certificate Production Rules

### When Each Certificate is Required

| Trigger | Certificate | Who Produces | Where Stored |
|---------|------------|--------------|--------------|
| Implementation complete | Task Review | Implementer | PR body or `docs/plans/` |
| Architectural choice made | Design Decision | Architect | Design doc in `docs/plans/` |
| Work deferred | Deferred Scope | Anyone | PR body or `docs/plans/`, with issue link |
| PR ready to submit | Impact Alignment | Implementer | PR body or `docs/plans/` |
| PR submitted | All applicable (validated) | Implementer | PR body |

### Certificate Evaluation Criteria

**Task Review Certificate passes when:**
- Every premise from the issue acceptance criteria maps to a SATISFIED entry
- Every quality assertion has fresh command output as evidence
- No Critical or Important issues remain open

**Design Decision Certificate passes when:**
- MATCHES or EXCEEDS reference implementation, with file:line evidence
- If DIVERGES: documented justification that ours is demonstrably better

**Deferred Scope Certificate passes when:**
- Tracking issue exists with clear acceptance criteria
- Issue is positioned in the correct milestone with correct dependencies
- Current deliverable is internally consistent without the deferred work

**Impact Alignment Certificate passes when:**
- Every open issue has been assessed (not just title-scanned — see Section 4)
- Every "NONE" claim for same-milestone issues has issue-body-level evidence
- Every "Verified" column entry states what was actually examined
- All impacted documentation has been updated (not just noted for later)
- Post-merge actions are explicitly listed
- All new issues created by the PR are linked

**ALL certificates pass validation (Section 4) when:**
- Every claim has been independently verified against its cited source
- A "Verified" annotation exists for each claim
- Any corrections from validation are committed (not silently fixed)

---

## 6. Quality Bar

### Reference Hierarchy

When evaluating design decisions, compare against (in order):

1. **Inspect AI** (`inspect_ai/` in `.venv/`) — primary reference
   - Entry point patterns: `inspect_ai/_util/registry.py`
   - Model API decoration: `inspect_ai/model/_registry.py`
   - Resolution/lookup: `inspect_ai/model/_model.py`

2. **MTEB** — embedding benchmark standard
   - Model loading patterns
   - Evaluation pipeline structure

3. **Python standard library** — language-level patterns
   - `importlib.metadata` for entry points
   - `typing.Protocol` for structural typing
   - `abc.ABC` for abstract base classes

### The Standard

> "What's the BEST we can do?" — not "What does the reference do?"

The reference establishes a floor. We aim for the ceiling. If Inspect AI does
zero validation at decoration time, we validate method existence AND signature.
If MTEB has no per-sample drill-down, we provide it via Inspect's EvalLog.

Never use "the reference does less" as justification for doing less ourselves.

---

## 7. Subprocess: Handling Review Feedback

When a PR receives review feedback:

1. **Read the feedback** — understand the reviewer's concern
2. **Verify against codebase** (5-point checklist):
   - Technically correct for THIS codebase?
   - Breaks existing functionality?
   - Reason for current implementation?
   - Works on all platforms/versions?
   - Does reviewer understand full context?
3. **If feedback is correct:** Fix it, reply inline with what was done
4. **If feedback is questionable:** Push back with technical evidence
5. **Never:** Performatively agree, mark conversations resolved, force-push after review

---

## 8. Subprocess: Handling Quality Debt

When a finding identifies existing (pre-existing) issues:

```
Is the issue in code we're touching?
├── YES → Fix it now. No excuses.
└── NO → Is it in adjacent code that affects our work?
    ├── YES → Fix it now.
    └── NO → Create a tracked issue (Decoupled Backlog).
              Produce Deferred Scope Certificate.
              Never say "pre-existing, not our problem."
```

---

## 9. Artifact Locations

| Artifact | Location | Convention |
|----------|----------|------------|
| Design documents | `docs/plans/YYYY-MM-DD-issue-NNN-<topic>-design.md` | Committed, not gitignored |
| Implementation plans | `docs/plans/YYYY-MM-DD-issue-NNN-<topic>-plan.md` | Committed |
| Review certificates | `docs/plans/YYYY-MM-DD-issue-NNN-review-certificates.md` | Committed |
| Process definitions | `docs/process/` | This directory |
| Contracts | `docs/contracts/` | Interface specs |
| Guides | `docs/guides/` | Implementer/researcher docs |
| Spike results | `docs/decisions/` | Decision records from spikes |
| Reviewer leaderboard | `docs/process/reviewer-leaderboard.md` | Persistent, updated after each competitive review |

---

## 10. Camunda BPMN Element Mapping

For implementation in Camunda 8:

| Process Element | BPMN Type | ID Convention |
|----------------|-----------|---------------|
| Triage | User Task | `triage_{issue_id}` |
| Design | Subprocess (embedded) | `design_{issue_id}` |
| Planning | User Task | `planning_{issue_id}` |
| Per-Task Cycle | Multi-instance subprocess | `task_cycle_{issue_id}` |
| TDD Red/Green | Script Task (within cycle) | `tdd_{task_n}` |
| Simplify | Parallel gateway → 3 service tasks | `simplify_{issue_id}` |
| Certificate Production | Parallel gateway → 2 reviewer tasks | `cert_produce_{issue_id}` |
| Cross-Validation | Parallel gateway → 2 validation tasks | `cert_crossval_{issue_id}` |
| Arbitration | Service Task (Claude Code) | `cert_arbitrate_{issue_id}` |
| Certificate Merge | Script Task | `cert_merge_{issue_id}` |
| Remediation Evidence | User Task (Implementer) | `remediation_{issue_id}_{deficiency_id}` |
| Finder Acceptance | User Task (Finder model) | `acceptance_{issue_id}_{deficiency_id}` |
| Human Escalation | User Task (Maintainer) | `escalation_{issue_id}_{deficiency_id}` |
| Integration | Service Task (gh CLI) | `integration_{issue_id}` |

### Process Variables

```yaml
variables:
  issue_id: string          # GitHub issue number
  issue_type: enum          # Contract, Implementation, Spike, Learning, Parity-Test
  milestone: string         # MS1..MS5, Decoupled
  assignee_role: enum       # Architect, Lead-Engineer
  epic_branch: string       # e.g., "inspect_integration"
  feature_branch: string    # e.g., "feat/ms4-embedder-extension-api"
  plan_tasks: list[object]  # Extracted from plan doc
  current_task_index: int   # Progress through plan
  certificates: list[object] # Produced certificates
  review_findings: list[object]  # From simplify agents
  pr_url: string            # Created PR URL
  test_output: string       # Fresh pytest output
  lint_output: string       # Fresh ruff output
  type_output: string       # Fresh mypy output

  # Competitive review variables
  review_mode: enum         # "competitive" or "single"
  certificate_a: object     # Reviewer A (Codex) certificate
  certificate_b: object     # Reviewer B (Gemini) certificate
  disputes_a: list[object]  # Disputes filed by Reviewer A against B
  disputes_b: list[object]  # Disputes filed by Reviewer B against A
  arbitration_rulings: list[object]  # Arbiter (Claude Code) rulings
  leaderboard: object       # Running scores for both reviewers

  # Remediation tracking variables
  deficiencies: list[object]           # All accepted deficiencies
  remediation_evidence: list[object]   # Evidence submitted by implementer
  finder_acceptances: list[object]     # Finder accept/reject decisions
  certificate_status: enum             # "deficient" or "clean"
  escalations: list[object]            # Deficiencies escalated to human
```

### Message Events

| Event | Direction | Payload |
|-------|-----------|---------|
| `issue.assigned` | Start | `{issue_id, assignee, milestone}` |
| `design.approved` | Intermediate Catch | `{design_doc_path}` |
| `plan.approved` | Intermediate Catch | `{plan_doc_path, execution_mode}` |
| `task.completed` | Intermediate Throw | `{task_index, commit_sha, test_output}` |
| `review.certified` | Intermediate Catch | `{certificate_path}` |
| `review.issues_found` | Intermediate Throw | `{issues: list}` |
| `cert.produced_a` | Intermediate Throw | `{certificate_a, reviewer: "codex"}` |
| `cert.produced_b` | Intermediate Throw | `{certificate_b, reviewer: "gemini"}` |
| `cert.disputes_filed` | Intermediate Throw | `{disputes_a, disputes_b}` |
| `cert.arbitrated` | Intermediate Throw | `{rulings, leaderboard_update}` |
| `cert.merged` | Intermediate Throw | `{final_certificate}` |
| `deficiency.accepted` | Intermediate Throw | `{deficiency_id, finder, description}` |
| `remediation.submitted` | Intermediate Throw | `{deficiency_id, commit_sha, evidence}` |
| `remediation.accepted` | Intermediate Throw | `{deficiency_id, finder, accepted: bool}` |
| `remediation.escalated` | Intermediate Throw | `{deficiency_id, reason}` |
| `certificate.clean` | Intermediate Throw | `{certificate_id, all_deficiencies_remediated}` |
| `pr.created` | Intermediate Throw | `{pr_url, pr_number}` |
| `pr.merged` | End | `{merge_sha}` |

### Timer Events

| Timer | Attached To | Duration | Action |
|-------|------------|----------|--------|
| Stale task warning | Per-Task Cycle | 4 hours | Notify assignee |
| Stale PR warning | Integration | 48 hours | Notify reviewer |
| Review timeout | Certificate Production | 30 minutes | Escalate to arbiter |
| Remediation stale | Remediation Evidence | 24 hours | Warn implementer |
| Remediation expired | Remediation Evidence | 48 hours | Escalate to human |

---

## 11. Example: Full Lifecycle for Issue #86

For reference, here is how the lifecycle played out for the Embedder Extension
API (issue #86), which was the first issue developed under this process:

1. **Triage:** Issue #86 assigned to MS4, labels `Type: Contract`, `Role: Architect`
2. **Design:** Brainstormed 3 approaches (unified registry, parallel path, adapter).
   Produced Design Decision Certificates for: unified registry, explicit-name
   decorator, entry points + programmatic. Design doc committed.
3. **Planning:** 10-task plan with TDD steps. Plan doc committed.
4. **Implementation:** Subagent-driven development. Each task followed red/green
   cycle. 18 commits on feature branch.
5. **Simplify:** Three parallel review agents (reuse, quality, efficiency).
   Fixed: `__init__.py` bloat, `Any` types, hf.py pre-existing lint.
   Strengthened: `_validate_class` signature checking.
   Deferred: Factory convergence → tracked by #112 with Deferred Scope Certificate.
6. **Certificate Review:** Task Review Certificate with all premises SATISFIED.
   Design Decision Certificate: EXCEEDS Inspect AI pattern.
   Deferred Scope Certificate for #112: VALID.
7. **Impact Alignment:** Produced certificate scanning 35 open issues.
   Initial production had 3 errors (wrong dependency for #89, wrong scope for
   #72, missing verification column). Caught by validation step — re-reading
   actual issue bodies. Corrected and re-committed. This failure became the
   basis for Section 4 (Certificate Validation) of this document.
8. **Integration:** PR #113 targeting `inspect_integration`. All certificates
   in `docs/plans/2026-03-08-issue-086-review-certificates.md`.
