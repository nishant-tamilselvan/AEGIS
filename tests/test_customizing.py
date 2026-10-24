"""Tests for aegis.config.yaml: plugin identity, overlays, standards server and artifact types."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

from artifact_tools import constants
from artifact_tools.__main__ import main as cli_main
from artifact_tools.config import (
    CONFIG_ENV,
    DEFAULT_CONFIG,
    ConfigError,
    find_config,
    load_config,
    register_artifact_types,
)
from artifact_tools.frontmatter import DEFINED_ID_RE, ID_TOKEN_RE
from artifact_tools.readiness import check_readiness
from artifact_tools.scaffold import scaffold
from artifact_tools.validate import validate_dir

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_sync():
    spec = importlib.util.spec_from_file_location("sync_platforms", REPO_ROOT / "scripts/sync_platforms.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sync = _load_sync()


def _copy_generator_inputs(root: Path) -> None:
    for name in ("aegis", ".github", ".claude", ".claude-plugin", "plugins", "scripts", "src"):
        shutil.copytree(REPO_ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(REPO_ROOT / "pyproject.toml", root / "pyproject.toml")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _config(root: Path, text: str) -> Path:
    return _write(root / "aegis.config.yaml", text)


def _planned(root: Path) -> dict[Path, bytes]:
    return sync.planned_files(root, load_config(root / "aegis.config.yaml", root=root))


AGENT = """\
---
name: example-reviewer
title: "Example Reviewer"
role: specialist
description: "Use to review example-app artifacts against example-org conventions."
tools: [read, search, standards]
---
You review artifacts for example-org.
"""

PROMPT = """\
---
name: example-review
description: "Run the example-org review."
agent: example-reviewer
argument-hint: "[app-name]"
---
Review the application.
"""

SKILL = """\
---
name: example-conventions
description: "Example-org naming conventions. Use when naming services."
---
Name services after the capability they provide.
"""

TEMPLATE = """\
---
artifact: privacy-assessment
title: "{{TITLE}}"
version: "0.1"
status: draft
last_updated: "{{DATE}}"
phase: 2
owner: artifact-manager
---

# Privacy Assessment: {{PROJECT_NAME}}

| Id | Finding |
| --- | --- |
| PIA-001 | Personal data is limited to contact details. |
"""


# --------------------------------------------------------------------------- defaults


def test_no_config_means_defaults(tmp_path: Path):
    assert load_config(None) == DEFAULT_CONFIG
    assert DEFAULT_CONFIG.plugin.name == "aegis"
    assert DEFAULT_CONFIG.standards_server == "enterprise-standards-server"
    assert DEFAULT_CONFIG.overlay is None and DEFAULT_CONFIG.artifact_types == ()


def test_empty_config_reproduces_default_output(tmp_path: Path):
    _copy_generator_inputs(tmp_path)
    _config(tmp_path, "# nothing configured\n")
    assert sync.main(["--check", "--root", str(tmp_path)]) == 0
    assert sync.planned_files(tmp_path, load_config(tmp_path / "aegis.config.yaml")) == sync.planned_files(tmp_path)


def test_default_artifact_registry_is_unchanged():
    assert len(constants.ARTIFACT_TYPES) == 11
    assert constants.ARTIFACT_TEMPLATES == {} and constants.OPTIONAL_ARTIFACT_TYPES == set()
    assert ID_TOKEN_RE.pattern == r"(?<!STD-)\b(PR|FR|NFR|UJ|BP|RISK|IF|DM|SEC|DEP|OBS|ADR)-(\d{3,})\b"
    assert DEFINED_ID_RE.pattern == r"^\|\s*((?:PR|FR|NFR|UJ|BP|RISK|IF|DM|SEC|DEP|OBS)-\d{3,})\s*\|"


# --------------------------------------------------------------------------- validation


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("- a list\n", "must be a mapping"),
        ("branding: {}\n", "unknown key(s) branding"),
        ("plugin: {name: Example Org}\n", "plugin.name"),
        ("plugin: {homepage: x}\n", "unknown key(s) homepage"),
        ("plugin: {repo_url: 'http://example.com/repo'}\n", "https://"),
        ("plugin: {description: ''}\n", "non-empty string"),
        ("overlay: {overrides: []}\n", "overlay.path is required"),
        ("overlay: {path: missing}\n", "is not a folder"),
        ("overlay: {path: ..}\n", "must be inside"),
        ("overlay: {path: .}\n", "its own folder"),
        ("standards: {server: 'has space'}\n", "standards.server"),
        ("artifact_types: {Bad_Name: {}}\n", "lower-case"),
        ("artifact_types: {privacy-assessment: {title: P, template: t.md}}\n", "prefix is required"),
        ("artifact_types: {privacy-assessment: {prefix: pia, title: P, template: t.md}}\n", "upper-case"),
        ("artifact_types: {privacy-assessment: {prefix: PIA, title: P, template: missing.md}}\n", "does not exist"),
        ("artifact_types: {privacy-assessment: {prefix: PIA, title: P, template: t.md, required: 'no'}}\n", "true or false"),
        ("artifact_types: {privacy-assessment: {prefix: PIA, title: P, template: t.md, filename: a/b.md}}\n", "plain file name"),
        (": not yaml : [\n", "not valid YAML"),
    ],
)
def test_invalid_config_is_rejected(tmp_path: Path, text: str, message: str):
    _write(tmp_path / "t.md", TEMPLATE)
    with pytest.raises(ConfigError, match=None) as excinfo:
        load_config(_config(tmp_path, text))
    assert message in str(excinfo.value)


def test_override_entries_must_name_a_source_path(tmp_path: Path):
    (tmp_path / "overlay").mkdir()
    for entry in ("instructions.md", "agents/x.txt", "skills/x", "../aegis/agents/x.md"):
        with pytest.raises(ConfigError, match="overrides entry"):
            load_config(_config(tmp_path, f"overlay: {{path: overlay, overrides: ['{entry}']}}\n"))


def test_valid_config_is_parsed(tmp_path: Path):
    (tmp_path / "overlay").mkdir()
    _write(tmp_path / "overlay/templates/privacy.md", TEMPLATE)
    config = load_config(_config(tmp_path, """\
