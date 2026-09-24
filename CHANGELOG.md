# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Until 1.0.0, minor versions
may include breaking changes; they are listed under **Changed**.

## [Unreleased]

### Added

- The CLI is packaged for PyPI as `aegis-sdlc` (the `artifact-tools` command and the
  `artifact_tools` module keep their names). Publishing a GitHub release publishes the
  package through Trusted Publishing. CI builds the package and runs the installed CLI
  outside the repository.

### Fixed

- When the implementation target is the same repository that holds `docs/artifacts/`,
  the guard no longer blocks `artifact-manager` and other non-implementation agents from
  writing artifacts. Implementers are still denied there, and code writes still require
  the active package's implementer.
- An installed CLI used outside an AEGIS clone could not find its templates. The wheel
  now bundles them; a repository's own templates still take precedence.

## [0.1.0] - 2026-09-24

First public, organization-neutral release, for GitHub Copilot and Claude Code.

### Added

- Three-phase agent system (ideation, architecture and implementation) with 18 agents,
  10 prompts and 4 skills, for two agent hosts:
  - **GitHub Copilot in VS Code:** custom agents, prompt files and skills in `.github/`,
    with hooks in `.github/hooks/`.
  - **Claude Code:** the 15 specialists as subagents (`.claude/agents/`), the 10 prompts as
    slash-command skills that run the orchestrators in the main conversation
    (`.claude/skills/`), hooks in `.claude/settings.json`, and `CLAUDE.md`. See
    [docs/claude-code.md](docs/claude-code.md).
- One source for both hosts: agents, prompts, skills and golden rules live in `aegis/`.
  `scripts/sync_platforms.py` generates the Copilot and Claude Code files, and CI and
  pre-commit fail when they drift.
- `artifact_tools` CLI to scaffold, validate and maintain artifacts, ADRs, interface
  contracts, diagrams and phase-3 implementation state.
- Implementation guard (`PreToolUse`) and automatic validation (`PostToolUse`) hooks,
  shared by both hosts. The guard recognizes Copilot agent names and Claude Code subagents
  (`agent_type`). The validation hook returns feedback as `systemMessage` for Copilot and
  `additionalContext` for Claude Code (`--platform claude`).
- A worked example, [`examples/artifacts/todo-list/`](examples/artifacts/): a complete,
  approved phase 1 and phase 2 artifact set for a simple to-do app, with an OpenAPI 3.1
  contract and two ADRs. CI keeps it passing strict validation and the readiness gate.
- Enterprise Standards integration: the `enterprise-standards` skill, a reference MCP
  server with a sample knowledge base, MCP templates for both hosts
  (`.vscode/mcp.example.json`, `.mcp.example.json`) and a setup guide.
- Repository checks for personal paths, denylisted terms, invisible Unicode, workflow
  security and broken links.
- CI on Windows, macOS and Linux with SHA-pinned actions, a secret scan, Dependabot and
  pre-commit hooks.
- CodeQL code scanning (Python and GitHub Actions) and OpenSSF Scorecard workflows.
- Community files: security policy, contributing guide, Code of Conduct, issue forms and
  a pull request template.
- Golden rules that treat external content as data and forbid copying secrets into
  artifacts.

### Changed

- The organization-specific playbook integration is now the generic Enterprise
  Standards library (`enterprise-standards-server`).
- The `--playbook-review` CLI option and the `playbook_review` pointer field are renamed to
  `--standards-review` and `standards_review`.
- The CLI reads templates from `aegis/skills/` instead of `.github/skills/`.
- Implementation readiness accepts `CLAUDE.md` as a target repository's conventions file.

### Security

- The implementation guard hook never fails open. An agent host lets a tool call proceed
  when its hook crashes, so on any failure the wrapper denies implementation agents and
  asks you about every other call. Deny reasons also go to stderr, where Claude Code reads
  them.
- Only the active work package's implementation agent may write to the target
  repository. Writes there from orchestrators, reviewers or the Claude Code main
  conversation are denied with a reminder to delegate.

### Fixed

- Writing implementation state no longer fails intermittently on Windows when another
  process briefly holds the file open. The atomic rename now retries.
- The CLI writes LF line endings on every platform. On Windows, scaffolded artifacts,
  ADRs, changelog entries and contract stubs were written with CRLF.

[Unreleased]: https://github.com/nishant-tamilselvan/AEGIS/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nishant-tamilselvan/AEGIS/releases/tag/v0.1.0
