# Artifact Frontmatter Schema

Every artifact document begins with a YAML frontmatter block delimited by `---`.
The `artifact_tools validate` command enforces this schema. Keep it exact.

## Common fields (all artifacts)

| Field | Type | Required | Notes |
| ------- | ------ | ---------- | ------- |
| `artifact` | string | yes | Stable machine id of the document. One of: `product-requirements`, `functional-requirements`, `non-functional-requirements`, `user-journey-map`, `system-blueprint`, `executive-briefing`, `interface-specifications`, `data-architecture`, `security-architecture`, `deployment-topology`, `observability-strategy`. |
| `title` | string | yes | Human-readable title. |
| `version` | string | yes | Semantic-ish `MAJOR.MINOR` string, e.g. `0.3`. Bump on every update. |
| `status` | enum | yes | One of: `draft`, `in-review`, `approved`, `superseded`. |
| `last_updated` | date | yes | ISO `YYYY-MM-DD`. |
| `phase` | integer | yes | Workflow phase this revision corresponds to (ideation = 1, architecture = 2). |
| `owner` | string | yes | Agent or person responsible. Default `artifact-manager`. |

Phase-3 pointer, decision-ledger and work-package files are nested under
`implementation/` and intentionally do not extend this eleven-artifact enum. Their schema
is defined by
[`implementation-management/references/implementation-schema.md`](../../implementation-management/references/implementation-schema.md)
and validated by `artifact_tools implementation validate` plus the integrated app validator.

## Body item frontmatter (requirement / journey / component tables)

Items inside `functional-requirements`, `non-functional-requirements`,
`user-journey-map`, and `system-blueprint` are tracked in Markdown tables. Each row
carries a stable `id`. Cross-references between artifacts use these ids.

- Functional requirements reference journeys and product goals:
  `FR-012` may list `traces_to: UJ-003, PR-002`.
- System blueprint components reference the functional requirements they satisfy:
  `BP-004` may list `satisfies: FR-012, FR-013`.

## Validation rules (summary)

1. Frontmatter parses as YAML and contains all required common fields with valid values.
2. `artifact` matches the file's expected type.
3. All ids within a document are unique and match their prefix
   (see [id-conventions](./id-conventions.md)).
4. Every cross-reference (`traces_to`, `satisfies`, `implements`, `exposes`,
   `mitigates`, ...) points to an id that exists in some artifact (including `ADR-*`).
5. Traceability: every `FR-*` should trace to at least one `PR-*` or `UJ-*`
   (advisory warning, not a hard failure unless `--strict`).
6. `status: approved` documents must not reference `draft`-only ids that were removed.

## ADR records

Architecture Decision Records live in each application's
`docs/artifacts/<app-name>/architecture-decisions/` folder as
individual files (`NNNN-title.md`) plus a `README.md` index. They use their own
frontmatter (not the common artifact schema):

| Field | Type | Required | Notes |
| ------- | ------ | ---------- | ------- |
| `id` | string | yes | `ADR-NNNN`, four-digit, matching the filename number. |
| `title` | string | yes | Human-readable decision title. |
| `status` | enum | yes | One of: `proposed`, `accepted`, `rejected`, `deprecated`, `superseded`. |
| `date` | date | yes | ISO `YYYY-MM-DD`. |
| `component` | string | yes | Component/domain tag for semantic routing. |
| `supersedes` | string | yes | `ADR-*` this record replaces, or empty. |
| `superseded_by` | string | yes | `ADR-*` that replaced this record, or empty. |
| `deciders` | string | yes | Who made the decision. |

ADR validation additionally checks: `id` matches the filename, ids are unique, a
`superseded` record names its `superseded_by`, `supersedes`/`superseded_by` resolve to
real ADRs, and every record has a row in the index.
