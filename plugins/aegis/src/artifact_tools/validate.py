"""Validate artifact documents for schema, id, and cross-reference consistency."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from artifact_tools.adr import collect_adr_ids, validate_adrs
from artifact_tools.constants import (
    ADR_DIR,
    ARTIFACT_TYPES,
    REQUIRED_FRONTMATTER,
    VALID_STATUS,
)
from artifact_tools.frontmatter import (
    DEFINED_ID_RE,
    ID_TOKEN_RE,
    FrontmatterError,
    split_document,
)
from artifact_tools.implementation import validate_implementation
from artifact_tools.issues import Issue, has_errors

__all__ = ["Issue", "has_errors", "validate_dir", "discover_app_dirs"]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_VERSION_RE = re.compile(r"^\d+\.\d+$")


@dataclass
class Document:
    """Parsed representation of one artifact file."""

    path: Path
    type_key: str | None
    frontmatter: dict | None
    body: str
    defined_ids: list[str] = field(default_factory=list)
    referenced_ids: list[str] = field(default_factory=list)


def _type_key_for_file(path: Path) -> str | None:
    for key, meta in ARTIFACT_TYPES.items():
        if meta["filename"] == path.name:
            return key
    return None


def _parse_document(path: Path) -> tuple[Document, list[Issue]]:
    issues: list[Issue] = []
    type_key = _type_key_for_file(path)
    text = path.read_text(encoding="utf-8")
    try:
        frontmatter, body = split_document(text)
    except FrontmatterError as exc:
        issues.append(Issue("error", path.name, str(exc)))
        frontmatter, body = None, text

    defined = DEFINED_ID_RE.findall(body)
    defined_set = set(defined)
    all_tokens = [f"{p}-{n}" for p, n in ID_TOKEN_RE.findall(body)]
    referenced = [tok for tok in all_tokens if tok not in defined_set]

    doc = Document(
        path=path,
        type_key=type_key,
        frontmatter=frontmatter,
        body=body,
        defined_ids=sorted(defined_set),
        referenced_ids=list(dict.fromkeys(referenced)),
    )
    return doc, issues


def _duplicate_ids_within_tables(body: str) -> list[str]:
    """Return ids that appear more than once inside the same contiguous table.

    An id repeated across *different* tables (e.g. a verification or acceptance
    table that references a requirement defined elsewhere) is allowed.
    """
    duplicates: list[str] = []
    seen_in_block: set[str] = set()
    in_table = False
    for line in body.splitlines():
        is_row = line.lstrip().startswith("|")
        if not is_row:
            in_table = False
            seen_in_block = set()
            continue
        if not in_table:
            in_table = True
            seen_in_block = set()
        match = DEFINED_ID_RE.match(line)
        if match:
            token = match.group(1)
            if token in seen_in_block:
                duplicates.append(token)
            seen_in_block.add(token)
    return duplicates


def _check_frontmatter(doc: Document) -> list[Issue]:
    issues: list[Issue] = []
    name = doc.path.name
    fm = doc.frontmatter
    if fm is None:
        issues.append(Issue("error", name, "missing YAML frontmatter block"))
        return issues

    for key in REQUIRED_FRONTMATTER:
        if key not in fm or fm[key] in (None, ""):
            issues.append(Issue("error", name, f"missing required frontmatter '{key}'"))

    status = fm.get("status")
    if status is not None and status not in VALID_STATUS:
        issues.append(
            Issue("error", name, f"invalid status '{status}' (allowed: {sorted(VALID_STATUS)})")
        )

    version = fm.get("version")
    if version is not None and not _VERSION_RE.match(str(version)):
        issues.append(Issue("error", name, f"version '{version}' must look like MAJOR.MINOR"))

    updated = fm.get("last_updated")
    if updated is not None and not _DATE_RE.match(str(updated)):
        issues.append(Issue("error", name, f"last_updated '{updated}' must be ISO YYYY-MM-DD"))

    phase = fm.get("phase")
    if phase is not None and not (isinstance(phase, int) and phase >= 1):
        issues.append(Issue("error", name, f"phase '{phase}' must be an integer >= 1"))

    if doc.type_key and fm.get("artifact") not in (None, doc.type_key):
        issues.append(
            Issue(
                "error",
                name,
                f"frontmatter artifact '{fm.get('artifact')}' does not match file type '{doc.type_key}'",
            )
        )
    return issues


def _check_ids(doc: Document) -> list[Issue]:
    issues: list[Issue] = []
    name = doc.path.name
    if not doc.type_key:
        return issues
    expected_prefix = ARTIFACT_TYPES[doc.type_key]["prefix"]

    for token in _duplicate_ids_within_tables(doc.body):
        issues.append(Issue("error", name, f"duplicate id defined: {token}"))

    for token in doc.defined_ids:
        prefix = token.rsplit("-", 1)[0]
        if prefix != expected_prefix:
            issues.append(
                Issue(
                    "error",
                    name,
                    f"id {token} uses prefix '{prefix}' but this document defines '{expected_prefix}-' ids",
                )
            )
    return issues


def _check_cross_references(
    docs: list[Document], extra_defined: set[str] | None = None
) -> list[Issue]:
    issues: list[Issue] = []
    global_defined: set[str] = set(extra_defined or ())
    for doc in docs:
        global_defined.update(doc.defined_ids)

    for doc in docs:
        for ref in doc.referenced_ids:
            if ref not in global_defined:
                issues.append(
                    Issue(
                        "error",
                        doc.path.name,
                        f"references unknown id {ref} (not defined in any artifact)",
                    )
                )
    return issues


def _check_traceability(docs: list[Document], strict: bool) -> list[Issue]:
    """Every FR row should trace to at least one PR-* or UJ-* id."""
    issues: list[Issue] = []
    severity = "error" if strict else "warning"
    fr_doc = next((d for d in docs if d.type_key == "functional-requirements"), None)
    if fr_doc is None:
        return issues

    for line in fr_doc.body.splitlines():
        row = DEFINED_ID_RE.match(line)
        if not row:
            continue
        fr_id = row.group(1)
        tokens = [f"{p}-{n}" for p, n in ID_TOKEN_RE.findall(line)]
        traces = [t for t in tokens if t.startswith(("PR-", "UJ-"))]
        if not traces:
            issues.append(
                Issue(
                    severity,
                    fr_doc.path.name,
                    f"{fr_id} has no traceability to a PR-* or UJ-* id",
                )
            )
    return issues


def _has_app_artifacts(directory: Path) -> bool:
    """True when `directory` directly holds a recognised app (artifacts or ADRs)."""
    known_names = {meta["filename"] for meta in ARTIFACT_TYPES.values()}
    if any(p.name in known_names for p in directory.glob("*.md")):
        return True
    return (directory / ADR_DIR).is_dir()


def discover_app_dirs(root: str | Path) -> list[Path]:
    """Return immediate subfolders of `root` that look like application artifact sets.

    A subfolder qualifies when it directly contains a recognised artifact document
    or an ``architecture-decisions/`` folder. Used to support the per-application
    layout ``docs/artifacts/<app-name>/``.
    """
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and _has_app_artifacts(p))


def _validate_app_dir(directory: Path, *, strict: bool, prefix: str = "") -> list[Issue]:
    """Validate one application's artifact set living directly in `directory`.

    `prefix` is prepended to each issue's file path so aggregated multi-app output
    stays unambiguous about which application a finding belongs to.
    """
    docs: list[Document] = []
    issues: list[Issue] = []
    known_names = {meta["filename"] for meta in ARTIFACT_TYPES.values()}

    for path in sorted(directory.glob("*.md")):
        if path.name not in known_names:
            continue
        doc, parse_issues = _parse_document(path)
        issues.extend(parse_issues)
        docs.append(doc)

    if not docs:
        issues.append(Issue("warning", str(directory), "no recognised artifact documents found"))

    # Architecture Decision Records live in a subfolder; validate them and register
    # their ids so other artifacts may cross-reference decisions.
    adr_ids: set[str] = set()
    adr_path = directory / ADR_DIR
    if adr_path.is_dir():
        adr_ids = collect_adr_ids(adr_path)
        issues.extend(validate_adrs(adr_path))

    for doc in docs:
        issues.extend(_check_frontmatter(doc))
        issues.extend(_check_ids(doc))
    issues.extend(_check_cross_references(docs, adr_ids))
    issues.extend(_check_traceability(docs, strict))

    # Phase-3 implementation state is nested under implementation/ and deliberately
    # has its own schema and identifiers. Validate it without treating those files as
    # one of the eleven top-level business/architecture artifacts.
    issues.extend(
        Issue(item.severity, item.file, item.message)
        for item in validate_implementation(directory, strict=strict)
    )

    if prefix:
        issues = [Issue(i.severity, f"{prefix}/{i.file}", i.message) for i in issues]
    return issues


def validate_dir(directory: str | Path, *, strict: bool = False) -> list[Issue]:
    """Validate artifacts in `directory`.

    Supports two layouts:

    * **Single application** — `directory` directly holds the artifact documents
      (and optionally `architecture-decisions/` / `interfaces/`).
    * **Multiple applications** — `directory` holds one subfolder per application
      (``docs/artifacts/<app-name>/``). Each app is validated independently so ids
      are scoped per application, and findings are aggregated with an app prefix.

    Returns a list of Issue objects (may be empty). Unrecognised .md files are
    ignored so scratch notes can live alongside artifacts.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return [Issue("error", str(directory), "artifact directory does not exist")]

    # A directory that directly holds artifacts is treated as a single application,
    # preserving backward-compatible behaviour.
    if _has_app_artifacts(directory):
        return _validate_app_dir(directory, strict=strict)

    # Otherwise look for a per-application layout and validate each app in isolation.
    app_dirs = discover_app_dirs(directory)
    if app_dirs:
        issues: list[Issue] = []
        for app_dir in app_dirs:
            issues.extend(_validate_app_dir(app_dir, strict=strict, prefix=app_dir.name))
        return issues

    # Nothing recognised at all — keep the single-app warning contract.
    return _validate_app_dir(directory, strict=strict)
