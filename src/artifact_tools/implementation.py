"""Deterministic state and readiness tooling for AEGIS implementation phase."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath

from artifact_tools.adr import collect_adr_ids
from artifact_tools.constants import ARTIFACT_TYPES
from artifact_tools.frontmatter import (
    DEFINED_ID_RE,
    FrontmatterError,
    packaged_templates_dir,
    render_document,
    split_document,
)

IMPLEMENTATION_DIR = "implementation"
POINTER_FILE = "implementation.md"
DECISION_FILE = "decision.md"
WORK_PACKAGES_DIR = "work-packages"

WORK_PACKAGE_STATUSES = frozenset(
    {"planned", "approved", "in-progress", "blocked", "review", "complete", "deferred", "cancelled"}
)
ACTIVE_WORK_PACKAGE_STATUSES = frozenset({"in-progress", "review"})
DECISION_STATUSES = frozenset({"pending", "accepted", "rejected", "superseded"})
DECISION_TYPES = frozenset({"tactical", "material"})
STANDARDS_REVIEW_STATUSES = frozenset({"verified", "manual-review-required"})

_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "planned": frozenset({"approved", "deferred", "cancelled"}),
    "approved": frozenset({"in-progress", "blocked", "deferred", "cancelled"}),
    "in-progress": frozenset({"review", "blocked"}),
    "blocked": frozenset({"approved", "in-progress", "deferred", "cancelled"}),
    "review": frozenset({"in-progress", "complete", "blocked"}),
    "complete": frozenset(),
    "deferred": frozenset({"planned"}),
    "cancelled": frozenset(),
}

_WP_ID_RE = re.compile(r"^WP-(\d{4})$")
_IDEC_ID_RE = re.compile(r"\bIDEC-(\d{4})\b")
_INTERNAL_SOURCE_RE = re.compile(r"^(?:FR|NFR|BP|IF|DM|SEC|DEP|OBS|ADR)-\d{3,4}$")
_OPEN_DECISIONS_HEADING_RE = re.compile(r"^#{2,3}\s+.*open decisions", re.IGNORECASE)
_BLOCKING_DECISION_RE = re.compile(r"\byes\b", re.IGNORECASE)


@dataclass(frozen=True)
class ImplementationFinding:
    """A phase-3 validation or readiness finding."""

    severity: str
    file: str
    message: str
    code: str = "implementation"

    def format(self) -> str:
        return f"[{self.severity.upper()}] {self.file}: {self.message}"


@dataclass(frozen=True)
class ReadinessReport:
    """Read-only result of evaluating whether code generation may begin."""

    findings: tuple[ImplementationFinding, ...]

    @property
    def ready(self) -> bool:
        return not any(item.severity == "error" for item in self.findings)


def _today() -> str:
    return date.today().isoformat()


def _implementation_path(app_dir: str | Path) -> Path:
    return Path(app_dir).resolve() / IMPLEMENTATION_DIR


def _find_templates_dir(start: Path | None = None) -> Path:
    relative = Path("aegis/skills/implementation-management/assets/templates")
    roots = [(start or Path.cwd()).resolve()]
    cwd = Path.cwd().resolve()
    if cwd not in roots:
        roots.append(cwd)
    for current in roots:
        for candidate in (current, *current.parents):
            target = candidate / relative
            if target.is_dir():
                return target
    packaged = packaged_templates_dir("implementation")
    if packaged is not None:
        return packaged
    raise FileNotFoundError(f"Could not locate implementation templates ({relative}) from {current}.")


def _yaml_scalar(value: str) -> str:
    # JSON escaping is YAML-compatible; templates provide the surrounding quotes.
    return json.dumps(str(value), ensure_ascii=False)[1:-1]


def _render_template(path: Path, replacements: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8")
    for token, value in replacements.items():
        text = text.replace("{{" + token + "}}", value)
    unresolved = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    if unresolved:
        raise ValueError(f"Unresolved template placeholders in {path.name}: {', '.join(sorted(set(unresolved)))}")
    return text


_REPLACE_ATTEMPTS = 8
_REPLACE_FIRST_DELAY = 0.02


def _replace_with_retry(source: Path, target: Path) -> None:
    """Rename ``source`` over ``target``, retrying brief Windows sharing violations.

    On Windows the rename fails with PermissionError while another process (an antivirus
    scanner, search indexer or editor) holds the target open for a moment.
    """
    delay = _REPLACE_FIRST_DELAY
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            source.replace(target)
            return
        except PermissionError:
            if attempt == _REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(delay)
            delay *= 2


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
        _replace_with_retry(Path(temporary), path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _load_document(path: Path) -> tuple[dict, str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        frontmatter, body = split_document(path.read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if frontmatter is None:
        raise ValueError(f"{path}: missing YAML frontmatter")
    return frontmatter, body


def _bump_version(frontmatter: dict) -> None:
    raw = str(frontmatter.get("version", "0.0"))
    match = re.fullmatch(r"(\d+)\.(\d+)", raw)
    if not match:
        raise ValueError(f"Invalid implementation document version: {raw}")
    frontmatter["version"] = f"{match.group(1)}.{int(match.group(2)) + 1}"
    frontmatter["last_updated"] = _today()


def _append_changelog(body: str, summary: str, version: str) -> str:
    line = f"- {_today()} — v{version} — {summary.strip().rstrip('.')}.\n"
    marker = "<!-- artifact_tools implementation commands append here -->"
    if marker in body:
        return body.replace(marker, marker + "\n" + line.rstrip("\n"), 1)
    if "## Changelog" in body:
        return body.replace("## Changelog", "## Changelog\n\n" + line.rstrip("\n"), 1)
    return body.rstrip() + "\n\n## Changelog\n\n" + line


def _write_bumped(path: Path, frontmatter: dict, body: str, summary: str) -> None:
    _bump_version(frontmatter)
    body = _append_changelog(body, summary, str(frontmatter["version"]))
    _atomic_write(path, render_document(frontmatter, body))


def init_implementation(
    app_dir: str | Path,
    *,
    target_workspace: str | Path,
    target_branch: str = "",
    target_baseline: str = "",
    standards_review: str = "manual-review-required",
    project: str | None = None,
    templates_dir: Path | None = None,
) -> Path:
    """Create the canonical implementation pointer, decision ledger, and package folder.

    The operation is idempotent only when the complete structure already exists. Partial
    state is rejected so it can never be silently overwritten.
    """

    app = Path(app_dir).resolve()
    if not app.is_dir():
        raise FileNotFoundError(f"Application artifact directory does not exist: {app}")
    target = Path(target_workspace).resolve()
    if standards_review not in STANDARDS_REVIEW_STATUSES:
        raise ValueError(f"Invalid standards review status: {standards_review}")

    implementation = app / IMPLEMENTATION_DIR
    pointer = implementation / POINTER_FILE
    decisions = implementation / DECISION_FILE
    packages = implementation / WORK_PACKAGES_DIR
    existing = [path.exists() for path in (pointer, decisions, packages)]
    if all(existing):
        current, _ = _load_document(pointer)
        if Path(str(current.get("target_workspace", ""))).resolve() != target:
            raise FileExistsError(
                f"Implementation state already targets {current.get('target_workspace')}, not {target}."
            )
        comparisons = {
            "target_branch": target_branch,
            "target_baseline": target_baseline,
            "standards_review": standards_review,
        }
        for key, expected in comparisons.items():
            if str(current.get(key, "")) != str(expected):
                raise FileExistsError(
                    f"Implementation state already records {key}={current.get(key)!r}, not {expected!r}."
                )
        return implementation
    if any(existing):
        raise FileExistsError(f"Partial implementation state exists at {implementation}; repair it before init.")

    templates = templates_dir or _find_templates_dir(app)
    name = project or app.name.replace("-", " ").title()
    replacements = {
        "PROJECT_NAME": name,
        "TITLE_YAML": _yaml_scalar(f"Implementation — {name}"),
        "DATE": _today(),
        "TARGET_WORKSPACE_YAML": _yaml_scalar(str(target)),
        "TARGET_BRANCH_YAML": _yaml_scalar(target_branch),
        "TARGET_BASELINE_YAML": _yaml_scalar(target_baseline),
        "STANDARDS_REVIEW_YAML": _yaml_scalar(standards_review),
    }
    decision_replacements = {
        "PROJECT_NAME": name,
        "TITLE_YAML": _yaml_scalar(f"Implementation Decisions — {name}"),
        "DATE": _today(),
    }
    pointer_text = _render_template(templates / "implementation.template.md", replacements)
    decision_text = _render_template(templates / "decision.template.md", decision_replacements)

    implementation.mkdir(parents=True, exist_ok=False)
    try:
        packages.mkdir()
        _atomic_write(pointer, pointer_text)
        _atomic_write(decisions, decision_text)
    except Exception:
        for child in (pointer, decisions):
            child.unlink(missing_ok=True)
        if packages.exists() and not any(packages.iterdir()):
            packages.rmdir()
        if implementation.exists() and not any(implementation.iterdir()):
            implementation.rmdir()
        raise
    return implementation


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "work-package"


def _normalise_target_path(value: str) -> str:
    cleaned = value.strip().replace("\\", "/")
    pure = PurePosixPath(cleaned)
    if not cleaned or pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"Target path must be a non-empty repository-relative path: {value!r}")
    return str(pure).rstrip("/")


def _work_package_documents(app_dir: str | Path) -> list[tuple[Path, dict, str]]:
    folder = _implementation_path(app_dir) / WORK_PACKAGES_DIR
    documents: list[tuple[Path, dict, str]] = []
    if not folder.is_dir():
        return documents
    for path in sorted(folder.glob("WP-*.md")):
        fm, body = _load_document(path)
        documents.append((path, fm, body))
    return documents


def _next_work_package_id(app_dir: str | Path) -> str:
    numbers = []
    for _, fm, _ in _work_package_documents(app_dir):
        match = _WP_ID_RE.fullmatch(str(fm.get("id", "")))
        if match:
            numbers.append(int(match.group(1)))
    return f"WP-{max(numbers, default=0) + 1:04d}"


def _find_work_package(app_dir: str | Path, work_package_id: str) -> tuple[Path, dict, str]:
    for path, frontmatter, body in _work_package_documents(app_dir):
        if frontmatter.get("id") == work_package_id:
            return path, frontmatter, body
    raise FileNotFoundError(f"Unknown work package {work_package_id}")


def create_work_package(
    app_dir: str | Path,
    title: str,
    *,
    scope: str,
    source_ids: Iterable[str],
    target_paths: Iterable[str],
    dependencies: Iterable[str] = (),
    owner: str = "implementation-orchestrator",
    parallel_group: str | None = None,
    source_versions: dict[str, str] | None = None,
    templates_dir: Path | None = None,
) -> tuple[Path, str]:
    """Create the next bounded work package and reconcile the canonical pointer."""

    implementation = _implementation_path(app_dir)
    if not (implementation / POINTER_FILE).is_file():
        raise FileNotFoundError("Implementation state is not initialized")
    work_package_id = _next_work_package_id(app_dir)
    paths = list(dict.fromkeys(_normalise_target_path(item) for item in target_paths))
    if not paths:
        raise ValueError("A work package must declare at least one target path")
    deps = list(dict.fromkeys(str(item).strip() for item in dependencies if str(item).strip()))
    sources = list(dict.fromkeys(str(item).strip() for item in source_ids if str(item).strip()))
    templates = templates_dir or _find_templates_dir(implementation)
    replacements = {
        "ID": work_package_id,
        "ID_YAML": _yaml_scalar(work_package_id),
        "TITLE": title,
        "TITLE_YAML": _yaml_scalar(title),
        "DATE": _today(),
        "OWNER_YAML": _yaml_scalar(owner),
        "SCOPE": scope.strip() or "Scope to be completed before approval.",
    }
    content = _render_template(templates / "work-package.template.md", replacements)
    fm, body = split_document(content)
    assert fm is not None
    fm["dependencies"] = deps
    fm["source_ids"] = sources
    fm["source_versions"] = source_versions or _source_versions_for_ids(Path(app_dir).resolve(), sources)
    fm["target_paths"] = paths
    fm["parallel_group"] = parallel_group
    target = implementation / WORK_PACKAGES_DIR / f"{work_package_id}-{_slugify(title)}.md"
    if target.exists():
        raise FileExistsError(target)
    _atomic_write(target, render_document(fm, body))
    reconcile_pointer(app_dir, summary=f"Created {work_package_id} ({title})")
    return target, work_package_id


def _append_status_history(body: str, old: str, new: str, actor: str, note: str) -> str:
    row = f"| {_today()} | {old} | {new} | {_escape_cell(actor)} | {_escape_cell(note or '—')} |"
    heading = "## Status History"
    if heading not in body:
        raise ValueError("Work package is missing the Status History section")
    return body.rstrip() + "\n" + row + "\n"


def transition_work_package(
    app_dir: str | Path,
    work_package_id: str,
    new_status: str,
    *,
    actor: str,
    note: str = "",
    approved_by: str | None = None,
    review_status: str | None = None,
) -> Path:
    """Apply a legal state transition and enforce approval/review completion gates."""

    path, fm, body = _find_work_package(app_dir, work_package_id)
    old = str(fm.get("status", ""))
    if new_status not in WORK_PACKAGE_STATUSES:
        raise ValueError(f"Invalid work-package status: {new_status}")
    if new_status not in _ALLOWED_TRANSITIONS.get(old, frozenset()):
        raise ValueError(f"Illegal work-package transition: {old} -> {new_status}")
    if new_status == "approved":
        approver = approved_by or fm.get("approved_by")
        if not approver:
            raise ValueError("Transition to approved requires approved_by")
        fm["approved_by"] = approver
    if review_status is not None:
        if review_status not in {"pending", "pass", "needs-changes"}:
            raise ValueError(f"Invalid review status: {review_status}")
        fm["review_status"] = review_status
    if new_status == "complete":
        if fm.get("review_status") != "pass":
            raise ValueError("A work package cannot complete until the independent reviewer passes it")
        if int(fm.get("evidence_count", 0)) < 1:
            raise ValueError("A work package cannot complete without recorded verification evidence")
    fm["status"] = new_status
    fm["last_updated"] = _today()
    fm["version"] = _increment_version(str(fm.get("version", "0.0")))
    body = _append_status_history(body, old, new_status, actor, note)
    _atomic_write(path, render_document(fm, body))
    reconcile_pointer(app_dir, summary=f"Transitioned {work_package_id} from {old} to {new_status}")
    return path


def _increment_version(raw: str) -> str:
    match = re.fullmatch(r"(\d+)\.(\d+)", raw)
    if not match:
        raise ValueError(f"Invalid implementation document version: {raw}")
    return f"{match.group(1)}.{int(match.group(2)) + 1}"


def _escape_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def record_evidence(
    app_dir: str | Path,
    work_package_id: str,
    command: str,
    outcome: str,
    details: str,
) -> Path:
    """Append actual verification evidence to a work package and pointer."""

    if outcome not in {"pass", "fail"}:
        raise ValueError("Evidence outcome must be 'pass' or 'fail'")
    path, fm, body = _find_work_package(app_dir, work_package_id)
    row = (
        f"| {_today()} | {_escape_cell(command)} | {outcome} | {_escape_cell(details or '—')} |"
    )
    marker = "## Status History"
    if marker not in body:
        raise ValueError("Work package is missing the Status History section")
    body = body.replace(marker, row + "\n\n" + marker, 1)
    fm["evidence_count"] = int(fm.get("evidence_count", 0)) + 1
    fm["last_updated"] = _today()
    fm["version"] = _increment_version(str(fm.get("version", "0.0")))
    _atomic_write(path, render_document(fm, body))
    _append_pointer_verification(app_dir, work_package_id, command, outcome, details)
    return path


def _append_pointer_verification(
    app_dir: str | Path, work_package_id: str, command: str, outcome: str, details: str
) -> None:
    pointer = _implementation_path(app_dir) / POINTER_FILE
    fm, body = _load_document(pointer)
    row = (
        f"| {_today()} | {work_package_id} | {_escape_cell(command)} | {outcome} | "
        f"{_escape_cell(details or '—')} |"
    )
    marker = "## Changelog"
    if marker not in body:
        raise ValueError("Implementation pointer is missing the Changelog section")
    body = body.replace(marker, row + "\n\n" + marker, 1)
    _write_bumped(pointer, fm, body, f"Recorded {work_package_id} verification evidence")


def _next_decision_id(body: str) -> str:
    numbers = [int(value) for value in _IDEC_ID_RE.findall(body)]
    return f"IDEC-{max(numbers, default=0) + 1:04d}"


def _decision_row_ids(body: str) -> list[str]:
    return [
        match.group(1)
        for line in body.splitlines()
        if (match := re.match(r"^\|\s*(IDEC-\d{4})\s*\|", line))
    ]


def add_decision(
    app_dir: str | Path,
    *,
    question: str,
    decision: str,
    rationale: str,
    work_package: str = "—",
    decision_type: str = "tactical",
    status: str = "accepted",
    sources: Iterable[str] = (),
    affected_paths: Iterable[str] = (),
    approver: str = "",
    adr: str = "—",
    supersedes: str | None = None,
) -> str:
    """Append a tactical decision, or a material decision linked to an ADR."""

    if decision_type not in DECISION_TYPES:
        raise ValueError(f"Invalid decision type: {decision_type}")
    if status not in DECISION_STATUSES:
        raise ValueError(f"Invalid decision status: {status}")
    if decision_type == "material" and (not approver or not re.fullmatch(r"ADR-\d{4}", adr)):
        raise ValueError("A material implementation decision requires an approver and ADR-NNNN link")
    path = _implementation_path(app_dir) / DECISION_FILE
    fm, body = _load_document(path)
    decision_id = _next_decision_id(body)
    if supersedes:
        body = _supersede_decision_row(body, supersedes, decision_id)
    row = "| " + " | ".join(
        _escape_cell(value)
        for value in (
            decision_id,
            _today(),
            status,
            decision_type,
            work_package,
            question,
            decision,
            rationale,
            ", ".join(sources) or "—",
            ", ".join(_normalise_target_path(item) for item in affected_paths) or "—",
            approver or "—",
            adr,
        )
    ) + " |"
    marker = "## Changelog"
    if marker not in body:
        raise ValueError("Decision ledger is missing the Changelog section")
    body = body.replace(marker, row + "\n\n" + marker, 1)
    _write_bumped(path, fm, body, f"Recorded {decision_id}")
    reconcile_pointer(app_dir, summary=f"Recorded implementation decision {decision_id}")
    return decision_id


def _supersede_decision_row(body: str, old_id: str, new_id: str) -> str:
    if not re.fullmatch(r"IDEC-\d{4}", old_id):
        raise ValueError(f"Invalid superseded decision id: {old_id}")
    lines = body.splitlines()
    found = False
    for index, line in enumerate(lines):
        if line.startswith(f"| {old_id} |"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 12:
                raise ValueError(f"Malformed decision row for {old_id}")
            cells[2] = "superseded"
            cells[7] = f"{cells[7]} Superseded by {new_id}."
            lines[index] = "| " + " | ".join(cells) + " |"
            found = True
            break
    if not found:
        raise FileNotFoundError(f"Unknown implementation decision {old_id}")
    return "\n".join(lines) + ("\n" if body.endswith("\n") else "")


def reconcile_pointer(app_dir: str | Path, *, summary: str = "Reconciled implementation pointer") -> Path:
    """Derive active/next work package and index rows from canonical package files."""

    pointer = _implementation_path(app_dir) / POINTER_FILE
    fm, body = _load_document(pointer)
    documents = _work_package_documents(app_dir)
    by_id = {str(item[1].get("id")): item for item in documents}
    active = [wp_id for wp_id, (_, wp_fm, _) in by_id.items() if wp_fm.get("status") in ACTIVE_WORK_PACKAGE_STATUSES]
    completed = {wp_id for wp_id, (_, wp_fm, _) in by_id.items() if wp_fm.get("status") == "complete"}
    eligible = []
    for wp_id, (_, wp_fm, _) in by_id.items():
        if wp_fm.get("status") not in {"planned", "approved"}:
            continue
        if set(wp_fm.get("dependencies") or ()).issubset(completed):
            eligible.append(wp_id)
    active.sort()
    eligible.sort()
    fm["active_work_package"] = active[0] if len(active) == 1 else (active or None)
    fm["next_work_package"] = eligible[0] if eligible else None
    if active:
        fm["status"] = "review" if any(by_id[item][1].get("status") == "review" for item in active) else "in-progress"
    elif any(item[1].get("status") == "blocked" for _, item in by_id.items()):
        fm["status"] = "blocked"
    elif documents and len(completed) == len(documents):
        fm["status"] = "complete"
    elif documents:
        fm["status"] = "planning"
    else:
        fm["status"] = "not-started"

    source_versions: dict[str, str] = {}
    for _, wp_fm, _ in documents:
        source_versions.update(wp_fm.get("source_versions") or {})
    fm["source_versions"] = dict(sorted(source_versions.items()))

    active_value = ", ".join(active) if active else "—"
    next_value = eligible[0] if eligible else "—"
    release_value = "Approved" if fm.get("release_approved") else "Not ready"
    body = _replace_table_rows(
        body,
        "## Current State",
        [
            f"| Active work package | {active_value} |",
            f"| Next work package | {next_value} |",
            f"| Release readiness | {release_value} |",
        ],
    )

    index_rows = []
    for path, wp_fm, _ in documents:
        deps = ", ".join(wp_fm.get("dependencies") or ()) or "—"
        paths = "<br>".join(_escape_cell(item) for item in wp_fm.get("target_paths") or ()) or "—"
        index_rows.append(
            f"| {wp_fm.get('id')} | {_escape_cell(wp_fm.get('title', ''))} | {wp_fm.get('status')} | "
            f"{deps} | {paths} | [{path.name}](work-packages/{path.name}) |"
        )
    body = _replace_table_rows(body, "## Work Package Index", index_rows)
    blockers = [wp_id for wp_id, (_, wp_fm, _) in by_id.items() if wp_fm.get("status") == "blocked"]
    blocker_lines = [f"- {item} is blocked." for item in sorted(blockers)]
    if fm.get("standards_review") != "verified":
        blocker_lines.append("- Enterprise Standards review requires manual verification.")
    blocker_text = "\n".join(blocker_lines) or "- None recorded."
    body = _replace_section(body, "## Blockers", blocker_text)
    _write_bumped(pointer, fm, body, summary)
    return pointer


def _replace_table_rows(body: str, heading: str, rows: list[str]) -> str:
    start = body.find(heading)
    if start < 0:
        raise ValueError(f"Missing pointer section: {heading}")
    next_heading = body.find("\n## ", start + len(heading))
    end = len(body) if next_heading < 0 else next_heading
    section = body[start:end]
    lines = section.splitlines()
    table_start = next((i for i, line in enumerate(lines) if line.startswith("|")), None)
    if table_start is None or table_start + 1 >= len(lines):
        raise ValueError(f"Missing table in pointer section: {heading}")
    new_lines = lines[: table_start + 2] + rows
    replacement = "\n".join(new_lines).rstrip() + "\n"
    return body[:start] + replacement + body[end:]


def _replace_section(body: str, heading: str, content: str) -> str:
    start = body.find(heading)
    if start < 0:
        raise ValueError(f"Missing pointer section: {heading}")
    next_heading = body.find("\n## ", start + len(heading))
    end = len(body) if next_heading < 0 else next_heading
    replacement = heading + "\n\n" + content.strip() + "\n"
    return body[:start] + replacement + body[end:]


def implementation_status(app_dir: str | Path) -> dict:
    """Return the canonical pointer frontmatter for read-only status reporting."""

    fm, _ = _load_document(_implementation_path(app_dir) / POINTER_FILE)
    return fm


def approve_release(app_dir: str | Path, *, approver: str, note: str = "") -> Path:
    """Record the explicit release gate after every package and coverage check passes."""

    if not approver.strip():
        raise ValueError("Release approval requires a named approver")
    pointer = _implementation_path(app_dir) / POINTER_FILE
    fm, body = _load_document(pointer)
    if fm.get("status") != "complete":
        raise ValueError("Release approval requires every work package to be complete")
    blockers = [
        item
        for item in validate_implementation(app_dir)
        if item.severity == "error" and item.code != "release-approval"
    ]
    if blockers:
        detail = "; ".join(f"{item.code}: {item.message}" for item in blockers[:5])
        raise ValueError(f"Release approval is blocked: {detail}")
    fm["release_approved"] = True
    fm["release_approved_by"] = approver.strip()
    fm["release_approved_on"] = _today()
    fm["release_approval_note"] = note.strip()
    active = fm.get("active_work_package")
    active_value = ", ".join(active) if isinstance(active, list) else (active or "—")
    body = _replace_table_rows(
        body,
        "## Current State",
        [
            f"| Active work package | {active_value} |",
            f"| Next work package | {fm.get('next_work_package') or '—'} |",
            "| Release readiness | Approved |",
        ],
    )
    _write_bumped(pointer, fm, body, f"Release approved by {approver.strip()}")
    return pointer


def _path_overlap(first: str, second: str) -> bool:
    a = _normalise_target_path(first).casefold().split("/")
    b = _normalise_target_path(second).casefold().split("/")
    shorter = min(len(a), len(b))
    return a[:shorter] == b[:shorter]


def _collect_defined_source_ids(app: Path) -> set[str]:
    ids: set[str] = set()
    for meta in ARTIFACT_TYPES.values():
        path = app / meta["filename"]
        if path.is_file():
            _, body = _load_document(path)
            ids.update(DEFINED_ID_RE.findall(body))
    adr_dir = app / "architecture-decisions"
    if adr_dir.is_dir():
        ids.update(collect_adr_ids(adr_dir))
    return ids


def _source_inventory(app: Path) -> dict[str, tuple[str, str]]:
    inventory: dict[str, tuple[str, str]] = {}
    for meta in ARTIFACT_TYPES.values():
        path = app / meta["filename"]
        if not path.is_file():
            continue
        fm, body = _load_document(path)
        relative = path.name
        fingerprint = str(fm.get("version", ""))
        for source_id in DEFINED_ID_RE.findall(body):
            inventory[source_id] = (relative, fingerprint)
    adr_dir = app / "architecture-decisions"
    if adr_dir.is_dir():
        for path in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md"):
            fm, _ = _load_document(path)
            source_id = str(fm.get("id", ""))
            if re.fullmatch(r"ADR-\d{4}", source_id):
                relative = str(path.relative_to(app)).replace("\\", "/")
                inventory[source_id] = (relative, f"{fm.get('date')}:{fm.get('status')}")
    return inventory


def _source_versions_for_ids(app: Path, source_ids: Iterable[str]) -> dict[str, str]:
    inventory = _source_inventory(app)
    versions: dict[str, str] = {}
    for source_id in source_ids:
        if source_id in inventory:
            path, fingerprint = inventory[source_id]
            versions[path] = fingerprint
    return dict(sorted(versions.items()))


def _current_source_version(app: Path, relative: str) -> str | None:
    path = app / relative
    if not path.is_file():
        return None
    fm, _ = _load_document(path)
    if relative.startswith("architecture-decisions/"):
        return f"{fm.get('date')}:{fm.get('status')}"
    return str(fm.get("version", ""))


def _collect_required_coverage_ids(app: Path) -> set[str]:
    required_prefixes = ("FR-", "NFR-", "BP-", "IF-", "DM-", "SEC-", "DEP-", "OBS-")
    ids: set[str] = set()
    for meta in ARTIFACT_TYPES.values():
        path = app / meta["filename"]
        if not path.is_file():
            continue
        _, body = _load_document(path)
        for line in body.splitlines():
            match = DEFINED_ID_RE.match(line)
            if not match or not match.group(1).startswith(required_prefixes):
                continue
            if re.search(r"\|\s*(?:removed|retired)\s*\|", line, re.IGNORECASE):
                continue
            ids.add(match.group(1))
    adr_dir = app / "architecture-decisions"
    if adr_dir.is_dir():
        for path in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md"):
            fm, _ = _load_document(path)
            if fm.get("status") == "accepted":
                ids.add(str(fm.get("id")))
    return ids


def validate_implementation(app_dir: str | Path, *, strict: bool = False) -> list[ImplementationFinding]:
    """Validate phase-3 state, traceability, dependencies, paths, and evidence."""

    app = Path(app_dir).resolve()
    implementation = app / IMPLEMENTATION_DIR
    if not implementation.exists():
        return []
    findings: list[ImplementationFinding] = []
    pointer = implementation / POINTER_FILE
    decisions = implementation / DECISION_FILE
    packages_dir = implementation / WORK_PACKAGES_DIR
    for required in (pointer, decisions, packages_dir):
        if not required.exists():
            findings.append(ImplementationFinding("error", str(required.relative_to(app)), "required implementation state is missing", "state-missing"))
    if findings:
        return findings

    try:
        pointer_fm, _ = _load_document(pointer)
    except (FileNotFoundError, ValueError) as exc:
        return [ImplementationFinding("error", POINTER_FILE, str(exc), "pointer-invalid")]
    required_pointer = (
        "artifact", "title", "version", "status", "last_updated", "phase", "owner",
        "target_workspace", "standards_review", "active_work_package", "next_work_package",
        "release_approved", "source_versions",
    )
    for key in required_pointer:
        if key not in pointer_fm:
            findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{POINTER_FILE}", f"missing pointer frontmatter '{key}'", "pointer-schema"))
    if pointer_fm.get("artifact") != "implementation" or pointer_fm.get("phase") != 3:
        findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{POINTER_FILE}", "pointer must be artifact 'implementation' in phase 3", "pointer-schema"))
    if pointer_fm.get("standards_review") not in STANDARDS_REVIEW_STATUSES:
        findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{POINTER_FILE}", "invalid standards_review status", "pointer-schema"))
    if strict and not str(pointer_fm.get("target_baseline", "")).strip():
        findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{POINTER_FILE}", "target_baseline is required for strict validation", "target-baseline"))

    try:
        decision_fm, decision_body = _load_document(decisions)
        if decision_fm.get("artifact") != "implementation-decisions" or decision_fm.get("phase") != 3:
            findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{DECISION_FILE}", "decision ledger must be implementation-decisions in phase 3", "decision-schema"))
        decision_ids = _decision_row_ids(decision_body)
        for decision_id in sorted({item for item in decision_ids if decision_ids.count(item) > 1}):
            findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{DECISION_FILE}", f"duplicate implementation decision id {decision_id}", "decision-duplicate"))
    except (FileNotFoundError, ValueError) as exc:
        findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{DECISION_FILE}", str(exc), "decision-invalid"))

    try:
        documents = _work_package_documents(app)
    except (FileNotFoundError, ValueError) as exc:
        findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{WORK_PACKAGES_DIR}", str(exc), "work-package-invalid"))
        return findings
    source_ids = _collect_defined_source_ids(app)
    by_id: dict[str, tuple[Path, dict, str]] = {}
    for path, fm, body in documents:
        relative = str(path.relative_to(app)).replace("\\", "/")
        wp_id = str(fm.get("id", ""))
        if not _WP_ID_RE.fullmatch(wp_id):
            findings.append(ImplementationFinding("error", relative, f"invalid work-package id '{wp_id}'", "work-package-id"))
            continue
        if wp_id in by_id:
            findings.append(ImplementationFinding("error", relative, f"duplicate work-package id {wp_id}", "work-package-duplicate"))
        by_id[wp_id] = (path, fm, body)
        if not path.name.startswith(wp_id + "-"):
            findings.append(ImplementationFinding("error", relative, f"filename must start with {wp_id}-", "work-package-filename"))
        if fm.get("artifact") != "work-package" or fm.get("phase") != 3:
            findings.append(ImplementationFinding("error", relative, "work package must be artifact 'work-package' in phase 3", "work-package-schema"))
        status = fm.get("status")
        if status not in WORK_PACKAGE_STATUSES:
            findings.append(ImplementationFinding("error", relative, f"invalid status '{status}'", "work-package-status"))
        paths = fm.get("target_paths")
        if not isinstance(paths, list) or not paths:
            findings.append(ImplementationFinding("error", relative, "target_paths must be a non-empty list", "work-package-paths"))
        else:
            for value in paths:
                try:
                    _normalise_target_path(str(value))
                except ValueError as exc:
                    findings.append(ImplementationFinding("error", relative, str(exc), "work-package-paths"))
        for source_id in fm.get("source_ids") or ():
            if _INTERNAL_SOURCE_RE.fullmatch(str(source_id)) and source_id not in source_ids:
                findings.append(ImplementationFinding("error", relative, f"references unknown source id {source_id}", "work-package-source"))
        recorded_versions = fm.get("source_versions") or {}
        if not isinstance(recorded_versions, dict):
            findings.append(ImplementationFinding("error", relative, "source_versions must be a mapping", "source-version-schema"))
            recorded_versions = {}
        expected_versions = _source_versions_for_ids(app, fm.get("source_ids") or ())
        for source_path, expected in expected_versions.items():
            if source_path not in recorded_versions:
                findings.append(ImplementationFinding("error", relative, f"missing source-version snapshot for {source_path}", "source-version-missing"))
            elif str(recorded_versions[source_path]) != expected:
                findings.append(ImplementationFinding("error", relative, f"source drift for {source_path}: recorded {recorded_versions[source_path]!r}, current {expected!r}", "source-drift"))
        for source_path, recorded in recorded_versions.items():
            if source_path in expected_versions:
                continue
            current = _current_source_version(app, str(source_path))
            if current is None:
                findings.append(ImplementationFinding("error", relative, f"recorded source file no longer exists: {source_path}", "source-drift"))
            elif str(recorded) != current:
                findings.append(ImplementationFinding("error", relative, f"source drift for {source_path}: recorded {recorded!r}, current {current!r}", "source-drift"))
        if status == "complete":
            if fm.get("review_status") != "pass":
                findings.append(ImplementationFinding("error", relative, "completed package has no reviewer PASS", "work-package-evidence"))
            if int(fm.get("evidence_count", 0)) < 1:
                findings.append(ImplementationFinding("error", relative, "completed package has no verification evidence", "work-package-evidence"))

    for wp_id, (path, fm, _) in by_id.items():
        relative = str(path.relative_to(app)).replace("\\", "/")
        for dependency in fm.get("dependencies") or ():
            if dependency not in by_id:
                findings.append(ImplementationFinding("error", relative, f"depends on unknown work package {dependency}", "work-package-dependency"))
            elif dependency == wp_id:
                findings.append(ImplementationFinding("error", relative, "work package cannot depend on itself", "work-package-dependency"))
    findings.extend(_dependency_cycle_findings(app, by_id))
    findings.extend(_active_path_findings(app, by_id))

    actual_active = sorted(wp_id for wp_id, (_, fm, _) in by_id.items() if fm.get("status") in ACTIVE_WORK_PACKAGE_STATUSES)
    pointer_active = pointer_fm.get("active_work_package")
    expected_active: object = actual_active[0] if len(actual_active) == 1 else (actual_active or None)
    if pointer_active != expected_active:
        findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{POINTER_FILE}", f"active_work_package is {pointer_active!r}; expected {expected_active!r}", "pointer-drift"))

    if pointer_fm.get("status") == "complete":
        covered = {str(source) for _, fm, _ in documents for source in (fm.get("source_ids") or ())}
        missing = sorted(_collect_required_coverage_ids(app) - covered)
        for source_id in missing:
            findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{POINTER_FILE}", f"final implementation has no disposition for {source_id}", "coverage-missing"))
        if not pointer_fm.get("release_approved"):
            findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{POINTER_FILE}", "completed implementation is not release-approved", "release-approval"))

    if strict and pointer_fm.get("standards_review") != "verified":
        findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{POINTER_FILE}", "Enterprise Standards review is not verified", "standards-review"))
    return findings


def _dependency_cycle_findings(app: Path, by_id: dict[str, tuple[Path, dict, str]]) -> list[ImplementationFinding]:
    findings: list[ImplementationFinding] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(wp_id: str, trail: list[str]) -> None:
        if wp_id in visited:
            return
        if wp_id in visiting:
            cycle = trail[trail.index(wp_id):] + [wp_id]
            path = by_id[wp_id][0]
            findings.append(ImplementationFinding("error", str(path.relative_to(app)).replace("\\", "/"), f"dependency cycle: {' -> '.join(cycle)}", "dependency-cycle"))
            return
        visiting.add(wp_id)
        for dependency in by_id[wp_id][1].get("dependencies") or ():
            if dependency in by_id:
                visit(dependency, trail + [dependency])
        visiting.remove(wp_id)
        visited.add(wp_id)

    for key in sorted(by_id):
        visit(key, [key])
    return findings


def _active_path_findings(app: Path, by_id: dict[str, tuple[Path, dict, str]]) -> list[ImplementationFinding]:
    active = [(wp_id, data) for wp_id, data in by_id.items() if data[1].get("status") in ACTIVE_WORK_PACKAGE_STATUSES]
    findings: list[ImplementationFinding] = []
    if len(active) <= 1:
        return findings
    groups = {data[1].get("parallel_group") for _, data in active}
    if None in groups or "" in groups or len(groups) != 1:
        findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{POINTER_FILE}", "multiple active work packages require one explicit shared parallel_group", "parallel-approval"))
    for index, (first_id, first) in enumerate(active):
        for second_id, second in active[index + 1:]:
            for first_path in first[1].get("target_paths") or ():
                for second_path in second[1].get("target_paths") or ():
                    if _path_overlap(str(first_path), str(second_path)):
                        findings.append(ImplementationFinding("error", f"{IMPLEMENTATION_DIR}/{POINTER_FILE}", f"active packages {first_id} and {second_id} overlap at {first_path!r} / {second_path!r}", "parallel-path-overlap"))
    return findings


def _blocking_open_decisions(path: Path, body: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    in_section = False
    for line in body.splitlines():
        if _OPEN_DECISIONS_HEADING_RE.match(line):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            in_section = False
        if not in_section or not re.match(r"^\|\s*D-\d+\s*\|", line):
            continue
        cells = [cell.strip().replace("**", "") for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and _BLOCKING_DECISION_RE.search(cells[-1]):
            rows.append((cells[0], re.sub(r"\s+", " ", cells[1])[:180]))
    return rows
