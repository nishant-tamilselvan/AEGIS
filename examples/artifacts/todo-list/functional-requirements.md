---
artifact: functional-requirements
title: "Functional Requirements — Todo List"
version: "1.0"
status: approved
last_updated: "2026-09-24"
phase: 1
owner: artifact-manager
---

# Functional Requirements — Todo List

> What the system must do. Each requirement is atomic, testable, and traces back to
> a product goal (`PR-*`) or a user journey (`UJ-*`). IDs use the `FR-` prefix.

## Legend

- **Priority**: `must` | `should` | `could` | `wont`
- **Status**: `draft` | `in-review` | `approved` | `removed`
- **traces_to**: comma-separated `PR-*` / `UJ-*` ids that justify this requirement.

## Requirements

| ID | Requirement | Priority | traces_to | Status |
|------|-------------|----------|-----------|--------|
| FR-001 | The system shall let a user sign in with their existing OpenID Connect identity provider | must | UJ-001, PR-004 | approved |
| FR-002 | The system shall show a signed-in user only their own tasks, open tasks first, newest first | must | UJ-001, PR-002 | approved |
| FR-003 | The system shall let a user add a task with a title of 1 to 200 characters | must | UJ-002, PR-001 | approved |
| FR-004 | The system shall let a user rename one of their tasks | should | UJ-002 | approved |
| FR-005 | The system shall let a user mark one of their tasks as done, and reopen it | must | UJ-003 | approved |
| FR-006 | The system shall let a user delete one of their tasks, with undo for 5 seconds | must | UJ-004, PR-002 | approved |

## Acceptance Criteria

### FR-001

- Given a user who is not signed in, when they open the app, then they are sent to the identity provider and return signed in.

### FR-002

- Given two users with tasks, when either one lists tasks, then they see only their own.
- Given open and done tasks, when the list loads, then open tasks appear above done tasks.

### FR-003

- Given a signed-in user, when they submit a title of 1 to 200 characters, then the task is saved and appears at the top.
- Given an empty title or one over 200 characters, when they submit it, then nothing is saved and they see why.

### FR-004

- Given one of the user's tasks, when they change its title to a valid one, then the new title is saved.

### FR-005

- Given an open task, when the user ticks it, then it is marked done; ticking it again reopens it.

### FR-006

- Given a task, when the user deletes it, then it disappears and can be restored for 5 seconds; after that it is removed.

## Changelog

<!-- artifact_tools changelog appends here -->
- 2026-09-24 — v0.1 — Initial scaffold (phase 1).
- 2026-09-24 — v1.0 — Approved at the end of ideation.
