#!/usr/bin/env python3
"""PreToolUse hook wrapper for bounded implementation-agent operations.

Used by both GitHub Copilot (`.github/hooks/`) and Claude Code (`.claude/settings.json`).

The wrapper fails closed. An agent host lets a tool call proceed when its hook crashes or
prints nothing, so every failure here still produces an explicit decision:

- the guard cannot be imported: ask the user;
- the hook payload cannot be read: ask the user;
- the guard raises while evaluating: deny.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))


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


def main() -> int:
    try:
        from artifact_tools.guard import evaluate_guard
    except Exception as exc:  # noqa: BLE001 - any import failure must not fail open
        return emit("ask", f"AEGIS implementation guard is unavailable ({type(exc).__name__}: {exc}). Approve only if this call is intended.")

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError, ValueError, UnicodeDecodeError):
        payload = None
    if not isinstance(payload, dict):
        return emit("ask", "AEGIS implementation guard could not read the hook payload. Approve only if this call is intended.")

    try:
        decision = evaluate_guard(payload, repo_root=REPO_ROOT)
    except Exception as exc:  # noqa: BLE001 - an evaluation error must not fail open
        return emit("deny", f"AEGIS implementation guard failed ({type(exc).__name__}: {exc}); denying to stay safe.")
    return emit(decision.permission, decision.reason)


if __name__ == "__main__":
    raise SystemExit(main())
