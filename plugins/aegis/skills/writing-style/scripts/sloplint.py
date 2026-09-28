#!/usr/bin/env python3
"""Check prose against references/banned.json.

Usage:
    sloplint.py FILE [FILE...]        report errors and warnings
    sloplint.py --errors-only FILE    suppress warnings
    sloplint.py --quiet FILE          summary counts only

Exit code 1 when any error-severity rule fires. Warnings never fail the run:
they are context-dependent and a human decides.

Excluded from checking: fenced code blocks, inline code spans, URLs, YAML
frontmatter, and any region between <!-- sloplint-disable --> and
<!-- sloplint-enable -->. Use the disable markers around text that quotes
forbidden writing on purpose.

This script is the only checker: references/banned.json is the single source of
truth for the patterns and this file is the single source of truth for measuring
them.
"""
import json
import re
import statistics
import sys
from pathlib import Path

RULES = json.loads(
    (Path(__file__).resolve().parent.parent / "references" / "banned.json").read_text(encoding="utf-8")
)
LIMITS = RULES["limits"]


def mask(text):
    """Blank out code, URLs, frontmatter and disabled regions, keeping offsets."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))

    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            text = blank(re.match(rf"(?s).{{{end + 4}}}", text)) + text[end + 4:]
    text = re.sub(r"(?s)<!--\s*sloplint-disable\s*-->.*?<!--\s*sloplint-enable\s*-->", blank, text)
    text = re.sub(r"(?sm)^```.*?^```", blank, text)
    text = re.sub(r"`[^`\n]*`", blank, text)
    text = re.sub(r"https?://\S+", blank, text)
    return text


def word_regex(words):
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")\b", re.I)


COMPILED = {
    "words_error": ("error", [(word_regex(RULES["words_error"]), "banned-word")]),
    "words_warn": ("warn", [(word_regex(RULES["words_warn"]), "watch-word")]),
    "phrases_error": ("error", [(re.compile(r["pattern"], re.I), r["label"]) for r in RULES["phrases_error"]]),
    "phrases_warn": ("warn", [(re.compile(r["pattern"], re.I), r["label"]) for r in RULES["phrases_warn"]]),
    "openers_error": ("error", [(re.compile(r["pattern"], re.I), r["label"]) for r in RULES["openers_error"]]),
    "structures_error": ("error", [(re.compile(r["pattern"], re.I), r["label"]) for r in RULES["structures_error"]]),
    "structures_warn": ("warn", [(re.compile(r["pattern"], re.I), r["label"]) for r in RULES["structures_warn"]]),
}

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Personification labels outside the person-* family. The density limit covers
# every construction that gives an abstraction a will of its own.
PERSONIFICATION = {"abstraction-answers-to", "process-as-actor"}


def sentences(text):
    plain = re.sub(r"(?m)^\s*[-*+|#>].*$", "", text)
    plain = re.sub(r"\s+", " ", plain).strip()
    return [s for s in SENTENCE_SPLIT.split(plain) if len(s.split()) > 2]


def logical_lines(lines):
    """Pair each line with the sentence it belongs to, keeping its line number.

    Several rules anchor to the end of a sentence. Running them against raw lines
    makes a hard wrap look like a sentence ending, so "which live in" plus a path
    on the next line reads as a stranded preposition. Joining a soft-wrapped
    continuation onto the line that starts it removes that whole false-positive
    class and lets the same rules see sentences that span a wrap.
    """

    def starts_block(line):
        stripped = line.strip()
        return (
            not stripped
            or bool(re.match(r"^\s*([-*+•>|]|\d+[.)]|#{1,6}\s|```)", line))
            or stripped.startswith("<!--")
        )

    out = []
    lineno, buffer = None, []
    for index, line in enumerate(lines, 1):
        if buffer and starts_block(line):
            out.append((lineno, " ".join(buffer)))
            lineno, buffer = None, []
        if starts_block(line):
            out.append((index, line))
            continue
        if lineno is None:
            lineno = index
        buffer.append(line.strip())
        if re.search(r"[.!?][)\]\"’]?\s*$", line):
            out.append((lineno, " ".join(buffer)))
            lineno, buffer = None, []
    if buffer:
        out.append((lineno, " ".join(buffer)))
    return out


def check(path):
    raw = Path(path).read_text(encoding="utf-8")
    text = mask(raw)
    lines = text.split("\n")
    hits = []
    seen = set()

    for group, (severity, patterns) in COMPILED.items():
        for lineno, line in logical_lines(lines):
            is_heading = bool(re.match(r"^#{1,6}\s", line))
            if is_heading and group == "openers_error":
                continue  # sycophant-opener patterns target reply openers, not headings
            variants = [line]
            heading = re.match(r"^#{1,6}\s*(.*)$", line)
            if heading:
                variants.append(heading.group(1))
            for variant in variants:
                for rx, label in patterns:
                    for m in rx.finditer(variant):
                        key = (lineno, label, m.group(0).lower().strip())
                        if key in seen:
                            continue
                        seen.add(key)
                        hits.append((lineno, severity, label, m.group(0).strip()))

    # A range en dash is correct typography, not prose punctuation: "1–3 developers",
    # "Low–medium", "pages 4–7". Counting those against the em-dash limit flagged
    # correctly written tables, and a rule that flags correct writing does more harm
    # than the slop it catches. Only dashes that separate words or clauses count.
    RANGE_EN_DASH = re.compile(
        r"(?<=[\w)])–(?=[\w(])"          # no spaces around it: 1–3, Low–medium
        r"|(?<=\d)\s*–\s*(?=\d)"          # numeric range, spaced or not
    )
    prose_dashes = RANGE_EN_DASH.sub("", text)
    em = len(re.findall(r"[—–]", prose_dashes))
    if em > LIMITS["em_dash_max"]:
        hits.append((0, "error", "em-dash-limit", f"{em} found, limit {LIMITS['em_dash_max']}"))

    sents = sentences(text)
    for s in sents:
        n = len(s.split())
        if n >= LIMITS["sentence_words_error"]:
            hits.append((0, "error", "sentence-too-long", f"{n} words: {s[:60]}..."))
        elif n >= LIMITS["sentence_words_warn"]:
            hits.append((0, "warn", "sentence-long", f"{n} words: {s[:60]}..."))

    if len(sents) >= LIMITS["cadence_min_sentences"]:
        counts = [len(s.split()) for s in sents]
        cv = statistics.pstdev(counts) / statistics.mean(counts)
        if cv < LIMITS["cadence_cv_floor"]:
            hits.append((0, "warn", "flat-cadence", f"CV {cv:.2f}, floor {LIMITS['cadence_cv_floor']}"))

    words = len(text.split()) or 1
    persons = sum(1 for h in hits if h[2] in PERSONIFICATION or h[2].startswith("person-"))
    rate = persons * 1000 / words
    if rate > LIMITS["personification_per_1k"]:
        hits.append((0, "warn", "personification-density", f"{rate:.1f} per 1k, limit {LIMITS['personification_per_1k']}"))

    return sorted(hits, key=lambda h: (h[0], h[1]))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print(__doc__)
        return 2
    unknown = flags - {"--errors-only", "--quiet"}
    if unknown:
        print(f"unknown flag(s): {' '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    missing = [p for p in args if not Path(p).is_file()]
    if missing:
        for p in missing:
            print(f"{p}: no such file", file=sys.stderr)
        return 2
    total = {"error": 0, "warn": 0}
    for path in args:
        hits = check(path)
        if "--errors-only" in flags:
            hits = [h for h in hits if h[1] == "error"]
        for lineno, severity, label, match in hits:
            total[severity] += 1
            if "--quiet" not in flags:
                loc = f"{path}:{lineno}" if lineno else f"{path}"
                print(f"{loc}: {severity}: {label}: {match}")
    print(f"\n{total['error']} error(s), {total['warn']} warning(s)")
    return 1 if total["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
