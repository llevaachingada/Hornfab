"""JobSpec: the one place a system job's argv is built (contract section 6).

Every kind is a plain CPU command.  The argv starts with ``sys.executable -m
hornlab_search.system.cli`` (or ``... .woofer_seed`` for the seed screen), which is exactly
what ``tools/system/gui_system_job.py`` routes today:

* ``screen``                   -> ``hornlab_search.system.woofer_seed``
* ``bl_stage``/``bl_validate``/``bl_solve`` -> ``cli reference prepare|validate|solve``
* ``pilot``/``portfolio``/``funnel``        -> the matching ``cli`` subcommand

``preview`` is the exact process command line: ``shlex.join`` on POSIX and
``subprocess.list2cmdline`` on Windows (the same split the launcher itself uses).  No shell is
involved and no GPU system job exists in v1 (``lane`` is always ``"cpu"``).
"""
from __future__ import annotations

import hashlib
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from .contracts import canonical_json

JobKind = Literal["screen", "pilot", "portfolio", "bl_stage", "bl_validate", "bl_solve", "funnel"]

JOB_KINDS: tuple[JobKind, ...] = (
    "screen", "pilot", "portfolio", "bl_stage", "bl_validate", "bl_solve", "funnel",
)

CLI_MODULE = "hornlab_search.system.cli"
SEED_MODULE = "hornlab_search.system.woofer_seed"


class JobError(ValueError):
    """A refused job build.  ``token`` is the stable UPPER_SNAKE refusal token."""

    def __init__(self, token: str, detail: str = "") -> None:
        self.token = str(token)
        self.detail = str(detail)
        super().__init__(f"{self.token}: {self.detail}" if self.detail else self.token)


