# Security Policy

## Supported versions

AEGIS is pre-1.0. Security fixes go into the latest release and `main` only.

| Version | Supported |
| --- | --- |
| Latest release / `main` | Yes |
| Older releases | No |

## Reporting a vulnerability

Report vulnerabilities privately through GitHub:
**[Report a vulnerability](https://github.com/nishant-tamilselvan/AEGIS/security/advisories/new)**.

Do not open a public issue, pull request or discussion for a vulnerability.

Include:

- what is affected (file, agent, hook, CLI command or workflow);
- how to reproduce it, with the smallest example you can;
- the impact you expect, such as a write outside a work package's declared paths;
- any fix you suggest.

Remove secrets, private repository names and personal paths before you send it.

This is a volunteer-maintained project. We aim to:

- acknowledge a report within 5 business days;
- confirm or reject it within 15 business days;
- publish a fix and a GitHub security advisory for confirmed issues, crediting you
  unless you ask us not to.

## Scope

In scope:

- **Implementation guard bypass.** Any way for an implementation agent to write
  outside its active work package's declared target paths, write under `docs/artifacts/`,
  or run a destructive or deployment command without the human gate
  (`scripts/implementation_guard.py`, `src/artifact_tools/guard.py`, and the hook
  configuration in `.github/hooks/` and `.claude/settings.json`). This includes any
  GitHub Copilot or Claude Code tool that edits files without the guard seeing it.
- **Prompt injection through repository content.** Agent, prompt, skill or template
  text that makes an agent ignore its rules, leak data or take unapproved actions.
- **Prompt injection through the Enterprise Standards library.** Standards content
  that makes an agent act on instructions instead of treating the content as data.
- **The reference MCP server** in `examples/enterprise-standards-server/`: path
  traversal, reading files outside the knowledge base, or crashes on crafted input.
- **The `artifact_tools` CLI and hooks:** unsafe file handling or command execution.
- **CI workflows:** anything that exposes a token or runs untrusted pull request code with
  write access.

Out of scope:

- vulnerabilities in VS Code, GitHub Copilot, Claude Code, the MCP SDK or other third-party tools
  (report those upstream);
- MCP servers you connect yourself, other than the reference server;
- attacks that need an already-compromised machine or repository;
- findings from automated scanners without a demonstrated impact.

## Security model

Know these limits before you rely on AEGIS:

- **The implementation guard is a safeguard, not a sandbox.** It checks the tool calls
  the agent host reports to it, and it never fails open: if it breaks, implementation
  agents are denied and every other call becomes an approval prompt. Only the active
  package's implementer may write to the target repository. It cannot see tools the host does not route
  through the hook, or hooks you have disabled. Review every change an agent makes before
  you merge it.
- **Standards content is untrusted input.** Agents treat documents returned by
  `enterprise-standards-server` as data and never as instructions. Only connect libraries
  your organization controls.
- **The reference MCP server has no authentication.** It binds to `127.0.0.1` by default.
  Put it behind a gateway that enforces TLS and authentication before you share it. See
  [Enterprise Standards Setup](docs/enterprise-standards-setup.md#security).
- **Deployment is never automatic.** Release approval needs a named human approver.

## Keeping secrets out of the repository

- `.vscode/mcp.json` and `.mcp.json` are gitignored. Start from `.vscode/mcp.example.json`
  or `.mcp.example.json`. Use VS Code `inputs` or `${ENV_VAR}` expansion for tokens. Never
  paste credentials into either file.
- CI scans the full history with [gitleaks](https://github.com/gitleaks/gitleaks), and the
  pre-commit hooks scan each commit.
- `python scripts/ci/repo_checks.py all` blocks personal paths, invisible Unicode
  characters and denylisted terms. Keep organization-specific terms in a local,
  gitignored `.denylist.local` file (see `scripts/ci/denylist.txt`).
- If you commit a secret by mistake, rotate it first. Removing it from history does not
  make it safe again.
