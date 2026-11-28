#!/usr/bin/env python3
"""Relative-link checker for markdown files in the hornlab-search checkout.

Stdlib only. Walks every ``*.md`` file under the repo root, extracts inline
markdown link targets (``](target)``), resolves each target relative to the
directory of the containing file, and reports targets that do not exist.

Behaviour:
  * Anchors (``#section``) and query strings (``?x``) are stripped before the
    existence check but preserved in the reported target.
  * External URLs (anything with a scheme, protocol-relative ``//``, absolute
    ``/path``), pure in-page anchors (``#...``), and template placeholders
    (targets starting with ``{``) are skipped.
  * Targets are percent-decoded before resolution (``%20`` -> space).
  * ``.git/``, ``.venv/``, ``runs/``, ``scratch/`` and ``node_modules/`` are
    never walked.

Exit status is 0 when no broken relative links are found, 1 otherwise.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.parse

SKIP_DIRS = {".git", ".venv", "runs", "scratch", "node_modules"}

# Inline markdown link/image target: ]( ... ) on a single line.
LINK_RE = re.compile(r"\]\(([^)\n]+)\)")

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


def iter_md(root: str):
    """Yield every markdown file under *root*, pruning SKIP_DIRS."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.lower().endswith(".md"):
                yield os.path.join(dirpath, name)


def parse_target(raw: str):
    """Split a raw link body into (path, suffix, rest, angle_bracketed).

    ``suffix`` is the trailing ``#anchor``/``?query`` portion, ``rest`` is a
    possible title (`` "title"``) after a space. Returns ``None`` for an empty
    body.
    """
    text = raw.strip()
    if not text:
        return None
    angle = False
    if text.startswith("<") and text.endswith(">"):
        text = text[1:-1].strip()
        angle = True
        rest = ""
    else:
        match = re.match(r"^(\S+)(\s+.*)?$", text)
        if not match:
            return None
        text = match.group(1)
        rest = match.group(2) or ""
    cut = len(text)
    for ch in "#?":
        pos = text.find(ch)
        if pos != -1:
            cut = min(cut, pos)
    return text[:cut], text[cut:], rest, angle


def is_external(path: str) -> bool:
    if not path or path.startswith("#") or path.startswith("/") or path.startswith("{"):
        return True
    if path.startswith("//"):
        return True
    return bool(_SCHEME_RE.match(path))


def check(root: str):
    root = os.path.abspath(root)
    broken = []
    total = 0
    for md in iter_md(root):
        try:
            with open(md, "rb") as fh:
                text = fh.read().decode("utf-8", "surrogateescape")
        except OSError:
            continue
        base_dir = os.path.dirname(md)
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in LINK_RE.finditer(line):
                parsed = parse_target(match.group(1))
                if parsed is None:
                    continue
                path, _suffix, _rest, _angle = parsed
                if is_external(path):
                    continue
                total += 1
                resolved = os.path.normpath(
                    os.path.join(base_dir, urllib.parse.unquote(path))
                )
                if not os.path.exists(resolved):
                    broken.append(
                        (
                            os.path.relpath(md, root).replace(os.sep, "/"),
                            lineno,
                            match.group(1).strip(),
                        )
                    )
    return total, broken


def main(argv):
    root = argv[1] if len(argv) > 1 else "."
    total, broken = check(root)
    for path, lineno, target in broken:
        print(f"{path}:{lineno}: {target}")
    print(f"checked {total} relative links; broken={len(broken)}")
    return 0 if not broken else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
