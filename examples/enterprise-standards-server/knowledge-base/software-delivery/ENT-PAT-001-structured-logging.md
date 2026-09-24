---
id: ENT-PAT-001
title: Structured Logging and Tracing
type: Pattern
status: Approved
domain: Software Delivery
classification: public
tags: [observability, logging, tracing]
version: "1"
owner: Platform Engineering
summary: JSON log format, required fields and OpenTelemetry tracing for services.
effective_date: 2026-03-01
last_reviewed: 2026-03-01
review_cycle_months: 12
---

# Structured Logging and Tracing

> Sample content. Replace this knowledge base with your organization's own standards.

Services write one JSON object per log line with these fields: `timestamp` (UTC, ISO 8601),
`level`, `service`, `environment`, `trace_id`, `span_id` and `message`. Services export
traces and the four golden signals (latency, traffic, errors, saturation) through
OpenTelemetry.