plugin:
  name: example-org-aegis
  description: AEGIS for example-org.
  author: Example Org
  repo_url: https://github.com/example-org/aegis-edition/
overlay:
  path: overlay
  overrides: [agents/critic-reviewer.md]
standards:
  server: example-standards
artifact_types:
  privacy-assessment:
    prefix: PIA
    title: Privacy Assessment
    template: overlay/templates/privacy.md
    aliases: [PIA, privacy]
    required: false
"""))
    assert config.plugin.name == "example-org-aegis"
    assert config.plugin.repo_url == "https://github.com/example-org/aegis-edition"
    assert config.overlay.path == (tmp_path / "overlay").resolve()
    assert config.overlay.overrides == ("agents/critic-reviewer.md",)
    assert config.standards_server == "example-standards"
    (item,) = config.artifact_types
    assert (item.key, item.filename, item.prefix, item.aliases, item.required) == (
        "privacy-assessment", "privacy-assessment.md", "PIA", ("pia", "privacy"), False,
    )


def test_find_config_walks_up_and_honours_the_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(CONFIG_ENV, raising=False)
    nested = tmp_path / "docs/artifacts/example-app"
    nested.mkdir(parents=True)
    assert find_config(nested) is None
    config = _config(tmp_path, "{}\n")
    assert find_config(nested) == config.resolve()

    other = _write(tmp_path / "elsewhere/edition.yaml", "{}\n")
    monkeypatch.setenv(CONFIG_ENV, str(other))
    assert find_config(nested) == other.resolve()
    monkeypatch.setenv(CONFIG_ENV, str(tmp_path / "missing.yaml"))
    with pytest.raises(ConfigError, match=CONFIG_ENV):
        find_config(nested)


# --------------------------------------------------------------------------- plugin identity


def test_plugin_identity_comes_from_config(tmp_path: Path):
    _copy_generator_inputs(tmp_path)
    _config(tmp_path, """\
plugin:
  name: example-org-aegis
  description: AEGIS agents for example-org teams.
  author: Example Org
  repo_url: https://github.com/example-org/aegis-edition
