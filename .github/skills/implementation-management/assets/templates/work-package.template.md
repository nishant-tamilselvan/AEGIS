---
artifact: work-package
id: "{{ID_YAML}}"
title: "{{TITLE_YAML}}"
version: "0.1"
status: planned
last_updated: "{{DATE}}"
phase: 3
owner: "{{OWNER_YAML}}"
dependencies: []
source_ids: []
source_versions: {}
target_paths: []
parallel_group: null
approved_by: null
review_status: pending
evidence_count: 0
---
<!-- markdownlint-disable MD025 MD060 -->

# {{ID}} — {{TITLE}}

## Scope

{{SCOPE}}

## Acceptance Criteria

- [ ] Every traced requirement and control in this package is implemented or explicitly
      dispositioned with approval.
- [ ] Target-repository format, lint, typecheck, build, and test checks applicable to this
      package pass.
- [ ] Security, observability, migration, rollback, and accessibility obligations are
      satisfied where applicable.
- [ ] The independent implementation reviewer returns `PASS`.

## Constraints

- Edit only the target paths declared in frontmatter.
- Do not change requirements or architecture implicitly; pause and escalate material gaps.
- Do not expose secrets or perform a production deployment.

## Migration and Rollback

Document compatibility, migration ordering, rollback, and irreversible effects before the
package enters review. Use `Not applicable` only with a reason.

## Completion Evidence

| Date | Command or check | Outcome | Details |
|---|---|---|---|

## Status History

| Date | From | To | Actor | Note |
|---|---|---|---|---|
| {{DATE}} | — | planned | artifact-manager | Work package created. |
