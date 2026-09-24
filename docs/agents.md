# Agents, prompts and skills

## Agents

Agents are written once in [`aegis/agents/`](../aegis/agents/) and generated for GitHub
Copilot (`.github/agents/`) and Claude Code (`.claude/agents/`). Orchestrators talk to
you. Specialists do focused work and report back to their orchestrator. In Claude Code,
orchestrators run in the main conversation and specialists run as subagents; see
[Using AEGIS with Claude Code](claude-code.md).

### Ideation (phase 1)

| Agent | Role |
| --- | --- |
| `ideation-orchestrator` | User-facing. Runs the phased conversation without overwhelming you. |
| `architecture` | Proposes the smallest system blueprint that meets the requirements. |

### Architecture (phase 2)

| Agent | Role |
| --- | --- |
| `architecture-orchestrator` | User-facing. Guides interfaces, data, security, deployment and observability in turn. |
| `interface-integration-architect` | Proposes API and event contracts, and the observability strategy. |
| `data-architect` | Proposes the data model, retention and data sovereignty. |
| `security-architect` | Proposes the threat model, identity and access, and trust boundaries. |
| `platform-architect` | Proposes the deployment topology, environments and disaster recovery. |
| `adr-author` | Records architectural decisions as ADRs. |

### Shared by phases 1 and 2

| Agent | Role |
| --- | --- |
| `artifact-manager` | The only writer of artifacts. Assigns ids, bumps versions and validates. |
| `critic-reviewer` | Read-only quality gate. Drives self-correction until validation passes. |

### Implementation (phase 3)

| Agent | Role |
| --- | --- |
| `implementation-orchestrator` | User-facing. Runs readiness, human checkpoints, execution and release. |
| `implementation-planner` | Read-only. Turns approved artifacts into bounded work packages. |
| `data-contract-implementer` | Migrations, persistence, contracts and shared types. |
| `service-implementer` | API, domain and integration code. |
| `ui-implementer` | Accessible UI built on the target's design system. |
| `platform-implementer` | CI/CD, containers, manifests and operational wiring. Never deploys automatically. |
| `test-quality-engineer` | Integration, end-to-end, performance and security verification. |
| `implementation-reviewer` | Independent, read-only package and release review. |

## Prompts

Prompts are written in [`aegis/prompts/`](../aegis/prompts/) and run as slash commands in
Copilot Chat and Claude Code. Most take the application name as their first argument.

| Prompt | Runs | Use it to |
| --- | --- | --- |
| `/start-ideation` | Ideation Orchestrator | Start a product from a one-line idea. |
| `/add-requirement` | Ideation Orchestrator | Add or change a requirement and propagate it. |
| `/start-architecture` | Architecture Orchestrator | Start phase 2 from the business artifacts. |
| `/add-adr` | ADR Author | Record a significant architectural decision. |
| `/run-review-cycle` | Critic Reviewer | Run a full self-correction review over the artifacts. |
| `/start-implementation` | Implementation Orchestrator | Start phase 3 against a target repository. |
| `/resume-implementation` | Implementation Orchestrator | Resume phase 3 after checking for drift. |
| `/implementation-status` | Implementation Orchestrator | Report progress, coverage and blockers (read-only). |
| `/add-implementation-decision` | Implementation Orchestrator | Record a tactical choice or escalate a material one. |
| `/run-implementation-review` | Implementation Reviewer | Review a work package or the final release. |

## Skills

Skills are written in [`aegis/skills/`](../aegis/skills/) and copied to both platforms.
Agents load them when a task needs them.

| Skill | Covers |
| --- | --- |
| [`artifact-management`](../aegis/skills/artifact-management/SKILL.md) | Authoring and validating the artifacts, with templates and id conventions. |
| [`adr-management`](../aegis/skills/adr-management/SKILL.md) | Creating, indexing and superseding ADRs. |
| [`implementation-management`](../aegis/skills/implementation-management/SKILL.md) | Phase 3: readiness, work packages, decisions, evidence and the release gate. |
| [`enterprise-standards`](../aegis/skills/enterprise-standards/SKILL.md) | Querying the Enterprise Standards library before each phase. |