""")
    files = _planned(tmp_path)
    manifest = json.loads(files[Path("plugins/example-org-aegis/.claude-plugin/plugin.json")])
    assert manifest["name"] == "example-org-aegis"
    assert manifest["author"] == {"name": "Example Org"}
    assert manifest["repository"] == manifest["homepage"] == "https://github.com/example-org/aegis-edition"
    marketplace = json.loads(files[Path(".claude-plugin/marketplace.json")])
    assert marketplace["owner"] == {"name": "Example Org"}
    assert marketplace["plugins"][0]["source"] == "./plugins/example-org-aegis"
    readme = files[Path("plugins/example-org-aegis/README.md")].decode()
    assert "/plugin marketplace add example-org/aegis-edition" in readme
    assert "/plugin install example-org-aegis@example-org-aegis" in readme
    assert "/example-org-aegis:start-ideation" in readme
    skill = files[Path("plugins/example-org-aegis/skills/start-ideation/SKILL.md")].decode()
    assert "`example-org-aegis:artifact-manager`" in skill
    assert not any(path.parts[:2] == ("plugins", "aegis") for path in files)

    # Writing replaces the default plugin folder with the renamed one.
    assert sync.main(["--root", str(tmp_path)]) == 0
    assert not (tmp_path / "plugins/aegis").exists()
    assert (tmp_path / "plugins/example-org-aegis/.claude-plugin/plugin.json").is_file()
    assert sync.main(["--check", "--root", str(tmp_path)]) == 0


def test_marketplace_source_outside_github(tmp_path: Path):
    config = load_config(_config(tmp_path, "plugin: {repo_url: 'https://git.example.com/org/aegis.git'}\n"))
    assert sync.marketplace_source(config) == "https://git.example.com/org/aegis.git"
    assert sync.marketplace_source(DEFAULT_CONFIG) == "nishant-tamilselvan/AEGIS"


# --------------------------------------------------------------------------- standards server


def test_standards_server_name_comes_from_config(tmp_path: Path):
    _copy_generator_inputs(tmp_path)
    _config(tmp_path, "standards: {server: example-standards}\n")
    files = _planned(tmp_path)
    copilot = files[Path(".github/agents/critic-reviewer.agent.md")].decode()
    assert "'example-standards/*'" in copilot
    claude = files[Path(".claude/agents/critic-reviewer.md")].decode()
    assert "tools: Read, Grep, Glob, Bash, mcp__example-standards\n" in claude
    for rel, data in files.items():
        if rel.suffix == ".md":
            text = data.decode()
            # Only paths such as examples/enterprise-standards-server keep the old name.
            assert "enterprise-standards-server" not in text.replace("/enterprise-standards-server", ""), rel
    assert "`example-standards` MCP" in files[Path(".github/copilot-instructions.md")].decode()


# --------------------------------------------------------------------------- overlays


def _overlay_repo(root: Path, overrides: str = "[]") -> Path:
    _copy_generator_inputs(root)
    overlay = root / "overlay"
    _write(overlay / "agents/example-reviewer.md", AGENT)
    _write(overlay / "prompts/example-review.md", PROMPT)
    _write(overlay / "skills/example-conventions/SKILL.md", SKILL)
    _write(overlay / "skills/example-conventions/references/names.md", "# Names\n")
    _write(overlay / "instructions.md", "## Example-org rules\n\n1. Cite example-org standards.\n")
    _config(root, f"overlay:\n  path: overlay\n  overrides: {overrides}\n")
    return overlay


def test_overlay_adds_agents_prompts_skills_and_rules(tmp_path: Path):
    _overlay_repo(tmp_path)
    files = _planned(tmp_path)
    agent = files[Path(".claude/agents/example-reviewer.md")].decode()
    assert "# Generated from overlay/agents/example-reviewer.md" in agent
    assert "mcp__enterprise-standards-server" in agent
    assert Path(".github/agents/example-reviewer.agent.md") in files
    assert Path("plugins/aegis/agents/example-reviewer.md") in files
    assert Path(".github/prompts/example-review.prompt.md") in files
    assert "`example-reviewer` subagent" in files[Path(".claude/skills/example-review/SKILL.md")].decode()
    for target in (".github/skills", ".claude/skills", "plugins/aegis/skills"):
        assert Path(target, "example-conventions/SKILL.md") in files
        assert Path(target, "example-conventions/references/names.md") in files
    rules = files[Path("plugins/aegis/instructions.md")].decode()
    assert rules.startswith((REPO_ROOT / "aegis/instructions.md").read_text(encoding="utf-8").rstrip("\n"))
    assert rules.endswith("\n\n## Example-org rules\n\n1. Cite example-org standards.\n")
    # Core sources are all still generated.
    assert Path(".claude/agents/critic-reviewer.md") in files

    assert sync.main(["--root", str(tmp_path)]) == 0
    assert sync.main(["--check", "--root", str(tmp_path)]) == 0


def test_overlay_file_that_shadows_core_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    overlay = _overlay_repo(tmp_path)
    core = (REPO_ROOT / "aegis/agents/critic-reviewer.md").read_text(encoding="utf-8")
    _write(overlay / "agents/critic-reviewer.md", core + "\nExample-org addition.\n")
    with pytest.raises(ValueError, match="overlay/agents/critic-reviewer.md shadows aegis/agents/critic-reviewer.md"):
        _planned(tmp_path)
    assert sync.main(["--check", "--root", str(tmp_path)]) == 2
    assert "overlay.overrides" in capsys.readouterr().err


def test_overlay_skill_file_that_shadows_core_is_an_error(tmp_path: Path):
    overlay = _overlay_repo(tmp_path)
    _write(overlay / "skills/enterprise-standards/SKILL.md", SKILL)
    with pytest.raises(ValueError, match="shadows aegis/skills/enterprise-standards/SKILL.md"):
        _planned(tmp_path)


def test_listed_override_replaces_the_core_file(tmp_path: Path):
    overlay = _overlay_repo(tmp_path, overrides="[agents/critic-reviewer.md]")
    core = (REPO_ROOT / "aegis/agents/critic-reviewer.md").read_text(encoding="utf-8")
    _write(overlay / "agents/critic-reviewer.md", core + "\nExample-org addition.\n")
    files = _planned(tmp_path)
    agent = files[Path(".claude/agents/critic-reviewer.md")].decode()
    assert "# Generated from overlay/agents/critic-reviewer.md" in agent
    assert agent.endswith("Example-org addition.\n")


def test_override_that_replaces_nothing_is_an_error(tmp_path: Path):
    _overlay_repo(tmp_path, overrides="[agents/critic-reviewer.md]")
    with pytest.raises(ValueError, match="agents/critic-reviewer.md, but no overlay file replaces"):
        _planned(tmp_path)


def test_overlay_prompt_cannot_collide_with_a_skill(tmp_path: Path):
    overlay = _overlay_repo(tmp_path)
    _write(overlay / "skills/example-review/SKILL.md", SKILL.replace("example-conventions", "example-review"))
    with pytest.raises(ValueError, match="collides with a prompt"):
        _planned(tmp_path)


def test_overlay_handoff_to_unknown_agent_is_an_error(tmp_path: Path):
    overlay = _overlay_repo(tmp_path)
    _write(overlay / "agents/example-lead.md", """\
