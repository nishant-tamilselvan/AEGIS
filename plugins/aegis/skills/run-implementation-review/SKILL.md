---
# Generated from aegis/prompts/run-implementation-review.md by scripts/sync_platforms.py. Edit the source, not this file.
name: run-implementation-review
description: "Run the independent implementation package or final release review with strict traceability and actual verification evidence."
argument-hint: "[app-name] [WP-NNNN or release]"
disable-model-invocation: true
---
## How to run this in Claude Code

Delegate this request to the `implementation-reviewer` subagent with the Agent tool. Pass it the
request below, the user's arguments and the application's `docs/artifacts/<app>` path.
If it needs a decision, ask the user with AskUserQuestion and send the answer back to it.
If its final message hands work to another agent, delegate that work to the named
subagent. Report the outcome to the user.
In a plugin install the subagents are listed with the `aegis:` prefix, for example `aegis:artifact-manager`.

## This request

Review the requested active work package, or the final release when `release` is supplied.
Remain read-only.

Check source and target drift, complete diff scope, traced artifacts and ADRs, native
contracts, current Approved Enterprise Standards guidance, target conventions, acceptance criteria,
security, data/migrations, observability, accessibility, failure behavior, tests and
rollback. Rerun required commands and return the reviewer's structured `PASS` or
`NEEDS-CHANGES` verdict. Never update evidence or status yourself.

Arguments from the user: $ARGUMENTS
