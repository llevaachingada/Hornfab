"""OS-agnostic path splitting for the system store (contract ``01_CONTRACTS.md`` section 1).

Pure string operations only: a Windows path (``C:\\a\\b\\mesh.msh``) and a POSIX path
(``/a/b/mesh.msh``) must produce the same parts on every operating system.  Nothing here
touches the filesystem, so the helpers are safe to use in the export, the reader and the
store migration on a Linux cloud runner that never saw the Windows checkout.
"""
from __future__ import annotations

import re
from typing import Sequence

__all__ = ["split_any", "to_store_relative", "leaf_dir_name"]

_DRIVE_RE = re.compile(r"^[A-Za-z]:$")
_SPLIT_RE = re.compile(r"[\\/]")


def _text(path_text: object) -> str:
    return path_text if isinstance(path_text, str) else str(path_text)


def split_any(path_text: str) -> tuple[str, ...]:
    """Split on both ``/`` and ``\\``; drop empty parts and a drive like ``C:``.

    >>> split_any(r"C:\\a\\b\\mesh.msh")
    ('a', 'b', 'mesh.msh')
    >>> split_any("C:/Users/x/system_runs/system/e/c/run/manifest.json")[:3]
    ('Users', 'x', 'system_runs')
    """
    parts = _SPLIT_RE.split(_text(path_text))
    return tuple(part for part in parts if part and not _DRIVE_RE.match(part))


def to_store_relative(path_text: str, store_root_hints: Sequence[str]) -> str | None:
    """Return the store-relative POSIX tail of ``path_text``, or ``None``.

    A hint matches when its own split parts are a (case-insensitive) prefix of the path.
    The marker ``system_runs`` is always recognised as a hint: it anchors the real store
    root even when no explicit hint is supplied, so
    ``C:/Users/x/system_runs/system/e/c/run/manifest.json`` -> ``system/e/c/run/manifest.json``.
    """
    parts = split_any(path_text)
    if not parts:
        return None
    lowered = tuple(part.lower() for part in parts)

    for hint in store_root_hints or ():
        hint_parts = split_any(hint)
        if not hint_parts:
            continue
        count = len(hint_parts)
        if len(parts) >= count and lowered[:count] == tuple(part.lower() for part in hint_parts):
            return "/".join(parts[count:])

    for index in range(len(parts) - 1, -1, -1):
        if lowered[index] == "system_runs":
            return "/".join(parts[index + 1:])
    return None


def leaf_dir_name(path_text: str) -> str | None:
    """The parent directory name of a file path, OS-agnostic.

    >>> leaf_dir_name(r"C:\\a\\b\\mesh.msh")
    'b'
    >>> leaf_dir_name("mesh.msh") is None
    True
    """
    parts = split_any(path_text)
    if len(parts) < 2:
        return None
    return parts[-2]
