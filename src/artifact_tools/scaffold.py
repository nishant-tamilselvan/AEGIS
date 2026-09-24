"""Scaffold an artifact document from its template."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from artifact_tools.constants import ARTIFACT_TYPES, resolve_type
from artifact_tools.frontmatter import find_templates_dir


def _fill_placeholders(text: str, project: str, title: str, today: str) -> str:
    replacements = {
        "{{PROJECT_NAME}}": project,
        "{{TITLE}}": title,
        "{{DATE}}": today,
        "{{PRIMARY_JOURNEY}}": f"{project} — primary journey",
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


def scaffold(
    type_name: str,
    out_dir: str | Path,
    *,
    project: str = "Untitled Project",
    title: str | None = None,
    force: bool = False,
    templates_dir: Path | None = None,
) -> Path:
    """Create a new artifact document from its template.

    Returns the path of the created file. Raises FileExistsError if the target
    already exists and `force` is False.
    """
    type_key = resolve_type(type_name)
    meta = ARTIFACT_TYPES[type_key]

    templates = templates_dir or find_templates_dir()
    template_path = templates / f"{type_key}.template.md"
    if not template_path.is_file():
        raise FileNotFoundError(f"Template not found: {template_path}")

    out_path = Path(out_dir) / meta["filename"]
    if out_path.exists() and not force:
        raise FileExistsError(
            f"{out_path} already exists. Use force=True to overwrite."
        )

    doc_title = title or f"{meta['title']} — {project}"
    today = date.today().isoformat()
    content = _fill_placeholders(
        template_path.read_text(encoding="utf-8"),
        project=project,
        title=doc_title,
        today=today,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    # The interface index is a router; create the native-format contract store beside it.
    if type_key == "interface-specifications":
        from artifact_tools.interfaces import init_interfaces_dir

        init_interfaces_dir(out_path.parent)

    return out_path
