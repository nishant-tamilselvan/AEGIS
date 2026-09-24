"""Tests for the MkDocs hook that rewrites links leaving docs/ to GitHub URLs."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE = "https://github.com/nishant-tamilselvan/AEGIS"


def _load():
    spec = importlib.util.spec_from_file_location("docs_hooks", REPO_ROOT / "scripts/docs_hooks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hooks = _load()


def test_links_leaving_docs_become_github_urls():
    text = "[c](../CONTRIBUTING.md#checks) [s](../aegis/skills/)"
    assert hooks.rewrite_links(text, "getting-started.md") == (
        f"[c]({BASE}/blob/main/CONTRIBUTING.md#checks) [s]({BASE}/tree/main/aegis/skills)"
    )
    assert hooks.rewrite_links("[id](../../aegis/x.md)", "artifacts/README.md") == f"[id]({BASE}/blob/main/aegis/x.md)"


def test_links_inside_docs_code_and_urls_are_untouched():
    text = "\n".join([
        "[same](agents.md) [anchor](#top) [web](https://example.com) ![img](../assets/logo.svg)",
        "`[code](../CONTRIBUTING.md)`",
        "```",
        "[fenced](../CONTRIBUTING.md)",
        "```",
    ])
    assert hooks.rewrite_links(text, "getting-started.md") == text


def test_every_page_link_resolves_on_the_site_or_on_github():
    """Each rewritten target must exist in the repository."""
    for page in (REPO_ROOT / "docs").rglob("*.md"):
        src = page.relative_to(REPO_ROOT / "docs").as_posix()
        rewritten = hooks.rewrite_links(page.read_text(encoding="utf-8"), src)
        for path in re.findall(rf"\]\({re.escape(BASE)}/(?:blob|tree)/main/([^)#]+)", rewritten):
            assert (REPO_ROOT / path).exists(), (src, path)
