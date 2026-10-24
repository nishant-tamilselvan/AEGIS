#!/usr/bin/env python3
"""Generate the GitHub Copilot and Claude Code customizations from ``aegis/``.

``aegis/`` is the single source of truth for AEGIS agents, prompts, skills and golden
rules. This script writes the platform-specific copies:

==========================  =======================================================
Source                      Generated
==========================  =======================================================
aegis/agents/<name>.md      .github/agents/<name>.agent.md  (all agents)
                            .claude/agents/<name>.md        (specialists only)
aegis/prompts/<name>.md     .github/prompts/<name>.prompt.md
                            .claude/skills/<name>/SKILL.md  (slash command)
aegis/skills/<name>/**      .github/skills/<name>/**  and  .claude/skills/<name>/**
aegis/instructions.md       .github/copilot-instructions.md
==========================  =======================================================

In Claude Code, orchestrators run in the main conversation: each prompt that targets an
orchestrator becomes a skill that loads the orchestrator's role, so it can talk to the
user and delegate to specialist subagents.

An optional ``aegis.config.yaml`` at the repository root changes the plugin identity and
the standards server name, and adds an overlay folder whose agents, prompts and skills
are merged on top of ``aegis/``. See docs/customizing.md.

Usage::

    python scripts/sync_platforms.py            # write the generated files
    python scripts/sync_platforms.py --check    # exit 1 if any generated file is stale
    python scripts/sync_platforms.py --config path/to/aegis.config.yaml
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from artifact_tools.config import (  # noqa: E402
    CONFIG_FILENAME,
    DEFAULT_CONFIG,
    DEFAULT_PLUGIN_NAME,
    DEFAULT_STANDARDS_SERVER,
    AegisConfig,
    ConfigError,
    load_config,
)

SOURCE = Path("aegis")

GENERATED_NOTE = "Generated from {source} by scripts/sync_platforms.py. Edit the source, not this file."

# Neutral tool names (Copilot vocabulary) and their Claude Code equivalents. The
# standards tool maps to the configured MCP server (standards.server in the config).
STANDARDS_TOOL = "standards"
CLAUDE_TOOLS = {
    "read": ["Read"],
    "search": ["Grep", "Glob"],
    "edit": ["Edit", "Write"],
    "execute": ["Bash"],
    "agent": ["Agent"],
    "todo": [],
    STANDARDS_TOOL: [],
}

# Mentions of the default server name in agent, prompt, skill and rules text. Paths such
# as examples/enterprise-standards-server are left alone.
_SERVER_MENTION_RE = re.compile(rf"(?<![\w./-]){re.escape(DEFAULT_STANDARDS_SERVER)}(?![\w-])")

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass(frozen=True)
class Agent:
    name: str
    title: str
    role: str
    description: str
    tools: list[str]
    handoffs: list[dict[str, str]]
    body: str
    source: str


@dataclass(frozen=True)
class Prompt:
    name: str
    description: str
    agent: str
    argument_hint: str
    body: str
    source: str


# --------------------------------------------------------------------------- loading


def _split(path: Path) -> tuple[dict, str]:
    match = _FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter")
    return yaml.safe_load(match.group(1)) or {}, match.group(2)


def _scan(base: Path) -> dict[str, Path]:
    """Agent, prompt and skill sources under `base`, keyed by path relative to it."""
    found = {}
    for kind in ("agents", "prompts"):
        for path in sorted((base / kind).glob("*.md")):
            found[f"{kind}/{path.name}"] = path
    skills = base / "skills"
    if skills.is_dir():
        for path in sorted(p for p in skills.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            found[f"skills/{path.relative_to(skills).as_posix()}"] = path
    return found


def source_tree(root: Path, config: AegisConfig = DEFAULT_CONFIG) -> dict[str, Path]:
    """Every source file, keyed by its path relative to ``aegis/`` (``agents/<name>.md``).

    Overlay files are merged on top of ``aegis/``. An overlay file at the same path as a
    core file replaces it only when ``overlay.overrides`` lists that path; otherwise it is
    an error, so a core file is never shadowed by accident. Every override must replace a
    core file, so a stale entry is caught when the core file is renamed or removed.
    """
    tree = _scan(root / SOURCE)
    overlay = config.overlay
    if overlay is None:
        return tree
    overrides = set(overlay.overrides)
    replaced = set()
    where = overlay.path.relative_to(root).as_posix()
    for rel, path in _scan(overlay.path).items():
        if rel in tree:
            if rel not in overrides:
                raise ValueError(
                    f"{where}/{rel} shadows {SOURCE.as_posix()}/{rel}. Rename it, or list "
                    f"{rel!r} under overlay.overrides in {CONFIG_FILENAME} to replace the core file."
                )
            replaced.add(rel)
        tree[rel] = path
    unused = sorted(overrides - replaced)
    if unused:
        raise ValueError(
            f"overlay.overrides in {CONFIG_FILENAME} lists {', '.join(unused)}, but no overlay "
            "file replaces a core file at that path"
        )
    return dict(sorted(tree.items()))


def load_agents(root: Path, tree: dict[str, Path] | None = None) -> dict[str, Agent]:
    tree = source_tree(root) if tree is None else tree
    agents = {}
    for path in (path for rel, path in tree.items() if rel.startswith("agents/")):
        fm, body = _split(path)
        name = fm["name"]
        if name != path.stem:
            raise ValueError(f"{path}: name {name!r} must match the file name")
        unknown = set(fm["tools"]) - set(CLAUDE_TOOLS)
        if unknown:
            raise ValueError(f"{path}: unknown tools {sorted(unknown)}; use {sorted(CLAUDE_TOOLS)}")
        if fm["role"] not in ("orchestrator", "specialist"):
            raise ValueError(f"{path}: role must be orchestrator or specialist")
        agents[name] = Agent(
            name=name,
            title=fm["title"],
            role=fm["role"],
            description=fm["description"],
            tools=list(fm["tools"]),
            handoffs=list(fm.get("handoffs") or []),
            body=body,
            source=path.relative_to(root).as_posix(),
        )
    for agent in agents.values():
        for handoff in agent.handoffs:
            if handoff["agent"] not in agents:
                raise ValueError(f"{agent.source}: handoff to unknown agent {handoff['agent']!r}")
    return agents


def load_prompts(root: Path, agents: dict[str, Agent], tree: dict[str, Path] | None = None) -> dict[str, Prompt]:
    tree = source_tree(root) if tree is None else tree
    prompts = {}
    for path in (path for rel, path in tree.items() if rel.startswith("prompts/")):
        fm, body = _split(path)
        if fm["name"] != path.stem:
            raise ValueError(f"{path}: name {fm['name']!r} must match the file name")
        if fm["agent"] not in agents:
            raise ValueError(f"{path}: unknown agent {fm['agent']!r}")
        prompts[fm["name"]] = Prompt(
            name=fm["name"],
            description=fm["description"],
            agent=fm["agent"],
            argument_hint=fm["argument-hint"],
            body=body,
            source=path.relative_to(root).as_posix(),
        )
    return prompts


# --------------------------------------------------------------------------- rendering


def _q(value: str) -> str:
    """Double-quoted YAML scalar (JSON string syntax is valid YAML)."""
    return json.dumps(value, ensure_ascii=False)


def _note(source: str) -> str:
    return f"# {GENERATED_NOTE.format(source=source)}"


def copilot_agent(agent: Agent, agents: dict[str, Agent], config: AegisConfig = DEFAULT_CONFIG) -> str:
    tools = ", ".join(f"'{config.standards_server}/*'" if t == STANDARDS_TOOL else t for t in agent.tools)
    lines = [
        "---",
        _note(agent.source),
        f"description: {_q(agent.description)}",
        f"name: {_q(agent.title)}",
        f"tools: [{tools}]",
    ]
    if agent.handoffs:
        lines.append("handoffs:")
        for handoff in agent.handoffs:
            lines += [
                f"  - label: {_q(handoff['label'])}",
                f"    agent: {_q(agents[handoff['agent']].title)}",
                f"    prompt: {_q(handoff['prompt'])}",
            ]
    lines.append("---")
    return "\n".join(lines) + "\n" + agent.body


def copilot_prompt(prompt: Prompt, agents: dict[str, Agent]) -> str:
    lines = [
        "---",
        _note(prompt.source),
        f"description: {_q(prompt.description)}",
        f"agent: {_q(agents[prompt.agent].title)}",
        f"argument-hint: {_q(prompt.argument_hint)}",
        "---",
    ]
    return "\n".join(lines) + "\n" + prompt.body


def _claude_tools(agent: Agent, config: AegisConfig) -> str:
    names: list[str] = []
    for tool in agent.tools:
        mapped = [f"mcp__{config.standards_server}"] if tool == STANDARDS_TOOL else CLAUDE_TOOLS[tool]
        for name in mapped:
            if name not in names:
                names.append(name)
    return ", ".join(names)


CLAUDE_SPECIALIST_PREAMBLE = """\
> **Claude Code:** you run as a subagent. You cannot talk to the user; the main
> conversation delegated this task to you and receives only your final message. Where
> these instructions say to hand work to another agent (for example `artifact-manager`),
> put that hand-off in your final message, addressed to the agent by name, with every id
> and path it needs. The main conversation delegates it. Ask for missing decisions the
> same way instead of guessing.

