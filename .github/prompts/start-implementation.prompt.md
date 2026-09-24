---
# Generated from aegis/prompts/start-implementation.md by scripts/sync_platforms.py. Edit the source, not this file.
description: "Start AEGIS phase 3 from approved requirements and architecture, running readiness before any code or implementation-state write."
agent: "Implementation Orchestrator"
argument-hint: "[app-name] [absolute target-workspace] optional bounded scope"
---
Begin the implementation phase.

Resolve the application under `docs/artifacts/<app-name>/` and the target repository from
the arguments. If either is ambiguous, ask one focused question. Before initializing state
or editing target code:

1. retrieve current Approved enterprise implementation patterns, Software Delivery standards and
   related ADRs, checking supersession and review health;
2. run the read-only implementation readiness gate;
3. inspect target-repository instructions, project/build graph and analogous code.

If readiness is blocked, make no writes. Report the smallest ordered blocker list and route
material gaps through architecture, Artifact Manager, ADR Author and Critic Reviewer.
If ready, delegate a complete dependency-ordered proposal to Implementation Planner,
delegate creation of `implementation/implementation.md`, `decision.md` and `WP-*` records
to Artifact Manager, and begin the first approved package.

Pause only at material HITL gates. Never deploy automatically or call generated code
production-ready without reviewer PASS and recorded evidence.