---
name: example-lead
title: "Example Lead"
role: orchestrator
description: "Use to lead the example-org review."
tools: [read, agent]
handoffs:
  - label: Review
    agent: missing-agent
    prompt: Review it.
---
Lead the review.
""")
    with pytest.raises(ValueError, match="handoff to unknown agent 'missing-agent'"):
        _planned(tmp_path)


def test_sync_reports_a_missing_config_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert sync.main(["--check", "--config", str(tmp_path / "missing.yaml")]) == 2
    assert "does not exist" in capsys.readouterr().err


# --------------------------------------------------------------------------- artifact types


@pytest.fixture
def registry():
    """Restore the CLI's artifact registry after a test registers types."""
    saved = (
        dict(constants.ARTIFACT_TYPES), dict(constants.TYPE_ALIASES), dict(constants.ARTIFACT_TEMPLATES),
        set(constants.OPTIONAL_ARTIFACT_TYPES), constants.ALL_PREFIXES,
    )
    yield
    for current, original in zip(
        (constants.ARTIFACT_TYPES, constants.TYPE_ALIASES, constants.ARTIFACT_TEMPLATES), saved[:3], strict=True
    ):
        current.clear()
        current.update(original)
    constants.OPTIONAL_ARTIFACT_TYPES.clear()
    constants.OPTIONAL_ARTIFACT_TYPES.update(saved[3])
    constants.ALL_PREFIXES = saved[4]


