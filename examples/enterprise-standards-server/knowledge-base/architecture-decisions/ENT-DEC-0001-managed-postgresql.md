---
id: ENT-DEC-0001
title: Use managed PostgreSQL for relational workloads
type: Architecture Decision Record (ADR)
status: Approved
domain: Data
classification: public
tags: [database, postgresql]
version: "1"
owner: Enterprise Architecture Board
summary: New relational workloads use the managed PostgreSQL service.
effective_date: 2024-09-01
last_reviewed: 2025-06-01
review_cycle_months: 12
relationships:
  depends_on: [ENT-STD-DAT-001]
---

# Use managed PostgreSQL for relational workloads

> Sample content. Replace this knowledge base with your organization's own standards.

## Decision

New applications that need a relational database use the managed PostgreSQL service.
Other engines need an exception approved by the Enterprise Architecture Board.

## Consequences

Teams get patching, backups and point-in-time recovery from the platform. Applications
must stay compatible with the supported PostgreSQL major versions.
