# AEGIS as a Claude Code plugin

The plugin installs AEGIS into **your own repository**, so you do not have to clone AEGIS
and work inside the clone. It provides the same agents, commands, skills, golden rules
and implementation guard as the [clone setup](claude-code.md).

> **Preview.** The plugin is new. Run the [guard check](#check-the-guard-once) before
> you rely on it.

## Requirements

- Claude Code.
- Python 3.10 or later on your PATH.
- The AEGIS CLI, which the agents call as `python -m artifact_tools`:

  ```bash
  pip install aegis-sdlc
  ```

## Install

In Claude Code, in your repository:

```text
/plugin marketplace add nishant-tamilselvan/AEGIS
/plugin install aegis@aegis
```

Or from a terminal: `claude plugin marketplace add nishant-tamilselvan/AEGIS`, then
`claude plugin install aegis@aegis`.

Restart Claude Code. The first time, trust the folder and approve the plugin's hooks. The
hooks are what keep implementation agents inside their work packages.

## Use

Plugin commands carry the `aegis:` prefix:

| Clone setup | Plugin |
| --- | --- |
| `/start-ideation` | `/aegis:start-ideation` |
| `/start-architecture` | `/aegis:start-architecture` |
| `/start-implementation` | `/aegis:start-implementation` |
| `/add-requirement`, `/add-adr`, `/run-review-cycle` | `/aegis:add-requirement`, `/aegis:add-adr`, `/aegis:run-review-cycle` |
| `/resume-implementation`, `/implementation-status` | `/aegis:resume-implementation`, `/aegis:implementation-status` |
| `/run-implementation-review`, `/add-implementation-decision` | `/aegis:run-implementation-review`, `/aegis:add-implementation-decision` |

Artifacts are written to `docs/artifacts/<app-name>/` in your repository. For phase 3,
pass your repository's own path as the target, or a separate repository if you prefer:

```text
/aegis:start-implementation my-app /absolute/path/to/your/repository
```

When the target is the same repository, `docs/artifacts/` stays writable for artifact
work, and only the active package's implementer can write code.

## What the plugin installs

| Part | What it does |
| --- | --- |
| 15 subagents | The specialists, listed as `aegis:artifact-manager`, `aegis:service-implementer` and so on. |
| 14 skills | The 10 commands above and the 4 AEGIS knowledge skills. |
| `SessionStart` hook | Loads the AEGIS golden rules into every session, and warns if `aegis-sdlc` is not installed. |
| `PreToolUse` hook | The implementation guard, run against your repository. |
| `PostToolUse` hook | Re-validates artifacts after each edit. |

The hooks carry their own copy of the guard, so the guard works even before
`aegis-sdlc` is installed. It still never fails open.

## Check the guard once

1. Approve a work package and let the orchestrator move it to `in-progress`.
2. Ask: *"As a guard test, have the package's implementer create one file outside the
   package's target paths. Do not retry."*
3. The write must be **denied** with *"… is outside the active work package's declared
   target paths."*

If the write goes through, run `/hooks` and check that the plugin's `PreToolUse` hook is
listed and enabled.

## Enterprise Standards

The plugin does not include a standards server. Connect your organization's server in your
repository's `.mcp.json` under the name `enterprise-standards-server`. See the
[Enterprise Standards setup guide](enterprise-standards-setup.md). Without a server, the
agents warn and continue.

## Update and remove

From a terminal:

```bash
claude plugin update aegis@aegis
claude plugin uninstall aegis@aegis
```

Keep `aegis-sdlc` on the same version as the plugin: `pip install -U aegis-sdlc`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Commands such as `/aegis:start-ideation` are missing | Run `/plugin` to check that `aegis` is installed and enabled, then restart Claude Code. |
| A message says the AEGIS CLI is not installed | Run `pip install aegis-sdlc` for the Python on your PATH, then restart. |
| The guard never denies anything | Run `/hooks`. The plugin's hooks run only after you trust the folder and approve them. |
| An "AEGIS implementation guard" approval prompt appears unexpectedly | The guard could not run. Check that `python` on your PATH works; see [Troubleshooting](troubleshooting.md). |

## For contributors

The plugin in `plugins/aegis/` and the marketplace file `.claude-plugin/marketplace.json`
are generated from `aegis/` by `python scripts/sync_platforms.py`. Do not edit them by
hand. CI validates them with `claude plugin validate --strict`.
