#!/usr/bin/env python3
"""Repository hygiene checks for AEGIS. Standard library only.

Run one check or all of them::

    python scripts/ci/repo_checks.py all
    python scripts/ci/repo_checks.py personal-paths
    python scripts/ci/repo_checks.py denylist
    python scripts/ci/repo_checks.py unicode
    python scripts/ci/repo_checks.py workflows
    python scripts/ci/repo_checks.py links

Each check prints one line per finding as ``path:line: message`` and exits 1 when it
finds anything. CI and pre-commit both call this script.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

TEXT_SUFFIXES = {
    ".md", ".txt", ".py", ".json", ".toml", ".yml", ".yaml", ".cfg", ".ini",
    ".sh", ".ps1", ".graphql", ".proto", ".js", ".ts", ".html", ".css",
}
TEXT_NAMES = {"LICENSE", "CODEOWNERS", ".gitignore", ".gitattributes", ".editorconfig"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}

# The generated per-application artifacts are not version-controlled.
SKIP_PREFIXES = ("docs/artifacts/",)
KEEP_FILES = {"docs/artifacts/README.md"}

# The checker and its tests contain deliberate examples of what the checks reject.
SELF_EXEMPT = {"scripts/ci/repo_checks.py", "tests/test_repo_checks.py"}

DENYLIST_FILE = Path("scripts/ci/denylist.txt")
LOCAL_DENYLIST_FILE = Path(".denylist.local")

PLACEHOLDER_USERS = {
    "example", "me", "user", "username", "you", "yourname", "your-name", "yourusername",
    "your-username", "name", "runner", "runneradmin", "public", "default", "shared", "<name>",
}
PERSONAL_PATH_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]+Users[\\/]+|/Users/|/home/)(?P<user>[A-Za-z][A-Za-z0-9._-]*)",
    re.IGNORECASE,
)

# Characters that can hide instructions from a human reviewer of agent, skill and prompt
# files: bidirectional overrides, zero-width characters and Unicode tag characters.
SUSPICIOUS_CODEPOINTS = (
    set(range(0x202A, 0x202F))
    | set(range(0x2066, 0x206A))
    | {0x200B, 0x200C, 0x200D, 0x2060, 0x180E, 0xFEFF}
    | set(range(0xE0000, 0xE0080))
)

SHA_PINNED_RE = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
USES_RE = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^'\"\s#]+)")
UNTRUSTED_CONTEXT_RE = re.compile(
    r"\$\{\{\s*github\.(?:head_ref|event\.(?:issue|pull_request|comment|review|discussion|head_commit)\.[\w.]*"
    r"(?:title|body|ref|label|name|message|email))"
)
ENV_ASSIGNMENT_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*:\s*['\"]?\$\{\{")
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


# --------------------------------------------------------------------------- files


def repo_files(root: Path) -> list[Path]:
    """Tracked plus untracked-but-not-ignored files, or a filesystem walk outside git."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root, capture_output=True, check=True,
        )
        names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
        paths = [root / name for name in names]
    except (OSError, subprocess.CalledProcessError):
        paths = []
        for current, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            paths.extend(Path(current) / name for name in files)
    selected = []
    for path in paths:
        rel = _rel(path, root)
        if any(part in SKIP_DIRS for part in Path(rel).parts):
            continue
        if rel.startswith(SKIP_PREFIXES) and rel not in KEEP_FILES:
            continue
        if path.is_file():
            selected.append(path)
    return sorted(selected)


