---
artifact: observability-strategy
title: "Observability Strategy — Todo List"
version: "1.0"
status: approved
last_updated: "2026-09-24"
phase: 2
owner: artifact-manager
---

# Observability Strategy — Todo List

> How the system is instrumented for production support from day one. Signals use the
> `OBS-` prefix and `mitigates` the observability/reliability non-functional
> requirements (`NFR-*`) they support. Proposed by `interface-integration-architect`,
> written by `artifact-manager`.

## Legend

- **Signal**: `log` | `metric` | `trace` | `alert`
- **Status**: `draft` | `in-review` | `approved` | `removed`

## 1. Logging Standards

Structured JSON logs with these mandatory fields on every entry:

| Field | Example | Notes |
|-------|---------|-------|
| `timestamp` | `2026-01-01T00:00:00Z` | ISO 8601, UTC |
| `level` | `INFO` | `DEBUG`/`INFO`/`WARN`/`ERROR` |
| `correlation_id` | `uuid` | From the W3C `traceparent` header |
| `service` | `todo-api` | Emitting component |
| `environment` | `prod` | Dev/Staging/Prod |
| `route` | `PATCH /tasks/{taskId}` | Route template, never the raw URL |
| `status` | `200` | HTTP status |
| `duration_ms` | `42` | Request duration |

Task titles and access tokens are never logged (SEC-005).

## 2. Metrics & Tracing

- **Metrics**: the four golden signals for the Todo API: latency, traffic, errors and
  saturation.
- **Distributed tracing**: W3C Trace Context from the web app through the API to the
  database, with 10% sampling and every error kept.

## 3. Signal Catalogue

| ID | Signal | Type | Source (BP) | mitigates | Status |
|------|--------|------|-------------|-----------|--------|
| OBS-001 | Request latency histogram per route | metric | BP-002 | NFR-001 | approved |
| OBS-002 | Error rate (5xx share of requests) | metric | BP-002 | NFR-004 | approved |
| OBS-003 | Structured request log | log | BP-002 | NFR-007 | approved |
| OBS-004 | End-to-end trace, web app to database | trace | BP-001 | NFR-007 | approved |
| OBS-005 | Error rate above 2% for 5 minutes | alert | BP-002 | NFR-004, NFR-007 | approved |

## 4. Key Performance Indicators (KPIs)

| KPI | Target | Alert threshold |
|-----|--------|-----------------|
| p95 API latency | < 300 ms | > 600 ms for 10 min |
| Error rate | < 0.5% | > 2% for 5 min |
| Monthly availability | ≥ 99.5% | Below 99.7% by mid-month |

## 5. Alerting & Runbook Baseline

- **Routing**: alerts go to the team's on-call channel; there is one on-call engineer
  per week.
- **Severities**: `page` for OBS-005 and availability risk; `ticket` for latency alerts.
- **First response**: check recent deploys, roll back the last image if errors began
  after it, then check database health.

## Changelog

<!-- artifact_tools changelog appends here -->
- 2026-09-24 — v0.1 — Initial scaffold (phase 2).
- 2026-09-24 — v1.0 — Approved at the end of architecture.
