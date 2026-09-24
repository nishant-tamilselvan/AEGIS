"""Frontmatter parsing/serialisation and repository path discovery."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)

# Matches an id token such as FR-014, RISK-002, SEC-003 or ADR-0004.
# The `(?<!STD-)` lookbehind prevents external Enterprise Standards citations
# (e.g. ENT-STD-SEC-001, ENT-STD-OBS-002) from being misread as internal artifact
# ids like SEC-001 or OBS-002.
ID_TOKEN_RE = re.compile(
    r"(?<!STD-)\b(PR|FR|NFR|UJ|BP|RISK|IF|DM|SEC|DEP|OBS|ADR)-(\d{3,})\b"
)

# Matches an id that starts a Markdown table row cell: "| FR-001 | ..."
# ADR ids are defined in the ADR index (a subfolder) and validated separately, so
# they are intentionally excluded here to keep them out of the top-level id scan.
DEFINED_ID_RE = re.compile(
    r"^\|\s*((?:PR|FR|NFR|UJ|BP|RISK|IF|DM|SEC|DEP|OBS)-\d{3,})\s*\|", re.MULTILINE
)


class FrontmatterError(ValueError):
    """Raised when a document's frontmatter cannot be parsed."""


def split_document(text: str) -> tuple[dict | None, str]:
    """Split a document into (frontmatter_dict, body).

    Returns (None, text) when no frontmatter block is present.
    Raises FrontmatterError when the block exists but is not valid YAML mapping.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    raw, body = match.group(1), match.group(2)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # pragma: no cover - passthrough detail
        raise FrontmatterError(f"invalid YAML frontmatter: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise FrontmatterError("frontmatter must be a YAML mapping")
    return data, body


def render_document(frontmatter: dict, body: str) -> str:
    """Serialise a frontmatter mapping and body back into a document string."""
    dumped = yaml.safe_dump(
        frontmatter, sort_keys=False, default_flow_style=False, allow_unicode=True
    ).rstrip("\n")
    return f"---\n{dumped}\n---\n{body}"


def packaged_templates_dir(kind: str) -> Path | None:
    """Templates bundled in an installed wheel (``artifact`` or ``implementation``)."""
    from importlib.resources import files

    try:
        target = Path(str(files("artifact_tools") / "templates" / kind))
    except (ModuleNotFoundError, TypeError):
        return None
    return target if target.is_dir() else None


def find_templates_dir(start: Path | None = None) -> Path:
    """Locate the artifact templates directory.

    A repository's own ``aegis/skills`` templates win, found by walking up from `start`,
    so customized templates are used. Otherwise the copies bundled with an installed
    package are used.
    """
    rel = Path("aegis/skills/artifact-management/assets/templates")
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        target = candidate / rel
        if target.is_dir():
            return target
    packaged = packaged_templates_dir("artifact")
    if packaged is not None:
        return packaged
    raise FileNotFoundError(
        f"Could not locate templates directory ({rel}) from {current}."
    )
