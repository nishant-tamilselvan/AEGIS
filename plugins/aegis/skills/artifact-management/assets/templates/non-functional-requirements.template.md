---
artifact: non-functional-requirements
title: "{{TITLE}}"
version: "0.1"
status: draft
last_updated: "{{DATE}}"
phase: 1
owner: artifact-manager
---

# Non-Functional Requirements — {{PROJECT_NAME}}

> Quality attributes: performance, security, reliability, usability, maintainability,
> compliance. Each NFR is measurable. IDs use the `NFR-` prefix.

## Legend

- **Category**: `performance` | `security` | `reliability` | `usability` |
  `maintainability` | `scalability` | `compliance` | `observability`
- **Status**: `draft` | `in-review` | `approved` | `removed`

## Requirements

| ID | Category | Requirement (measurable) | Target | Status |
|------|----------|--------------------------|--------|--------|
| NFR-001 | performance | _p95 response time_ | _< 200 ms_ | draft |
| NFR-002 | security | _..._ | _..._ | draft |

## Verification Approach

| ID | How it will be verified |
|------|-------------------------|
| NFR-001 | _load test / benchmark / ..._ |

## Changelog

<!-- artifact_tools changelog appends here -->
- {{DATE}} — v0.1 — Initial scaffold (phase 1).
