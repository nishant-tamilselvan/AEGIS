---
name: implementation-management
description: "Plan, execute, resume and validate AEGIS phase-3 implementation from approved artifacts. Use when starting implementation, creating or transitioning WP-* work packages, recording IDEC-* decisions or evidence, reviewing target code, handling drift, or approving release."
argument-hint: "e.g. 'start customer-portal implementation in C:\\repo' or 'resume WP-0004'"
---
# Implementation Management

Authoritative procedure for AEGIS phase 3. Approved requirements and architecture are
executable specifications; target code is produced only through bounded work packages and
actual verification evidence.

## Ownership

- **Artifact Manager is the sole writer** anywhere under `docs/artifacts/<app>/`, including
  `implementation/implementation.md`, `decision.md` and `work-packages/`.
- ADR Author is the sole writer to `architecture-decisions/`.
- Implementation code agents write only the active `WP-*` target paths in the separately
  resolved target workspace.
- Implementation Reviewer is read-only.

## Start procedure

1. Resolve one `docs/artifacts/<app>` and an absolute target workspace.
2. Follow [`enterprise-standards`](../enterprise-standards/SKILL.md): retrieve current Approved Patterns,
   Software Delivery standards and related ADRs; check supersession and review health.
3. Run readiness **before any write**:
   `python -m artifact_tools implementation readiness <app-dir> <target-workspace> --standards-review verified`
4. If blocked, do not initialize or edit code. Route material gaps back through the
   architecture specialist, user HITL, Artifact Manager/ADR Author and Critic Reviewer.
5. If ready, inspect target instructions and analogous code, ask Implementation Planner for
   the complete graph, then initialize:
   `python -m artifact_tools implementation init <app-dir> <target-workspace> --target-branch <branch> --target-baseline <commit> --standards-review verified`
6. Artifact Manager creates proposed packages with `implementation work-package new`.

If the MCP is unavailable, state: **"Enterprise Standards MCP unavailable — standards grounding
skipped, manual review required"**. Initialize only with `manual-review-required`; strict
validation and readiness remain blocked until a human records verified review.

## Context packet for every package

Pass the implementer exactly one approved package plus:

- canonical pointer and target baseline;
- every source row/document and source version listed by the package;
- accepted, non-superseded ADRs and current Enterprise Standards documents;
- native interface contracts;
- target instructions and analogous code;
- dependencies' completion evidence.

Never send an unbounded “implement the app” instruction.

## Work-package state machine

`planned -> approved -> in-progress -> review -> complete`

Allowed correction paths are `in-progress -> blocked`, `review -> in-progress`, and
`blocked -> approved|in-progress`. Planned/approved work may be deferred or cancelled;
deferred work may return to planned. Approval requires a named approver. Completion
requires at least one evidence record and independent reviewer `PASS`.

Useful commands:

- `implementation work-package transition <app> <WP> approved --actor <actor> --approved-by <person>`
- `implementation work-package transition <app> <WP> in-progress --actor <agent>`
- `implementation work-package record-evidence <app> <WP> "<command>" pass --details "<result>"`
- `implementation work-package transition <app> <WP> review --actor <agent> --review-status pass`
- `implementation work-package transition <app> <WP> complete --actor artifact-manager`

Only packages in one explicit parallel group with disjoint target paths may be active
concurrently. See [schema](references/implementation-schema.md).

## Decision policy

Record a tactical `IDEC-*` only when the choice is reversible, package-local, does not
change approved behavior or controls, and does not create material risk. Record the
question, choice, rationale, sources, paths and approver.

Pause and escalate when the choice changes scope, requirements, contracts, data ownership,
security/privacy, deployment topology, residual risk, multiple components, or is hard to
reverse. Obtain HITL, create/supersede an ADR, update affected artifacts, run strict review,
and refresh package source versions. See
[decision escalation](references/decision-and-traceability.md).

## Definition of done

A package is complete only when:

- all acceptance criteria and traced obligations are implemented;
- only declared paths changed;
- native format/lint/typecheck/build/test commands pass;
- applicable contract, migration/rollback, security, accessibility, performance and
  observability checks pass;
- no secrets or unapproved scope are present;
- Implementation Reviewer returns `PASS`;
- actual commands/outcomes are recorded as evidence.

The release gate additionally requires complete disposition of every active `FR-*`,
`NFR-*`, `BP-*`, `IF-*`, `DM-*`, `SEC-*`, `DEP-*`, `OBS-*` and accepted `ADR-*`, strict
validation, rollback readiness and explicit approval:
`python -m artifact_tools implementation release-approve <app> --approver <person>`.
Never deploy automatically.

## Resume and drift

`implementation.md` is the sole resume pointer. On every resume compare recorded source
versions, accepted ADR status, native contracts, Enterprise Standards currency and target baseline.
Drift invalidates affected approvals and evidence until the planner reconciles the package.
Run `implementation status` and `implementation validate --strict` before continuing.

## Self-correction

Reviewer `NEEDS-CHANGES` returns the package to `in-progress` and the same implementer.
Material findings follow the architecture remediation protocol, not an in-code workaround.
Artifact Manager updates state only after the orchestrator accepts observed evidence.
