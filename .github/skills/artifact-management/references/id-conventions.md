# ID Conventions

Stable identifiers make cross-references and traceability reliable across every
ideation cycle. IDs are **never reused or renumbered**. When an item is removed,
mark it `status: removed` in place rather than deleting the row, so historical
references remain resolvable.

IDs are scoped **per application**. Each `docs/artifacts/<app-name>/` folder has its own
independent id space — `FR-001` in one application is unrelated to `FR-001` in another,
and cross-references only resolve within the same application's folder.

## Prefixes

| Prefix | Artifact | Example |
| -------- | ---------- | --------- |
| `PR-` | Product requirement / goal | `PR-001` |
| `FR-` | Functional requirement | `FR-014` |
| `NFR-` | Non-functional requirement | `NFR-007` |
| `UJ-` | User journey / step | `UJ-003` |
| `BP-` | Blueprint component / flow | `BP-005` |
| `RISK-` | Risk (executive briefing) | `RISK-002` |
| `IF-` | Interface / contract | `IF-004` |
| `DM-` | Data entity / model | `DM-006` |
| `SEC-` | Security control | `SEC-002` |
| `DEP-` | Deployment node | `DEP-003` |
| `OBS-` | Observability signal | `OBS-005` |
| `ADR-` | Architecture decision record | `ADR-0004` |
| `WP-` | Phase-3 implementation work package | `WP-0004` |
| `IDEC-` | Phase-3 tactical implementation decision | `IDEC-0004` |

`PR-` through `RISK-` are produced in the **ideation phase**; `IF-`, `DM-`, `SEC-`,
`DEP-`, `OBS-` and `ADR-` in the **architecture phase**.
`WP-` and `IDEC-` are produced in the **implementation phase** and live only under the
application's `implementation/` folder.

## Format

`<PREFIX>-<zero-padded 3+ digit number>`

- Numbers are assigned sequentially per prefix, starting at `001`.
- Zero-pad to at least 3 digits (`001`, `042`, `1234`).
- No gaps required, but never reuse a retired number.
- ADRs are the exception: they zero-pad to **four** digits (`ADR-0001`) to match their
  filename (`0001-title.md`).
- Work packages and implementation decisions also use four digits (`WP-0001`,
  `IDEC-0001`) and are append-only within one application.

## Cross-reference fields

| Field | Meaning | Points to |
| ------- | --------- | ----------- |
| `traces_to` | Why a functional req exists | `PR-*`, `UJ-*` |
| `satisfies` | What a component implements | `FR-*` |
| `implements` | What an interface / entity realises | `FR-*` |
| `exposes` | Which component an interface fronts | `BP-*` |
| `mitigates` | What a control / node / NFR addresses | `RISK-*`, `NFR-*` |
| `supersedes` | Which decision an ADR replaces | `ADR-*` |
| `depends_on` | Ordering / prerequisite | any id |

Multiple ids are comma-separated: `traces_to: PR-001, UJ-003`.
