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

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

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
    name = re.sub(r"[-_]+", " ", str(value or "")).strip().casefold()
    return name in IMPLEMENTATION_CODE_AGENTS


def fail(payload: dict, problem: str) -> int:
    if is_code_agent(payload):
        return emit("deny", f"AEGIS implementation guard {problem}; denying to stay safe.")
    return emit("ask", f"AEGIS implementation guard {problem}. Approve only if this call is intended.")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError, ValueError, UnicodeDecodeError):
        payload = None
    if not isinstance(payload, dict):
        return emit("ask", "AEGIS implementation guard could not read the hook payload. Approve only if this call is intended.")

    try:
        from artifact_tools.guard import evaluate_guard
    except Exception as exc:  # noqa: BLE001 - any import failure must not fail open
        return fail(payload, f"is unavailable ({type(exc).__name__}: {exc})")

    try:
        decision = evaluate_guard(payload, repo_root=REPO_ROOT)
    except Exception as exc:  # noqa: BLE001 - an evaluation error must not fail open
        return fail(payload, f"failed ({type(exc).__name__}: {exc})")
    return emit(decision.permission, decision.reason)


if __name__ == "__main__":
    raise SystemExit(main())
