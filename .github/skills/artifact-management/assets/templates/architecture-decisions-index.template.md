# Architecture Decision Records (ADRs)

This index tracks every critical architectural decision for the platform. It is the
semantic-routing entry point: filter by **Status** to avoid stale decisions and by
**Component** to narrow a search before opening a record.

- **Status** values: `proposed`, `accepted`, `rejected`, `deprecated`, `superseded`.
- A `superseded` row must name its replacement in the **Consequences** column and set
  `superseded_by` in its own frontmatter.
- Records are immutable except for status transitions and back-links. Never renumber.

| ID | Title | Date | Status | Component | Consequences | File |
|------|-------|------|--------|-----------|--------------|------|
| ADR-0001 | Record architecture decisions | {{DATE}} | accepted | Governance | Establishes the Nygard/MADR template for all future decisions. | [0001-adr-template.md](0001-adr-template.md) |

## How to add a decision

```bash
python -m artifact_tools adr new "Event-driven topology" --status accepted --component "Core Topology"
# Supersede an earlier decision:
python -m artifact_tools adr new "Migrate catalogue to PostgreSQL" --supersedes ADR-0003
```

The tool auto-numbers the record, fills the template, and appends the row above.
