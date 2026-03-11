# Certificate-Driven Development

> "This team raises the bar in everything they do."

This document defines the development process for grounding-measure-core.
Every claim of completion, every deferred scope, and every design decision
must be backed by a verifiable certificate. No hand-waving. No "looks good."

**Reference:** Ugare & Chandra (2026) "Agentic Code Reasoning" — semi-formal
reasoning improves code analysis accuracy by 10+ percentage points by
requiring explicit premises, evidence traces, and formal conclusions.

---

## Core Principle

**Every assertion must have verifiable evidence.**

This applies to:
- "Tests pass" — show the output
- "This is out of scope" — show the tracking issue
- "This design decision is correct" — show the reference evidence
- "The implementation matches the spec" — trace each requirement to code

---

## State Machine

```
[Pending] ──→ [Implementing] ──→ [Self-Review] ──→ [Certificate Review]
                                                         │
                                               ┌─────────┤
                                               │         │
                                          [Issues]  [Certified]
                                               │         │
                                               ▼         ▼
                                        [Implementing] [Complete]
```

### Gate: Implementing → Self-Review
- Code committed on feature branch
- Tests written (TDD: red/green verified)
- Tests pass (fresh output)

### Gate: Self-Review → Certificate Review
- Implementer has reviewed own work for completeness, quality, discipline

### Gate: Certificate Review → Certified
- Task Review Certificate produced (see template below)
- All premises SATISFIED
- All quality assertions VERIFIED
- No Critical or Important issues open

### Gate: Certificate Review → Issues
- Certificate identifies gaps
- Loops back to Implementing with specific items

---

## Certificate Templates

### 1. Task Review Certificate

Produced after implementation, covering both spec compliance and code quality
in a single pass. This is the review — not an add-on to a separate review.

```
TASK REVIEW CERTIFICATE

DEFINITIONS:
D1: Task is COMPLETE iff all spec requirements are satisfied
    AND code quality meets project standards.

PREMISES (from task spec):
P1: [requirement] → Evidence: [file:line] → [SATISFIED/MISSING]
P2: [requirement] → Evidence: [file:line] → [SATISFIED/MISSING]
...

CODE QUALITY ASSERTIONS:
Q1: Tests follow TDD (red/green verified) → Evidence: [commit SHAs showing red then green]
Q2: No regressions → Evidence: [test command output]
Q3: Follows existing patterns → Evidence: [file:line comparison with codebase]
Q4: No overbuilding (YAGNI) → Evidence: [files changed vs spec scope]

VERIFICATION COMMANDS RUN:
V1: [test command] → [output summary, exit code]
V2: [lint command] → [output summary, exit code]
V3: [type check command] → [output summary, exit code]

FORMAL CONCLUSION:
By D1, since P1..PN are [SATISFIED] and Q1..QN are [VERIFIED],
task is [COMPLETE/NOT COMPLETE].

ISSUES (if any):
I1: [description] at [file:line] — Severity: [Critical/Important/Minor]
```

### 2. Design Decision Certificate

Produced when making an architectural or design choice. The standard is
not "does it work?" but "is this world-class?"

```
DESIGN DECISION CERTIFICATE

DEFINITION:
D1: A design decision is JUSTIFIED iff it matches or exceeds the
    pattern used by the reference implementation (Inspect AI) OR has
    documented evidence for why divergence is superior.

PREMISES:
P1: Our pattern is [description with file:line evidence]
P2: Reference pattern is [description with file:line evidence from reference repo]
P3: [If diverging] Reason for divergence: [evidence why ours is better]

EVALUATION:
- Match: [MATCHES / EXCEEDS / DIVERGES]
- If DIVERGES without justification: MUST REVISE

CONCLUSION:
By D1, this decision is [JUSTIFIED / NEEDS REVISION].
```

