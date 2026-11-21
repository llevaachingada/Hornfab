"""Verify quoted evidence blocks in a Markdown document against their source files.

Evidence documents quote real terminal / JSON bytes.  Copying those bytes by hand is
error prone, so each quoted block carries an HTML-comment annotation immediately above
its opening fence::

    <!-- evidence-quote: source=<path> mode=exact|lines decode=auto|utf-8|utf-16 -->

``source`` is relative to the repository root (``--root``); absolute paths and parent
escapes are refused.  The tool reads the decoded source and checks the fenced block:

``mode=exact``
    The block text (after newline normalisation) must equal a contiguous segment of the
    decoded source.  Use this for blocks that are quoted byte-for-byte.

``mode=lines``
    Every non-empty block line must appear verbatim in the decoded source (whitespace
    insensitive).  Lines that are exactly ``...`` are elision markers and are skipped.
    Balanced parenthetical annotations outside double-quoted strings (for example
    ``(mesh:horn, 381105 B)``) are treated as editorial notes and stripped before the
    comparison.  Lines are matched in document order; a hand-selected field excerpt that
    reorders a field is still accepted as long as the line is present, and the out-of-order
    count is reported.  Use this for hand-elided excerpts that cannot be byte-identical.

Blocks without an annotation are skipped and counted.  Exit status:

* ``0`` — every annotated block passed;
* ``1`` — at least one block mismatched (or an annotation was malformed);
* ``2`` — a source file could not be read (missing/unreadable/refused path).

Usage::

    .venv\\Scripts\\python.exe tools/system/verify_evidence_quotes.py `
        --doc docs/research/system_woofer_2026-11-18/FIRST_BEM_EVIDENCE.md --root .
"""
from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

ANNOTATION_RE = re.compile(r"^\s*<!--\s*evidence-quote:\s*(?P<body>.*?)\s*-->\s*$")
KV_RE = re.compile(r"(?P<key>[A-Za-z_]\w*)=(?P<value>\"[^\"]*\"|\S+)")
FENCE = "```"
VALID_MODES = ("exact", "lines")
VALID_DECODES = ("auto", "utf-8", "utf-16")


class AnnotationError(ValueError):
    """The annotation cannot be parsed or names an unsupported option."""


class SourceError(RuntimeError):
    """The source path is unsafe, missing or unreadable (exit code 2)."""


@dataclass
class BlockResult:
    block_index: int          # 1-based index among *annotated* blocks
    fence_line: int           # 1-based line of the opening fence
    source: str
    mode: str
    decode: str
    ok: bool
    unreadable: bool
    detail: str

    def as_dict(self) -> dict:
        return {
            "block": self.block_index,
            "fence_line": self.fence_line,
            "source": self.source,
            "mode": self.mode,
            "decode": self.decode,
            "status": "FAIL" if self.unreadable else ("PASS" if self.ok else "FAIL"),
            "detail": self.detail,
        }


# ------------------------------------------------------------------ parsing


def parse_annotation(line: str) -> dict[str, str] | None:
    """Return the key/value annotation on ``line`` or ``None`` if it is not one."""
    match = ANNOTATION_RE.match(line)
    if match is None:
        return None
    fields: dict[str, str] = {}
    for item in KV_RE.finditer(match.group("body")):
        value = item.group("value")
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        fields[item.group("key").lower()] = value
    return fields


def _annotation_for_fence(lines: list[str], fence_index: int) -> dict[str, str] | None:
    """Find the annotation that immediately precedes the fence at ``fence_index``."""
    probe = fence_index - 1
    while probe >= 0 and not lines[probe].strip():
        probe -= 1
    if probe < 0:
        return None
    return parse_annotation(lines[probe])


def _validate_annotation(fields: dict[str, str], fence_line: int) -> tuple[str, str, str]:
    source = fields.get("source")
    if not source:
        raise AnnotationError(f"line {fence_line}: annotation is missing source=")
    mode = fields.get("mode")
    if mode not in VALID_MODES:
        raise AnnotationError(
            f"line {fence_line}: mode must be one of {VALID_MODES}, got {mode!r}")
    decode = fields.get("decode", "auto")
    if decode not in VALID_DECODES:
        raise AnnotationError(
            f"line {fence_line}: decode must be one of {VALID_DECODES}, got {decode!r}")
    return source, mode, decode


