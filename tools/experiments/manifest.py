"""Build and validate bo-study-v1.1 M2 pilot manifests (S11).

PREPARE ONLY.  This module never launches a solver, never writes into a live
``runs/``/``cache/``/``dataset/`` tree and never changes defaults, objective
versions, tolerances, weights or registrations.  It reads configs/briefs through
the normal loader, hashes inputs, reserves scratch output paths, and validates a
manifest against the *current* CLI parser and the frozen execution policy.

Manifest schema (schema_version 1)
----------------------------------
A compact overlay YAML carries the experiment design; :func:`build_manifest`
adds the resolved task identity, input hashes, computed aggregate budgets,
measured runtime sources and CLI command templates.  Sections:

``task``                config/brief paths + cohort references + comparability
``arms``                two treatments; each has seeds and CLI command templates
``budget``              per-arm-per-replicate caps + cost accounting + aggregate
``replicates``          explicit seed schedule and predeclared pairing
``verification_policy`` shared verify/audit rules; per-arm allocation
``stop_rules``          budget/deadline/cancel/pool/three-infrastructure stops
``lane_ownership``      GPU lane + the ``runs/.cpu.lane.lock`` CPU-lane rule
``runtime_estimates``   measured S3-style ledgers + arithmetic extrapolation
``analysis_plan``       endpoint, practical threshold, stopping rule, hypotheses
``rollback_and_adoption`` fail/no-gain rollback + owner adoption decisions
``outputs``             reserved scratch paths (nothing is created)
``no_default_changes``  explicit no-default/no-objective/no-registration block

The results parser mirrors the S3 cost/outcome semantics conceptually (it does
not import or edit the S3-owned ``tools/analysis/_common.py``).  A solver failure,
a cheap pre-BEM refusal and an unclassified row stay distinct and are never
turned into ``J = 1000`` or a silent pass.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # allow `python tools/experiments/manifest.py`
    sys.path.insert(0, str(REPO))

SCHEMA_VERSION = 1
PROTOCOL = "bo-study-v1.1"
ALLOWED_OUTPUT_PREFIX = ("scratch", "bo_m0", "s11")
LIVE_ROOTS = ("runs", "dataset", "dataset_cpu", "cache", "cache_cpu", "examples")

#: Protocol caps from BAYESIAN_STUDY_ORCHESTRATOR_SPEC section 4.
MAX_SCREEN_NEW_BEM = 18
MAX_VERIFY_NEW_BEM = 6
MAX_TOTAL_NEW_BEM = 24
MAX_CANDIDATE_ATTEMPTS = 120

#: Placeholders permitted in a CLI command template.  Values are substituted by
#: the future lane-aware runner, never by this tool.
ALLOWED_PLACEHOLDERS = {
    "config", "brief", "seed", "budget", "max_evals", "out",
    "runs_dir", "cache_dir", "dataset_dir", "screen_run_dir",
    "finalist_hashes", "audit_designs_csv",
}
_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")
_SHELL_META_RE = re.compile(r"[;&|`$<>\n\r]")

#: S3-style outcome classes.  Mirrored, not imported (S3 owns _common.py).
CHEAP_REFUSAL_KINDS = ("invalid_geometry", "invalid_envelope", "mesh_too_large")
SOLVER_FAILURE_KINDS = ("solve_failed",)
PIPELINE_FAILURE_KINDS = ("exception", "metrics_failed")
OUTCOME_CLASSES = ("valid", "cached_replay", "cheap_refusal", "solver_failure",
                   "pipeline_failure", "unknown_failure", "unknown")

TOP_LEVEL_KEYS = {
    "schema_version", "protocol", "manifest_id", "kind", "mode",
    "execution_authorized", "question", "task", "arms", "budget", "replicates",
    "verification_policy", "stop_rules", "lane_ownership", "runtime_estimates",
    "analysis_plan", "rollback_and_adoption", "outputs", "no_default_changes",
    "inputs_sha256", "resolved_task", "cli_commands", "generated_utc", "notes",
}

_REQUIRED_SECTIONS = ("task", "arms", "budget", "replicates", "verification_policy",
                      "stop_rules", "lane_ownership", "runtime_estimates",
                      "analysis_plan", "rollback_and_adoption", "outputs",
                      "no_default_changes")


# ----------------------------------------------------------------- small helpers


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_json(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_rel(path: Path, repo: Path = REPO) -> str:
    try:
        return Path(path).resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


def resolve_path(value: str, repo: Path = REPO) -> Path:
    p = Path(str(value)).expanduser()
    return p if p.is_absolute() else (Path(repo) / p)


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_ndjson(path: Path) -> list[dict]:
    out: list[dict] = []
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _finite(value: Any) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _is_inside(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _under_live_root(path: Path, repo: Path = REPO) -> bool:
    try:
        rel = Path(path).resolve().relative_to(Path(repo).resolve())
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] in LIVE_ROOTS


# ------------------------------------------------------------------- findings


@dataclass
class Finding:
    level: str          # "error" | "warning"
    code: str
    path: str
    message: str

    def as_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "path": self.path,
                "message": self.message}


@dataclass
class ValidationResult:
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    def add(self, level: str, code: str, path: str, message: str) -> None:
        f = Finding(level, code, path, message)
        (self.errors if level == "error" else self.warnings).append(f)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict:
        return {"ok": self.ok,
                "error_count": len(self.errors),
                "warning_count": len(self.warnings),
                "errors": [e.as_dict() for e in self.errors],
                "warnings": [w.as_dict() for w in self.warnings]}


# -------------------------------------------------------- results parser (S3-ish)


def failed_kind(row: dict) -> str:
    kind = row.get("kind")
    if isinstance(kind, str) and kind.strip():
        return kind.strip()
    err = row.get("error")
    if isinstance(err, str) and err.strip():
        return err.split(":", 1)[0].strip() or "unknown"
    return "unknown"


def classify_outcome(row: dict) -> str:
    """``valid | cheap_refusal | solver_failure | pipeline_failure | unknown_failure``.

    ``cached`` is handled by the caller: a cached replay is not a new attempt.
    An unrecognised failure kind is ``unknown_failure``, never ``valid`` and never
    a fabricated objective value.
    """
    if row.get("ok") is True:
        return "valid"
    kind = failed_kind(row)
    if kind in CHEAP_REFUSAL_KINDS:
        return "cheap_refusal"
    if kind in SOLVER_FAILURE_KINDS:
        return "solver_failure"
    if kind in PIPELINE_FAILURE_KINDS:
        return "pipeline_failure"
    return "unknown_failure"


def _seconds(row: dict, key: str) -> float | None:
    sec = row.get("seconds")
    if not isinstance(sec, dict):
        return None
    return _finite(sec.get(key))


def _parse_utc(value: Any) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def measure_run_cost(run_dir: Path) -> dict:
    """Measured S3-style cost ledger for one run dir (read-only).

    Deliberately mirrors ``tools/analysis/_common.cost_ledger`` concepts:
    index rows, cache hits, new attempts, valid evaluations, cheap pre-BEM
    refusals, solver/pipeline/unknown failures, observed/inferred BEM calls,
    BEM seconds, timing observations and elapsed seconds including failed work.
    """
    run_dir = Path(run_dir)
    rows = read_ndjson(run_dir / "search.ndjson")
    rj = read_json(run_dir / "run.json") or {}
    cache_hits = 0
    attempts = 0
    valid = 0
    categories = {"cheap_refusal": 0, "solver_failure": 0,
                  "pipeline_failure": 0, "unknown_failure": 0}
    kind_counts: dict[str, int] = {}
    attempt_seconds = 0.0
    valid_seconds = 0.0
    failed_seconds = 0.0
    cached_seconds = 0.0
    missing_seconds = 0
    bem_observed = 0
    bem_inferred = 0
    bem_seconds = 0.0
    timing = 0
    for row in rows:
        total = _seconds(row, "total")
        solve = _seconds(row, "solve")
        if row.get("cached") is True:
            cache_hits += 1
            cached_seconds += total or 0.0
            continue
        attempts += 1
        if total is None:
            missing_seconds += 1
        else:
            attempt_seconds += total
        cat = classify_outcome(row)
        if cat == "valid":
            valid += 1
            valid_seconds += total or 0.0
        else:
            categories[cat] += 1
            kind = failed_kind(row)
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
            failed_seconds += total or 0.0
        if solve is not None and solve > 0:
            bem_observed += 1
            bem_inferred += 1
            bem_seconds += solve
            timing += 1
        elif cat == "solver_failure":
            bem_inferred += 1
    start = _parse_utc(rj.get("started_utc"))
    end = _parse_utc(rj.get("finished_utc"))
    wall_span = (end - start) if start is not None and end is not None and end >= start else None
    return {
        "run_dir": repo_rel(run_dir),
        "run_id": run_dir.name,
        "config_name": rj.get("config_name") or (rj.get("config") or {}).get("name"),
        "cma_seed": rj.get("cma_seed"),
        "status": rj.get("status"),
        "index_rows": len(rows),
        "cache_hits": cache_hits,
        "attempts": attempts,
        "valid_evaluations": valid,
        "cheap_refusals": categories["cheap_refusal"],
        "solver_failures": categories["solver_failure"],
        "pipeline_failures": categories["pipeline_failure"],
        "unknown_failures": categories["unknown_failure"],
        "failure_kinds": dict(sorted(kind_counts.items())),
        "new_bem_calls_observed": bem_observed,
        "new_bem_calls_inferred": bem_inferred,
        "bem_seconds": bem_seconds,
        "timing_observations": timing,
        "elapsed_seconds": {
            "attempts_all_incl_failed_refused": attempt_seconds,
            "valid": valid_seconds,
            "failed_refused": failed_seconds,
            "cached_replay": cached_seconds,
            "recorded_total": attempt_seconds + cached_seconds,
            "wall_span": wall_span,
            "missing_seconds_attempts": missing_seconds,
        },
        "per_bem_seconds": (bem_seconds / bem_inferred) if bem_inferred else None,
        "per_attempt_seconds": (attempt_seconds / attempts) if attempts else None,
        "cost_label": ("wall_start_end" if wall_span is not None
                       else "accumulated_candidate_cost_no_wall_span"),
    }


def parse_run_outcomes(run_dir: Path) -> dict:
    """Parse a finished run into explicit outcomes; unknown stays unknown.

    ``verify_calls`` is only reported when rows carry ``mode == "verify"``;
    otherwise it is ``None`` with ``verify_calls_unknown: true``.  No failure is
    mapped to an objective value.
    """
    run_dir = Path(run_dir)
    rows = read_ndjson(run_dir / "search.ndjson")
    counts = {name: 0 for name in OUTCOME_CLASSES}
    unclassified: dict[str, int] = {}
    verify_rows = 0
    verify_mode_known = False
    for row in rows:
        if row.get("cached") is True:
            counts["cached_replay"] += 1
            continue
        cat = classify_outcome(row)
        counts[cat] += 1
        if cat == "unknown_failure":
            kind = failed_kind(row)
            unclassified[kind] = unclassified.get(kind, 0) + 1
        mode = row.get("mode")
        if isinstance(mode, str):
            verify_mode_known = True
            if mode == "verify":
                verify_rows += 1
    ledger = measure_run_cost(run_dir)
    return {
        "run_dir": repo_rel(run_dir),
        "outcomes": counts,
        "unknown_failure_kinds": dict(sorted(unclassified.items())),
        "representable_failures": True,
        "unknown_is_explicit": True,
        "failure_to_objective_mapping": "none",
        "verify_calls": verify_rows if verify_mode_known else None,
        "verify_calls_unknown": not verify_mode_known,
        "attempts": ledger["attempts"],
        "new_bem_calls": ledger["new_bem_calls_inferred"],
        "ledger": ledger,
    }


# ------------------------------------------------------------------- CLI schema


def cli_schema() -> dict:
    """Subcommand -> option strings/required/choices from the live CLI parser."""
    from hornlab_search.cli import build_parser

    parser = build_parser()
    sub_action = next(a for a in parser._actions if a.dest == "cmd")
    out: dict[str, dict] = {}
    choices = getattr(sub_action, "choices", None) or {}
    for name, sub in choices.items():
        options: dict[str, dict] = {}
        for action in sub._actions:
            for opt in action.option_strings:
                options[opt] = {
                    "dest": action.dest,
                    "required": bool(action.required),
                    "choices": list(action.choices) if action.choices else None,
                    "takes_value": action.nargs != 0,
                    "type": getattr(action.type, "__name__", None) if action.type else None,
                }
        groups = []
        for group in sub._mutually_exclusive_groups:
            # ``_group_actions`` is the real member set; for subparsers built with
            # ``parents=[common]`` the shared ``_actions`` list also contains the
            # parent options, so it must not be used here.
            members = getattr(group, "_group_actions", group._actions)
            groups.append([opt for a in members for opt in a.option_strings])
        out[name] = {"options": options, "exclusive_groups": groups}
    return out


def validate_argv(argv: Any, schema: dict, path: str) -> list[Finding]:
    """Validate one command template against the current CLI, no execution."""
    findings: list[Finding] = []
    if not isinstance(argv, list) or not argv or not all(isinstance(t, str) for t in argv):
        findings.append(Finding("error", "command_shape", path,
                                "argv must be a non-empty list of strings"))
        return findings
    for token in argv:
        if _SHELL_META_RE.search(token):
            findings.append(Finding("error", "command_shell_meta", path,
                                    f"shell metacharacters are not allowed: {token!r}"))
    for token in argv:
        for name in _PLACEHOLDER_RE.findall(token):
            if name not in ALLOWED_PLACEHOLDERS:
                findings.append(Finding("error", "command_placeholder", path,
                                        f"unknown placeholder {{{name}}}"))
    sub = argv[0]
    if sub not in schema:
        findings.append(Finding("error", "command_subcommand", path,
                                f"unknown CLI subcommand {sub!r}"))
        return findings
    spec = schema[sub]
    options = spec["options"]
    used: dict[str, str] = {}
    i = 1
    while i < len(argv):
        token = argv[i]
        if not token.startswith("-"):
            i += 1
            continue
        flag = token.split("=", 1)[0]
        if flag not in options:
            findings.append(Finding("error", "command_unknown_flag", path,
                                    f"{sub!r} has no flag {flag!r}"))
            i += 1
            continue
        used[options[flag]["dest"]] = flag
        if "=" in token:
            value = token.split("=", 1)[1]
            i += 1
        elif options[flag]["takes_value"] and i + 1 < len(argv):
            value = argv[i + 1]
            i += 2
        else:
            value = None
            i += 1
        choices = options[flag]["choices"]
        if choices and value is not None and "{" not in value and value not in choices:
            findings.append(Finding("error", "command_choice", path,
                                    f"{flag} must be one of {choices}, got {value!r}"))
        value_type = options[flag].get("type")
        if value_type in ("int", "float") and value is not None and "{" not in value:
            try:
                (int if value_type == "int" else float)(value)
            except ValueError:
                findings.append(Finding("error", "command_type", path,
                                        f"{flag} expects {value_type}, got {value!r}"))
    for opt, info in options.items():
        if info["required"] and info["dest"] not in used:
            findings.append(Finding("error", "command_required", path,
                                    f"{sub!r} requires {opt}"))
    for group in spec["exclusive_groups"]:
        hit = [opt for opt in group if any(options[o]["dest"] in used for o in group if o in options)]
        chosen = sorted({used[options[o]["dest"]] for o in group
                         if o in options and options[o]["dest"] in used})
        if len(chosen) > 1:
            findings.append(Finding("error", "command_exclusive", path,
                                    f"{sub!r} accepts only one of {group}, got {chosen}"))
        del hit
    return findings


# --------------------------------------------------------------- task identity


def _task_config(raw: dict) -> dict:
    """Config with per-run seed/budget removed (task identity, not schedule)."""
    cfg = copy.deepcopy(raw or {})
    search = cfg.get("search")
    if isinstance(search, dict):
        search.pop("seed", None)
        search.pop("budget", None)
    return cfg


def extract_task(config_path: Path, brief_path: Path) -> tuple[dict | None, list[Finding]]:
    """Resolve config+brief through the normal loader; hash the files read-only."""
    from hornlab_search.config import load_config

    findings: list[Finding] = []
    if not Path(config_path).is_file():
        findings.append(Finding("error", "task_config_missing", str(config_path),
                                "config file does not exist"))
        return None, findings
    if not Path(brief_path).is_file():
        findings.append(Finding("error", "task_brief_missing", str(brief_path),
                                "brief file does not exist"))
        return None, findings
    try:
        cfg = load_config(config_path, brief=brief_path)
    except Exception as exc:  # noqa: BLE001 - surface loader refusal verbatim
        findings.append(Finding("error", "task_resolution", str(config_path),
                                f"{type(exc).__name__}: {exc}"))
        return None, findings
    target = dict(cfg.target_raw or {})
    objective = dict(cfg.objective_params or {})
    brief = dict(cfg.brief or {})
    source = {
        "config_path": str(Path(config_path).resolve()),
        "config_rel": repo_rel(config_path),
        "config_sha256": sha256_file(config_path),
        "config_name": cfg.name,
        "family": cfg.family,
        "objective_version": int(cfg.objective_version),
        "brief_path": str(Path(brief_path).resolve()),
        "brief_rel": repo_rel(brief_path),
        "brief_sha256": sha256_file(brief_path),
        "brief_name": brief.get("name"),
        "resolved_target": target,
        "weights": dict(cfg.weights or {}),
        "objective": {
            "version": objective.get("version", cfg.objective_version),
            "tolerances": objective.get("tolerances"),
            "cov_narrow_ratio": objective.get("cov_narrow_ratio"),
            "cov_below_f0": objective.get("cov_below_f0"),
            "diag_reference": objective.get("diag_reference"),
        },
        "brief_summary": {
            "band_lo_hz": target.get("band_lo_hz"),
            "band_hi_hz": target.get("band_hi_hz"),
            "coverage_h_deg": target.get("coverage_h_deg"),
            "coverage_v_deg": target.get("coverage_v_deg"),
            "f0_hz": target.get("f0_hz"),
            "freq_weights": target.get("freq_weights"),
            "driver": brief.get("driver"),
            "envelope": brief.get("envelope"),
            "symmetry": brief.get("symmetry"),
            "source": brief.get("source"),
        },
        "task_config_hash": sha256_json(_task_config(cfg.raw)),
        "backend": getattr(cfg.solve, "backend", None),
        "searched_knobs": sorted(
            k for k, b in (cfg.raw.get("bounds") or {}).items()
            if not isinstance(b, dict) or b.get("search", True)),
        "configured_search": {
            "algorithm": getattr(cfg.search, "algorithm", None),
            "sigma0": getattr(cfg.search, "sigma0", None),
            "seed": getattr(cfg.search, "seed", None),
            "budget": getattr(cfg.search, "budget", None),
        },
    }
    return source, findings


def warm_source_identity(run_dir: Path, task: dict | None) -> dict:
    """Read-only identity check for a ``search.warm_start`` source run."""
    task = task or {}
    rj = read_json(Path(run_dir) / "run.json")
    if not isinstance(rj, dict):
        return {"run_dir": repo_rel(run_dir), "ok": False,
                "reason": "missing_or_unreadable_run_json"}
    raw = rj.get("config") if isinstance(rj.get("config"), dict) else {}
    objective = raw.get("objective") if isinstance(raw.get("objective"), dict) else {}
    version = int(objective.get("version", rj.get("objective_version", 1)) or 1)
    brief = raw.get("brief_file") or (raw.get("brief") if isinstance(raw.get("brief"), dict)
                                      else None)
    bounds = raw.get("bounds") if isinstance(raw.get("bounds"), dict) else {}
    searched = sorted(k for k, b in bounds.items()
                      if not isinstance(b, dict) or b.get("search", True))
    expected_brief = task.get("brief_rel") if task else None
    brief_ok = brief == expected_brief or (
        brief is not None and expected_brief is not None
        and Path(str(brief)).as_posix().endswith(Path(expected_brief).name))
    knobs_ok = (not task.get("searched_knobs")) or searched == list(task.get("searched_knobs") or [])
    ok = (version == int(task.get("objective_version", -1))
          and str(rj.get("family")) == str(task.get("family"))
          and brief_ok and knobs_ok)
    return {
        "run_dir": repo_rel(run_dir),
        "ok": bool(ok),
        "reason": None if ok else "warm_start_identity_mismatch",
        "searched_knobs_match_task": bool(knobs_ok),
        "run_id": Path(run_dir).name,
        "config_name": rj.get("config_name") or raw.get("name"),
        "family": rj.get("family"),
        "objective_version": version,
        "brief": brief,
        "brief_matches_task": bool(brief_ok),
        "searched_knobs": searched,
    }


# --------------------------------------------------------------- build a manifest


def _require_mapping(value: Any, path: str, findings: list[Finding]) -> dict:
    if not isinstance(value, dict):
        findings.append(Finding("error", "schema_mapping", path, "must be a mapping"))
        return {}
    return value


def _arm_policy_payload(arms: Any) -> list[dict]:
    return [{k: arm.get(k) for k in ("id", "policy", "cma_seeds", "verification", "command")}
            for arm in (arms or []) if isinstance(arm, dict)]


def _warm_source_payload(arms: Any) -> list[dict]:
    payload = []
    for arm in (arms or []):
        if not isinstance(arm, dict) or not isinstance(arm.get("warm_start"), dict):
            continue
        ws = arm["warm_start"]
        payload.append({
            "arm": arm.get("id"),
            "from_runs": ws.get("from_runs"),
            "top_k": ws.get("top_k"),
            "sigma_from_spread": ws.get("sigma_from_spread"),
            "allow_cross_brief": ws.get("allow_cross_brief"),
            "resolved_sources": [
                {"run_dir": s.get("run_dir"),
                 "run_json_sha256": s.get("run_json_sha256"),
                 "search_ndjson_sha256": s.get("search_ndjson_sha256"),
                 "ok": s.get("ok")}
                for s in (ws.get("resolved_sources") or []) if isinstance(s, dict)
            ],
        })
    return payload


def build_manifest(overlay: dict, repo: Path = REPO) -> tuple[dict, list[Finding]]:
    """Normalize a compact overlay into a hash-pinned manifest (no writes)."""
    findings: list[Finding] = []
    if not isinstance(overlay, dict):
        return {}, [Finding("error", "schema_root", "<overlay>", "overlay must be a mapping")]
    unknown = set(overlay) - TOP_LEVEL_KEYS
    if unknown:
        findings.append(Finding("error", "schema_unknown_keys", "<overlay>",
                                f"unknown top-level key(s): {sorted(unknown)}"))
    manifest = copy.deepcopy(overlay)
    manifest["kind"] = "manifest"
    manifest["schema_version"] = int(manifest.get("schema_version", SCHEMA_VERSION))
    manifest.setdefault("protocol", PROTOCOL)
    manifest["generated_utc"] = utc_now()

    # ---- task + brief resolution (read-only)
    task_in = _require_mapping(manifest.get("task"), "task", findings)
    config_path = resolve_path(task_in.get("config", ""), repo)
    brief_path = resolve_path(task_in.get("brief", ""), repo)
    task, task_findings = extract_task(config_path, brief_path)
    findings.extend(task_findings)
    manifest["resolved_task"] = task

    # ---- replicates + arm seeds
    reps = _require_mapping(manifest.get("replicates"), "replicates", findings)
    manifest["replicates"] = reps
    seeds = reps.get("seeds")
    if not isinstance(seeds, list) or not seeds or not all(isinstance(s, int) and not isinstance(s, bool) for s in seeds):
        findings.append(Finding("error", "replicates_seeds", "replicates.seeds",
                                "seeds must be a non-empty list of integers"))
        seeds = []
    elif len(set(seeds)) != len(seeds):
        findings.append(Finding("error", "replicates_duplicate_seed", "replicates.seeds",
                                "seed schedule contains duplicates"))
    manifest["replicates"]["seeds"] = list(seeds)

    arms = manifest.get("arms")
    if not isinstance(arms, list) or len(arms) != 2:
        findings.append(Finding("error", "arms_count", "arms",
                                "exactly two arms are required for a paired pilot"))
        arms = []
    for idx, arm in enumerate(arms):
        if not isinstance(arm, dict):
            findings.append(Finding("error", "arm_shape", f"arms[{idx}]", "must be a mapping"))
            continue
        arm_seeds = arm.get("cma_seeds")
        if isinstance(arm_seeds, list) and list(arm_seeds) != list(seeds):
            findings.append(Finding("error", "arm_seeds_mismatch", f"arms[{idx}].cma_seeds",
                                    "each arm's cma_seeds must equal replicates.seeds"))
        elif not isinstance(arm_seeds, list):
            findings.append(Finding("error", "arm_seeds_missing", f"arms[{idx}].cma_seeds",
                                    "cma_seeds is required"))
        warm = arm.get("warm_start")
        if isinstance(warm, dict):
            from_runs = warm.get("from_runs")
            if not isinstance(from_runs, list) or not from_runs:
                findings.append(Finding("error", "warm_start_sources", f"arms[{idx}].warm_start.from_runs",
                                        "must be a non-empty list of run directories"))
            else:
                identities = []
                for value in from_runs:
                    run_dir = resolve_path(value, repo)
                    info = warm_source_identity(run_dir, task or {})
                    identities.append(info)
                    if not info["ok"]:
                        findings.append(Finding("warning", "warm_source_unresolved",
                                                f"arms[{idx}].warm_start.from_runs",
                                                f"{value}: {info.get('reason')}"))
                    else:
                        rj_path = run_dir / "run.json"
                        nd_path = run_dir / "search.ndjson"
                        identities[-1]["run_json_sha256"] = (
                            sha256_file(rj_path) if rj_path.is_file() else None)
                        identities[-1]["search_ndjson_sha256"] = (
                            sha256_file(nd_path) if nd_path.is_file() else None)
                arm["warm_start"]["resolved_sources"] = identities
        overlay_cfg = arm.get("config_overlay")
        if isinstance(overlay_cfg, dict):
            unknown_overlay = set(overlay_cfg) - {"search"}
            if unknown_overlay:
                findings.append(Finding("error", "config_overlay_schema",
                                        f"arms[{idx}].config_overlay",
                                        f"unknown top-level key(s) {sorted(unknown_overlay)}"))
            search_overlay = overlay_cfg.get("search")
            if isinstance(search_overlay, dict):
                allowed_search = {"budget_counts", "max_attempts", "warm_start"}
                unknown_search = set(search_overlay) - allowed_search
                if unknown_search:
                    findings.append(Finding("error", "config_overlay_schema",
                                            f"arms[{idx}].config_overlay.search",
                                            f"unknown key(s) {sorted(unknown_search)} "
                                            f"(allowed: {sorted(allowed_search)})"))
                bc = search_overlay.get("budget_counts")
                if bc is not None and bc not in ("new", "valid"):
                    findings.append(Finding("error", "config_overlay_budget_counts",
                                            f"arms[{idx}].config_overlay.search.budget_counts",
                                            "must be 'new' or 'valid'"))
                ma = search_overlay.get("max_attempts")
                if ma is not None and (isinstance(ma, bool) or not isinstance(ma, int) or ma < 1):
                    findings.append(Finding("error", "config_overlay_max_attempts",
                                            f"arms[{idx}].config_overlay.search.max_attempts",
                                            "must be a positive integer"))
            ws = (overlay_cfg.get("search") or {}).get("warm_start")
            if ws is not None:
                allowed = {"from_runs", "top_k", "sigma_from_spread", "allow_cross_brief"}
                unknown_ws = set(ws) - allowed
                if unknown_ws:
                    findings.append(Finding("error", "warm_start_schema", f"arms[{idx}].config_overlay.search.warm_start",
                                            f"unknown key(s) {sorted(unknown_ws)} (allowed: {sorted(allowed)})"))
                if not isinstance(ws.get("from_runs"), list) or not ws.get("from_runs"):
                    findings.append(Finding("error", "warm_start_schema", f"arms[{idx}].config_overlay.search.warm_start.from_runs",
                                            "must be a non-empty list of run-directory paths"))
                top_k = ws.get("top_k", 10)
                if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
                    findings.append(Finding("error", "warm_start_schema", f"arms[{idx}].config_overlay.search.warm_start.top_k",
                                            "must be a positive integer"))
                for key in ("sigma_from_spread", "allow_cross_brief"):
                    if key in ws and not isinstance(ws[key], bool):
                        findings.append(Finding("error", "warm_start_schema",
                                                f"arms[{idx}].config_overlay.search.warm_start.{key}",
                                                "must be true or false"))
        # command templates
        commands = arm.get("commands")
        if not isinstance(commands, dict) or not commands:
            findings.append(Finding("error", "arm_commands_missing", f"arms[{idx}].commands",
                                    "at least a screen command template is required"))
        else:
            for name, command in commands.items():
                argv = command.get("argv") if isinstance(command, dict) else command
                if not isinstance(argv, list):
                    findings.append(Finding("error", "command_shape", f"arms[{idx}].commands.{name}",
                                            "argv must be a list"))
                    continue
                # Templates are checked here; validate_manifest checks them again
                # against the live parser.
                for token in argv:
                    for ph in _PLACEHOLDER_RE.findall(str(token)):
                        if ph not in ALLOWED_PLACEHOLDERS:
                            findings.append(Finding("error", "command_placeholder",
                                                    f"arms[{idx}].commands.{name}",
                                                    f"unknown placeholder {{{ph}}}"))

    # ---- measured runtime sources (mutable copy of the declared list)
    estimates = manifest.get("runtime_estimates")
    if isinstance(estimates, dict):
        measured = []
        for value in estimates.get("source_runs", []) or []:
            run_dir = resolve_path(value, repo)
            if not (run_dir / "search.ndjson").is_file():
                findings.append(Finding("warning", "runtime_source_missing", "runtime_estimates.source_runs",
                                        f"{value}: no search.ndjson; no measured estimate"))
                continue
            ledger = measure_run_cost(run_dir)
            ledger["source"] = "measured_local_run_dir"
            ledger["task_config_name"] = (
                (read_json(run_dir / "run.json") or {}).get("config_name"))
            measured.append(ledger)
        estimates["measured_sources"] = measured
        estimates["measured_source_count"] = len(measured)

    # ---- hashes of the declared schedule/budget/seed list
    inputs = {
        "config_path_sha256": sha256_json((task or {}).get("config_rel")),
        "brief_path_sha256": sha256_json((task or {}).get("brief_rel")),
        "config_sha256": (task or {}).get("config_sha256"),
        "brief_sha256": (task or {}).get("brief_sha256"),
        "task_config_hash": (task or {}).get("task_config_hash"),
        "seeds_sha256": sha256_json(seeds),
        "budget_sha256": sha256_json(manifest.get("budget")),
        "arm_policies_sha256": sha256_json(_arm_policy_payload(arms)),
        "warm_sources_sha256": sha256_json(_warm_source_payload(arms)),
    }
    task_block = manifest.get("task")
    if isinstance(task_block, dict):
        for key, value in task_block.items():
            if key in ("cohort",) and isinstance(value, dict):
                for ckey in ("census", "offline_scores"):
                    cpath = value.get(ckey)
                    if cpath:
                        inputs[f"cohort_{ckey}_sha256"] = sha256_file(resolve_path(cpath, repo))
    manifest["inputs_sha256"] = inputs

    # ---- explicit CLI command catalog (templates, never executed)
    catalog = []
    for idx, arm in enumerate(arms):
        if not isinstance(arm, dict):
            continue
        for name, command in (arm.get("commands") or {}).items():
            argv = command.get("argv") if isinstance(command, dict) else command
            catalog.append({"arm": arm.get("id", f"arm{idx}"), "name": name,
                            "argv": argv, "executed": False})
    manifest["cli_commands"] = catalog
    return manifest, findings


# ------------------------------------------------------------------- validation


def _check_schema(manifest: dict, result: ValidationResult) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        result.add("error", "schema_version", "schema_version",
                   f"expected {SCHEMA_VERSION}, got {manifest.get('schema_version')!r}")
    if manifest.get("protocol") != PROTOCOL:
        result.add("error", "protocol", "protocol", f"expected {PROTOCOL!r}")
    if manifest.get("mode") != "prepare_only":
        result.add("error", "mode", "mode", "pilot manifests must be mode: prepare_only")
    if manifest.get("execution_authorized") is not False:
        result.add("error", "execution_authorized", "execution_authorized",
                   "a prepared pilot must declare execution_authorized: false")
    missing = [s for s in _REQUIRED_SECTIONS if not manifest.get(s)]
    for section in missing:
        result.add("error", "section_missing", section, "required section is missing")
    if not isinstance(manifest.get("question"), str) or not manifest.get("question", "").strip():
        result.add("error", "question", "question", "a study question is required")


def _check_task(manifest: dict, repo: Path, result: ValidationResult) -> None:
    task = manifest.get("resolved_task")
    if not isinstance(task, dict):
        result.add("error", "task_unresolved", "resolved_task", "task could not be resolved")
        return
    task_in = manifest.get("task") if isinstance(manifest.get("task"), dict) else {}
    located: dict[str, Path] = {}
    for declared_key, resolved_key in (("config", "config_path"), ("brief", "brief_path")):
        declared = resolve_path(str(task_in.get(declared_key, "")), repo)
        recorded = str(task.get(resolved_key, ""))
        rel = task.get(f"{declared_key}_rel")
        # The repo-relative locator is the portable identity; the absolute path is provenance
        # from the building host/checkout. Re-verify by the locator so a manifest built in one
        # checkout validates in another, and require the recorded absolute path to end in that
        # locator (separator-agnostic) so the two cannot silently disagree.
        actual = resolve_path(str(rel), repo) if rel else Path(recorded)
        try:
            same = declared.resolve() == actual.resolve()
        except OSError:
            same = False
        if same and rel and not Path(str(rel)).is_absolute():
            rel_parts = PurePosixPath(str(rel)).parts
            rec_parts = PureWindowsPath(recorded).parts
            same = tuple(rec_parts[-len(rel_parts):]) == rel_parts
        if not same:
            result.add("error", "task_path_mismatch", f"resolved_task.{resolved_key}",
                       f"task.{declared_key} ({declared}) does not match {recorded}")
        located[declared_key] = actual
    config_path = located["config"]
    brief_path = located["brief"]
    for label, path, key in (("config", config_path, "config_sha256"),
                             ("brief", brief_path, "brief_sha256")):
        if not path.is_file():
            result.add("error", f"{label}_missing", f"resolved_task.{label}_path",
                       f"{path} does not exist")
            continue
        actual = sha256_file(path)
        if actual != task.get(key):
            result.add("error", f"{label}_hash_mismatch", f"resolved_task.{key}",
                       f"declared {task.get(key)} != actual {actual}")
    target = task.get("resolved_target") or {}
    for key in ("band_lo_hz", "band_hi_hz", "coverage_h_deg", "coverage_v_deg"):
        if target.get(key) is None:
            result.add("error", "task_target_incomplete", "resolved_task.resolved_target",
                       f"resolved target is missing {key}")
    if task.get("objective_version") != (task.get("objective") or {}).get("version"):
        result.add("error", "task_objective_version", "resolved_task",
                   "objective_version disagrees with the resolved objective block")
    source_caveat = (manifest.get("task") or {}).get("source_caveat_hz")
    if source_caveat is not None and not isinstance(source_caveat, (int, float)):
        result.add("error", "task_source_caveat", "task.source_caveat_hz",
                   "source_caveat_hz must be a number or null")
    # Comparability, when this is a second task.
    task_in = manifest.get("task") if isinstance(manifest.get("task"), dict) else {}
    comp = task_in.get("comparability")
    if comp is not None:
        if not isinstance(comp, dict):
            result.add("error", "comparability_shape", "task.comparability", "must be a mapping")
        else:
            if comp.get("pool_across_tasks") is not False:
                result.add("error", "comparability_pool", "task.comparability.pool_across_tasks",
                           "must be false; different physical tasks are never pooled")
            caves = comp.get("caveats")
            if not isinstance(caves, list) or not caves:
                result.add("error", "comparability_caveat", "task.comparability.caveats",
                           "explicit comparability caveats are required")


def _check_inputs(manifest: dict, result: ValidationResult) -> None:
    """Recompute the declared input hashes; a tampered/stale manifest is an error."""
    inputs = manifest.get("inputs_sha256")
    if not isinstance(inputs, dict):
        result.add("error", "inputs_hashes", "inputs_sha256", "a hash block is required")
        return
    task = manifest.get("resolved_task") or {}
    reps = manifest.get("replicates") or {}
    expected = {
        "config_path_sha256": sha256_json(task.get("config_rel")),
        "brief_path_sha256": sha256_json(task.get("brief_rel")),
        "config_sha256": task.get("config_sha256"),
        "brief_sha256": task.get("brief_sha256"),
        "task_config_hash": task.get("task_config_hash"),
        "seeds_sha256": sha256_json(reps.get("seeds")),
        "budget_sha256": sha256_json(manifest.get("budget")),
        "arm_policies_sha256": sha256_json(_arm_policy_payload(manifest.get("arms"))),
        "warm_sources_sha256": sha256_json(_warm_source_payload(manifest.get("arms"))),
    }
    for key, value in expected.items():
        if inputs.get(key) != value:
            result.add("error", "input_hash_mismatch", f"inputs_sha256.{key}",
                       f"declared {inputs.get(key)!r} != recomputed {value!r}")
    # Re-hash the referenced cohort files and warm-source run files when present.
    task_in = manifest.get("task") if isinstance(manifest.get("task"), dict) else {}
    cohort = task_in.get("cohort") if isinstance(task_in.get("cohort"), dict) else {}
    for ckey in ("census", "offline_scores"):
        if cohort.get(ckey):
            path = resolve_path(cohort[ckey])
            declared = inputs.get(f"cohort_{ckey}_sha256")
            if path.is_file() and declared is not None and sha256_file(path) != declared:
                result.add("error", "input_hash_mismatch",
                           f"inputs_sha256.cohort_{ckey}_sha256",
                           f"{cohort[ckey]} changed since the manifest was built")
    for idx, arm in enumerate(manifest.get("arms") or []):
        if not isinstance(arm, dict):
            continue
        ws = arm.get("warm_start") if isinstance(arm.get("warm_start"), dict) else {}
        for source in ws.get("resolved_sources") or []:
            if not isinstance(source, dict):
                continue
            run_dir = resolve_path(source.get("run_dir", ""))
            for fname, hash_key in (("run.json", "run_json_sha256"),
                                    ("search.ndjson", "search_ndjson_sha256")):
                path = run_dir / fname
                declared = source.get(hash_key)
                if not path.is_file():
                    result.add("warning", "warm_source_unavailable",
                               f"arms[{idx}].warm_start.resolved_sources",
                               f"{path} is unavailable; re-check before dispatch")
                elif declared is not None and sha256_file(path) != declared:
                    result.add("error", "input_hash_mismatch",
                               f"arms[{idx}].warm_start.resolved_sources.{hash_key}",
                               f"{path} changed since the manifest was built")


def _check_budget(manifest: dict, result: ValidationResult) -> None:
    budget = manifest.get("budget")
    if not isinstance(budget, dict):
        result.add("error", "budget_shape", "budget", "must be a mapping")
        return
    per = budget.get("per_arm_per_replicate")
    if not isinstance(per, dict):
        result.add("error", "budget_per_arm", "budget.per_arm_per_replicate", "required")
        return
    screen = per.get("screen_new_bem")
    verify = per.get("verify_new_bem")
    total = per.get("total_new_bem")
    attempts = per.get("candidate_attempts")
    for name, value in (("screen_new_bem", screen), ("verify_new_bem", verify),
                        ("total_new_bem", total), ("candidate_attempts", attempts)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            result.add("error", "budget_number", f"budget.per_arm_per_replicate.{name}",
                       "must be a non-negative integer")
    if all(isinstance(v, int) and not isinstance(v, bool) for v in (screen, verify, total, attempts)):
        if total != screen + verify:
            result.add("error", "budget_arithmetic", "budget.per_arm_per_replicate",
                       f"total_new_bem ({total}) must equal screen ({screen}) + verify ({verify})")
        if screen > MAX_SCREEN_NEW_BEM:
            result.add("error", "budget_screen_cap", "budget.per_arm_per_replicate.screen_new_bem",
                       f"screen cap is {MAX_SCREEN_NEW_BEM}")
        if verify > MAX_VERIFY_NEW_BEM:
            result.add("error", "budget_verify_cap", "budget.per_arm_per_replicate.verify_new_bem",
                       f"verify cap is {MAX_VERIFY_NEW_BEM}")
        if total > MAX_TOTAL_NEW_BEM:
            result.add("error", "budget_total_cap", "budget.per_arm_per_replicate.total_new_bem",
                       f"total new-BEM cap is {MAX_TOTAL_NEW_BEM}")
        if attempts > MAX_CANDIDATE_ATTEMPTS:
            result.add("error", "budget_attempt_cap", "budget.per_arm_per_replicate.candidate_attempts",
                       f"attempt cap is {MAX_CANDIDATE_ATTEMPTS}")
        if attempts < total:
            result.add("error", "budget_attempt_floor", "budget.per_arm_per_replicate.candidate_attempts",
                       "attempts must be >= total new BEM calls")
    cost = budget.get("cost_accounting")
    if not isinstance(cost, dict):
        result.add("error", "budget_cost_accounting", "budget.cost_accounting", "required")
    else:
        for key in ("attempts_include_cheap_refusals", "new_bem_calls_separate",
                    "verify_calls_separate", "retries_reserve_another_unit",
                    "unknown_attempt_retains_reservation", "cache_hits_not_new_bem"):
            if cost.get(key) is not True:
                result.add("error", "budget_cost_rule", f"budget.cost_accounting.{key}",
                           "must be true")
        if cost.get("cheap_refusal_is_not_a_bem_call") is not True:
            result.add("error", "budget_cost_rule",
                       "budget.cost_accounting.cheap_refusal_is_not_a_bem_call", "must be true")
    agg = budget.get("replication_aggregate")
    if not isinstance(agg, dict):
        result.add("error", "budget_aggregate", "budget.replication_aggregate", "required")
    else:
        n_pairs = agg.get("n_pairs")
        n_arms = agg.get("n_arms")
        if n_pairs != len(manifest.get("replicates", {}).get("seeds") or []):
            result.add("error", "budget_aggregate_pairs", "budget.replication_aggregate.n_pairs",
                       "must equal the declared seed schedule length")
        if n_arms != len(manifest.get("arms") or []):
            result.add("error", "budget_aggregate_arms", "budget.replication_aggregate.n_arms",
                       "must equal the number of arms")
        if all(isinstance(v, int) and not isinstance(v, bool) for v in (n_pairs, n_arms, screen, total, attempts)):
            expected = {"screen_new_bem": n_pairs * n_arms * screen,
                        "verify_new_bem": n_pairs * n_arms * verify,
                        "total_new_bem": n_pairs * n_arms * total,
                        "candidate_attempts": n_pairs * n_arms * attempts}
            for key, value in expected.items():
                if agg.get(key) != value:
                    result.add("error", "budget_aggregate_arithmetic",
                               f"budget.replication_aggregate.{key}",
                               f"expected {value}, got {agg.get(key)}")
        if agg.get("planning_only") is not True:
            result.add("error", "budget_aggregate_authorization",
                       "budget.replication_aggregate.planning_only", "must be true")
        if agg.get("execution_authorized") is not False:
            result.add("error", "budget_aggregate_authorization",
                       "budget.replication_aggregate.execution_authorized", "must be false")


def _check_replicates(manifest: dict, result: ValidationResult) -> None:
    reps = manifest.get("replicates")
    if not isinstance(reps, dict):
        result.add("error", "replicates_shape", "replicates", "must be a mapping")
        return
    seeds = reps.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        result.add("error", "replicates_seeds", "replicates.seeds", "required")
    pairing = reps.get("pairing")
    if not isinstance(pairing, dict):
        result.add("error", "pairing_missing", "replicates.pairing", "required")
    else:
        required_true = ("predeclared", "same_seed_is_not_shared_candidates",
                         "resume_segments_are_one_replicate")
        for key in required_true:
            if pairing.get(key) is not True:
                result.add("error", "pairing_rule", f"replicates.pairing.{key}", "must be true")
        if pairing.get("difference_definition") != "d = A - B (negative => A has lower J / is better)":
            result.add("error", "pairing_difference", "replicates.pairing.difference_definition",
                       "must declare d = A - B and the direction")
        if not isinstance(pairing.get("method"), str) or "seed" not in pairing.get("method", ""):
            result.add("error", "pairing_method", "replicates.pairing.method",
                       "pairing must be explicitly by seed index")
    order = reps.get("run_order")
    if not isinstance(order, dict) or not isinstance(order.get("note"), str):
        result.add("error", "run_order", "replicates.run_order",
                   "an alternate/randomize order note is required")
    arms = manifest.get("arms") or []
    for idx, arm in enumerate(arms):
        if isinstance(arm, dict) and list(arm.get("cma_seeds") or []) != list(seeds or []):
            result.add("error", "arm_seeds_mismatch", f"arms[{idx}].cma_seeds",
                       "must equal replicates.seeds exactly")


def _check_verification(manifest: dict, result: ValidationResult) -> None:
    shared = manifest.get("verification_policy")
    if not isinstance(shared, dict):
        result.add("error", "verification_policy", "verification_policy", "required")
        return
    if shared.get("verify_new_bem_cap") != MAX_VERIFY_NEW_BEM:
        result.add("error", "verification_cap", "verification_policy.verify_new_bem_cap",
                   f"must be {MAX_VERIFY_NEW_BEM}")
    if not isinstance(shared.get("audit_rng_seed"), int):
        result.add("error", "verification_audit_seed", "verification_policy.audit_rng_seed",
                   "a reserved integer audit RNG seed is required")
    for key in ("exclude_duplicates_and_already_verified",):
        if shared.get(key) is not True:
            result.add("error", "verification_rule", f"verification_policy.{key}", "must be true")
    if not isinstance(shared.get("shortfall"), str) or "fewer" not in shared.get("shortfall", "").lower():
        result.add("error", "verification_shortfall", "verification_policy.shortfall",
                   "must say verify fewer rather than duplicate/substitute")
    for idx, arm in enumerate(manifest.get("arms") or []):
        if not isinstance(arm, dict):
            continue
        ver = arm.get("verification")
        if not isinstance(ver, dict):
            result.add("error", "arm_verification", f"arms[{idx}].verification", "required")
            continue
        finalists = ver.get("finalist_count")
        audit = ver.get("audit_count")
        if not isinstance(finalists, int) or not isinstance(audit, int):
            result.add("error", "arm_verification_counts", f"arms[{idx}].verification",
                       "finalist_count and audit_count must be integers")
            continue
        if finalists < 0 or audit < 0 or finalists + audit != MAX_VERIFY_NEW_BEM:
            result.add("error", "arm_verification_alloc", f"arms[{idx}].verification",
                       f"finalist_count + audit_count must equal {MAX_VERIFY_NEW_BEM}")
        if finalists > 4:
            result.add("error", "arm_verification_finalists", f"arms[{idx}].verification.finalist_count",
                       "at most four finalists are permitted")


def _check_stops(manifest: dict, result: ValidationResult) -> None:
    stops = manifest.get("stop_rules")
    if not isinstance(stops, dict):
        result.add("error", "stop_rules", "stop_rules", "must be a mapping")
        return
    required = ("budget", "deadline", "cancellation", "pool_exhaustion",
                "infrastructure_failures")
    for key in required:
        block = stops.get(key)
        if not isinstance(block, dict) or block.get("enabled") is not True:
            result.add("error", "stop_rule", f"stop_rules.{key}",
                       "required stop rule must be present and enabled")
    deadline = stops.get("deadline") or {}
    if deadline.get("deadline_required") is not True:
        result.add("error", "deadline_required", "stop_rules.deadline.deadline_required",
                   "a wall deadline is required before real scheduling")
    if deadline.get("deadline_utc") is None and deadline.get("placeholder") is not True:
        result.add("error", "deadline_placeholder", "stop_rules.deadline",
                   "a null deadline is allowed only when marked as a placeholder")
    infra = stops.get("infrastructure_failures") or {}
    if infra.get("consecutive_threshold") != 3:
        result.add("error", "stop_infra_threshold",
                   "stop_rules.infrastructure_failures.consecutive_threshold",
                   "must be three consecutive infrastructure/solver-host failures")


def _check_lanes(manifest: dict, repo: Path, result: ValidationResult) -> None:
    lanes = manifest.get("lane_ownership")
    if not isinstance(lanes, dict):
        result.add("error", "lane_ownership", "lane_ownership", "must be a mapping")
        return
    gpu = lanes.get("gpu")
    if not isinstance(gpu, dict):
        result.add("error", "lane_gpu", "lane_ownership.gpu", "required")
    else:
        if gpu.get("backend") != "beat_cuda":
            result.add("error", "lane_gpu_backend", "lane_ownership.gpu.backend",
                       "primary lane must be beat_cuda")
        if gpu.get("one_cuda_solve_at_a_time") is not True:
            result.add("error", "lane_gpu_serial", "lane_ownership.gpu.one_cuda_solve_at_a_time",
                       "must be true")
        if gpu.get("no_cross_lane_cleanup") is not True:
            result.add("error", "lane_gpu_cleanup", "lane_ownership.gpu.no_cross_lane_cleanup",
                       "must be true")
    cpu = lanes.get("cpu_if_beat_cpu")
    if not isinstance(cpu, dict):
        result.add("error", "lane_cpu", "lane_ownership.cpu_if_beat_cpu", "required")
    else:
        text = " ".join(str(cpu.get(k, "")) for k in ("lock", "rule", "worker_dir"))
        if ".cpu.lane.lock" not in text:
            result.add("error", "lane_cpu_lock", "lane_ownership.cpu_if_beat_cpu",
                       "must cite the runs/.cpu.lane.lock rule")
        if cpu.get("backend") != "beat_cpu":
            result.add("error", "lane_cpu_backend", "lane_ownership.cpu_if_beat_cpu.backend",
                       "CPU lane must be beat_cpu")
    # The resolved config's backend decides which lane must be held first.
    task = manifest.get("resolved_task") if isinstance(manifest.get("resolved_task"), dict) else {}
    task_block = manifest.get("task") if isinstance(manifest.get("task"), dict) else {}
    declared_backend = task_block.get("backend")
    configured_backend = task.get("backend")
    if declared_backend is not None and configured_backend is not None \
            and declared_backend != configured_backend:
        result.add("error", "lane_backend_mismatch", "task.backend",
                   f"declared {declared_backend!r} != resolved {configured_backend!r}")
    backend = configured_backend if configured_backend is not None else declared_backend
    if backend is not None and backend not in ("beat_cuda", "beat_cpu", "bempp_cpu",
                                               "beat_metal"):
        result.add("error", "lane_backend", "task.backend", f"unknown backend {backend!r}")


def _check_no_defaults(manifest: dict, result: ValidationResult) -> None:
    block = manifest.get("no_default_changes")
    if not isinstance(block, dict):
        result.add("error", "no_default_changes", "no_default_changes", "must be a mapping")
        return
    for key in ("production_defaults", "objective_version", "score_tolerances_or_weights",
                "registration", "cache_or_dataset_behavior", "gui_or_cli_behavior"):
        if block.get(key) is not False:
            result.add("error", "no_default_flag", f"no_default_changes.{key}", "must be false")
    statement = str(block.get("statement", "")).lower()
    for word in ("default", "objective", "registration"):
        if word not in statement:
            result.add("error", "no_default_statement", "no_default_changes.statement",
                       f"statement must mention {word!r}")
    if block.get("speedup_claimed") is not False:
        result.add("error", "no_speedup_claim", "no_default_changes.speedup_claimed",
                   "a prepared pilot must not claim a speedup")


def _check_outputs(manifest: dict, repo: Path, result: ValidationResult) -> None:
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict):
        result.add("error", "outputs", "outputs", "must be a mapping")
        return
    root_value = outputs.get("reserved_root")
    if not isinstance(root_value, str) or not root_value.strip():
        result.add("error", "outputs_root", "outputs.reserved_root", "required")
        return
    root = resolve_path(root_value, repo)
    prefix = Path(repo) / Path(*ALLOWED_OUTPUT_PREFIX)
    if not _is_inside(root, prefix):
        result.add("error", "outputs_containment", "outputs.reserved_root",
                   f"must be inside {prefix.as_posix()}")
    if _under_live_root(root, repo):
        result.add("error", "outputs_live_root", "outputs.reserved_root",
                   "must not point at a live runs/cache/dataset/examples root")
    if outputs.get("creates_nothing") is not True:
        result.add("error", "outputs_no_write", "outputs.creates_nothing",
                   "preparation must create nothing (creates_nothing: true)")
    reserved = outputs.get("reserved")
    if not isinstance(reserved, list) or not reserved:
        result.add("error", "outputs_reserved", "outputs.reserved", "a non-empty list is required")
        return
    for value in reserved:
        if not isinstance(value, str):
            result.add("error", "outputs_entry", "outputs.reserved", "entries must be strings")
            continue
        # Entries may use {out}; resolve the placeholder to the reserved root.
        candidate = value.replace("{out}", root.as_posix())
        path = resolve_path(candidate, repo)
        if not _is_inside(path, root) and not _is_inside(path, prefix):
            result.add("error", "outputs_entry_containment", "outputs.reserved",
                       f"{value!r} is outside the reserved scratch root")
        if _under_live_root(path, repo) or ".." in Path(candidate).parts:
            result.add("error", "outputs_live_root", "outputs.reserved",
                       f"{value!r} points at a live or escaping path")


def _check_analysis(manifest: dict, result: ValidationResult) -> None:
    plan = manifest.get("analysis_plan")
    if not isinstance(plan, dict):
        result.add("error", "analysis_plan", "analysis_plan", "must be a mapping")
        return
    if not isinstance(plan.get("primary_endpoint"), str) or not plan.get("primary_endpoint", "").strip():
        result.add("error", "analysis_endpoint", "analysis_plan.primary_endpoint", "required")
    threshold = plan.get("practical_improvement")
    if not isinstance(threshold, dict):
        result.add("error", "analysis_threshold", "analysis_plan.practical_improvement", "required")
    else:
        if threshold.get("direction") not in ("lower_is_better", "higher_is_better",
                                              "decision_stability"):
            result.add("error", "analysis_direction", "analysis_plan.practical_improvement.direction",
                       "declare the metric direction explicitly")
        if not (isinstance(threshold.get("delta"), (int, float))
                or isinstance(threshold.get("criterion"), str)):
            result.add("error", "analysis_threshold_value", "analysis_plan.practical_improvement",
                       "declare a numeric delta or an explicit criterion")
        if threshold.get("label") != "declared_practical_threshold_not_a_speedup_claim":
            result.add("error", "analysis_threshold_label",
                       "analysis_plan.practical_improvement.label",
                       "must be labeled declared_practical_threshold_not_a_speedup_claim")
    rule = plan.get("stopping_rule")
    lowered = str(rule).lower()
    for word in ("paired", "ci", "censoring"):
        if word not in lowered:
            result.add("error", "analysis_stopping_rule", "analysis_plan.stopping_rule",
                       f"stopping rule must mention {word!r} (pilot paired CI with censoring)")
    hyps = plan.get("hypotheses")
    if not isinstance(hyps, list) or not hyps:
        result.add("error", "analysis_hypotheses", "analysis_plan.hypotheses",
                   "at least one labeled hypothesis is required")
    else:
        for idx, hyp in enumerate(hyps):
            if not isinstance(hyp, dict):
                result.add("error", "analysis_hypothesis_shape",
                           f"analysis_plan.hypotheses[{idx}]", "must be a mapping")
                continue
            if hyp.get("label") != "hypothesis":
                result.add("error", "analysis_hypothesis_label",
                           f"analysis_plan.hypotheses[{idx}].label",
                           "expected outcomes must be labeled hypothesis")
            if not isinstance(hyp.get("falsified_if"), str):
                result.add("error", "analysis_hypothesis_falsifier",
                           f"analysis_plan.hypotheses[{idx}].falsified_if", "required")
    parser = plan.get("results_parser")
    if not isinstance(parser, dict):
        result.add("error", "analysis_results_parser", "analysis_plan.results_parser", "required")
    else:
        classes = set(parser.get("outcome_classes") or [])
        for required in ("valid", "cheap_refusal", "solver_failure",
                         "pipeline_failure", "unknown"):
            if required not in classes:
                result.add("error", "results_parser_classes",
                           "analysis_plan.results_parser.outcome_classes",
                           f"missing required class {required!r}")
        if parser.get("failure_to_objective_mapping") != "none":
            result.add("error", "results_parser_failure_mapping",
                       "analysis_plan.results_parser.failure_to_objective_mapping",
                       "failures must never be mapped to an objective value")
        if parser.get("unknown_representation") != "unknown":
            result.add("error", "results_parser_unknown",
                       "analysis_plan.results_parser.unknown_representation",
                       "unknown must stay explicit")


def _check_rollback(manifest: dict, result: ValidationResult) -> None:
    block = manifest.get("rollback_and_adoption")
    if not isinstance(block, dict):
        result.add("error", "rollback_block", "rollback_and_adoption", "must be a mapping")
        return
    rollback = block.get("fail_or_no_gain_rollback")
    if not isinstance(rollback, list) or not rollback:
        result.add("error", "rollback_items", "rollback_and_adoption.fail_or_no_gain_rollback",
                   "enumeration is required")
    decisions = block.get("owner_adoption_decisions")
    if not isinstance(decisions, list) or not decisions:
        result.add("error", "adoption_decisions", "rollback_and_adoption.owner_adoption_decisions",
                   "enumeration is required")
    else:
        for idx, decision in enumerate(decisions):
            if not isinstance(decision, dict):
                result.add("error", "adoption_shape",
                           f"rollback_and_adoption.owner_adoption_decisions[{idx}]",
                           "must be a mapping")
                continue
            for key in ("id", "decision", "adopt_if", "otherwise"):
                if not decision.get(key):
                    result.add("error", "adoption_field",
                               f"rollback_and_adoption.owner_adoption_decisions[{idx}].{key}",
                               "required")


def _check_runtime(manifest: dict, result: ValidationResult) -> None:
    est = manifest.get("runtime_estimates")
    if not isinstance(est, dict):
        result.add("error", "runtime_estimates", "runtime_estimates", "must be a mapping")
        return
    if est.get("speedup_claimed") is not False:
        result.add("error", "runtime_speedup", "runtime_estimates.speedup_claimed",
                   "must be false: this tool reports measured costs, not speedups")
    measured = est.get("measured_sources")
    if not isinstance(measured, list) or not measured:
        result.add("error", "runtime_measured_sources", "runtime_estimates.measured_sources",
                   "at least one measured local ledger is required")
    else:
        for idx, source in enumerate(measured):
            if not isinstance(source, dict) or source.get("source") != "measured_local_run_dir":
                result.add("error", "runtime_source_class",
                           f"runtime_estimates.measured_sources[{idx}]",
                           "must be a measured local run ledger")
                continue
            if not isinstance(source.get("new_bem_calls_inferred"), int):
                result.add("error", "runtime_source_ledger",
                           f"runtime_estimates.measured_sources[{idx}]",
                           "missing BEM call count")
    caves = est.get("caveats")
    if not isinstance(caves, list) or not caves:
        result.add("error", "runtime_caveats", "runtime_estimates.caveats", "required")
    block = est.get("block_estimate")
    if not isinstance(block, dict):
        result.add("error", "runtime_block", "runtime_estimates.block_estimate", "required")
    else:
        for key in ("basis", "screen_new_bem", "verify_new_bem"):
            if key not in block:
                result.add("error", "runtime_block_field",
                           f"runtime_estimates.block_estimate.{key}", "required")
    if not isinstance(est.get("method"), str) or "measured" not in est.get("method", "").lower():
        result.add("error", "runtime_method", "runtime_estimates.method",
                   "state that the estimate comes from measured logs")


def _check_commands(manifest: dict, result: ValidationResult) -> None:
    try:
        schema = cli_schema()
    except Exception as exc:  # noqa: BLE001 - the CLI is the authority
        result.add("error", "cli_schema_unavailable", "cli_commands",
                   f"cannot introspect the current CLI: {type(exc).__name__}: {exc}")
        return
    commands = manifest.get("cli_commands")
    if not isinstance(commands, list) or not commands:
        result.add("error", "cli_commands", "cli_commands", "required")
        return
    seen: set[tuple[str, str]] = set()
    for idx, command in enumerate(commands):
        if not isinstance(command, dict):
            result.add("error", "cli_command_shape", f"cli_commands[{idx}]", "must be a mapping")
            continue
        key = (str(command.get("arm")), str(command.get("name")))
        if key in seen:
            result.add("error", "cli_command_duplicate", f"cli_commands[{idx}]",
                       f"duplicate command {key}")
        seen.add(key)
        if command.get("executed") is not False:
            result.add("error", "cli_command_executed", f"cli_commands[{idx}].executed",
                       "a prepared manifest never executes commands")
        path = f"cli_commands[{idx}]({key[0]}/{key[1]})"
        result.errors.extend(validate_argv(command.get("argv"), schema, path))
    # Every arm must expose a screen/search and both verify templates.
    for idx, arm in enumerate(manifest.get("arms") or []):
        commands_map = arm.get("commands") if isinstance(arm, dict) else None
        if not isinstance(commands_map, dict):
            continue
        for required in ("search", "verify_finalists", "verify_audit"):
            if required not in commands_map:
                result.add("error", "arm_command_missing",
                           f"arms[{idx}].commands.{required}", "required template is missing")


def validate_manifest(manifest: dict, repo: Path = REPO, *, strict: bool = False) -> ValidationResult:
    """Validate a built manifest without executing or writing anything."""
    result = ValidationResult()
    if not isinstance(manifest, dict):
        result.add("error", "manifest_shape", "<manifest>", "must be a mapping")
        return result
    unknown = set(manifest) - TOP_LEVEL_KEYS
    if unknown:
        result.add("error", "schema_unknown_keys", "<manifest>",
                   f"unknown top-level key(s): {sorted(unknown)}")
    _check_schema(manifest, result)
    _check_task(manifest, repo, result)
    _check_inputs(manifest, result)
    _check_budget(manifest, result)
    _check_replicates(manifest, result)
    _check_verification(manifest, result)
    _check_stops(manifest, result)
    _check_lanes(manifest, repo, result)
    _check_no_defaults(manifest, result)
    _check_outputs(manifest, repo, result)
    _check_analysis(manifest, result)
    _check_rollback(manifest, result)
    _check_runtime(manifest, result)
    _check_commands(manifest, result)
    if strict:
        result.errors.extend(result.warnings)
        result.warnings = []
    return result


# ----------------------------------------------------------------------- CLI


def _load_overlay(path: Path) -> Any:
    if not Path(path).is_file():
        raise SystemExit(f"ERROR: overlay not found: {path}")
    try:
        return read_yaml(path)
    except yaml.YAMLError as exc:
        raise SystemExit(f"ERROR: invalid YAML in {path}: {exc}") from None


def _print_findings(result: ValidationResult) -> None:
    for finding in result.errors + result.warnings:
        print(f"{finding.level.upper():7s} {finding.code:32s} {finding.path}: {finding.message}")
    print(f"SUMMARY errors={len(result.errors)} warnings={len(result.warnings)} "
          f"ok={str(result.ok).lower()}")


def _write_json(path: Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n",
                    encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Build/validate bo-study-v1.1 M2 pilot manifests (prepare only; "
                    "never solves or edits live data).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build a normalized manifest from an overlay YAML")
    b.add_argument("--overlay", required=True, type=Path)
    b.add_argument("--out", type=Path, default=None,
                   help="write the built manifest here (scratch only)")
    b.add_argument("--dry-run", action="store_true",
                   help="build and print; write nothing")
    b.add_argument("--strict", action="store_true",
                   help="promote build warnings to errors")
    b.add_argument("--json", action="store_true", help="print the built manifest as JSON")
    v = sub.add_parser("validate", help="validate an overlay or a built manifest")
    src = v.add_mutually_exclusive_group(required=True)
    src.add_argument("--overlay", type=Path)
    src.add_argument("--manifest", type=Path)
    v.add_argument("--strict", action="store_true", help="promote warnings to errors")
    v.add_argument("--json", action="store_true", help="print the validation result as JSON")
    v.add_argument("--json-out", type=Path, default=None,
                   help="write the validation result here (scratch only)")
    args = ap.parse_args(argv)

    if args.cmd == "build":
        overlay = _load_overlay(args.overlay)
        manifest, findings = build_manifest(overlay)
        result = validate_manifest(manifest, strict=args.strict)
        # combine build findings with validation findings
        for finding in findings:
            result.add(finding.level, finding.code, finding.path, finding.message)
        if args.strict:
            result.errors.extend(result.warnings)
            result.warnings = []
        if args.json:
            print(json.dumps(manifest, indent=1, sort_keys=True, default=str))
        _print_findings(result)
        if args.out is not None and result.ok and not args.dry_run:
            _write_json(args.out, manifest)
            print(f"WROTE {args.out}")
        elif args.out is not None and args.dry_run:
            print(f"DRY-RUN: not writing {args.out}")
        return 0 if result.ok else 2

    if args.overlay is not None:
        overlay = _load_overlay(args.overlay)
        manifest, findings = build_manifest(overlay)
        result = validate_manifest(manifest, strict=args.strict)
        for finding in findings:
            result.add(finding.level, finding.code, finding.path, finding.message)
        if args.strict:
            result.errors.extend(result.warnings)
            result.warnings = []
    else:
        manifest = read_json(args.manifest)
        if manifest is None:
            raise SystemExit(f"ERROR: cannot read manifest: {args.manifest}")
        result = validate_manifest(manifest, strict=args.strict)
    if args.json:
        print(json.dumps(result.as_dict(), indent=1, sort_keys=True))
    if args.json_out is not None:
        _write_json(args.json_out, result.as_dict())
        print(f"WROTE {args.json_out}")
    _print_findings(result)
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
