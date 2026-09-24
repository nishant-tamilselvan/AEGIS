---
artifact: product-requirements
title: "Product Requirements — Todo List"
version: "1.0"
status: approved
last_updated: "2026-09-24"
phase: 1
owner: artifact-manager
---

# Product Requirements — Todo List

> Vision, scope, goals, and constraints. This is the "why" and the boundaries.
> Maintained by `artifact-manager`. Requirement IDs use the `PR-` prefix and are
> never reused.

## 1. Vision

Anyone can keep a short, private list of the things they need to do, and reach it from
any browser in seconds.

## 2. Problem Statement

People track small tasks on sticky notes, in chat messages to themselves and in heavy
project tools. Notes get lost, chat threads bury tasks, and project tools take too long
to open for a two-word reminder. They want one private list that opens fast and never
loses anything.

## 3. Goals & Success Metrics

| ID | Goal | Success metric | Status |
|------|------|----------------|--------|
| PR-001 | Capturing a task is effortless | Median time from opening the app to a saved task is under 5 seconds | approved |
| PR-002 | Users can trust the list | Zero lost or leaked tasks per quarter | approved |

## 4. Scope

### In scope

- A personal task list for one signed-in user.
- Add, rename, complete, reopen and delete tasks.
- Sign-in through an existing identity provider.

### Out of scope (for now)

- Sharing lists or tasks with other people.
- Due dates, reminders and notifications.
- Native mobile apps and offline use.

## 5. Constraints & Assumptions

| ID | Constraint / Assumption | Type | Status |
|------|-------------------------|------|--------|
| PR-003 | A two-person team builds and runs it, so it uses managed cloud services in a single region | constraint | approved |
| PR-004 | Users already have an account with an OpenID Connect identity provider | assumption | approved |

## 6. Stakeholders

| Stakeholder | Interest | Priority |
|-------------|----------|----------|
| End users | A fast, private list that never loses tasks | high |
| Product owner | Adoption and a small, predictable scope | high |
| Operations | Few moving parts and simple recovery | medium |

## Changelog

<!-- artifact_tools changelog appends here -->
- 2026-09-24 — v0.1 — Initial scaffold (phase 1).
- 2026-09-24 — v1.0 — Approved at the end of ideation.
