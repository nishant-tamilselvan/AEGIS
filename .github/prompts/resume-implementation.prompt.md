---
# Generated from aegis/prompts/resume-implementation.md by scripts/sync_platforms.py. Edit the source, not this file.
description: "Resume an existing AEGIS phase-3 implementation from its canonical pointer after rechecking source, target and Enterprise Standards drift."
agent: "Implementation Orchestrator"
argument-hint: "[app-name]"
---
Resume implementation from `docs/artifacts/<app-name>/implementation/implementation.md`.

First re-run strict implementation validation and readiness. Compare all recorded source
artifact versions, accepted ADRs, native contracts, Approved Enterprise Standards guidance and the
target baseline with current state. If anything drifted, stop and reconcile or re-plan the
affected packages before target edits.

If clean, continue the single active package or the pointer's next eligible package through
implementer -> independent reviewer -> evidence -> completion. Ask me only if a material
decision, risk acceptance, destructive action or release gate is reached.
