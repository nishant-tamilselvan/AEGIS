# Phase-3 implementation schema

All files live under `docs/artifacts/<app>/implementation/` and are authored only by
Artifact Manager through deterministic tooling.

## `implementation.md`

Required frontmatter: `artifact: implementation`, title, semantic `version`, status,
`last_updated`, `phase: 3`, owner, absolute `target_workspace`, target branch/baseline,
`standards_review`, active/next work package, release approval and source versions.
It is the canonical pointer, not a narrative plan.

## `decision.md`

Frontmatter uses `artifact: implementation-decisions`, `status: living`, and phase 3.
Rows use stable `IDEC-NNNN` ids and contain date, status, type, work package, question,
choice, rationale, sources, affected paths, approver and optional ADR. Records are
append-only; superseded rows remain present.

## Work packages

Files are `work-packages/WP-NNNN-<slug>.md`. Required frontmatter includes id/title,
version/status/date/phase/owner, dependencies, source ids and versions, target paths,
parallel group, approval, review status and evidence count.

Target paths are repository-relative, contain no `..`, and are immutable after approval
unless the package returns to planning. Dependencies must exist and be acyclic. Completed
packages require reviewer PASS and evidence. Multiple active packages require one shared
parallel group and pairwise disjoint target paths.
