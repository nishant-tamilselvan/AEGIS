"""Implementation readiness: the read-only gate before planning or code generation.

Separate from ``implementation`` so that module does not import ``validate``, which
itself validates implementation state. Keeping the two apart avoids an import cycle.
"""

from __future__ import annotations

from pathlib import Path

from artifact_tools.constants import ARTIFACT_TYPES
from artifact_tools.frontmatter import DEFINED_ID_RE
from artifact_tools.implementation import (
    _TBD_RE,
    IMPLEMENTATION_DIR,
    POINTER_FILE,
    ImplementationFinding,
    ReadinessReport,
    _blocking_open_decisions,
    _load_document,
)
from artifact_tools.validate import has_errors, validate_dir

__all__ = ["ReadinessReport", "check_readiness"]


def check_readiness(
    app_dir: str | Path,
    *,
    target_workspace: str | Path,
    standards_review: str | None = None,
) -> ReadinessReport:
    """Evaluate implementation readiness without writing any artifact or target file."""

    app = Path(app_dir).resolve()
    target = Path(target_workspace).resolve()
    findings: list[ImplementationFinding] = []
    if not app.is_dir():
        return ReadinessReport((ImplementationFinding("error", str(app), "application artifact directory does not exist", "app-missing"),))

    artifact_issues = validate_dir(app, strict=True)
    for issue in artifact_issues:
        if issue.severity == "error" or has_errors([issue], strict=True):
            findings.append(ImplementationFinding("error", issue.file, issue.message, "artifact-validation"))

    for type_key, meta in ARTIFACT_TYPES.items():
        path = app / meta["filename"]
        if not path.is_file():
            findings.append(ImplementationFinding("error", path.name, f"required {type_key} artifact is missing", "artifact-missing"))
            continue
        try:
            fm, body = _load_document(path)
        except ValueError as exc:
            findings.append(ImplementationFinding("error", path.name, str(exc), "artifact-invalid"))
            continue
        if fm.get("status") != "approved":
            findings.append(ImplementationFinding("error", path.name, f"artifact status is '{fm.get('status')}', not 'approved'", "artifact-not-approved"))
        for decision_id, decision_text in _blocking_open_decisions(path, body):
            findings.append(ImplementationFinding("error", path.name, f"{decision_id} blocks implementation: {decision_text}", "open-decision"))
        tbd_lines = [line.strip() for line in body.splitlines() if _TBD_RE.search(line)]
        if tbd_lines:
            findings.append(ImplementationFinding("error", path.name, f"contains unresolved TBD content ({len(tbd_lines)} occurrence(s))", "artifact-tbd"))

    interface_path = app / "interface-specifications.md"
    interface_ids: set[str] = set()
    if interface_path.is_file():
        _, interface_body = _load_document(interface_path)
        interface_ids = {item for item in DEFINED_ID_RE.findall(interface_body) if item.startswith("IF-")}
    contract_dir = app / "interfaces"
    contract_files = [] if not contract_dir.is_dir() else [
        path for path in contract_dir.rglob("*")
        if path.is_file() and path.name not in {"README.md", ".gitkeep"} and path.suffix.lower() in {".yaml", ".yml", ".json", ".graphql", ".proto"}
    ]
    if interface_ids and not contract_files:
        findings.append(ImplementationFinding("error", "interfaces/", f"{len(interface_ids)} active IF-* entries have no native contract files", "contracts-missing"))

    adr_dir = app / "architecture-decisions"
    accepted = 0
    if not adr_dir.is_dir():
        findings.append(ImplementationFinding("error", "architecture-decisions/", "ADR directory is missing", "adr-missing"))
    else:
        for path in sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")):
            if path.name == "0001-adr-template.md":
                continue
            fm, _ = _load_document(path)
            status = fm.get("status")
            if status == "accepted":
                accepted += 1
            elif status == "proposed":
                findings.append(ImplementationFinding("error", f"architecture-decisions/{path.name}", f"{fm.get('id')} remains proposed", "adr-proposed"))
        if accepted == 0:
            findings.append(ImplementationFinding("error", "architecture-decisions/", "no accepted architecture decisions were found", "adr-unaccepted"))

    if not target.is_dir():
        findings.append(ImplementationFinding("error", str(target), "target workspace does not exist", "target-missing"))
    else:
        convention_markers = (
            "AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md", "README.md", "package.json", "pyproject.toml", ".github/copilot-instructions.md"
        )
        if not any((target / marker).exists() for marker in convention_markers):
            findings.append(ImplementationFinding("error", str(target), "target workspace has no discoverable repository instructions or build manifest", "target-conventions"))

    effective_standards_review = standards_review
    pointer = app / IMPLEMENTATION_DIR / POINTER_FILE
    if effective_standards_review is None and pointer.is_file():
        pointer_fm, _ = _load_document(pointer)
        effective_standards_review = str(pointer_fm.get("standards_review", "manual-review-required"))
    if effective_standards_review != "verified":
        findings.append(ImplementationFinding("error", "Enterprise Standards", "current Approved implementation patterns and Software Delivery standards have not been verified; manual review required", "standards-review"))

    return ReadinessReport(tuple(findings))
