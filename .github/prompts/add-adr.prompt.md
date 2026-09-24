---
# Generated from aegis/prompts/add-adr.md by scripts/sync_platforms.py. Edit the source, not this file.
description: "Record a significant architectural decision as an ADR."
agent: "ADR Author"
argument-hint: "[app-name] the decision, e.g. 'PostgreSQL over MongoDB'"
---
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
