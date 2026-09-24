---
id: ADR-0003
title: Sign in with OIDC authorization code flow and PKCE
status: accepted
date: '2026-09-24'
component: Identity & Access
supersedes: ''
superseded_by: —
deciders: architecture-orchestrator, security-architect
---
# ADR-0003: Sign in with OIDC authorization code flow and PKCE

- **Status:** accepted
- **Date:** 2026-09-24
- **Component/Domain:** Identity & Access
- **Deciders:** architecture-orchestrator, security-architect
- **Supersedes:** —
- **Superseded by:** —

## Context

Users must sign in (FR-001) with an account they already have (PR-004), and only a
task's owner may see or change it (NFR-002). The web app (BP-001) runs entirely in the
browser, so it cannot keep a client secret.

## Decision Drivers

- No passwords stored by the Todo List.
- A flow that is safe for a browser-only app without a client secret.
- A stable user id for owner checks.

## Considered Alternatives

1. **OIDC authorization code flow with PKCE** — the current recommendation for browser
   apps; no client secret needed; the token's subject is a stable user id.
2. **OIDC implicit flow** — deprecated; tokens are exposed in the URL.
3. **Own username and password store** — full control, but we would store and protect
   passwords, add reset flows and take on more risk.

## Decision

The web app signs users in with the OIDC authorization code flow and PKCE. The Todo API
validates each access token (SEC-001) and uses its subject claim as the owner id (SEC-002).

## Consequences

### Positive

- No password storage or reset flows to build.
- A stable subject id makes owner-only access simple to enforce.

### Negative / Trade-offs

- Sign-in depends on the identity provider being available.
- Each deployment must register the web app with its identity provider.

## Links

- Security architecture: SEC-001, SEC-002. System blueprint: BP-003.
