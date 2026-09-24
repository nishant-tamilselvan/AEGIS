# CLAUDE.md

This repository is AEGIS. In Claude Code you can either **use AEGIS** (run the ideation,
architecture and implementation phases for an application) or **work on AEGIS itself**.
Both sets of rules are below.

## Using AEGIS

@aegis/instructions.md

### Running AEGIS in Claude Code

- **Start a phase with a slash command:** `/start-ideation`, `/start-architecture`,
  `/start-implementation` and the other prompts in `.claude/skills/`. Each one loads the
  orchestrator's role into this conversation. You then talk to the user and delegate.
- **Specialists are subagents** in `.claude/agents/`, such as `artifact-manager`,
  `critic-reviewer` and `service-implementer`. Delegate to them by name with the Agent tool.
  They cannot see this conversation, so give each one the `docs/artifacts/<app>` path, ids
  and decisions it needs.
- **Ask the user** with AskUserQuestion, one to three focused questions at a time.
- **Hooks** in `.claude/settings.json` run the implementation guard before edits and shell
  commands, and re-validate artifacts after edits. Treat a guard denial as final. Never
  work around it with another tool.
- **Enterprise Standards** come from the `enterprise-standards-server` MCP server when
  `.mcp.json` is configured (copy `.mcp.example.json`). Its tools appear as
  `mcp__enterprise-standards-server__search_documents` and similar. If the server is not
  connected, follow the "degrade gracefully" rule in the `enterprise-standards` skill.

## Working on the AEGIS repository

@AGENTS.md
