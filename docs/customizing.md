# Customizing AEGIS for your organization

You can run your own edition of AEGIS without editing the core files. Fork the
repository, add one config file and an overlay folder, and keep pulling upstream changes.
Your additions stay in files that upstream never touches, so merges stay simple.

An optional `aegis.config.yaml` at the repository root controls four extension points:

| Key | What it changes | Read by |
| --- | --- | --- |
| `plugin` | The Claude Code plugin's name, description, author and repository URL | `scripts/sync_platforms.py` |
| `overlay` | A folder of extra or replacement agents, prompts, skills and rules | `scripts/sync_platforms.py` |
| `standards` | The name of the MCP server that serves your Enterprise Standards | `scripts/sync_platforms.py` |
| `artifact_types` | Extra artifact types the CLI scaffolds, validates and checks for readiness | the `artifact-tools` CLI and the validation hook |

Every key is optional. Without the file, AEGIS behaves exactly as the public edition.

## A complete example

```yaml
# aegis.config.yaml
plugin:
  name: example-org-aegis
  description: AEGIS agents for example-org teams, grounded in example-org standards.
  author: Example Org
  repo_url: https://github.com/example-org/aegis-edition

overlay:
  path: overlay
  overrides:
    - agents/critic-reviewer.md

standards:
  server: example-standards-server

artifact_types:
  privacy-assessment:
    prefix: PIA
    title: Privacy Assessment
    template: overlay/templates/privacy-assessment.template.md
    aliases: [pia, privacy]
    required: true
```

After any change to the file or the overlay, regenerate the platform files:

```bash
python scripts/sync_platforms.py
python scripts/sync_platforms.py --check
```

The script reads `aegis.config.yaml` from the repository root. Pass `--config <path>` to
use a different file. Relative paths in the file resolve against the file's own folder.

## Plugin identity

| Field | Default | Used for |
| --- | --- | --- |
| `name` | `aegis` | The plugin folder (`plugins/<name>/`), the marketplace name and the command prefix (`/<name>:start-ideation`). Lower-case letters, digits and hyphens. |
| `description` | The public description | `plugin.json`, `marketplace.json` and the plugin README |
| `author` | The AEGIS maintainer | The plugin author and the marketplace owner |
| `repo_url` | The public repository | The plugin homepage, the install command and links from skills to repository files. Must start with `https://`. |

When `repo_url` is a GitHub repository, the install line in the plugin README reads
`/plugin marketplace add <owner>/<repo>`. For any other host it uses the full URL.

Renaming the plugin moves the generated plugin to `plugins/<name>/`. The sync script
deletes the old `plugins/aegis/` folder, so commit that deletion with the new folder.

## Overlays

An overlay folder mirrors the layout of `aegis/`:

```text
overlay/
  agents/<name>.md            extra agents, or replacements listed in overrides
  prompts/<name>.md           extra prompts
  skills/<name>/SKILL.md      extra skills, with any files they need
  instructions.md             extra golden rules, appended to aegis/instructions.md
```

