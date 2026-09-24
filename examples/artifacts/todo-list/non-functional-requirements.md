---
artifact: non-functional-requirements
title: "Non-Functional Requirements — Todo List"
version: "1.0"
status: approved
last_updated: "2026-09-24"
phase: 1
owner: artifact-manager
---

# Non-Functional Requirements — Todo List

> Quality attributes: performance, security, reliability, usability, maintainability,
> compliance. Each NFR is measurable. IDs use the `NFR-` prefix.

## Legend

- **Category**: `performance` | `security` | `reliability` | `usability` |
  `maintainability` | `scalability` | `compliance` | `observability`
- **Status**: `draft` | `in-review` | `approved` | `removed`

## Requirements

| ID | Category | Requirement (measurable) | Target | Status |
|------|----------|--------------------------|--------|--------|
| NFR-001 | performance | p95 API response time at 50 requests per second | < 300 ms | approved |
| NFR-002 | security | Only a task's owner can read, change or delete it | 0 cross-user access | approved |
| NFR-003 | security | All traffic is encrypted in transit, and stored data at rest | TLS 1.2+; AES-256 at rest | approved |
| NFR-004 | reliability | Monthly availability of the API | ≥ 99.5% | approved |
| NFR-005 | reliability | Data loss and recovery time after a failure | RPO 15 min; RTO 4 h | approved |
| NFR-006 | usability | Accessibility of the web app | WCAG 2.2 AA | approved |
| NFR-007 | observability | Every API request is logged with a correlation id, and error spikes raise an alert | 100% of requests; alert within 5 min | approved |
| NFR-008 | compliance | A deleted account's tasks are purged, including from backups | within 30 days | approved |

## Verification Approach

| ID | How it will be verified |
|------|-------------------------|
| NFR-001 | Load test at 50 requests per second in Staging before each release |
| NFR-002 | Automated tests that call every endpoint as a second user and expect 404 |
| NFR-003 | TLS scan of public endpoints; database encryption setting checked in infrastructure code review |
| NFR-004 | Uptime measured by an external probe every minute |
| NFR-005 | Quarterly restore drill from point-in-time recovery |
| NFR-006 | Automated accessibility checks in CI plus a manual keyboard and screen-reader pass per release |
| NFR-007 | Log sampling review and an alert fire drill in Staging |
| NFR-008 | Test that deletes an account and checks the purge job; backup retention set to 7 days |

## Changelog

<!-- artifact_tools changelog appends here -->
- 2026-09-24 — v0.1 — Initial scaffold (phase 1).
- 2026-09-24 — v1.0 — Approved at the end of ideation.
