"""Tests for the reference Enterprise Standards knowledge-base library."""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pytest

from artifact_tools.frontmatter import ID_TOKEN_RE

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples/enterprise-standards-server"
SAMPLE_KB = EXAMPLE_DIR / "knowledge-base"
TODAY = dt.date(2026, 9, 23)


def _load_library():
    spec = importlib.util.spec_from_file_location("enterprise_standards_library", EXAMPLE_DIR / "library.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


library = _load_library()


def _write(root: Path, name: str, frontmatter: str, body: str = "Body.") -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter.strip()}\n---\n\n{body}\n", encoding="utf-8")


@pytest.fixture()
def kb():
    return library.KnowledgeBase(SAMPLE_KB, today=TODAY)


def test_sample_knowledge_base_loads_cleanly(kb):
    assert kb.problems == []
    assert len(kb.documents) == 6


def test_sample_ids_are_not_misread_as_aegis_artifact_ids(kb):
    for doc_id in kb.documents:
        assert ID_TOKEN_RE.findall(doc_id) == [], doc_id


def test_search_defaults_to_approved_and_returns_metadata_only(kb):
    results = kb.search_documents(domain="Security")
    assert [item["id"] for item in results] == ["ENT-STD-SEC-001"]
    assert "body" not in results[0]

    everything = kb.search_documents(status="Any", domain="Security")
    assert {item["id"] for item in everything} == {"ENT-STD-SEC-000", "ENT-STD-SEC-001"}


def test_search_filters_combine(kb):
    assert [d["id"] for d in kb.search_documents(tags=["observability", "logging"])] == ["ENT-PAT-001"]
    assert [d["id"] for d in kb.search_documents(part_of_family="api standards")] == ["ENT-STD-API-001"]
    assert [d["id"] for d in kb.search_documents(type="Architecture Decision Record (ADR)")] == ["ENT-DEC-0001"]
    assert kb.search_documents(query="nothing matches this") == []


def test_inverse_edges_are_derived(kb):
    superseded = kb.get_related("ENT-STD-SEC-000", edge_type="superseded_by")
    assert [edge["to"] for edge in superseded["related"]] == ["ENT-STD-SEC-001"]

    required_by = kb.get_related("ENT-STD-DAT-001", edge_type="required_by")
    assert {edge["to"] for edge in required_by["related"]} == {"ENT-STD-SEC-001", "ENT-DEC-0001"}


def test_traversal_depth_does_not_revisit_documents(kb):
    related = kb.get_related("ENT-STD-SEC-001", depth=2)["related"]
    targets = [edge["to"] for edge in related]
    assert "ENT-STD-SEC-001" not in targets
    assert len(targets) == len(set(targets))
    assert "ENT-DEC-0001" in targets  # reached through ENT-STD-DAT-001 at depth 2


def test_get_document_includes_body_and_review(kb):
    doc = kb.get_document("ENT-STD-SEC-001")
    assert doc["body"].startswith("# Security Baseline")
    assert doc["review"]["review_status"] == "Current"
    with pytest.raises(KeyError):
        kb.get_document("ENT-STD-XXX-999")


def test_review_health_statuses(kb):
    by_id = {row["id"]: row["review_status"] for row in kb.review_health()}
    assert by_id["ENT-STD-SEC-000"] == "Severely Overdue"
    assert by_id["ENT-DEC-0001"] == "Overdue"
    assert by_id["ENT-STD-DAT-001"] == "Due Soon"
    assert by_id["ENT-STD-SEC-001"] == "Current"
    assert [row["id"] for row in kb.review_health(review_status="Overdue")] == ["ENT-DEC-0001"]


def test_listings(kb):
    domains = {row["domain"]: row for row in kb.list_domains()}
    assert domains["Security"] == {"domain": "Security", "document_count": 2, "approved_count": 1}
    assert {"tag": "hardening", "count": 2} in kb.list_tags()
    family = kb.list_families("Security Baseline")
    assert [doc["id"] for doc in family["documents"]] == ["ENT-STD-SEC-000", "ENT-STD-SEC-001"]


def test_problems_are_reported(tmp_path: Path):
    _write(tmp_path, "a.md", "id: ENT-STD-SEC-010\ntitle: A\ntype: Standard\nstatus: Approved\ndomain: Security")
    _write(tmp_path, "dup.md", "id: ENT-STD-SEC-010\ntitle: Dup\ntype: Standard\nstatus: Approved\ndomain: Security")
    _write(tmp_path, "missing.md", "id: ENT-STD-SEC-011\ntitle: Missing domain\ntype: Standard\nstatus: Approved")
    _write(tmp_path, "clash.md", "id: ACME-ADR-045\ntitle: Clash\ntype: Pattern\nstatus: Draft\ndomain: Data")
    _write(
        tmp_path,
        "orphan.md",
        "id: ENT-STD-SEC-012\ntitle: Orphan\ntype: Rule\nstatus: Superseded\ndomain: Security\n"
        "relationships:\n  depends_on: [ENT-STD-NOPE-001]",
    )
    (tmp_path / "README.md").write_text("# Not a standard\n", encoding="utf-8")

    kb = library.KnowledgeBase(tmp_path, today=TODAY)
    text = "\n".join(kb.problems)
    assert "duplicate id ENT-STD-SEC-010" in text
    assert "missing required field(s) domain" in text
    assert "ACME-ADR-045" in text and "misread by AEGIS" in text
    assert "unknown type 'Rule'" in text
    assert "depends_on target ENT-STD-NOPE-001 not found" in text
    assert "status Superseded but nothing supersedes it" in text
    assert "README" not in text
    assert library.main(["--check", str(tmp_path)]) == 1
    assert library.main(["--check", str(SAMPLE_KB)]) == 0