@dataclass(frozen=True, slots=True)
class JobSpec:
    """One deterministic, launchable system command (contract section 6)."""

    kind: JobKind
    argv: tuple[str, ...]
    cwd_rel: str
    env: tuple[tuple[str, str], ...]
    inputs_sha256: str
    lane: Literal["cpu"] = "cpu"
    authorization_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe view for the funnel ledger (sorted keys, tuples as lists)."""
        return {
            "argv": list(self.argv),
            "authorization_id": self.authorization_id,
            "cwd_rel": self.cwd_rel,
            "env": [[k, v] for k, v in self.env],
            "inputs_sha256": self.inputs_sha256,
            "kind": self.kind,
            "lane": self.lane,
        }


def preview(job: JobSpec) -> str:
    """The exact command line a launch would run (POSIX ``shlex.join`` / Windows list2cmdline)."""
    argv = [str(part) for part in job.argv]
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


_MISSING = object()


def _take(options: dict[str, Any], *names: str) -> Any:
    """Pop the first present alias (removing all aliases); ``None`` when absent."""
    found: Any = _MISSING
    for name in names:
        if name in options:
            value = options.pop(name)
            if found is _MISSING:
                found = value
    return None if found is _MISSING else found


def _add(argv: list[str], flag: str, value: Any) -> None:
    """Append ``flag value`` (``True`` = bare flag, sequences = repeated values)."""
    if value is None or value == "" or value is False:
        return
    if value is True:
        argv.append(flag)
        return
    if isinstance(value, (list, tuple)):
        if not value:
            return
        argv.append(flag)
        argv.extend(str(item) for item in value)
        return
    argv.extend([flag, str(value)])


def _flag_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def _build_screen(options: dict[str, Any]) -> list[str]:
    argv = ["-m", SEED_MODULE]
    _add(argv, "--spec", _take(options, "spec", "spec_path"))
    _add(argv, "--asset-id", _take(options, "asset_id"))
    drivers = _take(options, "drivers")
    if drivers is not None:
        _add(argv, "--drivers", _flag_list(drivers))
    _add(argv, "--out", _take(options, "out"))
    _add(argv, "--runs-root", _take(options, "runs_root"))
    _add(argv, "--scan-limit", _take(options, "scan_limit"))
    _add(argv, "--limit-boxes", _take(options, "limit_boxes"))
    _add(argv, "--shortlist-size", _take(options, "shortlist_size"))
    return argv


def _build_pilot(options: dict[str, Any]) -> list[str]:
    argv = ["-m", CLI_MODULE, "pilot"]
    _add(argv, "--spec", _take(options, "spec", "spec_path"))
    _add(argv, "--driver-stem", _take(options, "driver_stem"))
    _add(argv, "--driver-ts-dir", _take(options, "driver_ts_dir"))
    _add(argv, "--geometry", _take(options, "geometry"))
    _add(argv, "--asset-id", _take(options, "asset_id"))
    _add(argv, "--runs-root", _take(options, "runs_root"))
    _add(argv, "--scan-limit", _take(options, "scan_limit"))
    _add(argv, "--limit-boxes", _take(options, "limit_boxes"))
    _add(argv, "--out", _take(options, "out"))
    return argv


def _build_portfolio(options: dict[str, Any]) -> list[str]:
    argv = ["-m", CLI_MODULE, "portfolio"]
    _add(argv, "--spec", _take(options, "spec", "spec_path"))
    stems = _take(options, "driver_stems", "driver_stem")
    if stems is not None:
        for stem in _flag_list(stems):
            argv.extend(["--driver-stem", stem])
    _add(argv, "--k", _take(options, "k"))
    _add(argv, "--limit-boxes", _take(options, "limit_boxes"))
    _add(argv, "--scan-limit", _take(options, "scan_limit"))
    _add(argv, "--runs-root", _take(options, "runs_root"))
    _add(argv, "--driver-ts-dir", _take(options, "driver_ts_dir"))
    _add(argv, "--out", _take(options, "out"))
    return argv


def _build_bl_stage(options: dict[str, Any]) -> list[str]:
    argv = ["-m", CLI_MODULE, "reference", "prepare"]
    _add(argv, "--root", _take(options, "root"))
    _add(argv, "--horn-mesh", _take(options, "horn_mesh"))
    _add(argv, "--source-group", _take(options, "source_group"))
    _add(argv, "--mesh-role", _take(options, "mesh_role"))
    _add(argv, "--scale-factor", _take(options, "scale_factor"))
    translation = _take(options, "translation_mm")
    if translation is not None and not isinstance(translation, str):
        _add(argv, "--translation-mm", _flag_list(translation))
    _add(argv, "--overrides", _take(options, "overrides"))
    _add(argv, "--experiment-id", _take(options, "experiment_id"))
    _add(argv, "--out", _take(options, "out"))
    _add(argv, "--case-dir", _take(options, "case_dir"))
    _add(argv, "--timeout-s", _take(options, "timeout_s"))
    _add(argv, "--dry-run", _take(options, "dry_run"))
    return argv


def _case_dir(options: dict[str, Any], token: str) -> str:
    value = _take(options, "case_dir", "case")
    if value is None or str(value).strip() == "":
        raise JobError(token)
    return str(value)


def _build_bl_validate(options: dict[str, Any]) -> list[str]:
    argv = ["-m", CLI_MODULE, "reference", "validate", _case_dir(options, "CASE_DIR_MISSING")]
    _add(argv, "--request", _take(options, "request"))
    _add(argv, "--timeout-s", _take(options, "timeout_s"))
    return argv


def _build_bl_solve(options: dict[str, Any], authorization_id: str) -> list[str]:
    argv = ["-m", CLI_MODULE, "reference", "solve", _case_dir(options, "CASE_DIR_MISSING")]
    request = _take(options, "request")
    if request is None or str(request).strip() == "":
        raise JobError("REQUEST_MISSING")
    _add(argv, "--request", request)
    _add(argv, "--backend", _take(options, "backend"))
    authorized_by = _take(options, "authorized_by") or authorization_id
    _add(argv, "--authorized-by", authorized_by)
    _add(argv, "--run-out", _take(options, "run_out"))
    _add(argv, "--timeout-s", _take(options, "timeout_s"))
    return argv


def _build_funnel(options: dict[str, Any]) -> list[str]:
    argv = ["-m", CLI_MODULE, "funnel"]
    plan = _take(options, "plan", "plan_path", "spec", "spec_path")
    if plan is None or str(plan).strip() == "":
        raise JobError("PLAN_MISSING")
    _add(argv, "--plan", plan)
    _add(argv, "--execute", _take(options, "execute"))
    _add(argv, "--allow-bl", _take(options, "allow_bl"))
    _add(argv, "--authorization", _take(options, "authorization", "authorization_file"))
    return argv


_BUILDERS = {
    "screen": _build_screen,
    "pilot": _build_pilot,
    "portfolio": _build_portfolio,
    "bl_stage": _build_bl_stage,
    "bl_validate": _build_bl_validate,
    "funnel": _build_funnel,
}


def _env_tuple(value: Any) -> tuple[tuple[str, str], ...]:
    if not value:
        return ()
    if isinstance(value, Mapping):
        items = value.items()
    else:  # sequence of pairs
        items = value
    return tuple(sorted((str(k), str(v)) for k, v in items))


def build_job(kind: JobKind, **kwargs: Any) -> JobSpec:
    """Build the deterministic :class:`JobSpec` for ``kind``.

    ``cwd_rel`` (default ``"."``) and ``env`` are common options; every other keyword is the
    matching CLI flag with ``_`` for ``-`` (aliases accepted for ``spec``/``plan`` and
    ``case_dir``).  Unknown keywords are refused instead of silently dropped.
    """
    if kind not in JOB_KINDS:
        raise JobError("UNKNOWN_JOB_KIND", repr(kind))

    options = dict(kwargs)
    cwd_rel = str(options.pop("cwd_rel", "."))
    env = _env_tuple(options.pop("env", None))
    authorization_id = options.pop("authorization_id", None)

    if kind == "bl_solve" and (not isinstance(authorization_id, str)
                               or not authorization_id.strip()):
        # Contract section 6: refuse at build time, before any argv exists.
        raise JobError("AUTH_MISSING")

    if kind == "bl_solve":
        tail = _build_bl_solve(options, str(authorization_id))
    else:
        tail = _BUILDERS[kind](options)

    if options:
        raise JobError("UNKNOWN_ARG", ", ".join(sorted(options)))

    argv = (sys.executable, *tail)
    payload = {
        "argv": list(argv[1:]),
        "cwd_rel": cwd_rel,
        "env": [[k, v] for k, v in env],
        "kind": kind,
    }
    inputs_sha256 = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return JobSpec(
        kind=kind,
        argv=argv,
        cwd_rel=cwd_rel,
        env=env,
        inputs_sha256=inputs_sha256,
        lane="cpu",
        authorization_id=str(authorization_id) if authorization_id is not None else None,
    )
