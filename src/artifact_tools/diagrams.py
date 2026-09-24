"""Render Mermaid diagrams embedded in artifact markdown to image files.

Scans the ``.md`` files in an application's artifact directory for fenced
``mermaid`` code blocks and renders each one to an image (PNG by default).

Two engines are supported:

* ``mmdc`` (default) — the official ``@mermaid-js/mermaid-cli``. Highest
  fidelity (real Mermaid + headless Chromium); requires Node.js / mermaid-cli
  available on PATH, via a local ``node_modules`` install, or via ``npx``.
* ``mermaidx`` — a pure-Python fallback (no Node/browser), imported lazily.
  Install with ``pip install mermaidx``.

Output images are written to ``<app-dir>/assets/diagrams/`` and named
``<markdown-stem>-<NN>.<ext>`` (e.g. ``system-blueprint-01.png``). A
``manifest.json`` recording every diagram (source file, index, image, detected
title) is written alongside the images for downstream tooling.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

_MERMAID_BLOCK = re.compile(r"```mermaid[ \t]*\r?\n(.*?)\r?\n```", re.DOTALL)
_TITLE = re.compile(r"^\s*title\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class DiagramResult:
    """Outcome of rendering a single Mermaid block."""

    source_file: str
    index: int
    image: str | None
    title: str | None
    ok: bool
    error: str | None = None


def extract_mermaid_blocks(markdown: str) -> list[str]:
    """Return the source of every fenced ``mermaid`` block, in document order."""
    return [m.group(1).strip() for m in _MERMAID_BLOCK.finditer(markdown)]


def _detect_title(source: str) -> str | None:
    match = _TITLE.search(source)
    return match.group(1).strip() if match else None


def render_file(
    md_path: Path,
    out_dir: Path,
    *,
    fmt: str = "png",
    scale: float = 2.0,
    theme: str = "default",
    background: str = "white",
) -> list[DiagramResult]:
    """Render every Mermaid block in ``md_path`` with the pure-Python mermaidx engine."""
    text = md_path.read_text(encoding="utf-8")
    blocks = extract_mermaid_blocks(text)
    if not blocks:
        return []

    import mermaidx  # lazy, optional dependency

    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[DiagramResult] = []
    for index, source in enumerate(blocks, start=1):
        name = f"{md_path.stem}-{index:02d}.{fmt}"
        title = _detect_title(source)
        try:
            diagram = mermaidx.render(source, theme=theme)
            if fmt == "svg":
                (out_dir / name).write_text(diagram.svg(), encoding="utf-8")
            else:
                (out_dir / name).write_bytes(
                    diagram.png(scale=scale, background=background)
                )
            results.append(DiagramResult(md_path.name, index, name, title, True))
        except Exception as exc:  # noqa: BLE001
            results.append(
                DiagramResult(md_path.name, index, None, title, False, str(exc))
            )
    return results


def _find_mmdc() -> list[str]:
    """Return the command prefix used to invoke mermaid-cli (``mmdc``).

    Prefers ``mmdc`` on PATH, then a local ``node_modules`` install, then
    ``npx``. Raises :class:`FileNotFoundError` if none is available.
    """
    exe = shutil.which("mmdc")
    if exe:
        return [exe]
    node = shutil.which("node")
    local_cli = Path("node_modules/@mermaid-js/mermaid-cli/src/cli.js")
    if node and local_cli.is_file():
        return [node, str(local_cli)]
    npx = shutil.which("npx")
    if npx:
        return [npx, "-y", "@mermaid-js/mermaid-cli"]
    raise FileNotFoundError(
        "mermaid-cli (mmdc) not found. Install it (npm install -g "
        "@mermaid-js/mermaid-cli) or use --engine mermaidx."
    )


def render_file_mmdc(
    md_path: Path,
    out_dir: Path,
    *,
    fmt: str = "png",
    scale: float = 2.0,
    background: str = "white",
    puppeteer_config: Path | None = None,
) -> list[DiagramResult]:
    """Render every Mermaid block in ``md_path`` using the official mermaid-cli.

    Uses mermaid-cli's markdown mode (one browser launch per file), then copies
    the produced images to ``<stem>-<NN>.<ext>`` so naming matches the mermaidx
    engine. Raises :class:`FileNotFoundError` if ``mmdc`` is unavailable.
    """
    blocks = extract_mermaid_blocks(md_path.read_text(encoding="utf-8"))
    if not blocks:
        return []

    cmd = _find_mmdc()
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[DiagramResult] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        out_md = tmp / f"{md_path.stem}.md"
        args = [
            *cmd,
            "-i", str(md_path),
            "-o", str(out_md),
            "-e", fmt,
            "-b", background,
            "-s", str(scale),
        ]
        if puppeteer_config is not None:
            args += ["-p", str(puppeteer_config)]
        proc = subprocess.run(args, capture_output=True, text=True)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "mmdc failed").strip()
            return [
                DiagramResult(md_path.name, i, None, _detect_title(b), False, err)
                for i, b in enumerate(blocks, start=1)
            ]
        for index, source in enumerate(blocks, start=1):
            produced = tmp / f"{md_path.stem}-{index}.{fmt}"
            name = f"{md_path.stem}-{index:02d}.{fmt}"
            title = _detect_title(source)
            if produced.is_file():
                shutil.copyfile(produced, out_dir / name)
                results.append(DiagramResult(md_path.name, index, name, title, True))
            else:
                results.append(
                    DiagramResult(
                        md_path.name, index, None, title, False,
                        "mmdc produced no image for this block",
                    )
                )
    return results


def render_dir(
    directory: str | Path,
    *,
    engine: str = "mmdc",
    out_subdir: str = "assets/diagrams",
    fmt: str = "png",
    scale: float = 2.0,
    theme: str = "default",
    background: str = "white",
    puppeteer_config: str | Path | None = None,
) -> list[DiagramResult]:
    """Render Mermaid diagrams in every ``.md`` file under ``directory``."""
    base = Path(directory)
    if not base.is_dir():
        raise FileNotFoundError(f"not a directory: {base}")
    out_dir = base / out_subdir
    pconf = Path(puppeteer_config) if puppeteer_config else None

    results: list[DiagramResult] = []
    for md_path in sorted(base.glob("*.md")):
        if engine == "mmdc":
            results.extend(
                render_file_mmdc(
                    md_path, out_dir, fmt=fmt, scale=scale,
                    background=background, puppeteer_config=pconf,
                )
            )
        else:
            results.extend(
                render_file(
                    md_path, out_dir, fmt=fmt, scale=scale,
                    theme=theme, background=background,
                )
            )

    if results:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "manifest.json").write_text(
            json.dumps([asdict(r) for r in results], indent=2) + "\n",
            encoding="utf-8",
        )
    return results