The sync script merges the overlay on top of `aegis/` and generates the Copilot, Claude
Code and plugin files from the result. Overlay sources follow the same rules as core
sources: see the [component checklists](../CONTRIBUTING.md#component-checklists).

### Precedence

| Overlay file | Result |
| --- | --- |
| A new path, such as `agents/example-reviewer.md` | Added. |
| The same path as a core file, listed in `overrides` | Replaces the core file. |
| The same path as a core file, not listed in `overrides` | Error. Nothing is written. |
| `instructions.md` | Appended after the core golden rules. It cannot replace them. |

Every `overrides` entry must replace a core file. If upstream renames or removes the file
you override, the sync script fails, so you notice and update your copy. Entries take the
forms `agents/<name>.md`, `prompts/<name>.md` and `skills/<name>/<file>`.

Overrides work one file at a time. To change a core skill, override its `SKILL.md`. To
add a reference file to a core skill, put it at `overlay/skills/<skill>/references/...`.
That adds a file without replacing one, so it needs no override.

An overridden file stops receiving upstream changes. Prefer adding a new agent or skill.
Override a core file only when an addition cannot do the job.

### Links and placement

Write links in overlay files as if the file lived in `aegis/`. Generated agents link to
`../skills/<name>`, and generated skills climb out of their folder with `../../../`. Put
the overlay folder directly under the repository root, as `overlay/` is here, so skill
links that climb `../../../` resolve from both places.

In a clone, Claude Code reads the golden rules through the `@aegis/instructions.md`
import in `CLAUDE.md`. Add `@overlay/instructions.md` below it so the overlay rules load
too. The generated Copilot instructions and the plugin already include them.

## Standards server name

The agents call your Enterprise Standards library through an MCP server named
`enterprise-standards-server`. Set `standards.server` to use another name:

| Generated file | Default | With `server: example-standards-server` |
| --- | --- | --- |
| Copilot agent tools | `enterprise-standards-server/*` | `example-standards-server/*` |
| Claude Code subagent tools | `mcp__enterprise-standards-server` | `mcp__example-standards-server` |
| Agent, prompt, skill and rules text | `enterprise-standards-server` | `example-standards-server` |

The source files keep the neutral `standards` tool name. Paths such as
`examples/enterprise-standards-server/` keep their name. Name the server the same way in
your `.mcp.json` and `.vscode/mcp.json`. The
[Enterprise Standards setup](enterprise-standards-setup.md) guide covers those files.

## Extra artifact types

Each entry under `artifact_types` adds one document type to the CLI:

| Field | Required | Meaning |
| --- | --- | --- |
| `prefix` | Yes | The id prefix the document defines, such as `PIA` for `PIA-001`. Upper-case letters and digits. |
| `title` | Yes | The title used in new documents (`Privacy Assessment: <project>`). |
| `template` | Yes | The template file, relative to the config file. |
| `filename` | No | The document's file name. Default: `<type>.md`. |
| `aliases` | No | Extra names the `scaffold` command accepts. |
| `required` | No | Whether the implementation readiness gate requires the document. Default: `true`. |

A configured type cannot reuse a built-in type name, alias, file name or id prefix.
`ADR`, `WP` and `IDEC` are reserved as well.

A template uses the same frontmatter as the built-in ones. Set `artifact:` to the type
name. The `{{TITLE}}`, `{{PROJECT_NAME}}` and `{{DATE}}` placeholders are filled in:

```markdown
---
artifact: privacy-assessment
title: "{{TITLE}}"
version: "0.1"
status: draft
last_updated: "{{DATE}}"
phase: 2
owner: artifact-manager
---

# Privacy Assessment: {{PROJECT_NAME}}

| Id | Finding |
| --- | --- |
| PIA-001 | _..._ |
```

With the type configured, the CLI treats the document like the built-in ones:

| Command | Effect |
| --- | --- |
| `artifact-tools scaffold pia docs/artifacts/example-app` | Creates `privacy-assessment.md` from your template. |
| `artifact-tools validate docs/artifacts/example-app` | Checks its frontmatter, its `PIA-*` ids and references to them. |
| `artifact-tools implementation readiness ...` | Requires the document to exist and be approved, unless `required: false`. |

Agents do not learn about a new type on their own. Tell them in the overlay: add a rule to
`overlay/instructions.md`, and give an agent or skill the steps for writing the document.

### How the CLI finds the config

The CLI looks for the config in this order:

1. The file named by the `AEGIS_CONFIG` environment variable.
2. `aegis.config.yaml` in the current folder or the nearest parent folder.

The validation hook searches from the repository it validates. If you install the CLI
with `pip` and run it outside your edition's repository, set `AEGIS_CONFIG`. An invalid
config stops the CLI with exit code 2 and a message that names the bad key.

## Keeping up with upstream

1. Merge the upstream branch into your fork.
2. Run `python scripts/sync_platforms.py`. Conflicts in generated folders such as
   `.github/agents/` and `plugins/` resolve by regenerating them, so take either side
   and then run the script.
3. Run `python scripts/sync_platforms.py --check`, the tests and
   `python scripts/ci/repo_checks.py all`.
4. If the sync script reports a stale override, compare your copy with the new core file
   and update it.

List your organization's private terms in `.denylist.local` so the `denylist` check keeps
them out of anything you contribute back upstream.
