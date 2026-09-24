"""Tests for phase-3 implementation readiness and living execution state."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifact_tools.__main__ import main
from artifact_tools.adr import create_adr
from artifact_tools.constants import ARTIFACT_TYPES
from artifact_tools.frontmatter import render_document, split_document
from artifact_tools.implementation import (
    _collect_required_coverage_ids,
    add_decision,
    approve_release,
    check_readiness,
    create_work_package,
    implementation_status,
    init_implementation,
    record_evidence,
    transition_work_package,
    validate_implementation,
)
from artifact_tools.scaffold import scaffold

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_TEMPLATES = REPO_ROOT / "aegis/skills/artifact-management/assets/templates"
IMPLEMENTATION_TEMPLATES = REPO_ROOT / "aegis/skills/implementation-management/assets/templates"


def _approved_app(root: Path) -> Path:
    app = root / "sample-app"
    for type_key in ARTIFACT_TYPES:
        path = scaffold(type_key, app, project="Sample", templates_dir=ARTIFACT_TEMPLATES)
        text = path.read_text(encoding="utf-8").replace("status: draft", "status: approved", 1)
        path.write_text(text, encoding="utf-8")
    create_adr(
        "Use repository native patterns",
        app / "architecture-decisions",
        status="accepted",
        templates_dir=ARTIFACT_TEMPLATES,
    )
    return app


def _target_workspace(root: Path) -> Path:
    target = root / "target-repository"
    target.mkdir()
    (target / "README.md").write_text("# Target\n", encoding="utf-8")
    return target


def _init(app: Path, target: Path) -> Path:
    return init_implementation(
        app,
        target_workspace=target,
        target_baseline="test-baseline",
        standards_review="verified",
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )


def test_init_creates_canonical_structure_and_is_idempotent(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)

    implementation = _init(app, target)
    assert (implementation / "implementation.md").is_file()
    assert (implementation / "decision.md").is_file()
    assert (implementation / "work-packages").is_dir()

    same = _init(app, target)
    assert same == implementation
    status = implementation_status(app)
    assert status["phase"] == 3
    assert status["target_workspace"] == str(target.resolve())
    assert status["standards_review"] == "verified"


def test_init_rejects_partial_state(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    implementation = app / "implementation"
    implementation.mkdir()
    (implementation / "implementation.md").write_text("partial", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Partial implementation state"):
        _init(app, target)


def test_init_rejects_a_different_recorded_target_configuration(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)

    with pytest.raises(FileExistsError, match="already targets"):
        init_implementation(
            app,
            target_workspace=tmp_path / "different-target",
            target_baseline="test-baseline",
            standards_review="verified",
            templates_dir=IMPLEMENTATION_TEMPLATES,
        )


def test_work_package_creation_updates_pointer_and_validates(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)

    path, work_package_id = create_work_package(
        app,
        "Create service foundation",
        scope="Create the target-native service skeleton.",
        source_ids=["FR-001", "NFR-001", "ADR-0002"],
        target_paths=["apps/sample-service", "libs/sample-common"],
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )

    assert work_package_id == "WP-0001"
    assert path.name == "WP-0001-create-service-foundation.md"
    status = implementation_status(app)
    assert status["next_work_package"] == "WP-0001"
    assert not [finding for finding in validate_implementation(app) if finding.severity == "error"]


def test_invalid_target_path_is_rejected_without_creating_package(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)

    with pytest.raises(ValueError, match="repository-relative"):
        create_work_package(
            app,
            "Escape target",
            scope="Invalid",
            source_ids=["FR-001"],
            target_paths=["../outside"],
            templates_dir=IMPLEMENTATION_TEMPLATES,
        )
    assert list((app / "implementation/work-packages").glob("*.md")) == []


def test_transition_requires_approval_reviewer_pass_and_evidence(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)
    _, work_package_id = create_work_package(
        app,
        "Implement API",
        scope="Implement one endpoint.",
        source_ids=["FR-001", "IF-001"],
        target_paths=["apps/sample-service/src"],
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )

    with pytest.raises(ValueError, match="approved_by"):
        transition_work_package(app, work_package_id, "approved", actor="orchestrator")
    transition_work_package(
        app,
        work_package_id,
        "approved",
        actor="orchestrator",
        approved_by="product-owner",
    )
    transition_work_package(app, work_package_id, "in-progress", actor="service-implementer")
    transition_work_package(app, work_package_id, "review", actor="service-implementer")
    with pytest.raises(ValueError, match="reviewer passes"):
        transition_work_package(app, work_package_id, "complete", actor="artifact-manager")

    transition_work_package(
        app,
        work_package_id,
        "in-progress",
        actor="implementation-reviewer",
        review_status="needs-changes",
    )
    record_evidence(app, work_package_id, "pytest", "pass", "12 tests passed")
    transition_work_package(
        app,
        work_package_id,
        "review",
        actor="service-implementer",
        review_status="pass",
    )
    transition_work_package(app, work_package_id, "complete", actor="artifact-manager")

    assert implementation_status(app)["status"] == "complete"
    findings = validate_implementation(app)
    assert any(item.code == "release-approval" for item in findings)


def test_illegal_transition_is_rejected(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)
    _, work_package_id = create_work_package(
        app,
        "Implement UI",
        scope="UI slice.",
        source_ids=["FR-001"],
        target_paths=["apps/sample-app/src"],
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )

    with pytest.raises(ValueError, match="Illegal work-package transition"):
        transition_work_package(app, work_package_id, "complete", actor="artifact-manager")


def test_material_decision_requires_adr_and_approver(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)

    with pytest.raises(ValueError, match="requires an approver and ADR"):
        add_decision(
            app,
            question="Change database?",
            decision="Use another database",
            rationale="New constraint",
            decision_type="material",
        )

    decision_id = add_decision(
        app,
        question="Which generated folder naming convention?",
        decision="Use repository-standard kebab case",
        rationale="Matches adjacent projects",
        sources=["ADR-0002"],
        affected_paths=["apps/sample-service"],
        approver="delivery-lead",
    )
    assert decision_id == "IDEC-0001"
    assert not [item for item in validate_implementation(app) if item.code == "decision-duplicate"]


def test_decision_supersession_updates_prior_row(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)
    first = add_decision(
        app,
        question="Fixture naming?",
        decision="Use builders",
        rationale="Initial convention",
    )
    second = add_decision(
        app,
        question="Fixture naming?",
        decision="Use factories",
        rationale="Matches target repository",
        supersedes=first,
    )

    body = (app / "implementation/decision.md").read_text(encoding="utf-8")
    assert second == "IDEC-0002"
    assert f"| {first} |" in body
    assert "| superseded |" in body
    assert f"Superseded by {second}" in body


def test_dependency_cycle_is_reported(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)
    first_path, first = create_work_package(
        app,
        "First",
        scope="First.",
        source_ids=["FR-001"],
        target_paths=["apps/a"],
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )
    _, second = create_work_package(
        app,
        "Second",
        scope="Second.",
        source_ids=["FR-001"],
        target_paths=["apps/b"],
        dependencies=[first],
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )
    fm, body = split_document(first_path.read_text(encoding="utf-8"))
    assert fm is not None
    fm["dependencies"] = [second]
    first_path.write_text(render_document(fm, body), encoding="utf-8")

    findings = validate_implementation(app)
    assert any(item.code == "dependency-cycle" for item in findings)


def test_source_version_drift_invalidates_work_package(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)
    create_work_package(
        app,
        "Requirement-backed slice",
        scope="Implement FR-001.",
        source_ids=["FR-001"],
        target_paths=["apps/sample"],
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )
    requirement_path = app / "functional-requirements.md"
    fm, body = split_document(requirement_path.read_text(encoding="utf-8"))
    assert fm is not None
    fm["version"] = "9.9"
    requirement_path.write_text(render_document(fm, body), encoding="utf-8")

    findings = validate_implementation(app)
    assert any(item.code == "source-drift" and "functional-requirements.md" in item.message for item in findings)


def test_parallel_active_path_overlap_is_rejected(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)
    _, first = create_work_package(
        app,
        "First",
        scope="First.",
        source_ids=["FR-001"],
        target_paths=["apps/sample/src"],
        parallel_group="parallel-a",
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )
    _, second = create_work_package(
        app,
        "Second",
        scope="Second.",
        source_ids=["FR-001"],
        target_paths=["apps/sample/src/components"],
        parallel_group="parallel-a",
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )
    for work_package_id in (first, second):
        transition_work_package(
            app,
            work_package_id,
            "approved",
            actor="orchestrator",
            approved_by="delivery-lead",
        )
        transition_work_package(app, work_package_id, "in-progress", actor="implementer")

    findings = validate_implementation(app)
    assert any(item.code == "parallel-path-overlap" for item in findings)


def test_approved_synthetic_application_is_ready(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)

    report = check_readiness(app, target_workspace=target, standards_review="verified")
    assert report.ready, [item.format() for item in report.findings]


def test_draft_application_is_blocked_without_writes(tmp_path: Path):
    app = tmp_path / "draft-app"
    for type_key in ARTIFACT_TYPES:
        scaffold(type_key, app, project="Draft", templates_dir=ARTIFACT_TEMPLATES)
    target = _target_workspace(tmp_path)
    before = sorted(str(path.relative_to(app)) for path in app.rglob("*"))

    report = check_readiness(app, target_workspace=target, standards_review="manual-review-required")

    assert not report.ready
    codes = {item.code for item in report.findings}
    assert "artifact-not-approved" in codes
    assert "standards-review" in codes
    after = sorted(str(path.relative_to(app)) for path in app.rglob("*"))
    assert after == before
    assert not (app / "implementation").exists()


def test_release_approval_requires_complete_coverage_and_records_approver(tmp_path: Path):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    _init(app, target)
    coverage = sorted(_collect_required_coverage_ids(app))
    _, work_package_id = create_work_package(
        app,
        "Complete implementation",
        scope="Synthetic full-coverage implementation.",
        source_ids=coverage,
        target_paths=["apps/sample"],
        templates_dir=IMPLEMENTATION_TEMPLATES,
    )
    transition_work_package(
        app,
        work_package_id,
        "approved",
        actor="orchestrator",
        approved_by="delivery-lead",
    )
    transition_work_package(app, work_package_id, "in-progress", actor="implementer")
    record_evidence(app, work_package_id, "pytest", "pass", "All checks passed")
    transition_work_package(
        app,
        work_package_id,
        "review",
        actor="implementer",
        review_status="pass",
    )
    transition_work_package(app, work_package_id, "complete", actor="artifact-manager")

    approve_release(app, approver="release-owner", note="Synthetic release gate")
    status = implementation_status(app)
    assert status["release_approved"] is True
    assert status["release_approved_by"] == "release-owner"
    assert not [item for item in validate_implementation(app) if item.severity == "error"]


def test_cli_init_status_and_validation(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    app = _approved_app(tmp_path)
    target = _target_workspace(tmp_path)
    monkeypatch.chdir(REPO_ROOT)

    assert main([
        "implementation",
        "init",
        str(app),
        str(target),
        "--target-baseline",
        "test-baseline",
        "--standards-review",
        "verified",
    ]) == 0
    assert main(["implementation", "status", str(app)]) == 0
    assert main(["implementation", "validate", str(app), "--strict"]) == 0
    output = capsys.readouterr().out
    assert "initialised implementation state" in output
    assert '"phase": 3' in output
    assert "implementation validation OK" in output


def test_atomic_write_retries_transient_windows_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from artifact_tools import implementation

    real_replace = Path.replace
    calls = {"count": 0}

    def flaky_replace(self, target):
        calls["count"] += 1
        if calls["count"] < 3:
            raise PermissionError("[WinError 5] Access is denied")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)
    monkeypatch.setattr(implementation, "_REPLACE_FIRST_DELAY", 0)
    target = tmp_path / "implementation.md"
    implementation._atomic_write(target, "content\n")
    assert target.read_text(encoding="utf-8") == "content\n"
    assert calls["count"] == 3
    assert not list(tmp_path.glob("*.tmp"))


def test_atomic_write_gives_up_and_cleans_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from artifact_tools import implementation

    def locked(self, target):
        raise PermissionError("[WinError 5] Access is denied")

    monkeypatch.setattr(Path, "replace", locked)
    monkeypatch.setattr(implementation, "_REPLACE_FIRST_DELAY", 0)
    with pytest.raises(PermissionError):
        implementation._atomic_write(tmp_path / "implementation.md", "content\n")
    assert not list(tmp_path.glob("*.tmp"))
