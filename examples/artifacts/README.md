# Example: a complete artifact set

[`todo-list/`](todo-list/) is what AEGIS produces for a very small application after
**ideation** and **architecture**. It is a personal to-do list: one user signs in, then
adds, renames, completes and deletes tasks.

Read it to see what "done" looks like before you run AEGIS on your own idea. Every file
started from the real templates with `python -m artifact_tools scaffold`, and every
artifact is `approved`.

## What is in it

| Phase | Artifact | Highlights |
| --- | --- | --- |
| Ideation | [Product requirements](todo-list/product-requirements.md) | Two goals (`PR-001`, `PR-002`), scope, constraints |
| Ideation | [User journey map](todo-list/user-journey-map.md) | One persona, four journey steps (`UJ-001`–`UJ-004`) |
| Ideation | [Functional requirements](todo-list/functional-requirements.md) | Six requirements, each traced to a goal or journey step |
| Ideation | [Non-functional requirements](todo-list/non-functional-requirements.md) | Eight measurable targets, each with a verification method |
| Ideation | [System blueprint](todo-list/system-blueprint.md) | Four components (`BP-001`–`BP-004`) |
| Ideation | [Executive briefing](todo-list/executive-briefing.md) | The ask, metrics and three risks |
| Architecture | [Interface specifications](todo-list/interface-specifications.md) | One REST API with an [OpenAPI 3.1 contract](todo-list/interfaces/synchronous/todo-api-v1.yaml) |
| Architecture | [Data architecture](todo-list/data-architecture.md) | Two entities, an ERD, retention and residency |
| Architecture | [Security architecture](todo-list/security-architecture.md) | Five controls and a STRIDE summary |
| Architecture | [Deployment topology](todo-list/deployment-topology.md) | Three nodes, environments and disaster recovery |
| Architecture | [Observability strategy](todo-list/observability-strategy.md) | Five signals, KPIs and alerting |
| Architecture | [Architecture decisions](todo-list/architecture-decisions/README.md) | ADR-0002 managed PostgreSQL, ADR-0003 OIDC with PKCE |

## Check it yourself

```bash
python -m artifact_tools validate examples/artifacts/todo-list --strict
python -m artifact_tools implementation readiness examples/artifacts/todo-list <any-folder-with-a-README> --standards-review verified
```

The first command reports no errors or warnings. The second reports `READY`: the set
is complete enough to start implementation. CI runs both on every change, so the example
stays valid as AEGIS evolves.

Real applications live in `docs/artifacts/<app-name>/`, which is gitignored. This example
lives under `examples/` so it can be committed.
