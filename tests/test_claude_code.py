"""Tests for the generated Claude Code customizations and the aegis/ single source."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

from artifact_tools.frontmatter import split_document
from artifact_tools.guard import IMPLEMENTATION_CODE_AGENTS, _normalise_agent

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE = REPO_ROOT / ".claude"
KNOWN_CLAUDE_TOOLS = {"Read", "Grep", "Glob", "Edit", "Write", "Bash", "Agent", "mcp__enterprise-standards-server"}


def _load_sync():
    spec = importlib.util.spec_from_file_location("sync_platforms", REPO_ROOT / "scripts/sync_platforms.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sync = _load_sync()


def _frontmatter(path: Path) -> tuple[dict, str]:
    frontmatter, body = split_document(path.read_text(encoding="utf-8"))
    assert frontmatter is not None, f"missing frontmatter: {path}"
    return frontmatter, body


def test_generated_files_are_up_to_date():
    assert sync.main(["--check"]) == 0, "run: python scripts/sync_platforms.py"


def test_check_detects_edits_to_generated_files(tmp_path: Path):
    for name in ("aegis", ".github", ".claude"):
        shutil.copytree(REPO_ROOT / name, tmp_path / name)
    assert sync.main(["--check", "--root", str(tmp_path)]) == 0
    generated = tmp_path / ".claude/agents/artifact-manager.md"
    generated.write_text(generated.read_text(encoding="utf-8") + "\nhand edit\n", encoding="utf-8")
    (tmp_path / ".github/agents/stray.agent.md").write_text("---\n---\n", encoding="utf-8")
    assert sync.main(["--check", "--root", str(tmp_path)]) == 1


def test_check_ignores_crlf_checkouts(tmp_path: Path):
    """A Windows checkout with core.autocrlf holds CRLF copies of LF-generated files."""
    for name in ("aegis", ".github", ".claude"):
        shutil.copytree(REPO_ROOT / name, tmp_path / name)
    crlf = bytes([13, 10])
    lf = bytes([10])
    for path in [*(tmp_path / ".claude").rglob("*.md"), *(tmp_path / "aegis/skills").rglob("*.md")]:
        path.write_bytes(path.read_bytes().replace(lf, crlf))
    assert sync.main(["--check", "--root", str(tmp_path)]) == 0


def test_claude_subagents_are_valid_specialists():
    files = sorted((CLAUDE / "agents").glob("*.md"))
    sources = {path.stem: _frontmatter(path)[0] for path in (REPO_ROOT / "aegis/agents").glob("*.md")}
    specialists = {name for name, fm in sources.items() if fm["role"] == "specialist"}
    assert {path.stem for path in files} == specialists
    for path in files:
        fm, body = _frontmatter(path)
        assert fm["name"] == path.stem
        assert re.fullmatch(r"[a-z][a-z0-9-]*", fm["name"]), fm["name"]
        assert fm.get("description"), path
        tools = {tool.strip() for tool in fm["tools"].split(",")}
        assert tools and tools <= KNOWN_CLAUDE_TOOLS, (path, tools - KNOWN_CLAUDE_TOOLS)
        assert "Agent" not in tools, f"specialists do not delegate: {path}"
        assert "you run as a subagent" in body


def test_guard_recognizes_every_claude_implementation_agent():
    """The guard matches Claude Code's agent_type against IMPLEMENTATION_CODE_AGENTS."""
    claude_names = {_normalise_agent(path.stem) for path in (CLAUDE / "agents").glob("*.md")}
    assert IMPLEMENTATION_CODE_AGENTS <= claude_names
    for name in IMPLEMENTATION_CODE_AGENTS:
        fm, _ = _frontmatter(CLAUDE / "agents" / f"{name.replace(' ', '-')}.md")
        assert "Edit" in fm["tools"] and "Bash" in fm["tools"]


def test_claude_skills_cover_prompts_and_knowledge_skills():
    prompt_names = {path.stem for path in (REPO_ROOT / "aegis/prompts").glob("*.md")}
    knowledge = {path.name for path in (REPO_ROOT / "aegis/skills").iterdir() if path.is_dir()}
    skills = {path.parent.name: path for path in (CLAUDE / "skills").glob("*/SKILL.md")}
    assert set(skills) == prompt_names | knowledge
    agent_names = {path.stem for path in (REPO_ROOT / "aegis/agents").glob("*.md")}
    for name, path in skills.items():
        fm, body = _frontmatter(path)
        assert fm["name"] == name
        assert fm.get("description"), path
        if name in prompt_names:
            assert fm.get("disable-model-invocation") is True, path
            assert "$ARGUMENTS" in body, path
            delegated = re.findall(r"`([a-z][a-z0-9-]+)` subagent", body)
            for line in re.findall(r"Specialists for this role: ([^\n]+)", body):
                delegated += re.findall(r"`([a-z][a-z0-9-]+)`", line)
            assert delegated, f"no delegation target in {path}"
            for slug in delegated:
                assert slug in agent_names, (path, slug)


def test_claude_hooks_run_the_shared_scripts():
    settings = json.loads((CLAUDE / "settings.json").read_text(encoding="utf-8"))
    pre = settings["hooks"]["PreToolUse"][0]
    post = settings["hooks"]["PostToolUse"][0]
    for tool in ("Edit", "Write", "MultiEdit", "Bash"):
        assert tool in pre["matcher"].split("|")
    assert "implementation_guard.py" in pre["hooks"][0]["command"]
    assert "validate_hook.py" in post["hooks"][0]["command"]
    assert "--platform claude" in post["hooks"][0]["command"]
    for event in (pre, post):
        assert event["hooks"][0]["type"] == "command"
        assert event["hooks"][0]["timeout"] <= 30


def test_mcp_examples_use_the_server_name_the_agents_expect():
    claude_example = json.loads((REPO_ROOT / ".mcp.example.json").read_text(encoding="utf-8"))
    vscode_example = json.loads((REPO_ROOT / ".vscode/mcp.example.json").read_text(encoding="utf-8"))
    assert "enterprise-standards-server" in claude_example["mcpServers"]
    assert "enterprise-standards-server" in vscode_example["servers"]


def test_claude_md_imports_the_single_source_rules():
    text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "@aegis/instructions.md" in text
    assert "@AGENTS.md" in text
