"""Append a changelog entry to an artifact and bump its version."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from artifact_tools.frontmatter import render_document, split_document


def _bump_version(version: str, level: str) -> str:
    try:
        major_s, minor_s = str(version).split(".", 1)
        major, minor = int(major_s), int(minor_s)
    except (ValueError, AttributeError):
        return "0.1"
    if level == "major":
        return f"{major + 1}.0"
    return f"{major}.{minor + 1}"


def _insert_changelog_line(body: str, line: str) -> str:
    marker = "## Changelog"
    idx = body.find(marker)
    if idx == -1:
        return body.rstrip("\n") + f"\n\n## Changelog\n\n{line}\n"

    # Find the end of the "## Changelog" header line, then insert after any
    # HTML comment placeholder that immediately follows.
    lines = body.splitlines()
    out: list[str] = []
    inserted = False
    for i, current in enumerate(lines):
        out.append(current)
        if not inserted and current.strip() == marker:
            # Skip past blank lines and a comment placeholder to keep it tidy.
            j = i + 1
            while j < len(lines) and (
                lines[j].strip() == "" or lines[j].strip().startswith("<!--")
            ):
                out.append(lines[j])
                j += 1
            out.append(line)
            # Append the remaining lines and stop the loop cleanly.
            out.extend(lines[j:])
            inserted = True
            break
    if not inserted:
        out.append(line)
    return "\n".join(out) + ("\n" if body.endswith("\n") else "")


def add_changelog(
    file_path: str | Path,
    summary: str,
    *,
    level: str = "minor",
    phase: int | None = None,
) -> str:
    """Append a changelog entry, bump the version and refresh last_updated.

    Returns the new version string.
    """
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_document(text)
    if frontmatter is None:
        raise ValueError(f"{path} has no frontmatter to update")

    new_version = _bump_version(frontmatter.get("version", "0.0"), level)
    today = date.today().isoformat()
    frontmatter["version"] = new_version
    frontmatter["last_updated"] = today
    if phase is not None:
        frontmatter["phase"] = phase

    entry = f"- {today} — v{new_version} — {summary}"
    body = _insert_changelog_line(body, entry)

    path.write_text(render_document(frontmatter, body), encoding="utf-8")
    return new_version
