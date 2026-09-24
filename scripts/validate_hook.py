#!/usr/bin/env python3
"""PostToolUse hook: validate artifacts and surface consistency errors.

Reads the hook JSON payload from stdin (ignored here) and runs the artifact
validator. It is intentionally *advisory*: it never blocks the tool (always exits
0) and only emits a systemMessage when the artifact set has errors, so the agent is
nudged to self-correct without interrupting flow.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Where this script's own copy of artifact_tools lives (the clone, or a plugin folder).
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
# The repository whose artifacts are validated. A plugin passes --repo-root, because the
# script then lives in the plugin folder rather than in the user's repository.
REPO_ROOT = SCRIPT_ROOT


def hook_output(message: str, platform: str) -> dict:
    """Shape the advisory message for the calling agent host.

    Copilot shows ``systemMessage`` to the agent. Claude Code shows ``systemMessage`` only
    to the user, so the model receives the message through ``additionalContext``.
    """
    if platform == "claude":
        return {
            "systemMessage": "AEGIS: artifact validation found consistency errors.",
            "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": message},
        }
    return {"systemMessage": message}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PostToolUse artifact validation hook.")
    parser.add_argument("--platform", choices=["copilot", "claude"], default="copilot")
    parser.add_argument("--repo-root", type=Path, default=None, help="Repository to validate (default: the script's own).")
    args, _unknown = parser.parse_known_args(argv)
    artifact_dir = (args.repo_root or REPO_ROOT).resolve() / "docs" / "artifacts"

    # Drain stdin so the caller does not block on an unread pipe.
    try:
        sys.stdin.read()
    except Exception:  # noqa: BLE001
        # An unreadable or closed stdin is harmless here: the payload is not used.
        pass

    if not artifact_dir.is_dir():
        return 0  # nothing to validate yet

    # Validate whether artifacts live directly in docs/artifacts (single app) or in
    # per-application subfolders (docs/artifacts/<app>/...). validate_dir handles both.
    has_root_docs = any(artifact_dir.glob("*.md"))
    has_app_folders = any(
        p.is_dir() and (any(p.glob("*.md")) or (p / "architecture-decisions").is_dir())
        for p in artifact_dir.iterdir()
    )
    if not has_root_docs and not has_app_folders:
        return 0  # nothing to validate yet

    sys.path.insert(0, str(SCRIPT_ROOT / "src"))
    try:
        from artifact_tools.validate import validate_dir
    except Exception:
        return 0  # tooling not importable; stay out of the way

    issues = validate_dir(artifact_dir)
    errors = [i for i in issues if i.severity == "error"]
    if not errors:
        return 0

    lines = "\n".join(f"- {i.file}: {i.message}" for i in errors)
    message = (
        "Artifact validation found consistency errors. Delegate to `artifact-manager` "
        f"to fix before ending this phase:\n{lines}"
    )
    print(json.dumps(hook_output(message, args.platform)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
