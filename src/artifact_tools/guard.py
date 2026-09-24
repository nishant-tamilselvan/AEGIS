"""PreToolUse policy evaluation for bounded AEGIS implementation agents."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from artifact_tools.frontmatter import split_document
from artifact_tools.implementation import (
    POINTER_FILE,
    WORK_PACKAGES_DIR,
    implementation_status,
)
from artifact_tools.validate import discover_app_dirs

IMPLEMENTATION_CODE_AGENTS = frozenset(
    {
        "data contract implementer",
        "service implementer",
        "ui implementer",
        "platform implementer",
        "test quality engineer",
    }
)
# VS Code Copilot and Claude Code tool names that modify files.
_WRITE_TOOLS = frozenset(
    {"apply_patch", "create_file", "edit", "write", "replace_string_in_file", "multiedit", "notebookedit"}
)
_SHELL_FILE_EDIT_RE = re.compile(
    r"(?:\b(?:set-content|out-file|add-content|new-item|copy-item|move-item)\b|(?:^|\s)>{1,2}\s*[^&])",
    re.IGNORECASE,
)
_DESTRUCTIVE_RE = re.compile(
    r"(?:\bgit\s+(?:reset\s+--hard|clean\s+-)|\b(?:rm|del|remove-item)\b|"
    r"\b(?:kubectl|oc)\s+delete\b|\bhelm\s+uninstall\b|\bterraform\s+destroy\b)",
    re.IGNORECASE,
)
_DEPLOY_RE = re.compile(
    r"(?:\b(?:kubectl|oc)\s+apply\b|\bhelm\s+(?:install|upgrade)\b|"
    r"\bterraform\s+apply\b|\baz\s+(?:deployment|webapp)\b)",
    re.IGNORECASE,
)
_PATCH_PATH_RE = re.compile(r"^\*\*\*\s+(?:Add|Update|Delete)\s+File:\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class GuardDecision:
    """Permission decision returned to the Copilot or Claude Code hook wrapper."""

    permission: str
    reason: str


def _normalise_agent(value: object) -> str:
    return re.sub(r"[-_]+", " ", str(value or "")).strip().casefold()


def _payload_agent(payload: dict[str, Any]) -> str:
    # Copilot sends agentName; Claude Code sends agent_type for calls made by a subagent.
    direct = payload.get("agentName") or payload.get("agent_name") or payload.get("agent_type")
    if direct:
        return _normalise_agent(direct)
    agent = payload.get("agent")
    if isinstance(agent, dict):
        return _normalise_agent(agent.get("name"))
    return _normalise_agent(agent)


def _payload_tool(payload: dict[str, Any]) -> str:
    return str(payload.get("toolName") or payload.get("tool_name") or "").strip().casefold()


def _payload_args(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("toolArgs") or payload.get("tool_args") or payload.get("toolInput") or payload.get("tool_input") or {}
    return value if isinstance(value, dict) else {"input": value}


def _iter_strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _iter_strings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _iter_strings(child)


def _extract_paths(args: dict[str, Any]) -> list[Path]:
    raw_paths: list[str] = []
    for key in ("filePath", "file_path", "notebook_path", "path", "uri"):
        value = args.get(key)
        if isinstance(value, str) and value:
            raw_paths.append(value.removeprefix("file:///"))
    for text in _iter_strings(args):
        raw_paths.extend(_PATCH_PATH_RE.findall(text))
    paths: list[Path] = []
    for value in dict.fromkeys(item.strip() for item in raw_paths):
        try:
            path = Path(value)
            if path.is_absolute():
                paths.append(path.resolve())
        except (OSError, ValueError):
            continue
    return paths


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _implementation_apps(repo_root: Path) -> list[Path]:
    artifact_root = repo_root / "docs" / "artifacts"
    return [
        app
        for app in discover_app_dirs(artifact_root)
        if (app / "implementation" / POINTER_FILE).is_file()
    ]


def _active_package(app: Path) -> tuple[dict, dict] | None:
    pointer = implementation_status(app)
    active = pointer.get("active_work_package")
    if not isinstance(active, str):
        return None
    for path in (app / "implementation" / WORK_PACKAGES_DIR).glob("WP-*.md"):
        fm, _ = split_document(path.read_text(encoding="utf-8"))
        if fm and fm.get("id") == active:
            return pointer, fm
    return None


def _target_app_for_path(path: Path, apps: Iterable[Path]) -> Path | None:
    for app in apps:
        try:
            target = Path(str(implementation_status(app).get("target_workspace", ""))).resolve()
        except (OSError, ValueError):
            continue
        if _is_within(path, target):
            return app
    return None


def evaluate_guard(payload: dict[str, Any], *, repo_root: str | Path) -> GuardDecision:
    """Evaluate one tool request without executing it or modifying state."""

    root = Path(repo_root).resolve()
    agent = _payload_agent(payload)
    tool = _payload_tool(payload)
    args = _payload_args(payload)
    is_code_agent = agent in IMPLEMENTATION_CODE_AGENTS
    if not is_code_agent:
        return GuardDecision("allow", "No implementation code-agent policy applies.")

    paths = _extract_paths(args)
    artifact_root = root / "docs" / "artifacts"
    if any(_is_within(path, artifact_root) for path in paths):
        return GuardDecision(
            "deny",
            "Implementation code agents cannot write under docs/artifacts; delegate to Artifact Manager or ADR Author.",
        )

    apps = _implementation_apps(root)
    command = str(args.get("command") or args.get("input") or "")
    state_app = next((_target_app_for_path(path, apps) for path in paths if _target_app_for_path(path, apps)), None)
    if state_app is None and len(apps) == 1:
        state_app = apps[0]
    if state_app is None:
        return GuardDecision("deny", "No initialized implementation state resolves this target operation.")

    active = _active_package(state_app)
    if active is None:
        return GuardDecision("deny", "No single active work package authorizes implementation changes.")
    pointer, work_package = active
    if work_package.get("status") != "in-progress":
        return GuardDecision("deny", "Target writes require an in-progress work package; review packages are read-only.")

    target_root = Path(str(pointer["target_workspace"])).resolve()
    allowed_roots = [(target_root / str(value)).resolve() for value in work_package.get("target_paths") or ()]
    for path in paths:
        if _is_within(path, target_root) and not any(_is_within(path, allowed) for allowed in allowed_roots):
            return GuardDecision(
                "deny",
                f"Path {path} is outside the active work package's declared target paths.",
            )

    if _DESTRUCTIVE_RE.search(command):
        return GuardDecision("ask", "Destructive commands require explicit human approval at a material gate.")
    if _DEPLOY_RE.search(command) and not pointer.get("release_approved"):
        return GuardDecision("ask", "Deployment requires an explicitly approved release gate.")
    if _SHELL_FILE_EDIT_RE.search(command):
        return GuardDecision(
            "deny",
            "Implementation code agents must use bounded file-edit tools, not shell-based file writes.",
        )
    if tool in _WRITE_TOOLS or paths or command:
        return GuardDecision("allow", f"Authorized by active work package {work_package.get('id')}.")
    return GuardDecision("allow", "Read-only or non-mutating operation.")
