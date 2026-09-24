---
artifact: user-journey-map
title: "{{TITLE}}"
version: "0.1"
status: draft
last_updated: "{{DATE}}"
phase: 1
owner: artifact-manager
---

# User Journey Map — {{PROJECT_NAME}}

> Personas and their end-to-end journeys. Journey steps use the `UJ-` prefix and are
> referenced by functional requirements via `traces_to`.

## Personas

| Persona | Description | Primary goal | Pain points |
|---------|-------------|--------------|-------------|
| _..._ | _..._ | _..._ | _..._ |

## Journey: {{PRIMARY_JOURNEY}}

```mermaid
journey
    title {{PRIMARY_JOURNEY}}
    section Discover
      Becomes aware: 3: Persona
    section Engage
      Takes first action: 4: Persona
    section Retain
      Returns / succeeds: 5: Persona
```

## Journey steps

| ID | Stage | User action | System response | Emotion | Opportunity |
|------|-------|-------------|-----------------|---------|-------------|
| UJ-001 | Discover | _..._ | _..._ | 🙂 | _..._ |
| UJ-002 | Engage | _..._ | _..._ | 😐 | _..._ |

## Changelog

<!-- artifact_tools changelog appends here -->
- {{DATE}} — v0.1 — Initial scaffold (phase 1).
