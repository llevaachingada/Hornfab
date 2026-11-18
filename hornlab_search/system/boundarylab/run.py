"""Headless Boundary Lab project validate (and the hard-off solve gate).

``validate_project`` calls the installed BL's own console entry:
``blab project validate <project> --json`` (documented in its ``docs/advanced/cli-workflow.md``),
with bounded capture and no shell interpolation. ``solve_project`` NEVER runs anything on
its own: it exists so callers hit an explicit gate instead of silently reaching a solver.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from hornlab_search.system.boundarylab.probe import BLRoot, BLCapabilityError

__all__ = ["BlockedByGate", "ValidationResult", "validate_project", "solve_project"]

_MAX_CAPTURE_LINES = 400


class BlockedByGate(RuntimeError):
    """A capability behind an authorization gate was requested without authorization."""


@dataclass(frozen=True)
class ValidationResult:
    returncode: int
    parsed: dict[str, Any] | None
    stdout_tail: tuple[str, ...]
    stderr_tail: tuple[str, ...]
    argv: tuple[str, ...]


def _bounded(text: str, max_lines: int = _MAX_CAPTURE_LINES) -> tuple[str, ...]:
    lines = text.splitlines() or []
    return tuple(lines[-max_lines:])


def _run_bounded(argv: Sequence[str], timeout_s: float) -> tuple[int, str, str]:
    proc = subprocess.run(
        list(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def validate_project(root: BLRoot, project_path: str | os.PathLike[str],
                     *, timeout_s: float = 300.0) -> ValidationResult:
    """``blab project validate <project> --json`` in BL's own environment (no solve)."""
    if not root.verified:
        raise BLCapabilityError(
            (f"BLRoot at {root.path} is not verified: " + " | ".join(root.missing),))
    cli = root.cli_entry
    if not cli:
        raise BLCapabilityError(("verified BLRoot has no blab console entry",))
    project = Path(project_path)
    if not project.is_file():
        raise FileNotFoundError(f"project file not found: {project}")
    argv = [cli, "project", "validate", str(project), "--json"]
    try:
        code, out, err = _run_bounded(argv, timeout_s)
    except subprocess.TimeoutExpired:
        return ValidationResult(returncode=124, parsed=None, stdout_tail=(),
                                stderr_tail=(f"[adapter] validate timed out after {timeout_s:.0f}s",
                                             ), argv=tuple(argv))
    parsed = None
    try:
        candidate = json.loads(out)
        if isinstance(candidate, dict):
            return ValidationResult(returncode=code, parsed=candidate,
                                    stdout_tail=_bounded(out), stderr_tail=_bounded(err),
                                    argv=tuple(argv))
    except ValueError:
        pass
    try:
        start = out.index("{")
        parsed = json.loads(out[start:])
    except (ValueError, IndexError):
        for line in reversed(_bounded(out)):
            stripped = line.strip()
            if stripped.startswith("{"):
                try:
                    parsed = json.loads(stripped)
                    break
                except ValueError:
                    continue
    return ValidationResult(returncode=code, parsed=parsed,
                            stdout_tail=_bounded(out), stderr_tail=_bounded(err), argv=tuple(argv))


def solve_project(*args: Any, **kwargs: Any) -> None:
    """Refuse by design. Stage 4 coupled solves need a senior gate + free GPU lane.

    Two independent gates must be satisfied before this adapter will even consider
    touching a solver, and even then it refuses: (1) environment flag
    ``HORNLAB_BL_ALLOW_SOLVE=1``; (2) keyword ``authorized_by`` naming the senior
    approval. With both set it raises BlockedByGate telling the caller to use BL's own
    CLI directly for the senior-approved Stage 4 run — this lane never starts solves.
    """
    env_ok = os.environ.get("HORNLAB_BL_ALLOW_SOLVE", "").strip() == "1"
    authorized_by = kwargs.get("authorized_by")
    if env_ok and isinstance(authorized_by, str) and authorized_by.strip():
        raise BlockedByGate(
            "solve adapter is intentionally inert in this stage: run the senior-approved "
            "Stage 4 solve with Boundary Lab's own CLI (blab project solve), behind the GPU "
            f"gate, and record the authorization ({authorized_by!r}) in the case manifest. "
            "This adapter will not start solves.")
    missing = [] if env_ok else ["environment flag HORNLAB_BL_ALLOW_SOLVE=1 not set"]
    if not (isinstance(authorized_by, str) and authorized_by.strip()):
        missing.append("keyword authorized_by (senior approval record) not provided")
    raise BlockedByGate(
        "BL solve refused by gate: " + " | ".join(missing) +
        "; generate/validate only (Stage 1)")
