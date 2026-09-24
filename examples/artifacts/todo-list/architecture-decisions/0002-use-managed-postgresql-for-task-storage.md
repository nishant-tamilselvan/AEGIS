---
id: ADR-0002
title: Use managed PostgreSQL for task storage
status: accepted
date: '2026-09-24'
component: Data
supersedes: ''
superseded_by: —
deciders: architecture-orchestrator, data-architect
---
# ADR-0002: Use managed PostgreSQL for task storage

- **Status:** accepted
- **Date:** 2026-09-24
- **Component/Domain:** Data
- **Deciders:** architecture-orchestrator, data-architect
- **Supersedes:** —
- **Superseded by:** —

## Context

The Todo API (BP-002) must store each user's tasks (DM-001, DM-002) without losing them
(PR-002), recover within 4 hours with at most 15 minutes of lost writes (NFR-005), and be
run by a two-person team (PR-003).

## Decision Drivers

- Recovery targets from NFR-005 without building our own backup tooling.
- A small, relational data model: users own tasks.
- Little operational work for a two-person team.

## Considered Alternatives

1. **Managed PostgreSQL** — relational, point-in-time recovery and encryption at rest
   included; costs a small monthly fee.
2. **Managed document database** — flexible schema, but the data is relational and
   owner-scoped queries are simpler in SQL.
3. **SQLite on a mounted volume** — cheapest, but no managed recovery, and only one API
   instance could write to it, which conflicts with NFR-004.

## Decision

Use the cloud provider's managed PostgreSQL service with point-in-time recovery, in the
same region as the API (DEP-003).

## Consequences

### Positive

- Meets RPO 15 minutes and RTO 4 hours with built-in point-in-time recovery (NFR-005).
- Encryption at rest is on by default (NFR-003).
- Owner scoping is a simple indexed `WHERE owner_id = ...` query (NFR-001).

### Negative / Trade-offs

- Adds a fixed monthly cost even when there are few users.
- Ties the deployment to one provider's database service, although PostgreSQL itself is
  portable.

## Links

- System blueprint: BP-004. Data architecture: DM-001, DM-002.