def find_annotated_blocks(markdown: str) -> list[tuple[int, dict[str, str], str]]:
    """Return ``(fence_line, annotation, block_text)`` for annotated fenced blocks."""
    lines = markdown.split("\n")
    found: list[tuple[int, dict[str, str], str]] = []
    index = 0
    while index < len(lines):
        if not lines[index].strip().startswith(FENCE):
            index += 1
            continue
        opening = index
        closing = opening + 1
        while closing < len(lines) and not lines[closing].strip().startswith(FENCE):
            closing += 1
        if closing >= len(lines):
            break  # unterminated fence
        annotation = _annotation_for_fence(lines, opening)
        if annotation is not None:
            block_text = "\n".join(lines[opening + 1:closing])
            found.append((opening + 1, annotation, block_text))
        index = closing + 1
    return found


def count_fenced_blocks(markdown: str) -> int:
    """Count fenced code blocks (including annotated ones) in the document."""
    lines = markdown.split("\n")
    total = 0
    index = 0
    while index < len(lines):
        if not lines[index].strip().startswith(FENCE):
            index += 1
            continue
        total += 1
        closing = index + 1
        while closing < len(lines) and not lines[closing].strip().startswith(FENCE):
            closing += 1
        index = closing + 1
    return total


# ------------------------------------------------------------------ source handling


def resolve_source(root: Path, rel: str) -> Path:
    """Resolve ``rel`` against ``root``, refusing absolute and escaping paths.

    The check is lexical: ``..`` components are normalised but symlinks and junctions
    (for example the gitignored ``system_runs`` junction) are not followed, so a source
    that is nominally inside the repository root is accepted even when its storage lives
    outside the working tree.
    """
    if not rel:
        raise SourceError("empty source path")
    candidate = Path(rel)
    if candidate.is_absolute() or re.match(r"^[A-Za-z]:", rel):
        raise SourceError(f"refusing absolute source path: {rel!r}")
    root_abs = Path(os.path.abspath(root))
    target = Path(os.path.abspath(os.path.join(root_abs, rel)))
    try:
        target.relative_to(root_abs)
    except ValueError as exc:
        raise SourceError(f"refusing source path outside repo root: {rel!r}") from exc
    return target


def _looks_utf16(data: bytes) -> bool:
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return True
    sample = data[:4096]
    if len(sample) < 4:
        return False
    half = len(sample) // 2
    zeros_even = sample[0::2].count(0)
    zeros_odd = sample[1::2].count(0)
    return zeros_odd >= 0.6 * half or zeros_even >= 0.6 * half


def _decode_utf16(data: bytes) -> str:
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return data.decode("utf-16")
    sample = data[:4096]
    zeros_even = sample[0::2].count(0)
    zeros_odd = sample[1::2].count(0)
    encoding = "utf-16-le" if zeros_odd >= zeros_even else "utf-16-be"
    return data.decode(encoding, errors="replace")


def decode_source(data: bytes, decode: str) -> str:
    if decode == "utf-8":
        text = data.decode("utf-8")
    elif decode == "utf-16" or _looks_utf16(data):
        text = _decode_utf16(data)
    else:  # auto, not UTF-16-looking
        text = data.decode("utf-8")
    return _normalise_newlines(text)


def _normalise_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _strip_whitespace(text: str) -> str:
    return "".join(text.split())


def _strip_paren_annotations(line: str) -> str:
    """Remove balanced ``(...)`` groups that are outside double-quoted strings."""
    out: list[str] = []
    in_quotes = False
    escaped = False
    depth = 0
    for char in line:
        if escaped:
            if depth == 0:
                out.append(char)
            escaped = False
            continue
        if in_quotes and char == "\\":
            if depth == 0:
                out.append(char)
            escaped = True
            continue
        if char == '"':
            in_quotes = not in_quotes
            if depth == 0:
                out.append(char)
            continue
        if not in_quotes:
            if char == "(":
                depth += 1
                continue
            if char == ")" and depth > 0:
                depth -= 1
                continue
        if depth == 0:
            out.append(char)
    return "".join(out)


def _is_elision(line: str) -> bool:
    stripped = line.strip()
    return stripped == "..." or stripped.startswith("... ")


def _match_exact(block: str, source: str) -> tuple[bool, str]:
    if block in source:
        return True, "exact contiguous segment"
    return False, "block is not a contiguous segment of the decoded source"


