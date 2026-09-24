#!/usr/bin/env python3
"""SessionStart hook for the AEGIS Claude Code plugin.

A plugin cannot edit the user's CLAUDE.md, so this hook delivers the AEGIS golden rules
as session context. It also checks that the ``aegis-sdlc`` CLI, which the agents call as
``python -m artifact_tools``, is installed, and tells the user how to install it if not.

It never blocks a session: any problem becomes a message, and the exit code is always 0.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
# In the plugin the rules sit at the plugin root; in a clone they are in aegis/.
RULE_FILES = (SCRIPT_ROOT / "instructions.md", SCRIPT_ROOT / "aegis" / "instructions.md")
INSTALL_HINT = "The AEGIS CLI is not installed for this Python. Run: pip install aegis-sdlc"


def cli_installed() -> bool:
    """Whether artifact_tools is importable from the environment, not the vendored copy."""
    return importlib.util.find_spec("artifact_tools") is not None


def build_output(rules: str | None, installed: bool) -> dict:
    parts = []
    if rules:
        parts.append("# AEGIS golden rules (from the AEGIS plugin)\n\n" + rules.strip())
    else:
        parts.append("AEGIS plugin: the golden rules file is missing from the plugin folder. Reinstall the plugin.")
    if not installed:
        parts.append(f"Note: {INSTALL_HINT}. Until then, artifact_tools commands will fail.")
    output: dict = {
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n\n".join(parts)}
    }
    if not installed:
        output["systemMessage"] = f"AEGIS: {INSTALL_HINT}"
    return output


def main() -> int:
    try:
        sys.stdin.read()
    except Exception:  # noqa: BLE001 - drain the payload if there is one
        pass
    rules = next((path.read_text(encoding="utf-8") for path in RULE_FILES if path.is_file()), None)
    print(json.dumps(build_output(rules, cli_installed())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