"""


def claude_agent(agent: Agent, config: AegisConfig = DEFAULT_CONFIG) -> str:
    lines = [
        "---",
        _note(agent.source),
        f"name: {agent.name}",
        f"description: {_q(agent.description)}",
        f"tools: {_claude_tools(agent, config)}",
        "---",
    ]
    return "\n".join(lines) + "\n" + CLAUDE_SPECIALIST_PREAMBLE + agent.body


def _inline_links(body: str) -> str:
    """Agent bodies link to ``../skills/<name>``; prompt skills sit one level deeper."""
    return body.replace("](../skills/", "](../")


def plugin_dir(config: AegisConfig = DEFAULT_CONFIG) -> str:
    return f"plugins/{config.plugin.name}"


def _plugin_agent_note(config: AegisConfig) -> str:
    name = config.plugin.name
    return (
        f"In a plugin install the subagents are listed with the `{name}:` prefix, for "
        f"example `{name}:artifact-manager`."
    )


def _rules_line(plugin: bool) -> str:
    where = "that AEGIS loaded at the start of this session" if plugin else "in `CLAUDE.md`"
    return (
        f"- **Follow the golden rules** {where}, including that only `artifact-manager` writes\n"
        "  under `docs/artifacts/`.\n"
    )


def _orchestrator_preamble(
    agent: Agent, agents: dict[str, Agent], plugin: bool = False, config: AegisConfig = DEFAULT_CONFIG
) -> str:
    specialists = ", ".join(f"`{h['agent']}`" for h in agent.handoffs)
    plugin_note = f"\n  {_plugin_agent_note(config)}" if plugin else ""
    return f"""\
