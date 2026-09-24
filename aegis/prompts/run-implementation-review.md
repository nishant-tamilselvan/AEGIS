---
name: run-implementation-review
description: "Run the independent implementation package or final release review with strict traceability and actual verification evidence."
agent: implementation-reviewer
argument-hint: "[app-name] [WP-NNNN or release]"
---
Review the requested active work package, or the final release when `release` is supplied.
Remain read-only.

Check source and target drift, complete diff scope, traced artifacts and ADRs, native
contracts, current Approved Enterprise Standards guidance, target conventions, acceptance criteria,
security, data/migrations, observability, accessibility, failure behavior, tests and
rollback. Rerun required commands and return the reviewer's structured `PASS` or
`NEEDS-CHANGES` verdict. Never update evidence or status yourself.
