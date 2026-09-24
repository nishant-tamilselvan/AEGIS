---
artifact: interface-specifications
title: "{{TITLE}}"
version: "0.1"
status: draft
last_updated: "{{DATE}}"
phase: 2
owner: artifact-manager
---

# Interface & Integration Specifications Index — {{PROJECT_NAME}}

> **This document is a routing index, not a contract dump.** It maps every interface to
> its native contract file under [`interfaces/`](interfaces/) (OpenAPI/AsyncAPI `.yaml`
> / `.json`, `.graphql`, `.proto`). Keep one contract per file so real specs stay
> parseable, diffs stay reviewable, and teams do not fight merge conflicts in one file.
>
> Interfaces use the `IF-` prefix, `exposes` a blueprint component (`BP-*`) and
> `implements` the functional requirements (`FR-*`) they realise. Proposed by
> `interface-integration-architect`, written by `artifact-manager`. Run
> `python -m artifact_tools interfaces init docs/artifacts/<app>` to create the contract store.

## 1. Synchronous APIs (REST / gRPC)

| ID | Service | Version | Protocol | Base Path | exposes | implements | Contract |
|------|---------|---------|----------|-----------|---------|------------|----------|
| IF-001 | _Identity & Auth_ | v1 | REST (JSON) | `/api/v1/auth` | BP-001 | FR-001 | [`interfaces/synchronous/identity-auth-v1.yaml`](interfaces/synchronous/identity-auth-v1.yaml) |

## 2. Asynchronous Event Streams (Message Broker)

| ID | Event Domain | Broker | Topic / Queue | Pattern | exposes | implements | Schema |
|------|--------------|--------|---------------|---------|---------|------------|--------|
| IF-002 | _Order Processing_ | Kafka | `enterprise.orders.v1` | Pub/Sub | BP-001 | FR-001 | [`interfaces/asynchronous/order-events-kafka.yaml`](interfaces/asynchronous/order-events-kafka.yaml) |

## 3. Aggregation Layers (GraphQL)

| ID | Gateway | Type | Auth | exposes | implements | Schema |
|------|---------|------|------|---------|------------|--------|
| IF-003 | _Frontend BFF_ | GraphQL | JWT | BP-001 | FR-001 | [`interfaces/graphql/gateway-schema.graphql`](interfaces/graphql/gateway-schema.graphql) |

## 4. Conventions

- **One contract per file.** Name files `<service>-<version>` (sync) or
  `<domain>-<broker>` (async). Never inline a full spec into this index.
- **Error & versioning**: the standard error envelope and versioning policy live in the
  contract files; note breaking-change rules here only if they are cross-cutting.
- **Correlation**: every async payload carries a `correlation_id` (see the observability
  strategy).

## Changelog

<!-- artifact_tools changelog appends here -->
- {{DATE}} — v0.1 — Initial scaffold (phase 2).
