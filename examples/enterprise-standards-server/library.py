"""Load and query an Enterprise Standards knowledge base.

A knowledge base is a folder of Markdown files, each with YAML frontmatter that follows
the schema in ``docs/enterprise-standards-setup.md``. This module has no MCP dependency
so it can be tested and reused on its own; ``server.py`` exposes it over MCP.

Validate a knowledge base from the command line::

    python library.py --check path/to/knowledge-base
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DOCUMENT_TYPES = (
    "Standard",
    "Policy",
    "Guideline",
    "Pattern",
    "Architecture Decision Record (ADR)",
)
STATUSES = ("Approved", "Draft", "Under Review", "Deprecated", "Superseded")
CLASSIFICATIONS = ("public", "internal", "confidential")
REQUIRED_FIELDS = ("id", "title", "type", "status", "domain")

# Edges an author records in frontmatter, and the inverse edge derived for the target.
AUTHORED_EDGES = {
    "supersedes": "superseded_by",
    "depends_on": "required_by",
    "related_to": "related_to",
}
EDGE_TYPES = ("supersedes", "superseded_by", "depends_on", "required_by", "related_to")

REVIEW_STATUSES = ("Current", "Due Soon", "Overdue", "Severely Overdue", "Unknown")
DUE_SOON_DAYS = 60
SEVERELY_OVERDUE_DAYS = 180
MAX_DEPTH = 3

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)

# AEGIS reads tokens such as SEC-001 or ADR-0004 as internal artifact ids unless they
# are preceded by "STD-". Library ids must avoid that collision (see the setup guide).
_AEGIS_TOKEN_RE = re.compile(r"(?<!STD-)\b(PR|FR|NFR|UJ|BP|RISK|IF|DM|SEC|DEP|OBS|ADR)-\d{3,}\b")


@dataclass
class Document:
    """One knowledge-base document."""

    meta: dict[str, Any]
    body: str
    path: Path
    edges: dict[str, list[str]] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return str(self.meta["id"])

    def metadata(self) -> dict[str, Any]:
        """Frontmatter plus derived fields, without the body."""
        data = {key: _jsonable(value) for key, value in self.meta.items() if key != "relationships"}
        data["tags"] = list(self.meta.get("tags") or [])
        data["relationships"] = {edge: list(ids) for edge, ids in self.edges.items() if ids}
        data["path"] = self.path.as_posix()
        return data


class KnowledgeBase:
    """In-memory index over a folder of Markdown standards."""

    def __init__(self, root: Path, today: dt.date | None = None) -> None:
        self.root = Path(root)
        self.today = today or dt.date.today()
        self.documents: dict[str, Document] = {}
        self.problems: list[str] = []
        self._load()

    # ------------------------------------------------------------------ loading

    def _load(self) -> None:
        if not self.root.is_dir():
            raise FileNotFoundError(f"Knowledge base folder not found: {self.root}")
        for path in sorted(self.root.rglob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            relative = path.relative_to(self.root)
            match = _FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
            if not match:
                self.problems.append(f"{relative}: no YAML frontmatter; skipped")
                continue
            try:
                meta = yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError as exc:
                self.problems.append(f"{relative}: invalid YAML frontmatter ({exc}); skipped")
                continue
            missing = [name for name in REQUIRED_FIELDS if not meta.get(name)]
            if missing:
                self.problems.append(f"{relative}: missing required field(s) {', '.join(missing)}; skipped")
                continue
            doc = Document(meta=meta, body=match.group(2).strip(), path=relative)
            if doc.id in self.documents:
                self.problems.append(f"{relative}: duplicate id {doc.id}; skipped")
                continue
            self._check_fields(doc)
            self.documents[doc.id] = doc
        self._build_edges()

    def _check_fields(self, doc: Document) -> None:
        where = f"{doc.path} ({doc.id})"
        if doc.meta["type"] not in DOCUMENT_TYPES:
            self.problems.append(f"{where}: unknown type {doc.meta['type']!r}")
        if doc.meta["status"] not in STATUSES:
            self.problems.append(f"{where}: unknown status {doc.meta['status']!r}")
        classification = doc.meta.get("classification")
        if classification and classification not in CLASSIFICATIONS:
            self.problems.append(f"{where}: unknown classification {classification!r}")
        if _AEGIS_TOKEN_RE.search(doc.id):
            self.problems.append(
                f"{where}: id would be misread by AEGIS as an internal artifact id; "
                "use the <ORG>-STD-<DOMAIN>-NNN form or a non-AEGIS type code"
            )
        relationships = doc.meta.get("relationships") or {}
        if not isinstance(relationships, dict):
            self.problems.append(f"{where}: relationships must be a mapping")
            doc.meta["relationships"] = {}
            return
        for edge in relationships:
            if edge not in EDGE_TYPES:
                self.problems.append(f"{where}: unknown relationship {edge!r}")

    def _build_edges(self) -> None:
        for doc in self.documents.values():
            doc.edges = {edge: [] for edge in EDGE_TYPES}
        for doc in self.documents.values():
            relationships = doc.meta.get("relationships") or {}
            for edge, targets in relationships.items():
                if edge not in EDGE_TYPES:
                    continue
                for target in _as_list(targets):
                    if target not in self.documents:
                        self.problems.append(f"{doc.path} ({doc.id}): {edge} target {target} not found")
                        continue
                    _add_unique(doc.edges[edge], target)
                    inverse = AUTHORED_EDGES.get(edge) or _inverse_of(edge)
                    if inverse:
                        _add_unique(self.documents[target].edges[inverse], doc.id)
        for doc in self.documents.values():
            if doc.meta["status"] == "Superseded" and not doc.edges["superseded_by"]:
                self.problems.append(f"{doc.path} ({doc.id}): status Superseded but nothing supersedes it")

    # ------------------------------------------------------------------ queries

    def list_domains(self) -> list[dict[str, Any]]:
        total = Counter(doc.meta["domain"] for doc in self.documents.values())
        approved = Counter(
            doc.meta["domain"] for doc in self.documents.values() if doc.meta["status"] == "Approved"
        )
        return [
            {"domain": domain, "document_count": count, "approved_count": approved.get(domain, 0)}
            for domain, count in sorted(total.items())
        ]

    def list_tags(self) -> list[dict[str, Any]]:
        counts = Counter(tag for doc in self.documents.values() for tag in doc.meta.get("tags") or [])
        return [{"tag": tag, "count": count} for tag, count in sorted(counts.items())]

    def list_families(self, family: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
        if family:
            members = [
                doc.metadata()
                for doc in self._sorted()
                if _same(doc.meta.get("part_of_family"), family)
            ]
            return {"family": family, "documents": members}
        counts = Counter(
            doc.meta["part_of_family"] for doc in self.documents.values() if doc.meta.get("part_of_family")
        )
        return [{"family": name, "document_count": count} for name, count in sorted(counts.items())]

    def search_documents(
        self,
        status: str | None = "Approved",
        type: str | None = None,
        domain: str | None = None,
        classification: str | None = None,
        tags: list[str] | None = None,
        version: str | None = None,
        part_of_family: str | None = None,
        query: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Metadata-only search. ``status="Any"`` (or ``None``) disables the status filter."""
        wanted_tags = {tag.lower() for tag in tags or []}
        needle = (query or "").lower()
        results = []
        for doc in self._sorted():
            meta = doc.meta
            if status and status.lower() != "any" and not _same(meta["status"], status):
                continue
            if type and not _same(meta["type"], type):
                continue
            if domain and not _same(meta["domain"], domain):
                continue
            if classification and not _same(meta.get("classification"), classification):
                continue
            if version and str(meta.get("version", "")) != str(version):
                continue
            if part_of_family and not _same(meta.get("part_of_family"), part_of_family):
                continue
            if wanted_tags and not wanted_tags <= {str(tag).lower() for tag in meta.get("tags") or []}:
                continue
            if needle and needle not in f"{meta['title']} {meta.get('summary', '')}".lower():
                continue
            results.append(doc.metadata())
            if len(results) >= max(1, limit):
                break
        return results

    def get_document(self, id: str) -> dict[str, Any]:
        doc = self._require(id)
        data = doc.metadata()
        data["review"] = self._review(doc)
        data["body"] = doc.body
        return data

    def get_related(self, id: str, edge_type: str | None = None, depth: int = 1) -> dict[str, Any]:
        start = self._require(id)
        if edge_type and edge_type not in EDGE_TYPES:
            raise ValueError(f"Unknown edge_type {edge_type!r}; expected one of {', '.join(EDGE_TYPES)}")
        depth = min(max(1, depth), MAX_DEPTH)
        edges_to_follow = [edge_type] if edge_type else list(EDGE_TYPES)
        seen = {start.id}
        found: list[dict[str, Any]] = []
        queue = deque([(start.id, 0)])
        while queue:
            current, level = queue.popleft()
            if level >= depth:
                continue
            for edge in edges_to_follow:
                for target in self.documents[current].edges.get(edge, []):
                    if target in seen:
                        continue
                    seen.add(target)
                    queue.append((target, level + 1))
                    other = self.documents[target]
                    found.append(
                        {
                            "from": current,
                            "edge": edge,
                            "to": target,
                            "title": other.meta["title"],
                            "status": other.meta["status"],
                            "depth": level + 1,
                        }
                    )
        return {"id": start.id, "related": found}

    def review_health(self, domain: str | None = None, review_status: str | None = None) -> list[dict[str, Any]]:
        rows = []
        for doc in self._sorted():
            if domain and not _same(doc.meta["domain"], domain):
                continue
            review = self._review(doc)
            if review_status and not _same(review["review_status"], review_status):
                continue
            rows.append({"id": doc.id, "title": doc.meta["title"], "domain": doc.meta["domain"],
                         "status": doc.meta["status"], **review})
        return rows

    # ------------------------------------------------------------------ helpers

    def _require(self, id: str) -> Document:
        doc = self.documents.get(id)
        if doc is None:
            raise KeyError(f"No document with id {id!r}")
        return doc

    def _sorted(self) -> list[Document]:
        return [self.documents[key] for key in sorted(self.documents)]

    def _review(self, doc: Document) -> dict[str, Any]:
        last = _as_date(doc.meta.get("last_reviewed"))
        cycle = doc.meta.get("review_cycle_months") or 12
        if last is None:
            return {"last_reviewed": None, "next_review": None, "review_status": "Unknown", "days_overdue": None}
        next_review = _add_months(last, int(cycle))
        days_late = (self.today - next_review).days
        if days_late > SEVERELY_OVERDUE_DAYS:
            status = "Severely Overdue"
        elif days_late > 0:
            status = "Overdue"
        elif -days_late <= DUE_SOON_DAYS:
            status = "Due Soon"
        else:
            status = "Current"
        return {
            "last_reviewed": last.isoformat(),
            "next_review": next_review.isoformat(),
            "review_status": status,
            "days_overdue": max(0, days_late),
        }


def _inverse_of(edge: str) -> str | None:
    for authored, inverse in AUTHORED_EDGES.items():
        if edge == inverse:
            return authored
    return None


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _same(value: Any, expected: str) -> bool:
    return value is not None and str(value).lower() == str(expected).lower()


def _as_date(value: Any) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _add_months(day: dt.date, months: int) -> dt.date:
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    for candidate in (day.day, 30, 29, 28):
        try:
            return dt.date(year, month, candidate)
        except ValueError:
            continue
    raise ValueError(f"Cannot add {months} months to {day}")


def _jsonable(value: Any) -> Any:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an Enterprise Standards knowledge base.")
    parser.add_argument("--check", metavar="KNOWLEDGE_BASE", required=True, help="Folder to validate.")
    args = parser.parse_args(argv)
    kb = KnowledgeBase(Path(args.check))
    for problem in kb.problems:
        print(f"problem: {problem}")
    print(f"{len(kb.documents)} document(s) loaded, {len(kb.problems)} problem(s).")
    return 1 if kb.problems else 0


if __name__ == "__main__":
    sys.exit(main())
