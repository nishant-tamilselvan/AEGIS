---
# Generated from aegis/prompts/run-review-cycle.md by scripts/sync_platforms.py. Edit the source, not this file.
name: run-review-cycle
description: "Run a full self-correction review cycle over the artifact set."
argument-hint: "[app-name] or leave blank to review every application"
disable-model-invocation: true
---
## How to run this in Claude Code

Delegate this request to the `critic-reviewer` subagent with the Agent tool. Pass it the
request below, the user's arguments and the application's `docs/artifacts/<app>` path.
If it needs a decision, ask the user with AskUserQuestion and send the answer back to it.
If its final message hands work to another agent, delegate that work to the named
subagent. Report the outcome to the user.
In a plugin install the subagents are listed with the `aegis:` prefix, for example `aegis:artifact-manager`.

## This request

Run a complete review.

1. If I named an application above, review `docs/artifacts/<app-name>/` and run
   `python -m artifact_tools validate docs/artifacts/<app-name> --strict`. If I did not,
   review every application with `python -m artifact_tools validate docs/artifacts --strict`.
2. Add your qualitative checks: coverage, traceability, contradictions, testability,
   scope creep, and blueprint fit.
3. Return your standard report (VALIDATION / BLOCKING / ADVISORY / VERDICT).

Do not edit any files. If the verdict is NEEDS-CHANGES, list precise fixes so
`artifact-manager` can resolve them.

Arguments from the user: $ARGUMENTS
