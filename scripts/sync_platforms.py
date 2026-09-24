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

Usage::

    python scripts/sync_platforms.py            # write the generated files
    python scripts/sync_platforms.py --check    # exit 1 if any generated file is stale
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
SOURCE = Path("aegis")

GENERATED_NOTE = "Generated from {source} by scripts/sync_platforms.py. Edit the source, not this file."

# Neutral tool names (Copilot vocabulary) and their Claude Code equivalents.
STANDARDS_TOOL = "standards"
COPILOT_STANDARDS_TOOL = "enterprise-standards-server/*"
CLAUDE_TOOLS = {
    "read": ["Read"],
    "search": ["Grep", "Glob"],
    "edit": ["Edit", "Write"],
    "execute": ["Bash"],
    "agent": ["Agent"],
    "todo": [],
    STANDARDS_TOOL: ["mcp__enterprise-standards-server"],
}

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


def load_agents(root: Path) -> dict[str, Agent]:
    agents = {}
    for path in sorted((root / SOURCE / "agents").glob("*.md")):
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


def load_prompts(root: Path, agents: dict[str, Agent]) -> dict[str, Prompt]:
    prompts = {}
    for path in sorted((root / SOURCE / "prompts").glob("*.md")):
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


def copilot_agent(agent: Agent, agents: dict[str, Agent]) -> str:
    tools = ", ".join(f"'{COPILOT_STANDARDS_TOOL}'" if t == STANDARDS_TOOL else t for t in agent.tools)
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


def _claude_tools(agent: Agent) -> str:
    names: list[str] = []
    for tool in agent.tools:
        for name in CLAUDE_TOOLS[tool]:
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


def claude_agent(agent: Agent) -> str:
    lines = [
        "---",
        _note(agent.source),
        f"name: {agent.name}",
        f"description: {_q(agent.description)}",
        f"tools: {_claude_tools(agent)}",
        "---",
    ]
    return "\n".join(lines) + "\n" + CLAUDE_SPECIALIST_PREAMBLE + agent.body


def _inline_links(body: str) -> str:
    """Agent bodies link to ``../skills/<name>``; prompt skills sit one level deeper."""
    return body.replace("](../skills/", "](../")


def _orchestrator_preamble(agent: Agent, agents: dict[str, Agent]) -> str:
    specialists = ", ".join(f"`{h['agent']}`" for h in agent.handoffs)
    return f"""\
## How to run this in Claude Code

For this request you are the **{agent.title}**, working in the main conversation. You talk
to the user directly and delegate specialist work to subagents.

- **Delegate** with the Agent tool. Specialists for this role: {specialists}. Subagents
  cannot see this conversation, so give each one the application's `docs/artifacts/<app>`
  path, the relevant ids and every decision it needs.
- **Relay hand-offs.** When a subagent's final message hands work to another agent (for
  example "for `artifact-manager`: ..."), delegate that work to the named subagent.
- **Ask the user** with the AskUserQuestion tool, one to three focused questions at a time.
- **Track progress** with the task list.
- **Follow the golden rules** in `CLAUDE.md`, including that only `artifact-manager` writes
  under `docs/artifacts/`.

"""


def claude_prompt_skill(prompt: Prompt, agents: dict[str, Agent]) -> str:
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
        return header + _orchestrator_preamble(target, agents) + role + request
    delegate = f"""\
## How to run this in Claude Code

Delegate this request to the `{target.name}` subagent with the Agent tool. Pass it the
request below, the user's arguments and the application's `docs/artifacts/<app>` path.
If it needs a decision, ask the user with AskUserQuestion and send the answer back to it.
If its final message hands work to another agent, delegate that work to the named
subagent. Report the outcome to the user.

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


def planned_files(root: Path) -> dict[Path, bytes]:
    """Every generated path (relative to root) and its exact content."""
    agents = load_agents(root)
    prompts = load_prompts(root, agents)
    files: dict[Path, bytes] = {}

    def put(path: str, text: str) -> None:
        files[Path(path)] = text.encode("utf-8")

    for agent in agents.values():
        put(f".github/agents/{agent.name}.agent.md", copilot_agent(agent, agents))
        if agent.role == "specialist":
            put(f".claude/agents/{agent.name}.md", claude_agent(agent))
    for prompt in prompts.values():
        put(f".github/prompts/{prompt.name}.prompt.md", copilot_prompt(prompt, agents))
        put(f".claude/skills/{prompt.name}/SKILL.md", claude_prompt_skill(prompt, agents))

    skills_root = root / SOURCE / "skills"
    for path in sorted(p for p in skills_root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        rel = path.relative_to(skills_root)
        source = path.relative_to(root).as_posix()
        data = _lf(path.read_bytes())
        if path.name == "SKILL.md":
            data = skill_file(data.decode("utf-8"), source).encode("utf-8")
        for target in (".github/skills", ".claude/skills"):
            files[Path(target) / rel] = data
        if rel.parts[0] in prompts:
            raise ValueError(f"skill {rel.parts[0]!r} collides with a prompt of the same name")

    put(".github/copilot-instructions.md", copilot_instructions((root / SOURCE / "instructions.md").read_text(encoding="utf-8")))
    return files


# Directories whose contents this script owns entirely.
OWNED_DIRS = (".github/agents", ".github/prompts", ".github/skills", ".claude/agents", ".claude/skills")


_NUL = bytes([0])
_CRLF = bytes([13, 10])
_LF = bytes([10])


def _lf(data: bytes) -> bytes:
    """Normalize CRLF to LF for text; leave binary files untouched."""
    if _NUL in data:
        return data
    return data.replace(_CRLF, _LF)


def stale_files(root: Path, files: dict[Path, bytes]) -> tuple[list[Path], list[Path]]:
    """(paths whose content differs or is missing, generated-dir paths that should not exist).

    Line endings are ignored: a Windows checkout with core.autocrlf may hold CRLF copies of
    files this script writes with LF.
    """
    changed = [
        rel for rel, data in files.items()
        if not (root / rel).is_file() or _lf((root / rel).read_bytes()) != _lf(data)
    ]
    extra = []
    for owned in OWNED_DIRS:
        base = root / owned
        if base.is_dir():
            for path in base.rglob("*"):
                rel = path.relative_to(root)
                if path.is_file() and "__pycache__" not in path.parts and rel not in files:
                    extra.append(rel)
    return sorted(changed), sorted(extra)


def write(root: Path, files: dict[Path, bytes]) -> None:
    for owned in OWNED_DIRS:
        shutil.rmtree(root / owned, ignore_errors=True)
    for rel, data in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Report stale generated files and exit 1; write nothing.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root.resolve()

    files = planned_files(root)
    changed, extra = stale_files(root, files)
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
    write(root, files)
    print(f"Wrote {len(files)} files ({len(changed)} changed, {len(extra)} removed).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