## How to run this in Claude Code

For this request you are the **{agent.title}**, working in the main conversation. You talk
to the user directly and delegate specialist work to subagents.

- **Delegate** with the Agent tool. Specialists for this role: {specialists}. Subagents
  cannot see this conversation, so give each one the application's `docs/artifacts/<app>`
  path, the relevant ids and every decision it needs.{plugin_note}
- **Relay hand-offs.** When a subagent's final message hands work to another agent (for
  example "for `artifact-manager`: ..."), delegate that work to the named subagent.
- **Ask the user** with the AskUserQuestion tool, one to three focused questions at a time.
- **Track progress** with the task list.
{_rules_line(plugin)}
"""


def claude_prompt_skill(
    prompt: Prompt, agents: dict[str, Agent], plugin: bool = False, config: AegisConfig = DEFAULT_CONFIG
) -> str:
    target = agents[prompt.agent]
    lines = [
        "---",
        _note(prompt.source),
        f"name: {prompt.name}",
        f"description: {_q(prompt.description)}",
        f"argument-hint: {_q(prompt.argument_hint)}",
        "disable-model-invocation: true",
        "---",
    ]
    header = "\n".join(lines) + "\n"
    request = f"## This request\n\n{prompt.body.strip()}\n\nArguments from the user: $ARGUMENTS\n"
    if target.role == "orchestrator":
        role = f"## Your role: {target.title}\n\n{_inline_links(target.body).strip()}\n\n"
        return header + _orchestrator_preamble(target, agents, plugin, config) + role + request
    plugin_note = f"\n{_plugin_agent_note(config)}" if plugin else ""
    delegate = f"""\
