---
name: add-implementation-decision
description: "Record a reversible tactical IDEC-* choice or escalate a material implementation decision through HITL, ADR and upstream artifact reconciliation."
agent: implementation-orchestrator
argument-hint: "[app-name] [WP-NNNN] decision question and proposed choice"
---
Classify this implementation decision before recording it.

Ground the concern in current Approved Enterprise Standards guidance and the traced artifacts. If it is
reversible and package-local, confirm the rationale and delegate an append-only `IDEC-*`
entry to Artifact Manager. If it changes requirements, contracts, architecture, security
or residual risk; crosses components; or is hard to reverse, pause implementation, present
the real alternatives and trade-offs, obtain my approval, then delegate the ADR and any
upstream artifact corrections. Run strict artifact review and refresh affected work-package
source versions before resuming.

Never use `decision.md` as a substitute for an ADR.
