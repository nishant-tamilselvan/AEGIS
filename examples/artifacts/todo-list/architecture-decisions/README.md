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
| ADR-0001 | Record architecture decisions | 2026-09-24 | accepted | Governance | Establishes the Nygard/MADR template for all future decisions. | [0001-adr-template.md](0001-adr-template.md) |
| ADR-0002 | Use managed PostgreSQL for task storage | 2026-09-24 | accepted | Data | Point-in-time recovery meets RPO/RTO; adds a fixed monthly cost. | [0002-use-managed-postgresql-for-task-storage.md](0002-use-managed-postgresql-for-task-storage.md) |
| ADR-0003 | Sign in with OIDC authorization code flow and PKCE | 2026-09-24 | accepted | Identity & Access | No passwords stored; sign-in depends on the identity provider. | [0003-sign-in-with-oidc-authorization-code-flow-and-pkce.md](0003-sign-in-with-oidc-authorization-code-flow-and-pkce.md) |

## How to add a decision

```bash
python -m artifact_tools adr new "Event-driven topology" --status accepted --component "Core Topology"
# Supersede an earlier decision:
python -m artifact_tools adr new "Migrate catalogue to PostgreSQL" --supersedes ADR-0003
```

The tool auto-numbers the record, fills the template, and appends the row above.
