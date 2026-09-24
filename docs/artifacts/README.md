# Artifacts Directory — Applications Index

This directory holds the living business and technical artifacts maintained by AEGIS.
**Each application gets its own subfolder** — `docs/artifacts/<app-name>/` — so a single
workspace can specify and maintain many products side by side without their requirements
or decisions colliding.

```text
docs/artifacts/
├── README.md                 ← you are here (applications index / router)
└── <app-name>/               ← one folder per application
    ├── product-requirements.md
    ├── functional-requirements.md
    ├── ... (the 11 artifact documents)
    ├── architecture-decisions/   ← this app's ADRs (ADR-* index + records)
    └── interfaces/               ← this app's contract store (OpenAPI/AsyncAPI/GraphQL)
```

The documents are generated and maintained by the `artifact-manager` agent (and
`adr-author` for ADRs). Do not hand-create them — start a session and name the app:
`/start-ideation`, then `/start-architecture`. To scaffold from templates, always target
the application subfolder:

```bash
python -m artifact_tools scaffold <type> docs/artifacts/<app-name> --project "<Name>"
```

## Applications

| Application | Folder | Status |
| :--- | :--- | :--- |
| _Example: Customer Portal_ | `customer-portal/` | _example_ |

> Add a row here whenever a new application is started so agents can discover it.

## What lives inside each application folder

Every `<app-name>/` folder contains the same set of documents. Requirement IDs
(`PR-`, `FR-`, `NFR-`, …) are **unique within an application** and are never reused
inside that app; the same id may appear independently in a different app.

| Artifact Group | Document Name | Phase / IDs | Target Audience | Primary Core Meta-Tags |
| :--- | :--- | :--- | :--- | :--- |
| **Business Context** | `executive-briefing.md` | Ideation · `RISK-` | Executives, Stakeholders | ROI, Vision, Scope, Goals, Risks |
| **Product & UX** | `product-requirements.md` | Ideation · `PR-` | Product, Design, QA | Features, Epic Mapping, Scope, Constraints |
| | `functional-requirements.md` | Ideation · `FR-` | Product, Engineering | User Stories, System Actions, Acceptance Criteria |
| | `user-journey-map.md` | Ideation · `UJ-` | UX, Frontend Devs | User Flow, Touchpoints, Personas, Friction |
| **Technical Baseline** | `non-functional-requirements.md` | Ideation · `NFR-` | Platform, InfoSec, Infra | SLA, SLO, Performance, RTO/RPO |
| | `system-blueprint.md` | Ideation · `BP-` | All Engineering | Context Diagram, Macro Topology, Components |
| **Detailed Design** | `interface-specifications.md` | Architecture · `IF-` | Backend, Integration | Routing Index, API Specs, Events, GraphQL, JSON |
| | `security-architecture.md` | Architecture · `SEC-` | InfoSec, DevSecOps | OAuth2, RBAC, Encryption, PII, Trust Boundaries |
| | `data-architecture.md` | Architecture · `DM-` | DBAs, Data Engineers | ERD, DDL, Sovereignty, Retention |
| | `deployment-topology.md` | Architecture · `DEP-` | DevOps, SRE | Cloud Architecture, IaC, Network, DR |
| | `observability-strategy.md` | Architecture · `OBS-` | SRE, Support | Log Format, Spans, Alerts, KPI |
| **Governance** | `architecture-decisions/README.md` | Architecture · `ADR-` | Architecture, Leads | ADR Index, Immutable Log, Tech Stack |

**Business** artifacts belong to **phase 1** (ideation); **technical** artifacts and
ADRs to **phase 2** (architecture). Only the phase-1 set need exist before the
architecture phase begins. Every cross-reference between documents uses the stable IDs
above (see
[id-conventions](../../aegis/skills/artifact-management/references/id-conventions.md)).

### Decentralized contract stores

Within an application, two documents are **routers**, not containers — the real content
lives beside them in native formats so tools and LLMs parse it directly, one file per
contract:

- `interface-specifications.md` → `<app-name>/interfaces/` — OpenAPI/AsyncAPI
  (`.yaml` / `.json`), `.graphql`, `.proto`, split into `synchronous/`,
  `asynchronous/`, `graphql/`.
- `architecture-decisions/README.md` → one `NNNN-*.md` file per decision.

## The LLM parsing advantage

1. **Tokens are saved.** For _"What API gateway protocol are we using for
   authorization?"_, an agent reads this index, targets the right application's
   `security-architecture.md` or `interface-specifications.md`, and ignores everything else.
2. **Context drift is avoided.** Decoupling applications — and, inside each app,
   `data-architecture.md` from `deployment-topology.md` — keeps unrelated edits from
   muddying one another.

## Validate

```bash
# Validate a single application
python -m artifact_tools validate docs/artifacts/<app-name> [--strict]

# Validate every application at once
python -m artifact_tools validate docs/artifacts [--strict]
```

Validation runs per application — frontmatter, id uniqueness/prefixes, cross-reference
resolution, functional-requirement traceability, and ADR index/status integrity. When
pointed at `docs/artifacts`, each application is validated in isolation and findings are
prefixed with the application folder name.
