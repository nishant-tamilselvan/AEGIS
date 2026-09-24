# Using AEGIS with Claude Code

AEGIS runs in [Claude Code](https://code.claude.com/docs) as well as in GitHub Copilot.
Both platforms use the same agents, prompts, skills, golden rules, hooks and CLI. This page
covers what is specific to Claude Code.

## Set up

Requirements: Claude Code, Python 3.10 or later, and Git. The subagents, slash commands
and implementation guard were verified with Claude Code 2.1.263 on Windows.

```bash
git clone https://github.com/nishant-tamilselvan/AEGIS.git
cd AEGIS
pip install -e .
claude
```

Claude Code picks up the repository's configuration when you start it in the repository
root:

| File or folder | Gives you |
| --- | --- |
| `CLAUDE.md` | The golden rules (imported from `aegis/instructions.md`) and the contributor guide. |
| `.claude/skills/` | The slash commands (`/start-ideation` and the others) and the four AEGIS skills. |
| `.claude/agents/` | The 15 specialist subagents. |
| `.claude/settings.json` | The implementation guard and automatic validation hooks. |

The first time, Claude Code asks you to trust the folder. It may also ask you to approve
the project hooks. Approve them: the guard is what keeps implementation agents inside
their work packages.

> **Open the folder interactively before any headless run.** In our testing, `claude -p` in
> a folder that had never been trusted did not run the project hooks, so the guard did not
> run either. Start `claude` in the folder once, accept the trust prompt, and only then use
> `claude -p` or scripted runs there.

Check the setup inside Claude Code:

- Ask Claude "Without running any tools, list the subagent types you can delegate to."
  The list includes `artifact-manager`, `critic-reviewer`, `service-implementer` and the
  other specialists.
- `/hooks` shows the `PreToolUse` and `PostToolUse` hooks.
- Typing `/start` offers `/start-ideation`, `/start-architecture` and `/start-implementation`.

## Run the phases

```text
/start-ideation customer-portal A self-service portal where customers track orders
/start-architecture customer-portal
/start-implementation customer-portal /absolute/path/to/target-repository
```

The other commands are `/add-requirement`, `/add-adr`, `/run-review-cycle`,
`/resume-implementation`, `/implementation-status`, `/run-implementation-review` and
`/add-implementation-decision`. They behave as described in
[Getting started](getting-started.md).

## How AEGIS maps onto Claude Code

| AEGIS concept | In Claude Code |
| --- | --- |
| Orchestrators (ideation, architecture, implementation) | Run **in your main conversation**. Each phase command loads the orchestrator's role, so it can talk to you and ask questions with AskUserQuestion. |
| Specialists (`artifact-manager`, `data-architect`, `service-implementer`, ...) | **Subagents** that the orchestrator delegates to with the Agent tool. They cannot talk to you directly. When one needs a decision, it says so in its final report and the orchestrator asks you. |
| Prompts | **Slash-command skills** in `.claude/skills/<name>/`. They run only when you type them. |
| Skills (`artifact-management`, `adr-management`, `implementation-management`, `enterprise-standards`) | **Skills** in `.claude/skills/`, loaded when a task needs them. |
| Hooks | `.claude/settings.json`, calling the same `scripts/implementation_guard.py` and `scripts/validate_hook.py` as Copilot. |
| MCP server | `.mcp.json` (copy it from `.mcp.example.json`). |

### The implementation guard in Claude Code

Claude Code tells the hook which subagent made a tool call (the `agent_type` field). The
guard applies its rules when that subagent is one of the implementation agents:
`data-contract-implementer`, `service-implementer`, `ui-implementer`,
`platform-implementer` or `test-quality-engineer`. It checks `Edit`, `Write`, `MultiEdit`,
`NotebookEdit`, `Bash` and `PowerShell` calls:

- writes outside the active work package's declared paths are denied;
- writes under `docs/artifacts/` are denied;
- file writes through the shell (`>`, `Set-Content` and similar) are denied;
- destructive and deployment commands need your approval.

Everyone else, including your main conversation (which carries no `agent_type`), the
orchestrators and the reviewers, may read and run commands anywhere, and write anywhere
except the target repository of an initialized implementation. Code there is written only
by the active work package's implementer. A write there from anyone else is denied with a
reminder to delegate.

If the guard itself fails, it never silently allows the call. An implementation agent's
call is denied. Any other call, including yours, is turned into an approval prompt that
mentions "AEGIS implementation guard", so a broken guard cannot lock you out of your
session. Such a prompt means the hook needs attention: check that `python` on your PATH
can import PyYAML.

### Verify the guard once

After your first `/start-implementation`, while a work package is `in-progress`, ask the
orchestrator to have the package's implementer write a file **outside** the package's
target paths. The guard must deny it with "outside the active work package's declared
target paths". If the write goes through, run `/hooks` to check that the project hooks are
enabled, and see [Troubleshooting](troubleshooting.md#claude-code).

## Connect Enterprise Standards

```bash
pip install -r examples/enterprise-standards-server/requirements.txt
cp .mcp.example.json .mcp.json
```

Restart Claude Code, approve the `enterprise-standards-server` project server, and run
`/mcp` to check it is connected. `.mcp.json` is gitignored.

For a shared server with a token, keep the token in an environment variable. Claude Code
expands `${VAR}` in `.mcp.json`:

```json
{
  "mcpServers": {
    "enterprise-standards-server": {
      "type": "http",
      "url": "https://standards.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${ENTERPRISE_STANDARDS_TOKEN}"
      }
    }
  }
}
```

Keep the server name `enterprise-standards-server`. The subagents' tool lists refer to it
as `mcp__enterprise-standards-server`. The full setup is in the
[Enterprise Standards setup guide](enterprise-standards-setup.md).

## Differences from Copilot

| Topic | GitHub Copilot | Claude Code |
| --- | --- | --- |
| Where orchestrators run | As custom agents you select or start with a prompt | In the main conversation, started by a slash command |
| How specialists are called | Agent handoffs | Subagents via the Agent tool |
| Questions to the user | In chat | AskUserQuestion, from the main conversation |
| Validation feedback | Hook `systemMessage` | Hook `additionalContext` to the model, plus a short notice to you |
| MCP config | `.vscode/mcp.json` (`inputs` for secrets) | `.mcp.json` (`${ENV_VAR}` for secrets) |

## For contributors

Do not edit `.claude/agents/` or `.claude/skills/`. They are generated from `aegis/`
together with the Copilot files:

```bash
python scripts/sync_platforms.py          # regenerate
python scripts/sync_platforms.py --check  # what CI runs
```

See [CONTRIBUTING.md](../CONTRIBUTING.md).
