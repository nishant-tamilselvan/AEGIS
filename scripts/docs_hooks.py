"""MkDocs hook for the AEGIS documentation site.

The site is built from ``docs/``, but the pages also link to files elsewhere in the
repository (CONTRIBUTING.md, aegis/skills/..., examples/...). Those files are not part of
the site, so this hook rewrites such links to their GitHub pages. Links inside ``docs/``
and links inside code are left alone, so ``mkdocs build --strict`` still catches broken
internal links.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

REPO_URL = "https://github.com/nishant-tamilselvan/AEGIS"
BRANCH = "main"

_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)\)")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")


def _outside_docs(page_src: str, target: str) -> str | None:
    """Repository path of `target` if it points outside docs/, else None."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith(("#", "/")):
        return None
    path_part, _, anchor = target.partition("#")
    parts: list[str] = ["docs", *PurePosixPath(page_src).parent.parts]
    for piece in PurePosixPath(path_part).parts:
        if piece == "..":
            if not parts:
                return None
            parts.pop()
        elif piece != ".":
            parts.append(piece)
    if parts[:1] == ["docs"]:
        return None
    kind = "tree" if path_part.endswith("/") else "blob"
    url = f"{REPO_URL}/{kind}/{BRANCH}/{'/'.join(parts)}"
    return f"{url}#{anchor}" if anchor else url


def _rewrite_line(line: str, page_src: str) -> str:
    """Rewrite links on one line, leaving inline code untouched."""
    codes: list[str] = []

    def stash(match: re.Match[str]) -> str:
        codes.append(match.group(0))
        return f"\0{len(codes) - 1}\0"

    def replace(match: re.Match[str]) -> str:
        url = _outside_docs(page_src, match.group(2))
        return f"[{match.group(1)}]({url})" if url else match.group(0)

    def restore(match: re.Match[str]) -> str:
        return codes[int(match.group(1))]

    protected = _INLINE_CODE_RE.sub(stash, line)
    return re.sub(r"\0(\d+)\0", restore, _LINK_RE.sub(replace, protected))


def rewrite_links(markdown: str, page_src: str) -> str:
    out: list[str] = []
    in_fence = False
    for line in markdown.split("\n"):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
        elif in_fence:
            out.append(line)
        else:
            out.append(_rewrite_line(line, page_src))
    return "\n".join(out)


def on_page_markdown(markdown, page, config, files):  # MkDocs hook signature
    return rewrite_links(markdown, page.file.src_uri)
