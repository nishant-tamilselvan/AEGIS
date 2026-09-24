# Decisions and implementation traceability

## Tactical `IDEC-*`

Use for a reversible choice local to one work package, such as matching an existing file or
fixture naming convention. It must not alter behavior, interfaces, controls, topology or
material risk. Record the evidence and affected paths.

## Material ADR

Escalate when a choice changes an approved requirement or contract; data classification,
retention or ownership; identity/security/privacy; component or deployment topology;
operational risk; multiple packages; or is expensive to reverse. Pause code, query the
Enterprise Standards, present real alternatives, obtain approval, record/supersede an ADR, update source
artifacts and refresh package versions.

## Coverage

Every active `FR-*`, `NFR-*`, `BP-*`, `IF-*`, `DM-*`, `SEC-*`, `DEP-*`, `OBS-*` and
accepted `ADR-*` must appear in at least one work package or an approved deferred/not
applicable disposition. A code comment alone is not traceability. Completion evidence must
name reproducible commands/checks and actual outcomes; never record secrets or fabricated
results.
