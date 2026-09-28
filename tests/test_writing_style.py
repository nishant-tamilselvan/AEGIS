"""The writing-style checker flags slop, honours its disable markers and passes its own skill."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "aegis/skills/writing-style"
TEMPLATES = sorted(REPO_ROOT.glob("aegis/skills/*/assets/templates/*.md"))
CHECKER = SKILL / "scripts/sloplint.py"


def run(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--errors-only", *map(str, paths)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_checker_flags_a_banned_word(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("We delve into the design.\n", encoding="utf-8", newline="\n")
    result = run(draft)
    assert result.returncode == 1
    assert "banned-word: delve" in result.stdout


def test_checker_skips_disabled_regions_and_code(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(
        "<!-- sloplint-disable -->\nWe delve into it.\n<!-- sloplint-enable -->\n\n"
        "Run `delve` to start.\n",
        encoding="utf-8",
        newline="\n",
    )
    assert run(draft).returncode == 0


def test_skill_file_passes_its_own_checker():
    result = run(SKILL / "SKILL.md")
    assert result.returncode == 0, result.stdout


def test_every_template_passes_the_checker():
    assert TEMPLATES
    result = run(*TEMPLATES)
    assert result.returncode == 0, result.stdout


def test_a_freshly_scaffolded_artifact_set_passes_the_checker(tmp_path):
    from artifact_tools.adr import create_adr
    from artifact_tools.changelog import add_changelog
    from artifact_tools.constants import ARTIFACT_TYPES
    from artifact_tools.scaffold import scaffold

    templates = REPO_ROOT / "aegis/skills/artifact-management/assets/templates"
    for type_key in ARTIFACT_TYPES:
        path = scaffold(type_key, tmp_path, project="Example App", templates_dir=templates)
        add_changelog(path, "Recorded the agreed scope")
    create_adr("Use a relational store", tmp_path / "architecture-decisions", templates_dir=templates)
    result = run(*sorted(tmp_path.rglob("*.md")))
    assert result.returncode == 0, result.stdout