## How to run this in Claude Code

Delegate this request to the `{target.name}` subagent with the Agent tool. Pass it the
request below, the user's arguments and the application's `docs/artifacts/<app>` path.
If it needs a decision, ask the user with AskUserQuestion and send the answer back to it.
If its final message hands work to another agent, delegate that work to the named
subagent. Report the outcome to the user.{plugin_note}

"""
    return header + delegate + request


def skill_file(text: str, source: str) -> str:
    """Add the generated note to a SKILL.md frontmatter; other files are copied as-is."""
    if text.startswith("---\n"):
        return "---\n" + _note(source) + "\n" + text[len("---\n"):]
    return text


def copilot_instructions(text: str) -> str:
    return f"<!-- {GENERATED_NOTE.format(source='aegis/instructions.md')} -->\n\n{text}"


# --------------------------------------------------------------------------- planning


PLUGIN_SCRIPTS = ("implementation_guard.py", "validate_hook.py", "session_start.py")


def package_version(root: Path) -> str:
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8"))
    if not match:
        raise ValueError("pyproject.toml has no version")
    return match.group(1)


def _json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def plugin_manifest(version: str, config: AegisConfig = DEFAULT_CONFIG) -> str:
    plugin = config.plugin
    return _json({
        "name": plugin.name,
        "version": version,
        "description": plugin.description,
        "author": {"name": plugin.author},
        "homepage": plugin.repo_url,
        "repository": plugin.repo_url,
        "license": "MIT",
        "keywords": ["sdlc", "requirements", "architecture", "adr", "agents"],
    })


def marketplace_manifest(config: AegisConfig = DEFAULT_CONFIG) -> str:
    plugin = config.plugin
    return _json({
        "name": plugin.name,
        "description": f"AEGIS: {plugin.description[0].lower()}{plugin.description[1:]}",
        "owner": {"name": plugin.author},
        "plugins": [
            {"name": plugin.name, "source": f"./{plugin_dir(config)}", "description": plugin.description},
        ],
    })


def marketplace_source(config: AegisConfig = DEFAULT_CONFIG) -> str:
    """What ``/plugin marketplace add`` takes: ``owner/repo`` on GitHub, else the URL."""
    url = config.plugin.repo_url
    github = "https://github.com/"
    if url.startswith(github) and url[len(github):].count("/") == 1:
        return url[len(github):].removesuffix(".git")
    return url


def plugin_hooks() -> str:
    script = 'python "${CLAUDE_PLUGIN_ROOT}/scripts/%s"'
    repo = '--repo-root "$CLAUDE_PROJECT_DIR"'
    return _json({
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": script % "session_start.py", "timeout": 10}]},
            ],
            "PreToolUse": [{
                "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell",
                "hooks": [{"type": "command", "command": f"{script % 'implementation_guard.py'} {repo}", "timeout": 10}],
            }],
            "PostToolUse": [{
                "matcher": "Edit|Write|MultiEdit",
                "hooks": [{
                    "type": "command",
                    "command": f"{script % 'validate_hook.py'} --platform claude {repo}",
                    "timeout": 30,
                }],
            }],
        }
    })


def plugin_readme(version: str, config: AegisConfig = DEFAULT_CONFIG) -> str:
    plugin = config.plugin
    return f"""<!-- {GENERATED_NOTE.format(source="scripts/sync_platforms.py")} -->

