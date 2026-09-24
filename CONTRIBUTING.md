# Contributing to AEGIS

Thanks for helping improve AEGIS. This guide covers the development setup, the checks
your change must pass, and a checklist for each kind of component.

## Contents

- [Before you start](#before-you-start)
- [Development setup](#development-setup)
- [Checks](#checks)
- [Repository map](#repository-map)
- [Component checklists](#component-checklists)
- [Commit messages](#commit-messages)
- [Pull requests](#pull-requests)
- [Releasing](#releasing)

## Before you start

- **Bugs and docs:** open a pull request directly.
- **New agents, phases, artifact types or CLI commands:** open a
  [feature request](https://github.com/nishant-tamilselvan/AEGIS/issues/new/choose) first,
  so we can agree the design before you build it.
- **Security issues:** follow [SECURITY.md](SECURITY.md). Do not open a public issue.
- **Keep it generic.** AEGIS is organization-neutral. Do not add company names, internal
  hostnames, private standards or real application names. Use `customer-portal` or
  `example-app` in examples.

By contributing, you agree that your contribution is licensed under the
[MIT License](LICENSE) and that you follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Development setup

Requirements: Python 3.10 or later, Git, and an agent host to try your change in (VS Code
with GitHub Copilot Chat, Claude Code, or both). The Markdown lint pre-commit hook installs
its own copy of Node.js.

```bash
git clone https://github.com/nishant-tamilselvan/AEGIS.git
cd AEGIS
python -m venv .venv
.venv/Scripts/activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -e ".[dev]"
pre-commit install
```

If you work on the reference Enterprise Standards server, also install its dependencies:

```bash
pip install -r examples/enterprise-standards-server/requirements.txt
```

## Checks

CI runs everything below on every pull request. Run it locally first:

```bash
python scripts/sync_platforms.py        # regenerate Copilot and Claude Code files from aegis/
python -m pytest                        # tests (CI: Linux, Windows and macOS; full matrix weekly)
ruff check .                            # Python lint
python scripts/ci/repo_checks.py all    # personal paths, denylist, unicode, workflows, links
pre-commit run --all-files              # all of the above plus Markdown lint and gitleaks
claude plugin validate --strict plugins/aegis   # optional; needs Claude Code
```

Pull requests need these checks to pass before they can merge:

| Check | What it runs |
| --- | --- |
| Test (7 jobs) | pytest on Linux with Python 3.10–3.13, Windows with 3.10 and 3.13, and macOS with 3.13. All 12 combinations run weekly in `full-matrix.yml`. |
| Lint and repository checks | ruff, the generated-file drift check, `repo_checks.py`, the sample knowledge base and Markdown lint |
| Build package | Builds the sdist and wheel, then runs the installed CLI outside the repository |
| Validate Claude Code plugin | `claude plugin validate --strict` on the marketplace, plugin, skills and agents |
| Secret scan | gitleaks over the full history |
| Analyze (python), Analyze (actions) | CodeQL. Every review comment it leaves must be resolved, preferably by fixing the code. |

`repo_checks.py` enforces these rules:

| Check | Rejects |
| --- | --- |
| `personal-paths` | Paths such as `C:\Users\<name>` or `/home/<name>` that contain a real user name. |
| `denylist` | Credentials, internal hostnames and any term in `scripts/ci/denylist.txt`, `.denylist.local` or the `AEGIS_DENYLIST` environment variable. |
| `unicode` | Zero-width, bidirectional-override and tag characters that can hide instructions in agent files, stray control bytes such as NUL, and byte order marks. |
| `workflows` | Actions not pinned to a commit SHA, a missing `permissions:` block, `pull_request_target`, checkouts that keep credentials, and untrusted event text used inline. |
| `links` | Relative Markdown links to files that do not exist. |

If you work on AEGIS for an organization, list that organization's private terms in
`.denylist.local`. The file is gitignored, and the check reads it on every run.

## Repository map

| Path | What lives there |
| --- | --- |
| `aegis/agents/` | **Source** agent definitions (`<name>.md`). |
| `aegis/prompts/` | **Source** slash-command prompts. |
| `aegis/skills/` | **Source** skills: `SKILL.md`, templates and references. |
| `aegis/instructions.md` | **Source** golden rules for every agent. |
| `.github/agents/`, `.github/prompts/`, `.github/skills/`, `.github/copilot-instructions.md` | Generated for GitHub Copilot. Do not edit. |
| `.claude/agents/`, `.claude/skills/` | Generated for Claude Code. Do not edit. |
| `plugins/aegis/`, `.claude-plugin/marketplace.json` | Generated Claude Code plugin and marketplace, including copies of the hook scripts and `artifact_tools`. Do not edit. |
| `.github/hooks/`, `.claude/settings.json` | Hook configuration for each platform. Both call the same scripts. |
| `CLAUDE.md` | Claude Code entry point. Imports the golden rules and `AGENTS.md`. |
| `src/artifact_tools/` | The CLI: scaffold, validate, ADRs, implementation state and the guard. |
| `scripts/` | Hook entry points and CI checks. |
| `examples/enterprise-standards-server/` | Reference MCP server and sample standards. |
| `docs/` | User documentation. |
| `tests/` | pytest suite. |

## Component checklists

Agents, prompts and skills are written once in `aegis/`. After any change there, run
`python scripts/sync_platforms.py` and commit the regenerated `.github/` and `.claude/`
files with it. CI runs `sync_platforms.py --check` and fails if they are out of date.

Agent source frontmatter uses platform-neutral fields. The generator maps them for each
platform:

| Field | Meaning |
| --- | --- |
| `name` | Slug, equal to the file name. Claude Code uses it as the subagent name. |
| `title` | Display name. Copilot uses it as the agent name. |
| `role` | `orchestrator` (talks to the user; runs in the main conversation in Claude Code) or `specialist` (becomes a Claude Code subagent). |
| `tools` | Any of `read`, `search`, `edit`, `execute`, `agent`, `todo`, `standards`. |
| `handoffs` | Orchestrators only: `label`, `agent` (a slug) and `prompt`. |

### Agent (`aegis/agents/<name>.md`)

- [ ] Frontmatter has `name` (equal to the file name), `title`, `role`, a `description`
      that says when to use the agent, and a non-empty `tools` list. The generator and
      `tests/test_customizations.py` and `tests/test_claude_code.py` enforce this.
- [ ] Tools are the minimum the role needs. Read-only reviewers get no `edit` tool.
- [ ] If the agent calls the standards library, it lists `standards`
      and follows the [`enterprise-standards` skill](aegis/skills/enterprise-standards/SKILL.md).
- [ ] Its body makes sense on both platforms. It hands work to other agents by slug
      (`artifact-manager`) rather than by platform-specific mechanics.
- [ ] It respects the golden rules in `aegis/instructions.md`, including that only
      `artifact-manager` writes artifacts.
- [ ] It is listed in the [agent catalog](docs/agents.md).

### Prompt (`aegis/prompts/<name>.md`)

- [ ] Frontmatter has `name` (equal to the file name), `description`, `argument-hint`, and
      `agent` naming an existing agent by slug.
- [ ] A prompt name must not clash with a skill name. Both become Claude Code skills.
- [ ] It is listed in the [prompt catalog](docs/agents.md#prompts).

### Skill (`aegis/skills/<name>/SKILL.md`)

- [ ] Frontmatter `name` matches the folder name, and `description` says when to load it.
- [ ] Referenced files (templates, references) exist. The `links` check verifies this.

### Artifact template (`aegis/skills/artifact-management/assets/templates/`)

- [ ] Frontmatter keeps `version`, `status`, `last_updated` and `phase`.
- [ ] Id prefixes follow [id-conventions](aegis/skills/artifact-management/references/id-conventions.md).
- [ ] A freshly scaffolded document validates. Run
      `python -m artifact_tools scaffold <type> <tmp-dir> --project Test`, then
      `python -m artifact_tools validate <tmp-dir>`.

### CLI or validator change (`src/artifact_tools/`)

- [ ] Tests cover the new behavior, including the failure path.
- [ ] The [CLI reference](docs/cli-reference.md) is updated.
- [ ] It uses only the standard library and PyYAML, unless a new dependency was agreed in an issue.

### Workflow change (`.github/workflows/`)

- [ ] Every third-party action is pinned to a full commit SHA with a `# vX.Y.Z` comment.
- [ ] Top-level `permissions: contents: read`. Grant more only to the job that needs it.
- [ ] `actions/checkout` sets `persist-credentials: false`.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<optional scope>): <summary in lower case>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`, `revert`.
Example: `fix(guard): reject target paths that escape through symlinks`.

## Pull requests

1. Branch from `main` and keep each pull request to one concern.
2. Fill in the pull request template, including the checks you ran.
3. Add an entry under **Unreleased** in [CHANGELOG.md](CHANGELOG.md) for any change users
   will notice.
4. CI must pass. `CODEOWNERS` requests a maintainer review automatically.

## Releasing

Maintainers release from `main`:

1. Open a pull request that sets `version` in `pyproject.toml` to the new version and
   renames the changelog's **Unreleased** section to `[X.Y.Z] - YYYY-MM-DD`, with a
   new empty **Unreleased** section above it and updated comparison links at the bottom.
   Run `python scripts/sync_platforms.py`: the plugin manifest takes its version from
   `pyproject.toml`.
2. Merge it once CI passes.
3. Publish a GitHub release with the tag `vX.Y.Z` on that commit, using the changelog
   section as the notes.
4. Approve the deployment: open the **Publish to PyPI** run, select **Review
   deployments**, tick `pypi` and approve.
5. Check the result: `pip install aegis-sdlc==X.Y.Z` in a clean environment, and run
   `artifact-tools validate` on a scaffolded folder outside the repository.

Publishing the release runs `.github/workflows/publish.yml`. It checks that the tag
matches the package version, builds the sdist and wheel, and publishes `aegis-sdlc` to
PyPI through Trusted Publishing, so no API token is stored. PyPI records a provenance
attestation that links each file to this repository and workflow. Only `v*` tags can
deploy to the `pypi` environment, and each deployment needs a maintainer's approval.