**Reference repos (in priority order):**
1. [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) — our primary sibling framework
2. [MTEB](https://github.com/embeddings-benchmark/mteb) — embedding evaluation standard
3. Python standard library patterns

**The bar:** We match or exceed. Never slouch to a lower standard because
"others do it that way." If the reference does zero validation, we do more.

### 3. Deferred Scope Certificate

Produced when work is intentionally deferred. "Out of scope" is not an
excuse — it's a claim that requires proof.

```
DEFERRED SCOPE CERTIFICATE

DEFINITION:
D1: Work is validly DEFERRED iff it is tracked by an open issue
    with clear acceptance criteria, positioned correctly in the
    roadmap dependency graph, and does not leave the current
    deliverable in an inconsistent state.

PREMISES:
P1: The deferred work is [description]
P2: Tracked by issue [#N] with title [title]
P3: Issue acceptance criteria: [list]
P4: Roadmap position: [milestone, blocked-by, blocks]
P5: Current deliverable consistency: [evidence]

EVALUATION:
- Tracked: [YES with issue link / NO — must create]
- Acceptance criteria clear: [YES/NO]
- Roadmap position valid: [YES/NO]
- Current state consistent: [YES/NO with evidence]

CONCLUSION:
By D1, this deferral is [VALID / INVALID — must address now or create issue].
```

### 4. Impact Alignment Certificate

Produced before a PR is submitted. Ensures the change does not silently
invalidate, contradict, or drift from existing issues, roadmap, or
documentation. Every open issue and core document is inspected for impact.

```
IMPACT ALIGNMENT CERTIFICATE

DEFINITION:
D1: A PR is ALIGNED iff it does not introduce inconsistencies with
    any open issue, the roadmap, or core documentation — and any
    impacts are acknowledged with updates or tracked follow-ups.

ROADMAP IMPACT:
R1: v3 project plan (docs/inspect_refactor/grounding_lab_project_plan_v3.md)
    Impact: [NONE / description of impact]
    Action: [N/A / updated plan / created follow-up issue #N]

OPEN ISSUE SCAN:
For each open issue that could be affected by this PR:
I1: #[N] [title] → Impact: [NONE / description] → Action: [N/A / updated / created follow-up]
I2: #[N] [title] → Impact: [NONE / description] → Action: [N/A / updated / created follow-up]
...

DOCUMENTATION IMPACT:
D1: CLAUDE.md → [NONE / UPDATED with description]
D2: CONTRIBUTING.md → [NONE / UPDATED with description]
D3: docs/contracts/embedder_v1.md → [NONE / UPDATED with description]
D4: docs/guides/adding-an-embedder.md → [NONE / UPDATED with description]
D5: [other affected docs] → [NONE / UPDATED]

DEPENDENCY GRAPH:
- Issues now unblocked by this PR: [list]
- Issues that should update their blocked-by: [list]
- New issues created by this PR: [list with #numbers]

FORMAL CONCLUSION:
By D1, this PR is [ALIGNED / NOT ALIGNED — must address impacts].
```

---

## When to Produce Certificates

| Event | Certificate Required |
|-------|---------------------|
| Task implementation complete | Task Review Certificate |
| Architecture/design choice made | Design Decision Certificate |
| Work deferred as "out of scope" | Deferred Scope Certificate |
| PR ready for review | Impact Alignment Certificate + all applicable certs |

---

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| "Looks good" | No evidence | Produce certificate with file:line references |
| "Out of scope" | No tracking | Create issue, produce Deferred Scope Certificate |
| "Inspect does X" | Matching a lower bar | Ask: "What's the BEST we can do?" then do that |
| "Pre-existing issue" | Ignoring quality debt | Fix it or create a tracked issue |
| "Tests pass" (without output) | Unverified claim | Run command, show output, then claim |
| Review as separate layer | Redundant work | Certificate IS the review — one integrated pass |

---

## Process for Camunda State Engine

Each state transition requires specific artifacts:

```yaml
states:
  pending:
    transitions:
      - to: implementing
        trigger: assignment

  implementing:
    transitions:
      - to: self_review
        requires:
          - code_committed: true
          - tests_written_tdd: true
          - tests_pass: fresh_output

  self_review:
    transitions:
      - to: certificate_review
        requires:
          - self_review_complete: true

  certificate_review:
    transitions:
      - to: certified
        requires:
          - task_review_certificate: all_premises_satisfied
          - no_critical_issues: true
          - no_important_issues: true
      - to: issues
        requires:
          - task_review_certificate: has_issues

  issues:
    transitions:
      - to: implementing
        trigger: issues_assigned

  certified:
    transitions:
      - to: complete
        requires:
          - pr_created_or_merged: true
```

---

## Living Document

This process evolves. When a new certificate type is needed, add it here.
When a failure mode is discovered, add it to anti-patterns. Every developer
(human or AI) working on this project reads this document.
