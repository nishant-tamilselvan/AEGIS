---
# Generated from aegis/prompts/add-requirement.md by scripts/sync_platforms.py. Edit the source, not this file.
description: "Add or change a requirement and propagate it consistently across artifacts."
agent: "Ideation Orchestrator"
argument-hint: "[app-name] the requirement or change to make"
---
A requirement has changed. Handle it as a small ideation cycle:

1. Identify the target application's `docs/artifacts/<app-name>/` folder (from the
   app name above, or ask me if unclear). Restate the requirement/change in one line and
   confirm it with me if it is ambiguous.
2. Delegate to `artifact-manager` to update the affected artifacts in that app folder:
   - assign a new stable id (or update the existing one),
   - fill cross-references (`traces_to` / `satisfies` / `mitigates`),
   - bump the document version via `artifact_tools changelog`.
3. If architecture is affected, delegate to `architecture` first for a proposal.
4. Delegate to `critic-reviewer` and loop until validation passes.
5. Report which ids and files changed, plus the new versions.
