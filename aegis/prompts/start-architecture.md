---
name: start-architecture
description: "Kick off the architecture phase from the completed business artifacts."
agent: architecture-orchestrator
argument-hint: "[app-name] optional focus, e.g. 'start with data'"
---
Begin the architecture phase.

First determine which application this targets. If I named an app above, use its
`docs/artifacts/<app-name>/` folder; otherwise list the applications in
`docs/artifacts/` (see its `README.md`) and ask me to pick. Thread that path through
every handoff.

Then read the phase-1 artifacts in `docs/artifacts/<app-name>/` (product, functional and
non-functional requirements, the user journey map and the system blueprint) and give
me a short recap of the scope you will design for. If any foundation is missing or
ambiguous, ask me before proceeding.

Then proceed **one phase at a time** — Context → Data → Interfaces → Security →
Deployment → Observability — capturing significant choices as ADRs along the way.
After each phase:

- delegate the proposal to the relevant specialist,
- delegate document work to `artifact-manager`,
- delegate a consistency pass to `critic-reviewer`,
- give me a 2–3 line recap and ask before continuing.

Do not overwhelm me. Keep it to a few focused questions per turn.
