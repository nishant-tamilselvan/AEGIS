---
# Generated from aegis/skills/artifact-management/SKILL.md by scripts/sync_platforms.py. Edit the source, not this file.
name: artifact-management
description: 'Create, update, and validate the living artifact documents — the six business artifacts (product requirements, functional requirements, NFRs, user journey map, system blueprint, executive briefing) and the five technical artifacts (interface specifications, data/security/deployment/observability architecture). Use when scaffolding artifacts, adding or changing requirements or design, running consistency validation, or bumping document versions.'
argument-hint: 'e.g. "scaffold all artifacts" or "add functional requirement"'
---

# Artifact Management

Authoritative procedure for producing and maintaining the workflow's living artifacts:
six **business** artifacts (ideation phase) and five **technical** artifacts
(architecture phase). Only the `artifact-manager` agent should apply these edits; other
agents propose content. Architecture Decision Records are handled by the sibling
[`adr-management`](../adr-management/SKILL.md) skill.

Artifact Manager is also the sole writer of phase-3 state under
`docs/artifacts/<app>/implementation/`, but those documents use the separate
[`implementation-management`](../implementation-management/SKILL.md) procedure and CLI;
they are not additional business or technical artifact types.

## When to use

- Starting a new project (scaffold the full set from templates).
- A new requirement, persona, journey, or component was agreed during ideation.
- An existing requirement changed, was refined, or removed.
- After any artifact edit, to validate consistency before ending a phase.

## Ground rules

1. Never hand-write a document shape. Always start from the templates in
   [`./assets/templates/`](./assets/templates/).
2. Every application lives in its own folder: `docs/artifacts/<app-name>/`. All commands
   below target that per-application directory — never bare `docs/artifacts`. The active
   `<app-name>` is provided by the orchestrator at session start.
3. Requirement IDs are stable and never reused **within an application**. The same id may
   exist independently in another app. Follow
   [`./references/id-conventions.md`](./references/id-conventions.md).
4. Frontmatter must match [`./references/artifact-schema.md`](./references/artifact-schema.md).
5. After every change, run validation and resolve all errors before ending the phase.

## Procedure

### 1. Scaffold (first time only)

Replace `<app>` with the active application's folder (e.g. `docs/artifacts/customer-portal`).
If the application is brand new, also add a row for it in
[`docs/artifacts/README.md`](../../../docs/artifacts/README.md).

```bash
python -m artifact_tools scaffold product-requirements docs/artifacts/<app> --project "<Name>"
python -m artifact_tools scaffold functional-requirements docs/artifacts/<app> --project "<Name>"
python -m artifact_tools scaffold non-functional-requirements docs/artifacts/<app> --project "<Name>"
python -m artifact_tools scaffold user-journey-map docs/artifacts/<app> --project "<Name>"
python -m artifact_tools scaffold system-blueprint docs/artifacts/<app> --project "<Name>"
python -m artifact_tools scaffold executive-briefing docs/artifacts/<app> --project "<Name>"
```

Type aliases also work: `prd`, `fr`, `nfr`, `journey`, `blueprint`, `briefing`.

In the **architecture phase**, scaffold the technical artifacts the same way:

```bash
python -m artifact_tools scaffold interface-specifications docs/artifacts/<app> --project "<Name>"
python -m artifact_tools scaffold data-architecture docs/artifacts/<app> --project "<Name>"
python -m artifact_tools scaffold security-architecture docs/artifacts/<app> --project "<Name>"
python -m artifact_tools scaffold deployment-topology docs/artifacts/<app> --project "<Name>"
python -m artifact_tools scaffold observability-strategy docs/artifacts/<app> --project "<Name>"
```

Technical aliases: `interfaces`, `data`, `security`, `deployment`, `observability`.

Scaffolding `interface-specifications` also creates the `<app>/interfaces/`
contract store (`synchronous/`, `asynchronous/`, `graphql/`). That single-file document
is a **routing index** — record real API/event/schema contracts as native `.yaml` /
`.json` / `.graphql` / `.proto` files there, one contract per file, and link each from
the index. Re-create the store at any time with
`python -m artifact_tools interfaces init docs/artifacts/<app>`.

### 2. Edit content

- Add or modify rows in the relevant table(s), assigning the next sequential id.
- Fill cross-reference columns (`traces_to`, `satisfies`, `mitigates`) with existing ids.
- Keep each requirement atomic and testable.
- To retire an item, set its row `Status` to `removed`; do not delete the row.

### 3. Record the change and bump the version

```bash
python -m artifact_tools changelog docs/artifacts/<app>/functional-requirements.md "Added FR-014 for offline sync" --phase 3
```

This appends a changelog line and bumps `version` + `last_updated` in frontmatter.

### 4. Validate (always)

```bash
python -m artifact_tools validate docs/artifacts/<app>
```

- Exit code `0` = consistent. Non-zero = errors that must be fixed.
- Add `--strict` to also fail on advisory warnings (e.g. missing traceability).
- Validate every application at once with `python -m artifact_tools validate docs/artifacts`;
  each app is checked in isolation and findings are prefixed with the app folder name.

## What validation checks

- Frontmatter completeness and valid `status` / `version` / `last_updated` / `phase`.
- `artifact` field matches the file type.
- Ids are unique within a table and use the correct prefix for the document.
- Every cross-referenced id resolves to an id defined in some artifact.
- Every functional requirement traces to a `PR-*` or `UJ-*` (warning, or error in `--strict`).

## Multiple applications

A workspace can hold many applications, each in its own `docs/artifacts/<app-name>/`
folder with its own full artifact set, `architecture-decisions/`, and `interfaces/`.

- **Pick the app first.** Every command targets `docs/artifacts/<app-name>`. Never write
  artifacts to the bare `docs/artifacts` root — that folder only holds the applications
  index (`README.md`).
- **New application?** Choose a short kebab-case slug for the folder, scaffold into it,
  and add a row to [`docs/artifacts/README.md`](../../../docs/artifacts/README.md).
- **IDs are per application.** `FR-001` in one app is unrelated to `FR-001` in another.
  Cross-references only resolve within the same application's folder.

## Resources

- Templates: [`./assets/templates/`](./assets/templates/)
- Schema: [`./references/artifact-schema.md`](./references/artifact-schema.md)
- ID conventions: [`./references/id-conventions.md`](./references/id-conventions.md)
