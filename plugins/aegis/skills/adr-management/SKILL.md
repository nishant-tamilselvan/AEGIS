---
# Generated from aegis/skills/adr-management/SKILL.md by scripts/sync_platforms.py. Edit the source, not this file.
name: adr-management
description: 'Create, index and validate Architecture Decision Records (ADRs) in each application''s docs/artifacts/<app-name>/architecture-decisions/ folder. Use when recording a significant architecture or implementation-discovered material choice, superseding an earlier decision, or validating the ADR index.'
argument-hint: 'e.g. "record decision: PostgreSQL over MongoDB" or "supersede ADR-0003"'
---

# ADR Management

Authoritative procedure for recording architectural decisions. Only the `adr-author`
agent should run these commands; specialists propose the decision and its alternatives.

## When to use

- A specialist chose between real alternatives for a hard-to-reverse concern.
- An earlier decision is being replaced (supersede it — never edit it in place).
- Validating the ADR folder and index before closing the architecture phase.
- Implementation discovers a hard-to-reverse, cross-component, security/risk, contract or
   scope choice that cannot remain a tactical `IDEC-*` record.

## Ground rules

1. One decision per record. Records are immutable except status transitions and
   back-links. Never renumber or delete.
2. IDs are `ADR-NNNN` (zero-padded four digits) and match the file number. `ADR-0001`
   is the seed "record architecture decisions" template. Numbering is **per application**.
3. ADRs live in the active application's folder: `docs/artifacts/<app-name>/architecture-decisions/`.
   The `<app-name>` is provided by the orchestrator. Never target the bare `docs/artifacts` root.
4. Frontmatter follows [`../artifact-management/references/artifact-schema.md`](../artifact-management/references/artifact-schema.md#adr-records).
5. After any change, validate and resolve all errors before ending the phase.

## Procedure

### 1. Initialise (first time only)

Replace `<app>` with the active application folder (e.g. `customer-portal`).

```bash
python -m artifact_tools adr init docs/artifacts/<app>/architecture-decisions
```

Creates the folder, the `README.md` index, and the seed `0001-adr-template.md`.
`adr new` also initialises the folder automatically if it is missing.

### 2. Record a decision

```bash
python -m artifact_tools adr new "Event-driven topology" docs/artifacts/<app>/architecture-decisions \
  --status accepted --component "Core Topology"
```

The tool auto-numbers the record, fills the Nygard/MADR template, and appends the row
to the index. Then edit the record to complete Context, Decision Drivers, Considered
Alternatives, Decision and Consequences, referencing the driving `FR-*` / `NFR-*` / `BP-*`.

### 3. Supersede an earlier decision

```bash
python -m artifact_tools adr new "Migrate catalogue to PostgreSQL" docs/artifacts/<app>/architecture-decisions --supersedes ADR-0003
```

This creates the new record, flips `ADR-0003` to `superseded`, sets its `superseded_by`
back-link, and updates the index status.

### 4. Validate (always)

```bash
python -m artifact_tools validate docs/artifacts/<app>
```

ADR validation runs as part of the artifact validation.

## What validation checks

- Each record's frontmatter is present and its `id` matches the filename number.
- `status` is one of `proposed`, `accepted`, `rejected`, `deprecated`, `superseded`.
- `superseded` records name a `superseded_by` id, and `supersedes` / `superseded_by`
  point to real ADRs.
- Every record has a row in the index, and ids are unique.

## Resources

- Templates: [`../artifact-management/assets/templates/adr.template.md`](../artifact-management/assets/templates/adr.template.md),
  [`../artifact-management/assets/templates/architecture-decisions-index.template.md`](../artifact-management/assets/templates/architecture-decisions-index.template.md)
- Schema: [`../artifact-management/references/artifact-schema.md`](../artifact-management/references/artifact-schema.md)
- ID conventions: [`../artifact-management/references/id-conventions.md`](../artifact-management/references/id-conventions.md)
