"""End-to-end tests for scaffold, validate and changelog."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifact_tools.changelog import add_changelog
from artifact_tools.constants import ARTIFACT_TYPES, resolve_type
from artifact_tools.frontmatter import split_document
from artifact_tools.scaffold import scaffold
from artifact_tools.validate import has_errors, validate_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "aegis/skills/artifact-management/assets/templates"


def _scaffold_all(out_dir: Path) -> None:
    for type_key in ARTIFACT_TYPES:
        scaffold(
            type_key,
            out_dir,
            project="Test Project",
            templates_dir=TEMPLATES,
        )


def test_resolve_type_aliases():
    assert resolve_type("prd") == "product-requirements"
    assert resolve_type("FR") == "functional-requirements"
    assert resolve_type("system-blueprint") == "system-blueprint"
    with pytest.raises(KeyError):
        resolve_type("nonsense")


def test_scaffold_creates_file(tmp_path: Path):
    path = scaffold("prd", tmp_path, project="Acme", templates_dir=TEMPLATES)
    assert path.exists()
    fm, body = split_document(path.read_text(encoding="utf-8"))
    assert fm["artifact"] == "product-requirements"
    assert "{{" not in body  # all placeholders filled
    assert "Acme" in body


def test_scaffold_refuses_overwrite(tmp_path: Path):
    scaffold("prd", tmp_path, templates_dir=TEMPLATES)
    with pytest.raises(FileExistsError):
        scaffold("prd", tmp_path, templates_dir=TEMPLATES)
    # force succeeds
    scaffold("prd", tmp_path, templates_dir=TEMPLATES, force=True)


def test_fresh_scaffold_set_validates_clean(tmp_path: Path):
    _scaffold_all(tmp_path)
    issues = validate_dir(tmp_path)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == [], [i.format() for i in errors]
    assert not has_errors(issues)


def test_unknown_cross_reference_is_error(tmp_path: Path):
    _scaffold_all(tmp_path)
    fr = tmp_path / "functional-requirements.md"
    text = fr.read_text(encoding="utf-8")
    # Reference an id that is defined nowhere.
    text = text.replace("| PR-001 | draft |", "| PR-999 | draft |")
    fr.write_text(text, encoding="utf-8")

    issues = validate_dir(tmp_path)
    assert has_errors(issues)
    assert any("PR-999" in i.message for i in issues)


def test_duplicate_id_is_error(tmp_path: Path):
    _scaffold_all(tmp_path)
    nfr = tmp_path / "non-functional-requirements.md"
    text = nfr.read_text(encoding="utf-8")
    text = text.replace("| NFR-002 | security", "| NFR-001 | security")
    nfr.write_text(text, encoding="utf-8")

    issues = validate_dir(tmp_path)
    assert has_errors(issues)
    assert any("duplicate id" in i.message for i in issues)


def test_wrong_prefix_is_error(tmp_path: Path):
    _scaffold_all(tmp_path)
    nfr = tmp_path / "non-functional-requirements.md"
    text = nfr.read_text(encoding="utf-8")
    text = text.replace("| NFR-001 | performance", "| FR-500 | performance")
    nfr.write_text(text, encoding="utf-8")

    issues = validate_dir(tmp_path)
    assert has_errors(issues)


def test_bad_frontmatter_status_is_error(tmp_path: Path):
    _scaffold_all(tmp_path)
    prd = tmp_path / "product-requirements.md"
    text = prd.read_text(encoding="utf-8")
    text = text.replace("status: draft", "status: banana", 1)
    prd.write_text(text, encoding="utf-8")

    issues = validate_dir(tmp_path)
    assert has_errors(issues)
    assert any("invalid status" in i.message for i in issues)


def test_missing_traceability_warns_but_passes(tmp_path: Path):
    _scaffold_all(tmp_path)
    fr = tmp_path / "functional-requirements.md"
    text = fr.read_text(encoding="utf-8")
    # Remove the traces_to reference so FR-001 has no PR/UJ link.
    text = text.replace("| must | PR-001 | draft |", "| must | | draft |")
    fr.write_text(text, encoding="utf-8")

    issues = validate_dir(tmp_path)
    assert not has_errors(issues)  # advisory only
    assert any(i.severity == "warning" and "traceability" in i.message for i in issues)
    # strict mode turns it into a failure
    strict_issues = validate_dir(tmp_path, strict=True)
    assert has_errors(strict_issues, strict=True)


def test_changelog_bumps_version(tmp_path: Path):
    path = scaffold("prd", tmp_path, templates_dir=TEMPLATES)
    version = add_changelog(path, "Added scope section", level="minor")
    assert version == "0.2"
    fm, body = split_document(path.read_text(encoding="utf-8"))
    assert fm["version"] == "0.2"
    assert "Added scope section" in body

    major = add_changelog(path, "Breaking restructure", level="major")
    assert major == "1.0"


# --------------------------------------------------------------------------- #
# Architecture-phase artifacts
# --------------------------------------------------------------------------- #


def test_new_technical_types_registered():
    for type_key in (
        "interface-specifications",
        "data-architecture",
        "security-architecture",
        "deployment-topology",
        "observability-strategy",
    ):
        assert type_key in ARTIFACT_TYPES


def test_technical_type_aliases():
    assert resolve_type("interfaces") == "interface-specifications"
    assert resolve_type("data") == "data-architecture"
    assert resolve_type("security") == "security-architecture"
    assert resolve_type("deployment") == "deployment-topology"
    assert resolve_type("observability") == "observability-strategy"


def test_scaffold_technical_artifact(tmp_path: Path):
    path = scaffold("security", tmp_path, project="Acme", templates_dir=TEMPLATES)
    assert path.name == "security-architecture.md"
    fm, body = split_document(path.read_text(encoding="utf-8"))
    assert fm["artifact"] == "security-architecture"
    assert fm["phase"] == 2
    assert "{{" not in body


def test_scaffold_interface_creates_contract_store(tmp_path: Path):
    scaffold("interfaces", tmp_path, project="Acme", templates_dir=TEMPLATES)
    store = tmp_path / "interfaces"
    assert (store / "synchronous").is_dir()
    assert (store / "asynchronous").is_dir()
    assert (store / "graphql").is_dir()
    assert (store / "README.md").is_file()
    # Native contract stubs are parseable schema files, not Markdown.
    assert (store / "synchronous" / "identity-auth-v1.yaml").is_file()
    assert (store / "graphql" / "gateway-schema.graphql").is_file()


def test_interfaces_init_is_idempotent(tmp_path: Path):
    from artifact_tools.interfaces import init_interfaces_dir

    store = init_interfaces_dir(tmp_path)
    marker = store / "graphql" / "gateway-schema.graphql"
    marker.write_text("# edited\n", encoding="utf-8")
    init_interfaces_dir(tmp_path)  # must not overwrite existing files
    assert marker.read_text(encoding="utf-8") == "# edited\n"


def test_interface_index_validates_and_ignores_contract_store(tmp_path: Path):
    _scaffold_all(tmp_path)  # includes interface-specifications + its interfaces/ store
    issues = validate_dir(tmp_path)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == [], [i.format() for i in errors]


# --------------------------------------------------------------------------- #
# Architecture Decision Records
# --------------------------------------------------------------------------- #


def _adr_dir(tmp_path: Path) -> Path:
    return tmp_path / "architecture-decisions"


def test_adr_new_numbers_and_indexes(tmp_path: Path):
    from artifact_tools.adr import create_adr

    adr_dir = _adr_dir(tmp_path)
    path, adr_id = create_adr(
        "Event driven topology", adr_dir, status="accepted", templates_dir=TEMPLATES
    )
    # Seed template is ADR-0001, so the first real record is ADR-0002.
    assert adr_id == "ADR-0002"
    assert path.name == "0002-event-driven-topology.md"
    index = (adr_dir / "README.md").read_text(encoding="utf-8")
    assert "ADR-0002" in index


def test_adr_supersede_sets_backlink(tmp_path: Path):
    from artifact_tools.adr import create_adr
    from artifact_tools.frontmatter import split_document as split

    adr_dir = _adr_dir(tmp_path)
    old_path, old_id = create_adr("Use MongoDB", adr_dir, templates_dir=TEMPLATES)
    _, new_id = create_adr(
        "Use PostgreSQL", adr_dir, supersedes=old_id, templates_dir=TEMPLATES
    )
    fm, _ = split(old_path.read_text(encoding="utf-8"))
    assert fm["status"] == "superseded"
    assert fm["superseded_by"] == new_id


def test_adr_validation_clean(tmp_path: Path):
    from artifact_tools.adr import create_adr, validate_adrs

    adr_dir = _adr_dir(tmp_path)
    create_adr("A decision", adr_dir, status="accepted", templates_dir=TEMPLATES)
    issues = validate_adrs(adr_dir)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == [], [i.format() for i in errors]


def test_adr_bad_status_is_error(tmp_path: Path):
    from artifact_tools.adr import create_adr, validate_adrs

    adr_dir = _adr_dir(tmp_path)
    path, _ = create_adr("A decision", adr_dir, templates_dir=TEMPLATES)
    text = path.read_text(encoding="utf-8").replace(
        "status: proposed", "status: banana", 1
    )
    path.write_text(text, encoding="utf-8")
    issues = validate_adrs(adr_dir)
    assert any("invalid status" in i.message for i in issues)


def test_adr_ids_resolve_as_cross_references(tmp_path: Path):
    from artifact_tools.adr import create_adr

    _scaffold_all(tmp_path)
    create_adr("Core topology", _adr_dir(tmp_path), templates_dir=TEMPLATES)
    # Reference the ADR from the blueprint; it must resolve, not error.
    bp = tmp_path / "system-blueprint.md"
    text = bp.read_text(encoding="utf-8").replace(
        "## 3. Data Flow", "See decision ADR-0002.\n\n## 3. Data Flow", 1
    )
    bp.write_text(text, encoding="utf-8")
    issues = validate_dir(tmp_path)
    assert not any("ADR-0002" in i.message for i in issues)
    assert not has_errors(issues)


# --------------------------------------------------------------------------- #
# Multiple applications (per-app layout: docs/artifacts/<app>/...)
# --------------------------------------------------------------------------- #


def test_discover_app_dirs_finds_apps(tmp_path: Path):
    from artifact_tools.validate import discover_app_dirs

    _scaffold_all(tmp_path / "app-a")
    _scaffold_all(tmp_path / "app-b")
    (tmp_path / "not-an-app").mkdir()  # empty dir must be ignored

    apps = discover_app_dirs(tmp_path)
    assert [p.name for p in apps] == ["app-a", "app-b"]


def test_multi_app_root_validates_each_app(tmp_path: Path):
    _scaffold_all(tmp_path / "app-a")
    _scaffold_all(tmp_path / "app-b")

    issues = validate_dir(tmp_path)
    errors = [i for i in issues if i.severity == "error"]
    assert errors == [], [i.format() for i in errors]
    assert not has_errors(issues)


def test_ids_are_scoped_per_app(tmp_path: Path):
    # The same requirement id in two different apps is fine — ids are per-app.
    _scaffold_all(tmp_path / "app-a")
    _scaffold_all(tmp_path / "app-b")

    issues = validate_dir(tmp_path)
    assert not has_errors(issues)


def test_multi_app_error_is_prefixed_with_app(tmp_path: Path):
    _scaffold_all(tmp_path / "app-a")
    _scaffold_all(tmp_path / "app-b")
    # Break a cross-reference in app-b only.
    fr = tmp_path / "app-b" / "functional-requirements.md"
    text = fr.read_text(encoding="utf-8").replace("| PR-001 | draft |", "| PR-999 | draft |")
    fr.write_text(text, encoding="utf-8")

    issues = validate_dir(tmp_path)
    assert has_errors(issues)
    offending = [i for i in issues if "PR-999" in i.message]
    assert offending, [i.format() for i in issues]
    assert all(i.file.startswith("app-b/") for i in offending)
    # app-a must remain clean.
    assert not any(i.file.startswith("app-a/") and i.severity == "error" for i in issues)


def test_single_app_layout_still_supported(tmp_path: Path):
    # A directory holding artifacts directly is treated as one application.
    _scaffold_all(tmp_path)
    issues = validate_dir(tmp_path)
    assert not has_errors(issues)
    # File paths are not prefixed in the single-app case.
    assert not any("/" in i.file for i in issues if i.file.endswith(".md"))


def test_cli_writes_lf_line_endings_on_every_platform(tmp_path: Path):
    """Path.write_text translates newlines to CRLF on Windows unless told not to."""
    from artifact_tools.adr import create_adr, init_adr_dir
    from artifact_tools.interfaces import init_interfaces_dir

    app = tmp_path / "app"
    for type_key in ARTIFACT_TYPES:
        scaffold(type_key, app, project="LF", templates_dir=TEMPLATES)
    adr_dir = app / "architecture-decisions"
    init_adr_dir(adr_dir, templates_dir=TEMPLATES)
    create_adr("Pick a database", adr_dir, status="accepted", templates_dir=TEMPLATES)
    create_adr("Pick a better database", adr_dir, supersedes="ADR-0002", templates_dir=TEMPLATES)
    init_interfaces_dir(app)
    add_changelog(app / "product-requirements.md", "Tightened scope")

    written = [path for path in app.rglob("*") if path.is_file()]
    assert len(written) > 15
    carriage_return = bytes([13])
    assert [p.name for p in written if carriage_return in p.read_bytes()] == []