def text_files(root: Path) -> list[Path]:
    return [p for p in repo_files(root) if p.suffix.lower() in TEXT_SUFFIXES or p.name in TEXT_NAMES]


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _lines(path: Path) -> Iterable[tuple[int, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    return enumerate(text.splitlines(), start=1)


# --------------------------------------------------------------------------- checks


def check_personal_paths(root: Path) -> list[Finding]:
    """User-specific absolute paths such as C:\\Users\\<name> or /home/<name>."""
    findings = []
    for path in text_files(root):
        rel = _rel(path, root)
        if rel in SELF_EXEMPT:
            continue
        for number, line in _lines(path):
            for match in PERSONAL_PATH_RE.finditer(line):
                if match.group("user").rstrip("._-").lower() not in PLACEHOLDER_USERS:
                    findings.append(Finding(rel, number, f"personal path {match.group(0)!r}; use a placeholder"))
    return findings


def load_denylist(root: Path) -> list[tuple[re.Pattern[str], str]]:
    """Patterns from the committed denylist plus an optional local, gitignored one."""
    patterns = []
    for source in (root / DENYLIST_FILE, root / LOCAL_DENYLIST_FILE):
        if not source.is_file():
            continue
        for raw in source.read_text(encoding="utf-8").splitlines():
            entry = raw.strip()
            if not entry or entry.startswith("#"):
                continue
            patterns.append((re.compile(entry, re.IGNORECASE), entry))
    extra = os.environ.get("AEGIS_DENYLIST", "")
    for entry in filter(None, (item.strip() for item in extra.split(";"))):
        patterns.append((re.compile(entry, re.IGNORECASE), entry))
    return patterns


def check_denylist(root: Path) -> list[Finding]:
    """Organization-specific names, internal hosts and credentials that must not ship."""
    patterns = load_denylist(root)
    skip = {DENYLIST_FILE.as_posix(), LOCAL_DENYLIST_FILE.as_posix(), *SELF_EXEMPT}
    findings = []
    for path in text_files(root):
        rel = _rel(path, root)
        if rel in skip:
            continue
        for number, line in _lines(path):
            for pattern, entry in patterns:
                if pattern.search(line):
                    findings.append(Finding(rel, number, f"matches denylist pattern {entry!r}"))
    return findings


ALLOWED_CONTROL_BYTES = {9, 10, 13}  # tab, line feed, carriage return


def check_unicode(root: Path) -> list[Finding]:
    """Invisible or direction-changing characters that can hide prompt injection,
    and stray control bytes (such as NUL) that break or disguise text files."""
    findings = []
    for path in text_files(root):
        rel = _rel(path, root)
        data = path.read_bytes()
        for number, raw in enumerate(data.split(bytes([10])), start=1):
            stray = sorted({b for b in raw if b < 32 and b not in ALLOWED_CONTROL_BYTES})
            if stray:
                codes = ", ".join(f"0x{b:02X}" for b in stray)
                findings.append(Finding(rel, number, f"control byte(s) {codes}; use an escape sequence instead"))
        for number, line in _lines(path):
            for column, char in enumerate(line, start=1):
                code = ord(char)
                if code == 0xFEFF and number == 1 and column == 1:
                    findings.append(Finding(rel, number, "UTF-8 byte order mark; save without BOM"))
                elif code in SUSPICIOUS_CODEPOINTS:
                    name = unicodedata.name(char, "UNNAMED")
                    findings.append(Finding(rel, number, f"column {column}: invisible character U+{code:04X} {name}"))
    return findings


def check_workflows(root: Path) -> list[Finding]:
    """GitHub Actions hardening: SHA pins, least privilege, no credential persistence."""
    findings = []
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return findings
    for path in sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")]):
        rel = _rel(path, root)
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not re.search(r"^permissions:", text, re.MULTILINE):
            findings.append(Finding(rel, 1, "missing top-level 'permissions:' block"))
        if re.search(r"^\s*pull_request_target\s*:", text, re.MULTILINE):
            findings.append(Finding(rel, 1, "pull_request_target runs untrusted code with a write token; use pull_request"))
        for number, line in enumerate(lines, start=1):
            match = USES_RE.match(line)
            if not match:
                continue
            action = match.group(1)
            if action.startswith(("./", "docker://")):
                continue
            if not SHA_PINNED_RE.match(action):
                findings.append(Finding(rel, number, f"action {action!r} is not pinned to a full commit SHA"))
            if action.startswith("actions/checkout@"):
                step = "\n".join(lines[number - 1 : number + 6])
                if not re.search(r"persist-credentials:\s*false", step):
                    findings.append(Finding(rel, number, "actions/checkout must set 'persist-credentials: false'"))
        for number, line in enumerate(lines, start=1):
            if UNTRUSTED_CONTEXT_RE.search(line) and not ENV_ASSIGNMENT_RE.match(line):
                findings.append(Finding(rel, number, "untrusted event text used inline; pass it through an env variable"))
    return findings


def check_links(root: Path) -> list[Finding]:
    """Relative Markdown links must point at files that exist."""
    findings = []
    for path in repo_files(root):
        if path.suffix.lower() != ".md":
            continue
        rel = _rel(path, root)
        if "/assets/templates/" in rel:
            continue  # template links are relative to where the scaffolded file will live
        in_fence = False
        for number, line in _lines(path):
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            stripped = re.sub(r"`[^`]*`", "", line)
            for target in MD_LINK_RE.findall(stripped):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith("#"):
                    continue
                file_part = target.split("#", 1)[0]
                if not file_part or "{{" in file_part or "<" in file_part:
                    continue
                resolved = (path.parent / file_part).resolve()
                if not resolved.exists():
                    findings.append(Finding(rel, number, f"broken link {target!r}"))
    return findings


CHECKS: dict[str, Callable[[Path], list[Finding]]] = {
    "personal-paths": check_personal_paths,
    "denylist": check_denylist,
    "unicode": check_unicode,
    "workflows": check_workflows,
    "links": check_links,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("check", choices=[*CHECKS, "all"])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    names = list(CHECKS) if args.check == "all" else [args.check]
    failed = False
    for name in names:
        findings = CHECKS[name](args.root.resolve())
        for finding in findings:
            print(f"[{name}] {finding.format()}")
        status = "ok" if not findings else f"{len(findings)} finding(s)"
        print(f"{name}: {status}", file=sys.stderr)
        failed = failed or bool(findings)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
