---
artifact: observability-strategy
title: "{{TITLE}}"
version: "0.1"
status: draft
last_updated: "{{DATE}}"
phase: 2
owner: artifact-manager
---

# Observability Strategy — {{PROJECT_NAME}}

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
| `correlation_id` | `uuid` | propagated across services |
| `service` | `example-service` | emitting component |
| `environment` | `prod` | Dev/QA/Staging/Prod |

## 2. Metrics & Tracing

- **Metrics**: _the golden signals — latency, traffic, errors, saturation._
- **Distributed tracing**: _propagation format (W3C Trace Context), sampling._

## 3. Signal Catalogue

| ID | Signal | Type | Source (BP) | mitigates | Status |
|------|--------|------|-------------|-----------|--------|
| OBS-001 | _..._ | metric | BP-001 | NFR-001 | draft |

## 4. Key Performance Indicators (KPIs)

| KPI | Target | Alert threshold |
|-----|--------|-----------------|
| _p95 latency_ | _< 200 ms_ | _> 500 ms for 5 min_ |

## 5. Alerting & Runbook Baseline

_Alert routing, severities, on-call ownership, and the first-response runbook link._

## Changelog

<!-- artifact_tools changelog appends here -->
- {{DATE}} — v0.1 — Initial scaffold (phase 2).
