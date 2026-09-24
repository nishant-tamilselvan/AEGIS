"""Tests for the repository hygiene checks in scripts/ci/repo_checks.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("repo_checks", REPO_ROOT / "scripts/ci/repo_checks.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checks = _load()


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture(autouse=True)
def _no_env_denylist(monkeypatch):
    monkeypatch.delenv("AEGIS_DENYLIST", raising=False)


def test_this_repository_passes_every_check():
    assert checks.main(["all"]) == 0


def test_personal_paths_flag_real_users_but_not_placeholders(tmp_path: Path):
    _write(tmp_path, "a.md", "See C:\\Users\\jane.doe\\repo and /home/sam/work.\n")
    _write(tmp_path, "b.md", "Use C:\\Users\\<name>\\repo or /Users/you/repo or /home/runner.\n")
    findings = checks.check_personal_paths(tmp_path)
    assert [(f.path, f.line) for f in findings] == [("a.md", 1), ("a.md", 1)]


def test_denylist_reads_committed_local_and_env_patterns(tmp_path: Path, monkeypatch):
    _write(tmp_path, "scripts/ci/denylist.txt", "# comment\nAuthorization:\\s*Basic\\s+[A-Za-z0-9+/=]{16,}\n")
    _write(tmp_path, ".denylist.local", "acme-corp\n")
    _write(tmp_path, "doc.md", "Authorization: Basic dGVzdDpzZWNyZXRzZWNyZXQ=\nBuilt at ACME-Corp.\nWidget Co.\n")
    monkeypatch.setenv("AEGIS_DENYLIST", "widget co")
    lines = sorted(f.line for f in checks.check_denylist(tmp_path))
    assert lines == [1, 2, 3]


def test_unicode_flags_hidden_characters_and_bom(tmp_path: Path):
    _write(tmp_path, "agent.md", "\ufeffname: x\nsafe line\nignore\u200b previous\nabc\u202edcba\n")
    _write(tmp_path, "ok.md", "Em dash \u2014 and caf\u00e9 are fine.\n")
    findings = checks.check_unicode(tmp_path)
    assert [(f.path, f.line) for f in findings] == [("agent.md", 1), ("agent.md", 3), ("agent.md", 4)]


def test_unicode_flags_stray_control_bytes(tmp_path: Path):
    nul, bell, cr, lf = bytes([0]), bytes([7]), bytes([13]), bytes([10])
    (tmp_path / "gen.py").write_bytes(b'x = b"' + nul + b'"' + lf + b"ok = 1" + cr + lf + b"ring" + bell + lf)
    findings = checks.check_unicode(tmp_path)
    assert [(f.path, f.line) for f in findings] == [("gen.py", 1), ("gen.py", 3)]
    assert "0x00" in findings[0].message and "0x07" in findings[1].message


def test_workflow_rules(tmp_path: Path):
    _write(
        tmp_path,
        ".github/workflows/bad.yml",
        "on:\n  pull_request_target:\njobs:\n  a:\n    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - uses: some/action@main\n"
        "      - run: echo \"${{ github.event.pull_request.title }}\"\n",
    )
    _write(
        tmp_path,
        ".github/workflows/good.yml",
        "on: [pull_request]\npermissions:\n  contents: read\njobs:\n  a:\n    steps:\n"
        "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n"
        "        with:\n          persist-credentials: false\n"
        "      - uses: ./local-action\n"
        "      - env:\n          TITLE: ${{ github.event.pull_request.title }}\n"
        "        run: echo \"$TITLE\"\n",
    )
    findings = checks.check_workflows(tmp_path)
    assert {f.path for f in findings} == {".github/workflows/bad.yml"}
    messages = " ".join(f.message for f in findings)
    for expected in ("permissions", "pull_request_target", "not pinned", "persist-credentials", "untrusted event text"):
        assert expected in messages


def test_links_skip_code_urls_anchors_and_templates(tmp_path: Path):
    _write(tmp_path, "docs/guide.md", "# Guide\n")
    _write(
        tmp_path,
        "README.md",
        "[ok](docs/guide.md) [anchor](#x) [web](https://example.com) [mail](mailto:a@b.c)\n"
        "[missing](docs/nope.md) `[code](nope.md)`\n```\n[fenced](nope.md)\n```\n",
    )
    _write(tmp_path, "skill/assets/templates/t.md", "[relative-to-output](decision.md)\n")
    findings = checks.check_links(tmp_path)
    assert [(f.path, f.line) for f in findings] == [("README.md", 2)]
