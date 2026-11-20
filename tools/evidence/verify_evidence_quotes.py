"""Verify that quoted evidence lines really occur verbatim in the cited logs.

Usage::

    python tools/evidence/verify_evidence_quotes.py EVIDENCE.md LOG [LOG ...]

A fenced block is treated as a quote when its preceding non-blank line carries a quote marker.
The convention observed in ``docs/evidence/`` is a line ending in ``verbatim``/``verbatim:``
(e.g. ``Final run, verbatim:``); the task's explicit markers ``quote:`` and ``[measured]`` are
accepted too.  Every non-blank line inside such a block must appear verbatim in at least one log.

Logs are decoded as UTF-16 when they start with a UTF-16 BOM (PowerShell ``Tee-Object`` writes
that), else as UTF-8.  Exit code 1 means at least one quoted line was not found.

Standard library only; no shell, no network.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

#: Markers on the line before a fence that make its contents a quote block.
QUOTE_MARKER = re.compile(r"(quote:|\[measured\]|verbatim)", re.IGNORECASE)

_FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")


@dataclass(frozen=True)
class QuoteLine:
    """One quoted line and its 1-based line number in the evidence markdown."""

    line_no: int
    text: str


@dataclass(frozen=True)
class Miss:
    """A quoted line that is absent from every supplied log."""

    line_no: int
    text: str

    def format(self, evidence: str) -> str:
        return f"MISS {evidence}:{self.line_no}: {self.text}"


def _fence_open(line: str) -> tuple[str, int] | None:
    match = _FENCE.match(line)
    if match is None:
        return None
    fence = match.group(2)
    return fence[0], len(fence)


def quote_lines(markdown: str) -> list[QuoteLine]:
    """Every non-blank line inside a fenced block tagged as a quote."""
    lines = markdown.splitlines()
    out: list[QuoteLine] = []
    previous = ""
    index = 0
    while index < len(lines):
        opener = _fence_open(lines[index])
        if opener is None:
            if lines[index].strip():
                previous = lines[index]
            index += 1
            continue

        char, width = opener
        end = index + 1
        while end < len(lines):
            closer = _fence_open(lines[end])
            if closer is not None and closer[0] == char and closer[1] >= width:
                break
            end += 1

        if QUOTE_MARKER.search(previous):
            for offset in range(index + 1, end):
                text = lines[offset]
                if text.strip():                       # blank lines are trivially "found"
                    out.append(QuoteLine(offset + 1, text))

        # The closing fence (or the last line read when unterminated) is the next "preceding line".
        previous = lines[end] if end < len(lines) and lines[end].strip() else previous
        index = end + 1
    return out


def decode_log(data: bytes) -> str:
    """Decode a log as UTF-16 when it has a UTF-16 BOM, else UTF-8."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    return data.decode("utf-8", errors="replace")


def verify(evidence_path: str | Path, log_paths: Sequence[str | Path]) -> tuple[int, list[Miss]]:
    """Return ``(number_of_quoted_lines, misses)`` for one evidence file and its logs."""
    markdown = Path(evidence_path).read_text(encoding="utf-8", errors="replace")
    log_lines: set[str] = set()
    for log_path in log_paths:
        log_lines.update(decode_log(Path(log_path).read_bytes()).splitlines())
    quotes = quote_lines(markdown)
    misses = [Miss(q.line_no, q.text) for q in quotes if q.text not in log_lines]
    return len(quotes), misses


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report quoted evidence lines that are absent verbatim from the cited logs.")
    parser.add_argument("evidence", help="evidence markdown file")
    parser.add_argument("logs", nargs="+", help="one or more log files cited by the evidence")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        total, misses = verify(args.evidence, args.logs)
    except OSError as exc:
        print(f"verify_evidence_quotes: {exc}", file=sys.stderr)
        return 2

    for miss in misses:
        print(miss.format(args.evidence))
    if misses:
        print(f"{len(misses)} of {total} quoted line(s) not found verbatim in "
              f"{len(args.logs)} log file(s)", file=sys.stderr)
        return 1
    print(f"OK: {total} quoted line(s) found verbatim in {len(args.logs)} log file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
