# Troubleshooting

## Setup

| Symptom | Fix |
| --- | --- |
| **Copilot:** AEGIS agents or slash commands do not appear in Copilot Chat. | Open the repository root as the VS Code workspace, not a subfolder. Switch Copilot Chat to Agent mode. Update VS Code and Copilot Chat if the agent picker is missing. |
| `No module named artifact_tools` | In a clone, run `pip install -e .` in the active environment, or set `PYTHONPATH=src`. Anywhere else, including with the plugin, run `pip install aegis-sdlc`. |
| `python` is not found on Windows. | Use `py -3` or install Python from python.org with "Add to PATH" selected. |
| Hooks do not run. | Hooks are configured in `.github/hooks/validate-artifacts.json` (Copilot) and `.claude/settings.json` (Claude Code), and call `python`. Make sure `python` on your PATH has PyYAML installed. |
| Agents say "Enterprise Standards MCP unavailable". | See [Enterprise Standards troubleshooting](enterprise-standards-setup.md#troubleshooting). |

## Validation errors

Run `python -m artifact_tools validate docs/artifacts/<app>` to see the full list.

| Message | Meaning and fix |
| --- | --- |
| `references unknown id X-NNN (not defined in any artifact)` | An artifact cites an id that no artifact defines. Define it, or fix the typo. If the id belongs to an external standard, see the [ID convention](enterprise-standards-setup.md#id-convention). |
| `FR-NNN has no traceability to a PR-* or UJ-* id` | Each functional requirement must reference a product goal or a user journey on its row. |
| `index is missing a row for ADR-NNNN` | Add the ADR to `architecture-decisions/README.md`, or create ADRs with `adr new`, which indexes them for you. |
| `date '...' must be ISO YYYY-MM-DD` | Fix the date in the ADR frontmatter. |

## Implementation readiness is blocked

`implementation readiness` lists every blocking finding with a code. The common ones:

| Code | Fix |
| --- | --- |
| `artifact-not-approved` | Review the artifact and set `status: approved` once it is agreed. |
| `artifact-missing` | Finish the phase that produces it: ideation for business artifacts, architecture for technical ones. |
| `artifact-tbd` | Resolve the remaining `TBD` content. |
| `open-decision` | Resolve the open decision that the artifact marks as blocking implementation. |
| `contracts-missing` | Add native contract files under `interfaces/` for every active `IF-*`. |
| `adr-proposed` / `adr-unaccepted` | Accept, reject or supersede the proposed ADRs. |
| `standards-review` | Verify current Enterprise Standards, then pass `--standards-review verified`. Without a library, a person must do this review. See [Running without a library](enterprise-standards-setup.md#running-without-a-library). |
| `target-missing` / `target-conventions` | Pass the correct absolute path to the target repository. It needs repository instructions or a build manifest that the agents can follow. |

## Implementation validation

| Code | Fix |
| --- | --- |
| `source-drift` | An artifact changed after a package was planned. Re-plan or re-approve the affected package. |
| `pointer-drift` | The pointer's active package does not match the package states. Transition the packages so exactly one is active, or use a shared `parallel_group`. |
| `parallel-path-overlap` | Two active packages share target paths. Give each package its own paths. |
| `work-package-evidence` | Record a reviewer PASS and at least one piece of evidence before completing. |
| `release-approval` | Run `implementation release-approve --approver <name>` after the final review. |

## The implementation guard denied an action

The guard runs before every tool call from an implementation agent.

| Reason | Fix |
| --- | --- |
| "No single active work package authorizes implementation changes." | Approve a work package and move it to `in-progress`. |
| "Target writes require an in-progress work package; review packages are read-only." | Move the package back to `in-progress` to make changes. |
| "No initialized implementation state resolves this target operation." | Run `/start-implementation` so the implementation state exists. |
| "Destructive commands require explicit human approval..." | Expected. Approve the command yourself if it is intended. |
| "Deployment requires an explicitly approved release gate." | Expected. Deployment needs the release gate and a person's approval. |

## Claude Code

Using the plugin? See also the [plugin troubleshooting](claude-code-plugin.md#troubleshooting).

| Symptom | Fix |
| --- | --- |
| `/start-ideation` and the other commands are missing. | Start `claude` in the repository root, and trust the folder when asked. |
| Claude does not list the AEGIS specialists when you ask which subagents it can delegate to. | Check that `.claude/agents/` exists. Contributors: run `python scripts/sync_platforms.py`. |
| The guard never denies anything in a `claude -p` (headless) run. | Project hooks did not run because the folder was never trusted. Start `claude` in the folder interactively once and accept the trust prompt. |
| The guard never denies anything. | Run `/hooks` and check the project `PreToolUse` hook is listed and enabled. Hooks call `python`, so make sure `python` on your PATH has PyYAML installed. |
| Validation errors are not fed back to the model. | The `PostToolUse` hook must run `validate_hook.py --platform claude`. See `.claude/settings.json`. |
| `enterprise-standards-server` is not connected. | Copy `.mcp.example.json` to `.mcp.json`, restart Claude Code, approve the project server and check `/mcp`. |

Still stuck? Open a [bug report](https://github.com/nishant-tamilselvan/AEGIS/issues/new/choose).
Redact anything private first.
