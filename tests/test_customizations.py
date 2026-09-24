"""Structural tests for the generated GitHub Copilot customizations and hook discovery."""

from __future__ import annotations

import json
from pathlib import Path

from artifact_tools.frontmatter import split_document

REPO_ROOT = Path(__file__).resolve().parents[1]
GITHUB = REPO_ROOT / ".github"


def _frontmatter(path: Path) -> dict:
    frontmatter, _ = split_document(path.read_text(encoding="utf-8"))
    assert frontmatter is not None, f"missing frontmatter: {path}"
    return frontmatter


def test_all_agents_have_unique_discoverable_frontmatter():
    files = sorted((GITHUB / "agents").glob("*.agent.md"))
    records = [_frontmatter(path) for path in files]
    names = [record.get("name") for record in records]
    assert all(names), "every agent requires a name"
    assert len(names) == len(set(names)), "agent names must be unique"
    for path, record in zip(files, records, strict=True):
        assert record.get("description"), f"missing description: {path}"
        assert isinstance(record.get("tools"), list) and record["tools"], f"missing tools: {path}"


def test_prompt_agents_and_handoffs_resolve():
    agent_records = {
        record["name"]: record
        for record in (_frontmatter(path) for path in (GITHUB / "agents").glob("*.agent.md"))
    }
    for path in (GITHUB / "prompts").glob("*.prompt.md"):
        record = _frontmatter(path)
        assert record.get("description"), f"missing description: {path}"
        assert record.get("agent") in agent_records, f"unknown prompt agent in {path}: {record.get('agent')}"
    for agent_name, record in agent_records.items():
        for handoff in record.get("handoffs") or ():
            assert handoff.get("agent") in agent_records, (
                f"unknown handoff agent from {agent_name}: {handoff.get('agent')}"
            )
            assert handoff.get("label") and handoff.get("prompt")


def test_skills_have_matching_names_and_discovery_descriptions():
    for path in (GITHUB / "skills").glob("*/SKILL.md"):
        record = _frontmatter(path)
        assert record.get("name") == path.parent.name, f"skill name/folder mismatch: {path}"
        assert record.get("description"), f"missing description: {path}"


def test_hook_configuration_has_guard_and_validation_commands():
    path = GITHUB / "hooks/validate-artifacts.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    hooks = data["hooks"]
    assert set(hooks) == {"PreToolUse", "PostToolUse"}
    assert "implementation_guard.py" in hooks["PreToolUse"][0]["command"]
    assert "validate_hook.py" in hooks["PostToolUse"][0]["command"]
    for event in hooks.values():
        assert event[0]["type"] == "command"
        assert event[0]["timeout"] <= 30
