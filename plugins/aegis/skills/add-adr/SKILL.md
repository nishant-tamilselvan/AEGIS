---
# Generated from aegis/prompts/add-adr.md by scripts/sync_platforms.py. Edit the source, not this file.
name: add-adr
description: "Record a significant architectural decision as an ADR."
argument-hint: "[app-name] the decision, e.g. 'PostgreSQL over MongoDB'"
disable-model-invocation: true
---
## How to run this in Claude Code

Delegate this request to the `adr-author` subagent with the Agent tool. Pass it the
request below, the user's arguments and the application's `docs/artifacts/<app>` path.
If it needs a decision, ask the user with AskUserQuestion and send the answer back to it.
If its final message hands work to another agent, delegate that work to the named
subagent. Report the outcome to the user.
In a plugin install the subagents are listed with the `aegis:` prefix, for example `aegis:artifact-manager`.

## This request

Record an architecture decision.

1. Identify the target application's `docs/artifacts/<app-name>/` folder (from the app
   name above, or ask me if unclear). Restate the decision in one line and confirm it is
   architecturally significant (hard to reverse or under scrutiny). If it is trivial,
   tell me it does not need an ADR.
2. Gather context from `docs/artifacts/<app-name>/` — the driving `FR-*` / `NFR-*` / `BP-*` and the
   real alternatives that were considered.
3. Create the record with the tooling (auto-numbered, indexed):
   `python -m artifact_tools adr new "<title>" docs/artifacts/<app-name>/architecture-decisions --status <status> --component "<domain>"`.
   If this replaces an earlier decision, add `--supersedes ADR-000X`.
4. Fill Context, Decision Drivers, Considered Alternatives (pros/cons), Decision and
   Consequences, referencing the driving ids.
5. Validate with `python -m artifact_tools validate docs/artifacts/<app-name>` and report the ADR
   id, status, and the validation result.

Arguments from the user: $ARGUMENTS
