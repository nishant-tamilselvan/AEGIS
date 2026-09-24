"""The committed todo-list example must stay valid and ready for implementation."""

from __future__ import annotations

from pathlib import Path

from artifact_tools.constants import ARTIFACT_TYPES
from artifact_tools.frontmatter import split_document
from artifact_tools.implementation import check_readiness
from artifact_tools.validate import validate_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples/artifacts/todo-list"


def test_example_has_every_artifact_approved():
    for type_key in ARTIFACT_TYPES:
        path = EXAMPLE / f"{type_key}.md"
        assert path.is_file(), f"missing {path.name}"
        frontmatter, _ = split_document(path.read_text(encoding="utf-8"))
        assert frontmatter["status"] == "approved", path.name


def test_example_passes_strict_validation():
    issues = validate_dir(EXAMPLE, strict=True)
    assert issues == [], [f"{issue.file}: {issue.message}" for issue in issues]


def test_example_is_ready_for_implementation(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "README.md").write_text("# Target\n", encoding="utf-8")
    report = check_readiness(EXAMPLE, target_workspace=target, standards_review="verified")
    assert report.ready, [item.format() for item in report.findings]