def _match_lines(block: str, source: str) -> tuple[bool, str]:
    flat_source = _strip_whitespace(source)
    position = 0
    out_of_order = 0
    checked = 0
    for lineno, raw in enumerate(block.split("\n"), start=1):
        if not raw.strip() or _is_elision(raw):
            continue
        candidate = _strip_paren_annotations(raw).strip()
        if not candidate:
            continue
        needle = _strip_whitespace(candidate)
        if not needle:
            continue
        checked += 1
        found_at = flat_source.find(needle, position)
        if found_at >= 0:
            position = found_at + len(needle)
            continue
        if flat_source.find(needle) >= 0:
            out_of_order += 1
            continue
        return False, f"block line {lineno} not found in source: {raw.strip()!r}"
    if out_of_order:
        return True, f"{checked} line(s) present ({out_of_order} out of source order)"
    return True, f"{checked} line(s) present in order"


def verify_block(block_text: str, source_text: str, mode: str) -> tuple[bool, str]:
    if mode == "exact":
        return _match_exact(block_text, source_text)
    return _match_lines(block_text, source_text)


# ------------------------------------------------------------------ CLI


def run_check(doc: Path, root: Path) -> tuple[list[BlockResult], int, int]:
    """Return ``(results, skipped_count, unreadable_count)`` for ``doc``."""
    markdown = _normalise_newlines(doc.read_text(encoding="utf-8"))
    annotated = find_annotated_blocks(markdown)
    total_blocks = count_fenced_blocks(markdown)
    skipped = total_blocks - len(annotated)
    results: list[BlockResult] = []
    unreadable = 0

    for block_index, (fence_line, fields, block_text) in enumerate(annotated, start=1):
        try:
            source_rel, mode, decode = _validate_annotation(fields, fence_line)
        except AnnotationError as exc:
            results.append(BlockResult(
                block_index, fence_line, fields.get("source", "?"),
                fields.get("mode", "?"), fields.get("decode", "?"),
                ok=False, unreadable=False, detail=str(exc)))
            continue

        try:
            source_path = resolve_source(root, source_rel)
        except SourceError as exc:
            unreadable += 1
            results.append(BlockResult(
                block_index, fence_line, source_rel, mode, decode,
                ok=False, unreadable=True, detail=str(exc)))
            continue

        try:
            raw = source_path.read_bytes()
        except OSError as exc:
            unreadable += 1
            results.append(BlockResult(
                block_index, fence_line, source_rel, mode, decode,
                ok=False, unreadable=True,
                detail=f"cannot read source: {exc.__class__.__name__}: {exc}"))
            continue

        try:
            source_text = decode_source(raw, decode)
        except UnicodeDecodeError as exc:
            unreadable += 1
            results.append(BlockResult(
                block_index, fence_line, source_rel, mode, decode,
                ok=False, unreadable=True,
                detail=f"cannot decode source as {decode}: {exc}"))
            continue

        ok, detail = verify_block(block_text, source_text, mode)
        results.append(BlockResult(
            block_index, fence_line, source_rel, mode, decode,
            ok=ok, unreadable=False, detail=detail))

    return results, skipped, unreadable


def _exit_code(results: list[BlockResult], unreadable: int) -> int:
    if unreadable:
        return 2
    if any(not result.ok for result in results):
        return 1
    return 0


def _print_summary(doc: Path, results: list[BlockResult], skipped: int) -> None:
    print(f"evidence-quote check: {doc}")
    for result in results:
        status = "FAIL" if result.unreadable else ("PASS" if result.ok else "FAIL")
        print(
            f"  [{status}] block {result.block_index} @ line {result.fence_line} "
            f"mode={result.mode} decode={result.decode} source={result.source} "
            f"({result.detail})")
    passed = sum(1 for result in results if result.ok)
    print(
        f"annotated={len(results)} passed={passed} failed={len(results) - passed} "
        f"skipped={skipped} result={'PASS' if passed == len(results) else 'FAIL'}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify annotated evidence-quote blocks against their source files.")
    parser.add_argument("--doc", required=True, help="evidence Markdown file to check")
    parser.add_argument("--root", default=".", help="repository root (default: .)")
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    args = parser.parse_args(argv)

    doc = Path(args.doc)
    root = Path(args.root)
    try:
        results, skipped, unreadable = run_check(doc, root)
    except OSError as exc:
        print(f"evidence-quote check: cannot read document {doc}: {exc}",
              file=sys.stderr)
        return 2

    code = _exit_code(results, unreadable)
    if args.json:
        payload = {
            "doc": str(doc),
            "annotated": len(results),
            "skipped": skipped,
            "unreadable": unreadable,
            "exit_code": code,
            "blocks": [result.as_dict() for result in results],
        }
        print(json.dumps(payload, indent=2))
    else:
        _print_summary(doc, results, skipped)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
