# Implementation readiness gates

Readiness is read-only and blocks before state creation or target edits when any of these
conditions exists:

1. One of the eleven required artifacts is missing, invalid or not `approved`.
2. Strict artifact/ADR validation fails.
3. An explicit Open Decisions table marks a `D-*` item as blocking implementation.
4. Approved artifacts retain `TBD`/`TO BE DECIDED` content.
5. Active `IF-*` entries have no native OpenAPI/AsyncAPI/GraphQL/protobuf/JSON contract.
6. Architecture decisions are missing, proposed, invalid or superseded while still relied on.
7. Current Approved enterprise implementation patterns and Software Delivery standards have not
   been verified for supersession and review health.
8. The target workspace is missing or has no discoverable instructions/build conventions.
9. Existing implementation state has dependency, path, traceability, evidence or drift
   errors.

A blocker is never converted into generated code. Route it to the owning phase, obtain HITL,
update and validate source artifacts, then re-run readiness.
