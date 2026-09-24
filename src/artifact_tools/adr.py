"""Create, index and validate Architecture Decision Records (ADRs).

ADRs differ from the single-file artifacts: they are a *folder* of many immutable
records under ``<artifact-dir>/architecture-decisions/`` plus a ``README.md`` index
table. Each record follows a lightweight Nygard/MADR shape and carries its own
frontmatter (``id``, ``status``, ``supersedes`` / ``superseded_by`` ...).

This module is intentionally free of any import of :mod:`artifact_tools.validate` at
module load time; :func:`validate_adrs` imports the shared ``Issue`` lazily so the
validator can depend on this module without a circular import.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from artifact_tools.constants import (
    ADR_INDEX_FILENAME,
    ADR_TEMPLATE_FILENAME,
    VALID_ADR_STATUS,
)
from artifact_tools.frontmatter import (
    find_templates_dir,
    render_document,
    split_document,
)
from artifact_tools.issues import Issue

# Matches an ADR file such as "0002-event-driven-topology.md".
ADR_FILE_RE = re.compile(r"^(\d{4})-.+\.md$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Frontmatter fields carried by every ADR record.
ADR_FRONTMATTER: tuple[str, ...] = (
    "id",
    "title",
    "status",
    "date",
    "component",
    "supersedes",
    "superseded_by",
    "deciders",
)


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")
    return slug or "decision"


def adr_id(number: int) -> str:
    """Return the canonical ADR id for a number, e.g. 2 -> 'ADR-0002'."""
    return f"ADR-{number:04d}"


def _iter_adr_files(adr_dir: Path):
    """Yield (number, path) for every numbered ADR file, sorted by number."""
    found: list[tuple[int, Path]] = []
    for path in adr_dir.glob("*.md"):
        match = ADR_FILE_RE.match(path.name)
        if match:
            found.append((int(match.group(1)), path))
    return sorted(found, key=lambda item: item[0])


def next_adr_number(adr_dir: Path) -> int:
    """Return the next free ADR number (max existing + 1, or 1 when empty)."""
    numbers = [num for num, _ in _iter_adr_files(adr_dir)]
    return (max(numbers) + 1) if numbers else 1


def collect_adr_ids(adr_dir: str | Path) -> set[str]:
    """Return the set of ADR ids defined by files in ``adr_dir``."""
    adr_dir = Path(adr_dir)
    ids: set[str] = set()
    if not adr_dir.is_dir():
        return ids
    for number, path in _iter_adr_files(adr_dir):
        fm, _ = _safe_split(path)
        declared = str(fm.get("id")) if fm and fm.get("id") else None
        ids.add(declared or adr_id(number))
    return ids


def _safe_split(path: Path):
    try:
        return split_document(path.read_text(encoding="utf-8"))
    except Exception:
        return None, ""


# --------------------------------------------------------------------------- #
# Index table maintenance
# --------------------------------------------------------------------------- #



def _index_row(
    *, id_: str, title: str, dt: str, status: str, component: str,
    consequences: str, filename: str,
) -> str:
    return (
        f"| {id_} | {title} | {dt} | {status} | {component} "
        f"| {consequences} | [{filename}]({filename}) |"
    )


def _find_table_bounds(lines: list[str]) -> tuple[int, int] | None:
    """Return (header_idx, last_data_idx) for the ADR index table, or None."""
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("| ID ") and "Title" in stripped and "Status" in stripped:
            header_idx = i
            break
    if header_idx is None:
        return None
    # Data rows start two lines after the header (skip the separator line).
    last = header_idx + 1
    j = header_idx + 2
    while j < len(lines) and lines[j].lstrip().startswith("|"):
        last = j
        j += 1
    return header_idx, last


def _append_index_row(index_path: Path, row: str) -> None:
    lines = index_path.read_text(encoding="utf-8").splitlines()
    bounds = _find_table_bounds(lines)
    if bounds is None:
        raise ValueError(f"No ADR index table found in {index_path}")
    _, last_data_idx = bounds
    lines.insert(last_data_idx + 1, row)
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _update_index_status(index_path: Path, target_id: str, new_status: str) -> None:
    lines = index_path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if not line.lstrip().startswith(f"| {target_id} "):
            continue
        cells = line.split("|")
        # cells: ['', ' ID ', ' Title ', ' Date ', ' Status ', ...]
        if len(cells) > 4:
            cells[4] = f" {new_status} "
            lines[i] = "|".join(cells)
        break
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _set_frontmatter_fields(path: Path, updates: dict) -> None:
    fm, body = split_document(path.read_text(encoding="utf-8"))
    if fm is None:
        raise ValueError(f"{path} has no frontmatter to update")
    fm.update(updates)
    path.write_text(render_document(fm, body), encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- #
# Public commands
# --------------------------------------------------------------------------- #

def _fill(text: str, mapping: dict[str, str]) -> str:
    for token, value in mapping.items():
        text = text.replace(token, value)
    return text


def init_adr_dir(adr_dir: str | Path, *, templates_dir: Path | None = None) -> Path:
    """Create the ADR folder, its index README, and the seed template ADR.

    Idempotent: existing files are left untouched. Returns the index path.
    """
    adr_dir = Path(adr_dir)
    adr_dir.mkdir(parents=True, exist_ok=True)
    templates = templates_dir or find_templates_dir()
    today = date.today().isoformat()

    index_path = adr_dir / ADR_INDEX_FILENAME
    if not index_path.exists():
        src = templates / "architecture-decisions-index.template.md"
        index_path.write_text(
            _fill(src.read_text(encoding="utf-8"), {"{{DATE}}": today}),
            encoding="utf-8", newline="\n",
        )

    seed_path = adr_dir / ADR_TEMPLATE_FILENAME
    if not seed_path.exists():
        src = templates / "adr.template.md"
        seed_path.write_text(
            _fill(
                src.read_text(encoding="utf-8"),
                {
                    "{{ADR_ID}}": adr_id(1),
                    "{{TITLE}}": "Record architecture decisions",
                    "{{STATUS}}": "accepted",
                    "{{DATE}}": today,
                    "{{COMPONENT}}": "Governance",
                    "{{DECIDERS}}": "architecture-orchestrator",
                    "{{SUPERSEDES}}": "—",
                    "{{SUPERSEDED_BY}}": "—",
                },
            ),
            encoding="utf-8", newline="\n",
        )
    return index_path


def create_adr(
    title: str,
    adr_dir: str | Path,
    *,
    status: str = "proposed",
    component: str = "TBD",
    supersedes: str | None = None,
    deciders: str = "architecture-orchestrator",
    templates_dir: Path | None = None,
) -> tuple[Path, str]:
    """Create the next ADR from the template and append it to the index.

    Returns (path, adr_id). When ``supersedes`` is given, the superseded record's
    status is flipped to ``superseded`` and its ``superseded_by`` back-link is set.
    """
    if status not in VALID_ADR_STATUS:
        raise ValueError(
            f"invalid status '{status}' (allowed: {sorted(VALID_ADR_STATUS)})"
        )

    adr_dir = Path(adr_dir)
    templates = templates_dir or find_templates_dir()
    index_path = init_adr_dir(adr_dir, templates_dir=templates)

    number = next_adr_number(adr_dir)
    new_id = adr_id(number)
    today = date.today().isoformat()
    filename = f"{number:04d}-{_slugify(title)}.md"
    out_path = adr_dir / filename

    supersedes_val = supersedes or ""
    template = (templates / "adr.template.md").read_text(encoding="utf-8")
    out_path.write_text(
        _fill(
            template,
            {
                "{{ADR_ID}}": new_id,
                "{{TITLE}}": title,
                "{{STATUS}}": status,
                "{{DATE}}": today,
                "{{COMPONENT}}": component,
                "{{DECIDERS}}": deciders,
                "{{SUPERSEDES}}": supersedes_val or "—",
                "{{SUPERSEDED_BY}}": "—",
            },
        ),
        encoding="utf-8", newline="\n",
    )
    _set_frontmatter_fields(out_path, {"supersedes": supersedes_val})

    _append_index_row(
        index_path,
        _index_row(
            id_=new_id,
            title=title,
            dt=today,
            status=status,
            component=component,
            consequences="See record.",
            filename=filename,
        ),
    )

    if supersedes:
        _supersede(adr_dir, index_path, superseded_id=supersedes, by_id=new_id)

    return out_path, new_id


def _supersede(
    adr_dir: Path, index_path: Path, *, superseded_id: str, by_id: str
) -> None:
    for _, path in _iter_adr_files(adr_dir):
        fm, _ = _safe_split(path)
        if fm and str(fm.get("id")) == superseded_id:
            _set_frontmatter_fields(
                path, {"status": "superseded", "superseded_by": by_id}
            )
            break
    _update_index_status(index_path, superseded_id, "superseded")


def validate_adrs(adr_dir: str | Path) -> list:
    """Validate ADR records and their index. Returns a list of ``Issue`` objects."""
    adr_dir = Path(adr_dir)
    issues: list = []
    if not adr_dir.is_dir():
        return issues

    index_path = adr_dir / ADR_INDEX_FILENAME
    index_text = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    if not index_text:
        issues.append(Issue("error", ADR_INDEX_FILENAME, "ADR index README is missing"))

    seen_ids: dict[str, str] = {}
    file_ids: set[str] = set()

    for number, path in _iter_adr_files(adr_dir):
        name = path.name
        fm, _ = _safe_split(path)
        if fm is None:
            issues.append(Issue("error", name, "missing or invalid ADR frontmatter"))
            continue

        for key in ADR_FRONTMATTER:
            if key not in fm:
                issues.append(Issue("error", name, f"missing ADR frontmatter '{key}'"))

        declared = str(fm.get("id") or "")
        expected = adr_id(number)
        if declared and declared != expected:
            issues.append(
                Issue("error", name, f"id '{declared}' does not match filename number ({expected})")
            )
        rid = declared or expected
        file_ids.add(rid)
        if rid in seen_ids:
            issues.append(Issue("error", name, f"duplicate ADR id {rid} (also in {seen_ids[rid]})"))
        seen_ids[rid] = name

        status = fm.get("status")
        if status is not None and status not in VALID_ADR_STATUS:
            issues.append(
                Issue("error", name, f"invalid status '{status}' (allowed: {sorted(VALID_ADR_STATUS)})")
            )
        if status == "superseded" and not fm.get("superseded_by"):
            issues.append(Issue("error", name, "status 'superseded' requires a 'superseded_by' id"))

        dt = fm.get("date")
        if dt is not None and not _DATE_RE.match(str(dt)):
            issues.append(Issue("error", name, f"date '{dt}' must be ISO YYYY-MM-DD"))

        if index_text and rid not in index_text:
            issues.append(Issue("error", ADR_INDEX_FILENAME, f"index is missing a row for {rid}"))

    # Every superseded_by / supersedes reference must point to a known ADR.
    for _number, path in _iter_adr_files(adr_dir):
        fm, _ = _safe_split(path)
        if not fm:
            continue
        for field in ("supersedes", "superseded_by"):
            ref = str(fm.get(field) or "").strip()
            if ref and ref not in ("—", "-") and ref not in file_ids:
                issues.append(
                    Issue("error", path.name, f"{field} references unknown ADR {ref}")
                )

    return issues
