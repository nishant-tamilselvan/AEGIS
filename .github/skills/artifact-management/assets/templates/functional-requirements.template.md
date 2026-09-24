---
artifact: functional-requirements
title: "{{TITLE}}"
version: "0.1"
status: draft
last_updated: "{{DATE}}"
phase: 1
owner: artifact-manager
---

# Functional Requirements — {{PROJECT_NAME}}

> What the system must do. Each requirement is atomic, testable, and traces back to
> a product goal (`PR-*`) or a user journey (`UJ-*`). IDs use the `FR-` prefix.

## Legend

- **Priority**: `must` | `should` | `could` | `wont`
- **Status**: `draft` | `in-review` | `approved` | `removed`
- **traces_to**: comma-separated `PR-*` / `UJ-*` ids that justify this requirement.

## Requirements

| ID | Requirement | Priority | traces_to | Status |
|------|-------------|----------|-----------|--------|
| FR-001 | The system shall _..._ | must | PR-001 | draft |

## Acceptance Criteria

### FR-001
- Given _..._, when _..._, then _..._.

## Changelog

<!-- artifact_tools changelog appends here -->
- {{DATE}} — v0.1 — Initial scaffold (phase 1).
