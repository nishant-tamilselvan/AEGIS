---
name: run-review-cycle
description: "Run a full self-correction review cycle over the artifact set."
agent: critic-reviewer
argument-hint: "[app-name] or leave blank to review every application"
---
Run a complete review.

1. If I named an application above, review `docs/artifacts/<app-name>/` and run
   `python -m artifact_tools validate docs/artifacts/<app-name> --strict`. If I did not,
   review every application with `python -m artifact_tools validate docs/artifacts --strict`.
2. Add your qualitative checks: coverage, traceability, contradictions, testability,
   scope creep, and blueprint fit.
3. Return your standard report (VALIDATION / BLOCKING / ADVISORY / VERDICT).

Do not edit any files. If the verdict is NEEDS-CHANGES, list precise fixes so
`artifact-manager` can resolve them.
