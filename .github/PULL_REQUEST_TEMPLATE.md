## What changed

<!-- The specific change, in a sentence or two. Link the issue: "Closes #123". -->

## Why

<!-- The problem this solves. -->

## Type of change

- [ ] `fix:` bug fix
- [ ] `feat:` new feature
- [ ] `docs:` documentation
- [ ] `refactor:` / `perf:` / `test:`
- [ ] `build:` / `ci:` / `chore:`

## Checks run

- [ ] `python scripts/sync_platforms.py` (after any change under `aegis/`)
- [ ] `python -m pytest`
- [ ] `ruff check .`
- [ ] `python scripts/ci/repo_checks.py all`
- [ ] `pre-commit run --all-files` (includes Markdown lint and gitleaks)

## Tested on

- [ ] GitHub Copilot (VS Code)
- [ ] Claude Code
- [ ] Not applicable (CLI, docs or CI only)

## Checklist

- [ ] Followed the [component checklist](https://github.com/nishant-tamilselvan/AEGIS/blob/main/CONTRIBUTING.md#component-checklists) for any agent, prompt, skill, template, CLI or workflow I changed.
- [ ] Changed agents, prompts, skills or golden rules in `aegis/`, not in the generated `.github/`, `.claude/` or `plugins/aegis/` copies.
- [ ] No secrets, internal hostnames, organization names or personal paths.
- [ ] Docs updated (`README.md`, `docs/`), if behavior or usage changed.
- [ ] `CHANGELOG.md` updated under **Unreleased**, if users will notice the change.
