#!/usr/bin/env python3
"""PreToolUse hook wrapper for bounded implementation-agent operations.

Used by both GitHub Copilot (`.github/hooks/`) and Claude Code (`.claude/settings.json`).

An agent host lets a tool call proceed when its hook crashes or prints nothing, so the
wrapper never fails silently. When something goes wrong it still returns a decision:

======================================  ====================  ===========================
Failure                                 Implementation agent  Anyone else
======================================  ====================  ===========================
The hook payload cannot be read         ask                   ask
The guard cannot be imported            deny                  ask
The guard raises while evaluating       deny                  ask
======================================  ====================  ===========================

Implementation agents are always denied on failure, so a broken guard never widens what
they can do. Everyone else is asked rather than denied, so a broken guard cannot lock a
person out of their own session (for example while they edit the guard itself).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Where this script's own copy of artifact_tools lives (the clone, or a plugin folder).
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "src"))
# The repository being guarded. A plugin passes --repo-root, because the script then
# lives in the plugin folder rather than in the user's repository.
REPO_ROOT = SCRIPT_ROOT

# Kept in sync with artifact_tools.guard.IMPLEMENTATION_CODE_AGENTS by a test. Duplicated
# here so the wrapper can classify the caller even when the guard cannot be imported.
IMPLEMENTATION_CODE_AGENTS = frozenset(
    {
        "data contract implementer",
        "service implementer",
        "ui implementer",
        "platform implementer",
        "test quality engineer",
    }
)


def emit(permission: str, reason: str) -> int:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": permission,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    if permission == "deny":
        # Hosts that act on exit code 2 read the reason from stderr.
        print(reason, file=sys.stderr)
        return 2
    return 0


def is_code_agent(payload: dict) -> bool:
    """Whether the caller is an implementation agent (Copilot agentName or Claude agent_type)."""
    value = payload.get("agentName") or payload.get("agent_name") or payload.get("agent_type")
    if not value:
        agent = payload.get("agent")
        value = agent.get("name") if isinstance(agent, dict) else agent
    # Plugin agents are namespaced ("aegis:service-implementer"); compare the bare name.
    name = re.sub(r"[-_]+", " ", str(value or "").rsplit(":", 1)[-1]).strip().casefold()
    return name in IMPLEMENTATION_CODE_AGENTS


def fail(payload: dict, problem: str) -> int:
    if is_code_agent(payload):
        return emit("deny", f"AEGIS implementation guard {problem}; denying to stay safe.")
    return emit("ask", f"AEGIS implementation guard {problem}. Approve only if this call is intended.")


def repo_root_from(argv: list[str]) -> Path | None:
    """The --repo-root value, REPO_ROOT when the option is absent, or None when unusable.

    Parsed by hand: argparse would exit on a bad argument without emitting a decision.
    An option that is given but empty (for example an unset $CLAUDE_PROJECT_DIR) or that
    is not a directory returns None, because falling back to the script's own folder
    would guard the wrong repository and fail open.
    """
    value: str | None = None
    for index, arg in enumerate(argv):
        if arg == "--repo-root":
            value = argv[index + 1] if index + 1 < len(argv) else ""
        elif arg.startswith("--repo-root="):
            value = arg.split("=", 1)[1]
    if value is None:
        return REPO_ROOT
    path = Path(value.strip()) if value.strip() else None
    return path.resolve() if path is not None and path.is_dir() else None


def main(argv: list[str] | None = None) -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError, ValueError, UnicodeDecodeError):
        payload = None
    if not isinstance(payload, dict):
        return emit("ask", "AEGIS implementation guard could not read the hook payload. Approve only if this call is intended.")

    repo_root = repo_root_from(sys.argv[1:] if argv is None else argv)
    if repo_root is None:
        return fail(payload, "could not resolve the repository to guard (--repo-root is empty or not a folder)")

    try:
        from artifact_tools.guard import evaluate_guard
    except Exception as exc:  # noqa: BLE001 - any import failure must not fail open
        return fail(payload, f"is unavailable ({type(exc).__name__}: {exc})")

    try:
        decision = evaluate_guard(payload, repo_root=repo_root)
    except Exception as exc:  # noqa: BLE001 - an evaluation error must not fail open
        return fail(payload, f"failed ({type(exc).__name__}: {exc})")
    return emit(decision.permission, decision.reason)


if __name__ == "__main__":
    raise SystemExit(main())
