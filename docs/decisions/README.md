# Design Decisions

> **Status:** Informative — rationale and history
> **Audience:** Contributors, certificate-producing agents, reviewers

Design decisions record *why* specific technical choices were made. Each decision evaluates options with trade-offs and documents the chosen approach.

## Session 3: Minimal BPMN Process (Happy Path)

| Decision | Summary |
|----------|---------|
| [Handler `**kwargs` Pattern](s3-handler-kwargs-pattern.md) | Use `**kwargs` in pyzeebe handlers; `job: Job` annotation broken under PEP 563 |
| [Sync/Async Strategy](s3-sync-async-strategy.md) | `SyncZeebeClient` for deploy/start; `asyncio.run()` wrapping `ZeebeWorker` for job completion |
| [CI Cluster Topology](s3-ci-cluster-topology.md) | Integration tests target unauthenticated CI cluster (36500/18088); auth deferred |

## Session 2: Evidence Inventory + Referential Validation

| Decision | Summary |
|----------|---------|
| [Canonical Evidence Inventory](s2-canonical-evidence-inventory.md) | Inventories on the certificate envelope, not companion documents |
| [Claim Namespace Semantics](s2-claim-namespace-semantics.md) | All ClaimBase nodes share one document-wide namespace |
| [Diagnostic Model](s2-diagnostic-model.md) | Machine-readable diagnostics from day one using Pydantic |
| [Path Validation Semantics](s2-path-validation-semantics.md) | Lexical containment for path safety, filesystem checks opt-in |
