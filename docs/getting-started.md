# Getting started

This guide takes you from a fresh clone to your first set of business artifacts.

## Requirements

- An agent host: **VS Code with GitHub Copilot Chat** in Agent mode, or **Claude Code**.
- Python 3.10 or later.
- Git.

## 1. Install

```bash
git clone https://github.com/nishant-tamilselvan/AEGIS.git
cd AEGIS
python -m venv .venv
.venv/Scripts/activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -e .
```

Check the tooling works:

```bash
python -m artifact_tools --help
```

## 2. Open the workspace

**GitHub Copilot:** open the `AEGIS` folder in VS Code. Copilot Chat picks up the
repository's customizations automatically:

| Folder | Gives you |
| --- | --- |
| `.github/agents/` | The AEGIS agents in the agent picker. |
| `.github/prompts/` | Slash commands such as `/start-ideation`. |
| `.github/skills/` | Skills the agents load on demand. |
| `.github/copilot-instructions.md` | Rules every agent follows. |
| `.github/hooks/` | The implementation guard and automatic validation. |

**Claude Code:** run `claude` in the `AEGIS` folder. See
[Using AEGIS with Claude Code](claude-code.md) for what it loads and how to check it.

The rest of this guide works the same on both platforms.

## 3. Connect your standards (optional)

AEGIS works without a standards library, but it asks fewer questions with one. To try it
with the included sample standards:

```bash
pip install -r examples/enterprise-standards-server/requirements.txt
cp .vscode/mcp.example.json .vscode/mcp.json   # GitHub Copilot
cp .mcp.example.json .mcp.json                 # Claude Code
```

In VS Code, open `.vscode/mcp.json` and start `enterprise-standards-server`. In Claude
Code, restart and approve the project server. The
[Enterprise Standards setup guide](enterprise-standards-setup.md) explains how to use your
own standards instead.

## 4. Run ideation (phase 1)

In Copilot Chat or Claude Code, run:

```text
/start-ideation customer-portal A self-service portal where customers track orders and raise support tickets
```

The Ideation Orchestrator works through the idea one small phase at a time. Answer its
questions, and confirm each recap before it moves on. When the phase ends,
`docs/artifacts/customer-portal/` holds six business artifacts:

- product requirements (`PR-*`)
- functional requirements (`FR-*`)
- non-functional requirements (`NFR-*`)
- user journey map (`UJ-*`)
- system blueprint (`BP-*`)
- executive briefing (`RISK-*`)

Check the set at any time:

```bash
python -m artifact_tools validate docs/artifacts/customer-portal
```

## 5. Run architecture (phase 2)

```text
/start-architecture customer-portal
```

The Architecture Orchestrator guides you through interfaces, data, security, deployment
and observability. It records significant choices as ADRs. This adds five technical
artifacts, the `architecture-decisions/` folder and the `interfaces/` contract store.

## 6. Run implementation (phase 3)

Implementation writes code into a **separate target repository**. Pass its absolute path:

```text
/start-implementation customer-portal /path/to/target-repository
```

A read-only readiness gate runs first. It blocks until:

- every artifact has `status: approved`;
- no open decision is marked as blocking;
- every interface has a native contract file;
- the standards review is verified;
- the target repository has discoverable conventions.

The orchestrator then plans bounded work packages (`WP-*`). Each needs your approval,
an independent review and recorded evidence before it can complete.

## Other prompts

| Prompt | Use it to |
| --- | --- |
| `/add-requirement` | Add or change a requirement and update every affected artifact. |
| `/run-review-cycle` | Run the critic's self-correction loop over the artifacts. |
| `/add-adr` | Record an architectural decision. |
| `/resume-implementation` | Pick up phase 3 where you left off. |
| `/implementation-status` | See progress, blockers and the next work package. |
| `/run-implementation-review` | Run the independent review of a package or the release. |
| `/add-implementation-decision` | Record a tactical choice or escalate a material one. |

## Next steps

- [The to-do list example](../examples/artifacts/): what a finished set of artifacts
  looks like, before you run your own session.
- [How it works](how-it-works.md): the phases, artifacts and guarantees.
- [Agents, prompts and skills](agents.md): the full catalog.
- [Troubleshooting](troubleshooting.md): when validation or readiness blocks you.