def _type_config(root: Path, *, required: bool = True, prefix: str = "PIA", aliases: str = "[pia]") -> Path:
    _write(root / "templates/privacy-assessment.template.md", TEMPLATE)
    return _config(root, f"""\
artifact_types:
  privacy-assessment:
    prefix: {prefix}
    title: Privacy Assessment
    template: templates/privacy-assessment.template.md
    aliases: {aliases}
    required: {str(required).lower()}
""")


def test_configured_artifact_type_scaffolds_and_validates(tmp_path: Path, registry):
    register_artifact_types(load_config(_type_config(tmp_path)).artifact_types)
    assert constants.resolve_type("pia") == "privacy-assessment"
    app = tmp_path / "docs/artifacts/example-app"
    path = scaffold("pia", app, project="Example App")
    assert path.name == "privacy-assessment.md"
    assert "# Privacy Assessment: Example App" in path.read_text(encoding="utf-8")
    assert DEFINED_ID_RE.findall(path.read_text(encoding="utf-8")) == ["PIA-001"]
    assert [i for i in validate_dir(app) if i.severity == "error"] == []

    # A PIA id that no artifact defines is reported like any other dangling reference.
    path.write_text(path.read_text(encoding="utf-8") + "\nSee PIA-009.\n", encoding="utf-8", newline="\n")
    assert any("PIA-009" in i.message for i in validate_dir(app))


def test_registering_the_same_type_twice_is_a_no_op(tmp_path: Path, registry):
    types = load_config(_type_config(tmp_path)).artifact_types
    register_artifact_types(types)
    register_artifact_types(types)
    assert constants.ALL_PREFIXES.count("PIA") == 1


@pytest.mark.parametrize(
    ("prefix", "aliases", "message"),
    [("FR", "[]", "id prefix FR"), ("ADR", "[]", "id prefix ADR"), ("PIA", "[prd]", "alias 'prd'")],
)
def test_configured_type_cannot_clash_with_built_ins(tmp_path: Path, registry, prefix, aliases, message):
    types = load_config(_type_config(tmp_path, prefix=prefix, aliases=aliases)).artifact_types
    with pytest.raises(ConfigError, match=message):
        register_artifact_types(types)


def test_configured_type_cannot_reuse_a_built_in_name_or_file(tmp_path: Path, registry):
    _write(tmp_path / "t.md", TEMPLATE)
    for text, message in (
        ("data-architecture: {prefix: XA, title: X, template: t.md}", "type name"),
        ("data: {prefix: XA, title: X, template: t.md}", "type name"),
        ("data-copy: {prefix: XA, title: X, template: t.md, filename: data-architecture.md}", "file name"),
    ):
        with pytest.raises(ConfigError, match=message):
            register_artifact_types(load_config(_config(tmp_path, f"artifact_types:\n  {text}\n")).artifact_types)


@pytest.mark.parametrize("required", [True, False])
def test_readiness_requires_configured_types_unless_optional(tmp_path: Path, registry, required: bool):
    register_artifact_types(load_config(_type_config(tmp_path, required=required)).artifact_types)
    app = tmp_path / "docs/artifacts/example-app"
    app.mkdir(parents=True)
    report = check_readiness(app, target_workspace=tmp_path, standards_review="verified")
    missing = [f for f in report.findings if f.code == "artifact-missing" and "privacy-assessment" in f.message]
    assert bool(missing) is required


def test_cli_reads_the_config_from_the_environment(tmp_path: Path, registry, monkeypatch, capsys):
    monkeypatch.setenv(CONFIG_ENV, str(_type_config(tmp_path)))
    app = tmp_path / "docs/artifacts/example-app"
    assert cli_main(["scaffold", "privacy-assessment", str(app), "--project", "Example App"]) == 0
    assert (app / "privacy-assessment.md").is_file()


def test_cli_rejects_an_invalid_config(tmp_path: Path, registry, monkeypatch, capsys):
    monkeypatch.setenv(CONFIG_ENV, str(_config(tmp_path, "branding: {}\n")))
    assert cli_main(["validate", str(tmp_path)]) == 2
    assert "unknown key(s) branding" in capsys.readouterr().err
