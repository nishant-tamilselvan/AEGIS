---
hide:
  - navigation
  - toc
---

<!-- The docs site's home page. Material "grid cards" need the "-   " list indent. -->
<!-- markdownlint-disable MD030 -->

# AEGIS

**Agentic Enterprise Guided Intelligent System.** Agents for GitHub Copilot and Claude
Code that turn a one-line idea into approved requirements, an implementable architecture
and reviewed code, grounded in your organization's standards.

[Get started](getting-started.md){ .md-button .md-button--primary }
[:fontawesome-brands-github: Star on GitHub](https://github.com/nishant-tamilselvan/AEGIS){ .md-button }
[See a complete example](https://github.com/nishant-tamilselvan/AEGIS/tree/main/examples/artifacts){ .md-button }

## Choose your setup

<div class="grid cards setups" markdown>

-   :material-microsoft-visual-studio-code:{ .lg .middle } **GitHub Copilot**

    ---

    Clone AEGIS, open it in VS Code and run `/start-ideation` in Copilot Chat's Agent mode.

    [:octicons-arrow-right-24: Getting started](getting-started.md)

-   :material-console:{ .lg .middle } **Claude Code**

    ---

    Clone AEGIS and run `claude` in the folder. Orchestrators run in your conversation;
    specialists run as subagents.

    [:octicons-arrow-right-24: Using AEGIS with Claude Code](claude-code.md)

-   :material-puzzle:{ .lg .middle } **Claude Code plugin** (preview)

    ---

    Install AEGIS into your own repository with `/plugin install aegis@aegis`, then
    `pip install aegis-sdlc`.

    [:octicons-arrow-right-24: The plugin guide](claude-code-plugin.md)

-   :material-language-python:{ .lg .middle } **CLI only**

    ---

    `pip install aegis-sdlc` gives you the `artifact-tools` command: scaffold and
    validate artifacts, for example in CI.

    [:octicons-arrow-right-24: CLI reference](cli-reference.md)

</div>

## How it works

| Phase | You get |
| --- | --- |
| **1. Ideation** | Product, functional and non-functional requirements, a user journey map, a system blueprint and an executive briefing. |
| **2. Architecture** | Interface specifications with native contracts, data, security, deployment and observability architecture, and ADRs. |
| **3. Implementation** | Work packages traced to the artifacts, a decision ledger, and reviewed code in your target repository. |

- **One step at a time.** Orchestrators ask a few focused questions, recap and wait for you.
- **Documents that stay consistent.** Fixed templates, stable ids, and validation after every edit.
- **Grounded in your standards.** Agents check your Enterprise Standards first and cite them.
- **Bounded, reviewed implementation.** A guard keeps each implementer inside one approved
  work package; completion needs an independent review and recorded evidence.
- **No automatic deployment.** Release needs a named human approver.

Read [how it works](how-it-works.md) for the details, or browse the
[complete example for a simple to-do app](https://github.com/nishant-tamilselvan/AEGIS/tree/main/examples/artifacts).

## Support the project

If AEGIS saves you time, please
**[:fontawesome-brands-github: star it on GitHub](https://github.com/nishant-tamilselvan/AEGIS)** so other teams can find it,
and tell us what worked or what got in your way in a
[feature request or bug report](https://github.com/nishant-tamilselvan/AEGIS/issues/new/choose).

AEGIS is [MIT licensed](https://github.com/nishant-tamilselvan/AEGIS/blob/main/LICENSE).
