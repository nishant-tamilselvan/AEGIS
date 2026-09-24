---
name: implementation-status
description: "Report read-only AEGIS phase-3 progress, coverage, blockers, active/next work package, decisions and verification state."
agent: implementation-orchestrator
argument-hint: "[app-name]"
---
Provide a read-only implementation status for the selected application. Do not edit any
artifact or target file.

Read the canonical pointer, work packages and decision ledger; run implementation
validation; and summarize:

- overall and release status;
- target workspace, branch and baseline;
- source-version or Enterprise Standards drift;
- active and next eligible package;
- completed, blocked, deferred and remaining packages;
- requirement/control/ADR coverage;
- pending material decisions and blockers;
- latest actual verification outcomes.

Keep the result concise and call out the single most important next action.
