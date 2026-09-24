---
artifact: interface-specifications
title: "Interface & Integration Specifications Index — Todo List"
version: "1.0"
status: approved
last_updated: "2026-09-24"
phase: 2
owner: artifact-manager
---

# Interface & Integration Specifications Index — Todo List

> **This document is a routing index, not a contract dump.** It maps every interface to
> its native contract file under [`interfaces/`](interfaces/) (OpenAPI/AsyncAPI `.yaml`
> / `.json`, `.graphql`, `.proto`). Keep one contract per file so real specs stay
> parseable, diffs stay reviewable, and teams do not fight merge conflicts in one file.
>
> Interfaces use the `IF-` prefix, `exposes` a blueprint component (`BP-*`) and
> `implements` the functional requirements (`FR-*`) they realise. Proposed by
> `interface-integration-architect`, written by `artifact-manager`.

## 1. Synchronous APIs (REST / gRPC)

| ID | Service | Version | Protocol | Base Path | exposes | implements | Contract |
|------|---------|---------|----------|-----------|---------|------------|----------|
| IF-001 | Todo API | v1 | REST (JSON) | `/api/v1` | BP-002 | FR-002, FR-003, FR-004, FR-005, FR-006 | [`interfaces/synchronous/todo-api-v1.yaml`](interfaces/synchronous/todo-api-v1.yaml) |

Sign-in (FR-001) uses the identity provider's standard OpenID Connect endpoints
(BP-003). AEGIS does not own that contract, so it is not listed here.

## 2. Asynchronous Event Streams (Message Broker)

None. The MVP has no events or message broker.

## 3. Aggregation Layers (GraphQL)

None. The web app calls the Todo API directly.

## 4. Conventions

- **One contract per file.** Name files `<service>-<version>`. Never inline a full spec
  into this index.
- **Errors:** every error response uses RFC 9457 problem details
  (`application/problem+json`).
- **Versioning:** the major version is in the path (`/api/v1`). A breaking change needs a
  new major version.
- **Ownership:** a task that belongs to someone else returns `404`, never `403`, so the
  API does not reveal which task ids exist (NFR-002).
- **Correlation:** every request carries a W3C `traceparent` header, which becomes the
  log `correlation_id` (see the observability strategy).

## Changelog

<!-- artifact_tools changelog appends here -->
- 2026-09-24 — v0.1 — Initial scaffold (phase 2).
- 2026-09-24 — v1.0 — Approved at the end of architecture.
