---
id: ENT-STD-API-001
title: REST API Design
type: Standard
status: Approved
domain: Integration
classification: public
tags: [api, rest, openapi]
version: "1"
part_of_family: API Standards
owner: Integration Architecture
summary: Contract, versioning and error conventions for REST APIs.
effective_date: 2026-01-10
last_reviewed: 2026-01-10
review_cycle_months: 12
relationships:
  related_to: [ENT-PAT-001]
---

# REST API Design

> Sample content. Replace this knowledge base with your organization's own standards.

1. Every API publishes an OpenAPI 3.1 contract before implementation starts.
2. Versions appear in the path (`/v1/...`). A breaking change requires a new major version.
3. Errors use RFC 9457 problem details (`application/problem+json`).
4. Collections support cursor pagination with `limit` and `cursor` parameters.
5. Every request carries or receives a correlation id (`traceparent` header).
