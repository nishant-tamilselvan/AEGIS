---
name: start-ideation
description: "Kick off a new product ideation session from a raw idea."
agent: ideation-orchestrator
argument-hint: "[app-name] your one-line idea"
---
Begin a new ideation session.

First establish which application this is for. If I named an app above (or one is
obvious from the idea), use it as the `docs/artifacts/<app-name>/` folder; otherwise
propose a short kebab-case slug and confirm it with me. If it is a new application, have
`artifact-manager` create the folder and add a row to the `docs/artifacts/README.md` index.

If I provided an idea above, start at the **Spark** phase: reflect it back in one
sentence and confirm it with me. If I did not, ask me for my idea in one sentence.

Then proceed **one phase at a time**, following your phased process. After each phase:

- delegate artifact work to `artifact-manager`,
- delegate a consistency pass to `critic-reviewer`,
- give me a 2–3 line recap and ask before continuing.

Do not overwhelm me. Keep it to a few focused questions per turn.