# AEGIS plugin for Claude Code (v{version})

{plugin.description}

## Install

```text
/plugin marketplace add {marketplace_source(config)}
/plugin install {plugin.name}@{plugin.name}
```

The agents call the AEGIS CLI, so install it for the Python on your PATH:

```bash
pip install aegis-sdlc
```

## Use

Run `/{plugin.name}:start-ideation <app-name> <idea>` in your repository. Artifacts are written to
`docs/artifacts/<app-name>/` in that repository. See the
[Claude Code plugin guide]({plugin.repo_url}/blob/main/docs/claude-code-plugin.md).
"""


def rules_text(root: Path, config: AegisConfig = DEFAULT_CONFIG) -> str:
    """The golden rules: ``aegis/instructions.md``, then the overlay's ``instructions.md``.

    Overlay rules are appended. They add to the core rules and never replace them.
    """
    text = (root / SOURCE / "instructions.md").read_text(encoding="utf-8")
    extra = config.overlay.path / "instructions.md" if config.overlay is not None else None
    if extra is not None and extra.is_file():
        text = text.rstrip("\n") + "\n\n" + extra.read_text(encoding="utf-8").lstrip("\n")
    return text


def planned_files(root: Path, config: AegisConfig = DEFAULT_CONFIG) -> dict[Path, bytes]:
    """Every generated path (relative to root) and its exact content."""
    tree = source_tree(root, config)
    agents = load_agents(root, tree)
    prompts = load_prompts(root, agents, tree)
    plugin = plugin_dir(config)
    files: dict[Path, bytes] = {}

    def put(path: str, text: str) -> None:
        files[Path(path)] = text.encode("utf-8")

    for agent in agents.values():
        put(f".github/agents/{agent.name}.agent.md", copilot_agent(agent, agents, config))
        if agent.role == "specialist":
            put(f".claude/agents/{agent.name}.md", claude_agent(agent, config))
            put(f"{plugin}/agents/{agent.name}.md", claude_agent(agent, config))
    for prompt in prompts.values():
        put(f".github/prompts/{prompt.name}.prompt.md", copilot_prompt(prompt, agents))
        put(f".claude/skills/{prompt.name}/SKILL.md", claude_prompt_skill(prompt, agents, config=config))
        put(f"{plugin}/skills/{prompt.name}/SKILL.md", claude_prompt_skill(prompt, agents, plugin=True, config=config))

    for key, path in tree.items():
        if not key.startswith("skills/"):
            continue
        rel = Path(key).relative_to("skills")
        source = path.relative_to(root).as_posix()
        data = _lf(path.read_bytes())
        if path.name == "SKILL.md":
            data = skill_file(data.decode("utf-8"), source).encode("utf-8")
        for target in (".github/skills", ".claude/skills"):
            files[Path(target) / rel] = data
        # The plugin has no docs/ or repository config, so links that climb out of the
        # skill folder point at the repository on GitHub instead.
        files[Path(plugin) / "skills" / rel] = (
            data.replace(b"](../../../", f"]({config.plugin.repo_url}/blob/main/".encode())
            if path.suffix == ".md" else data
        )
        if rel.parts[0] in prompts:
            raise ValueError(f"skill {rel.parts[0]!r} collides with a prompt of the same name")

    instructions = rules_text(root, config)
    put(".github/copilot-instructions.md", copilot_instructions(instructions))

    # Claude Code plugin (see docs/claude-code-plugin.md).
    version = package_version(root)
    put(".claude-plugin/marketplace.json", marketplace_manifest(config))
    put(f"{plugin}/.claude-plugin/plugin.json", plugin_manifest(version, config))
    put(f"{plugin}/hooks/hooks.json", plugin_hooks())
    put(f"{plugin}/README.md", plugin_readme(version, config))
    put(f"{plugin}/instructions.md", instructions)
    for name in PLUGIN_SCRIPTS:
        files[Path(plugin) / "scripts" / name] = _lf((root / "scripts" / name).read_bytes())
    # The hooks run from the plugin folder, so they carry their own artifact_tools copy.
    # The agents use the installed aegis-sdlc CLI instead.
    for path in sorted((root / "src" / "artifact_tools").glob("*.py")):
        files[Path(plugin) / "src" / "artifact_tools" / path.name] = _lf(path.read_bytes())

    # The agents and skills name the standards server in prose as well as in their tools.
    if config.standards_server != DEFAULT_STANDARDS_SERVER:
        for rel, data in files.items():
            if rel.suffix == ".md":
                files[rel] = _SERVER_MENTION_RE.sub(config.standards_server, data.decode("utf-8")).encode("utf-8")
    return files


def owned_dirs(config: AegisConfig = DEFAULT_CONFIG) -> tuple[str, ...]:
    """Directories whose contents this script owns entirely.

    The default plugin folder stays owned when the plugin is renamed, so it is removed.
    """
    dirs = (
        ".github/agents", ".github/prompts", ".github/skills",
        ".claude/agents", ".claude/skills",
        ".claude-plugin", f"plugins/{DEFAULT_PLUGIN_NAME}",
    )
    return dirs if config.plugin.name == DEFAULT_PLUGIN_NAME else (*dirs, plugin_dir(config))


_NUL = bytes([0])
_CRLF = bytes([13, 10])
_LF = bytes([10])


def _lf(data: bytes) -> bytes:
    """Normalize CRLF to LF for text; leave binary files untouched."""
    if _NUL in data:
        return data
    return data.replace(_CRLF, _LF)


def stale_files(
    root: Path, files: dict[Path, bytes], owned: tuple[str, ...] | None = None
) -> tuple[list[Path], list[Path]]:
    """(paths whose content differs or is missing, generated-dir paths that should not exist).

    Line endings are ignored: a Windows checkout with core.autocrlf may hold CRLF copies of
    files this script writes with LF.
    """
    changed = [
        rel for rel, data in files.items()
        if not (root / rel).is_file() or _lf((root / rel).read_bytes()) != _lf(data)
    ]
    extra = []
    for directory in owned or owned_dirs():
        base = root / directory
        if base.is_dir():
            for path in base.rglob("*"):
                rel = path.relative_to(root)
                if path.is_file() and "__pycache__" not in path.parts and rel not in files:
                    extra.append(rel)
    return sorted(changed), sorted(extra)


def write(root: Path, files: dict[Path, bytes], owned: tuple[str, ...] | None = None) -> None:
    for directory in owned or owned_dirs():
        shutil.rmtree(root / directory, ignore_errors=True)
    for rel, data in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Report stale generated files and exit 1; write nothing.")
    parser.add_argument(
        "--config", type=Path, default=None,
        help=f"Config file to use. Default: {CONFIG_FILENAME} in the repository root, if present.",
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root.resolve()

    config_path = args.config if args.config is not None else root / CONFIG_FILENAME
    try:
        if not config_path.is_file() and args.config is not None:
            raise ConfigError(f"{config_path} does not exist")
        config = load_config(config_path if config_path.is_file() else None, root=root)
        files = planned_files(root, config)
    except (ConfigError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    owned = owned_dirs(config)
    changed, extra = stale_files(root, files, owned)
    if args.check:
        for rel in changed:
            print(f"stale: {rel.as_posix()}")
        for rel in extra:
            print(f"unexpected: {rel.as_posix()}")
        if changed or extra:
            print("Generated files are out of date. Run: python scripts/sync_platforms.py", file=sys.stderr)
            return 1
        print(f"{len(files)} generated files are up to date.", file=sys.stderr)
        return 0
    write(root, files, owned)
    print(f"Wrote {len(files)} files ({len(changed)} changed, {len(extra)} removed).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
