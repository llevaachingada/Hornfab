"""One-command REAL Boundary Lab lane (CPU only): probe -> stage -> validate -> tiny solve.

Risk R11: Boundary-Lab-facing code (probe, staging adapter, BL's own ``project validate`` and
the reference ``solve`` wrapper) can be exercised end-to-end before a push with one command:

    .venv/Scripts/python.exe tools/system/real_bl_lane.py --real
    .venv/Scripts/python.exe tools/system/real_bl_lane.py --real --solve --store system_runs

What it does
------------
``--real`` is an explicit opt-in.  Without it the lane refuses (rc 2) before touching anything.
With it the lane:

1. probes for a verified Boundary Lab install (:func:`probe_boundarylab`) and refuses (rc 3)
   when none is verified;
2. stages the vented-only reference fixture through BL's *own* generator + ``project validate``
   (:func:`stage_reference_project`), writing under ``--store`` / ``system_runs``;
3. with ``--solve``, runs BL's own ``project solve`` through
   :func:`hornlab_search.system.reference.solve` with the committed 3-frequency request
   (``vented/voltage`` at 250/700/1100 Hz, one on-axis probe at 2 m).

This is the CPU lane: the solve backend is always ``beat_cpu`` and the solve is wrapped in
:func:`hornlab_search.search.gpulock.cpu_lane_lock`.  There is no GPU flag anywhere and the GPU
lock is never touched.

The command prints one JSON report (probe status, stage case dir / ok / valid, solve status / run
dir, and the exact argv used).  ``--json`` pretty-prints that report.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.search.gpulock import cpu_lane_lock  # noqa: E402
from hornlab_search.system.boundarylab.probe import (  # noqa: E402
    BL_CAPABILITY_MISSING,
    probe_boundarylab,
)
from hornlab_search.system.boundarylab.stage import stage_reference_project  # noqa: E402
from hornlab_search.system.reference import (  # noqa: E402
    ReferenceError,
    load_request,
    solve as reference_solve,
)

__all__ = [
    "AUTHORIZED_BY",
    "DEFAULT_STORE",
    "DEFAULT_TIMEOUT_S",
    "EXPERIMENT_ID",
    "REQUEST_PATH",
    "SOLVE_BACKEND",
    "build_plan",
    "build_parser",
    "main",
    "run_lane",
]

#: Store root used when ``--store`` is absent (case dirs land in ``<store>/system/...``).
DEFAULT_STORE = "system_runs"
DEFAULT_TIMEOUT_S = 1800.0
EXPERIMENT_ID = "real_bl_lane"
#: The committed tiny vented-only request this lane solves with.
REQUEST_PATH = (
    REPO / "docs" / "queue" / "system_evidence_2026-11-19" / "requests"
    / "real_bl_lane_vented_3f.json"
)
#: BL solve backend for the CPU lane (never beat_cuda).
SOLVE_BACKEND = "beat_cpu"
#: The explicit authorization record the reference solve wrapper demands.
AUTHORIZED_BY = "readiness R11 2026-11-21: real-BL lane"

#: Exit codes (documented so wrappers can branch without parsing text).
RC_OK = 0
RC_REFUSED_NO_REAL = 2
RC_REFUSED_NO_BL = 3
RC_STAGE_FAILED = 4
RC_SOLVE_FAILED = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="One-command REAL Boundary Lab lane (CPU only; probe + stage + optional solve)"
    )
    parser.add_argument("--real", action="store_true",
                        help="required: stage and validate a real Boundary Lab project")
    parser.add_argument("--solve", action="store_true",
                        help="after a valid stage, run BL's own solve with the tiny CPU request")
    parser.add_argument("--store", default=DEFAULT_STORE,
                        help=f"case/store root (default: {DEFAULT_STORE})")
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S,
                        help=f"per-step timeout in seconds (default: {DEFAULT_TIMEOUT_S:g})")
    parser.add_argument("--json", action="store_true",
                        help="pretty-print the JSON report (default is compact JSON)")
    return parser


def build_plan(*, store: str | Path, solve: bool, timeout_s: float) -> dict[str, Any]:
    """The dry-run plan (no BL import, no staging): what the real lane would do.

    This is pure: it reads the committed request shape through the same
    :func:`hornlab_search.system.reference.load_request` the solve path uses, so a request
    mistake fails here before any BL process is started.
    """
    request = load_request(REQUEST_PATH)
    resolved_store = str(Path(store).resolve())
    return {
        "real": True,
        "gpu": False,
        "store": resolved_store,
        "request": request.as_dict(),
        "stage": {
            "function": "stage_reference_project",
            "experiment_id": EXPERIMENT_ID,
            "store_root": resolved_store,
            "timeout_s": float(timeout_s),
            "run_now": True,
        },
        "solve": None if not solve else {
            "function": "reference.solve",
            "backend": SOLVE_BACKEND,
            "authorized_by": AUTHORIZED_BY,
            "request_path": str(REQUEST_PATH),
            "lock": "cpu_lane_lock",
            "gpu": False,
        },
    }


def _stage_report(staged: Any) -> dict[str, Any]:
    detail = getattr(staged, "detail", {}) or {}
    return {
        "case_dir": str(staged.case_dir),
        "ok": bool(staged.ok),
        "valid": bool(staged.valid),
        "returncode": int(staged.returncode),
        "argv": list(detail.get("argv") or []),
        "log_tail": list(getattr(staged, "captured_log_tail", ()) or ())[-12:],
    }


def _solve_report(result: Any) -> dict[str, Any]:
    payload = result.as_dict() if hasattr(result, "as_dict") else dict(result)
    return {
        "status": payload.get("status"),
        "run_dir": payload.get("run_dir"),
        "returncode": payload.get("returncode"),
        "argv": list(payload.get("argv") or []),
        "backend": payload.get("backend"),
        "manifest_path": payload.get("manifest_path"),
        "record_path": payload.get("record_path"),
        "stdout_tail": list(payload.get("stdout_tail") or []),
        "stderr_tail": list(payload.get("stderr_tail") or []),
    }


def run_lane(*, real: bool, solve: bool, store: str | Path, timeout_s: float,
             argv: Sequence[str] = ()) -> tuple[int, dict[str, Any]]:
    """Execute the lane and return ``(exit_code, report)``.

    BL work only happens with ``real=True``; the report's keys are stable so a caller can
    log it even on refusal/failure.
    """
    report: dict[str, Any] = {
        "argv": [str(item) for item in argv],
        "real": bool(real),
        "gpu": False,
        "store": str(Path(store).resolve()),
        "probe": None,
        "stage": None,
        "solve": None,
    }
    if not real:
        report["refused"] = (
            "real Boundary Lab lane refused: pass --real to stage and validate a real BL project"
        )
        return RC_REFUSED_NO_REAL, report

    probe = probe_boundarylab()
    verified = probe.verified_root
    report["probe"] = {
        "status": probe.status,
        "found": bool(probe.found),
        "verified_root": None if verified is None else verified.path,
        "capability_missing": list(probe.capability_missing),
    }
    if verified is None:
        report["refused"] = (
            f"{BL_CAPABILITY_MISSING}: no verified Boundary Lab root; staging refused"
        )
        return RC_REFUSED_NO_BL, report

    staged = stage_reference_project(
        verified,
        store_root=store,
        experiment_id=EXPERIMENT_ID,
        timeout_s=timeout_s,
        run_now=True,
    )
    report["stage"] = _stage_report(staged)
    if not (staged.ok and staged.valid):
        report["refused"] = "staging or BL project validate failed; solve not attempted"
        return RC_STAGE_FAILED, report

    if not solve:
        return RC_OK, report

    request = load_request(REQUEST_PATH)
    try:
        # CPU lane marker: the reference solve never acquires the GPU lock, and an already-held
        # CPU lane lock is respected by the shared context manager (we never delete it here).
        with cpu_lane_lock(f"real-bl-lane: {staged.case_dir}"):
            solved = reference_solve(
                staged.case_dir,
                REQUEST_PATH,
                backend=SOLVE_BACKEND,
                authorized_by=AUTHORIZED_BY,
                timeout_s=timeout_s,
            )
    except ReferenceError as exc:
        report["solve"] = {
            "status": "error",
            "error": f"{exc.token}: {exc.detail}",
            "backend": SOLVE_BACKEND,
            "request_path": str(REQUEST_PATH),
            "request_sha256": request.sha256,
            "run_dir": str(Path(staged.case_dir) / "run"),
        }
        return RC_SOLVE_FAILED, report

    report["solve"] = _solve_report(solved)
    return RC_OK, report


def _emit(report: Mapping[str, Any], *, pretty: bool) -> None:
    print(json.dumps(report, sort_keys=True,
                     indent=2 if pretty else None, separators=None if pretty else (",", ":")))


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(args_list)
    code, report = run_lane(
        real=args.real,
        solve=args.solve,
        store=args.store,
        timeout_s=args.timeout_s,
        argv=args_list,
    )
    _emit(report, pretty=args.json)
    if code != RC_OK:
        message = report.get("refused") or (report.get("solve") or {}).get("error") or (
            "real Boundary Lab lane failed"
        )
        print(f"[real_bl_lane] {message}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
