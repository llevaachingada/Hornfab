"""P1c: controlled, pre-registered matched-benchmark orchestrator (advisory, offline).

Two subcommands, neither of which dispatches GPU work::

    python tools/analysis/benchmark_orchestrator.py plan --spec <yaml> --out <dir>
    python tools/analysis/benchmark_orchestrator.py report --plan <plan.json> \
        --results <arm>=<run_dir>[,<run_dir>...] [--results ...] --out <dir>

``plan`` validates a ``benchmark-plan-v1`` spec, loads the real base config and
brief, derives one YAML per arm under ``<out>/arms/`` applying only the declared
search overrides, proves the non-search task identity is equal across arms, and
writes ``benchmark_plan.json`` / ``benchmark_plan.md`` with an explicit
``dispatched: false`` advisory block and the exact launch commands as *text*.

``report`` loads completed run directories, enforces the declared paired seed set
exactly once per arm, refuses any identity mismatch (task/brief/family/objective/
mesh/solve), verifies the information-parity declarations, and delegates every
predeclared pair to :func:`ab_compare.analyse`.  It adds per-arm typed cost
ledgers, best-so-far curves and floor-aware verdict labels.  A decisive
superiority claim is refused when the spec declares no ``floor_j``.

Read-only inputs: ``_common`` and ``ab_compare`` are imported, never modified.
Never writes into ``runs/``, ``examples/``, ``docs/`` or the input spec directory.
Schema: ``tools/analysis/schema.md`` § benchmark_plan / benchmark_report.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from _common import (REPO, best_so_far_curve, bounds_of, cost_ledger, fail, load_run,
                     read_json, replicate_summary, sum_cost_ledgers, write_report)

# ``hornlab_search`` is the canonical package; tools/analysis is not a package and the
# tests load this module by file path, so make the repo importable explicitly.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.config import (ConfigError, QD_DESCRIPTORS, load_brief,  # noqa: E402
                                   load_config)

import ab_compare  # noqa: E402  (sibling tool; imported read-only)

PLAN_SCHEMA = "benchmark-plan-v1"
REPORT_SCHEMA = "benchmark-report-v1"
TOOL_PLAN = "benchmark_plan"
TOOL_REPORT = "benchmark_report"

#: Canonical benchmark treatments.  ``config_algorithm`` is what the derived YAML
#: writes to ``search.algorithm``; ``None`` means "leave the base config's algorithm
#: alone" (BO/TuRBO arms are launched through the study runner, not ``search``).
ALGORITHMS: dict[str, dict[str, Any]] = {
    "cma": {"family": "cma", "config_algorithm": "cma", "warm": None},
    "cma_warm_mean": {"family": "cma", "config_algorithm": "cma", "warm": "mean"},
    "cma_warm_covariance": {"family": "cma", "config_algorithm": "cma",
                            "warm": "covariance"},
    "bo_scalar": {"family": "bo", "config_algorithm": None, "policy": "scalar"},
    "turbo": {"family": "bo", "config_algorithm": None, "policy": "turbo"},
}

#: Accepted spellings of the canonical treatment names.
ALGORITHM_ALIASES = {
    "cold_cma": "cma",
    "cma_cold": "cma",
    "mean_warm_cma": "cma_warm_mean",
    "warm_mean_cma": "cma_warm_mean",
    "covariance_cma": "cma_warm_covariance",
    "warm_covariance_cma": "cma_warm_covariance",
    "scalar_bo": "bo_scalar",
    "bo": "bo_scalar",
}

OVERRIDE_KEYS = ("sigma0", "bounds", "seed", "algorithm", "policy", "warm_start",
                 "restarts", "qd")
ARM_KEYS = {"id", "algorithm", "base", "overrides", "expected_information", "label"}
SPEC_KEYS = {"schema", "task", "description", "notes", "base_config", "brief", "family",
             "objective_version", "seeds", "seed_count", "seed_base", "budget",
             "cost_budget_s", "target_j", "practical_delta", "floor_j",
             "information_parity", "arms", "pairs"}
WARM_START_KEYS = {"from_runs", "top_k", "sigma_from_spread", "allow_cross_brief",
                   "covariance"}
COVARIANCE_KEYS = {"blend", "eig_floor", "eig_cap", "max_dim", "scale_sigma"}
RESTART_KEYS = {"mode", "max"}
QD_KEYS = {"descriptor_h", "descriptor_v", "bins_h", "bins_v", "maes"}
FORBIDDEN_OUTPUT_PARENTS = ("examples", "runs", "docs")


# ------------------------------------------------------------------ helpers


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def _sha16(obj) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()[:16]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _is_number(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(float(value)))


def _brief_payload(brief: dict) -> dict:
    """A brief without its source ``path`` key; the content that defines task identity."""
    return {str(k): v for k, v in (brief or {}).items() if k != "path"}


def _brief_identity(brief: dict | None) -> str:
    return _sha16(_brief_payload(brief or {}))


def _config_identity(raw: dict, brief: dict | None = None) -> dict:
    """Task/brief/family/objective/mesh/solve identity of a config (never search/bounds).

    Search treatment (``search.*``, ``bounds``) is deliberately excluded: a matched
    benchmark expects arms to differ there and nowhere else.
    """
    raw = raw or {}
    b = brief if brief is not None else (
        raw.get("brief") if isinstance(raw.get("brief"), dict) else {})
    objective = raw.get("objective") if isinstance(raw.get("objective"), dict) else {}
    version = objective.get("version")
    if version is None:
        version = (b.get("objective") or {}).get("version") if isinstance(b, dict) else None
    fields = {
        "name": raw.get("name"),
        "family": raw.get("family"),
        "objective_version": version,
        "brief_sha": _brief_identity(b),
        "target": raw.get("target"),
        "weights": raw.get("weights"),
        "objective": objective,
        "mesh": raw.get("mesh"),
        "solve": raw.get("solve"),
        "seed_params": raw.get("seed_params"),
        "generator": raw.get("generator"),
        "mounting": raw.get("mounting"),
        "grid": raw.get("grid"),
    }
    return {"fields": fields, "hash": _sha16(fields)}


def _resolve(path_str, *bases) -> Path:
    p = Path(str(path_str))
    if p.is_absolute():
        return p.resolve()
    for base in bases:
        if base is not None:
            cand = (Path(base) / p)
            if cand.exists():
                return cand.resolve()
    return p.resolve()


def _guard_output(out: Path, *, inputs: list[Path], spec_dir: Path | None = None) -> None:
    """Refuse an output directory inside repo inputs, the spec dir or a run dir."""
    out_r = Path(out).resolve()
    for name in FORBIDDEN_OUTPUT_PARENTS:
        forbidden = (REPO / name).resolve()
        if out_r == forbidden or forbidden in out_r.parents:
            raise fail(f"output {out_r} is inside {forbidden}; choose a different --out")
    if spec_dir is not None:
        sd = Path(spec_dir).resolve()
        if out_r == sd or sd in out_r.parents:
            raise fail(f"output {out_r} is inside the input spec directory {sd}")
    for path in inputs:
        p = Path(path).resolve()
        if out_r == p or p in out_r.parents:
            raise fail(f"output {out_r} is inside input {p}")


# ------------------------------------------------------------------ spec


def load_spec(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise fail(f"spec not found: {path}")
    try:
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise fail(f"cannot read spec {path}: {exc}") from None
    if not isinstance(spec, dict):
        raise fail(f"spec {path}: top level must be a mapping")
    unknown = set(spec) - SPEC_KEYS
    if unknown:
        raise fail(f"spec {path}: unknown key(s) {sorted(unknown)} "
                   f"(allowed: {sorted(SPEC_KEYS)})")
    if spec.get("schema") != PLAN_SCHEMA:
        raise fail(f"spec {path}: schema must be {PLAN_SCHEMA!r}, got {spec.get('schema')!r}")
    return spec


def _normalise_seeds(spec: dict, *, pilot: bool) -> tuple[list[int], bool]:
    declared = spec.get("seeds") is not None
    if declared:
        raw = spec["seeds"]
        if not isinstance(raw, list) or not raw:
            raise fail("spec.seeds must be a non-empty list of integers")
        seeds = []
        for s in raw:
            if isinstance(s, bool) or not isinstance(s, int):
                raise fail(f"spec.seeds entries must be integers, got {s!r}")
            seeds.append(int(s))
        if spec.get("seed_count") is not None and int(spec["seed_count"]) != len(seeds):
            raise fail("spec.seed_count does not match len(spec.seeds)")
    else:
        count = spec.get("seed_count", 5)
        base = spec.get("seed_base", 1000)
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise fail("spec.seed_count must be a positive integer")
        if isinstance(base, bool) or not isinstance(base, int):
            raise fail("spec.seed_base must be an integer")
        seeds = [int(base) + i for i in range(int(count))]
    if len(set(seeds)) != len(seeds):
        raise fail(f"spec declares duplicate seeds: {seeds}")
    if len(seeds) < 5 and not pilot:
        raise fail(f"spec declares {len(seeds)} seed(s); a matched benchmark needs at "
                   "least 5. Pass --pilot to relabel this plan as a pilot (never silent).")
    return seeds, declared


def _canonical_algorithm(value, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise fail(f"{where}: algorithm must be a non-empty string")
    name = ALGORITHM_ALIASES.get(value.strip(), value.strip())
    if name not in ALGORITHMS:
        raise fail(f"{where}: unknown algorithm {value!r} "
                   f"(known: {sorted(ALGORITHMS)})")
    return name


def _validate_covariance(block, where: str) -> dict:
    if not isinstance(block, dict):
        raise fail(f"{where}: covariance must be a mapping")
    unknown = set(block) - COVARIANCE_KEYS
    if unknown:
        raise fail(f"{where}: unknown covariance key(s) {sorted(unknown)} "
                   f"(allowed: {sorted(COVARIANCE_KEYS)})")
    out = dict(block)
    for key in ("blend", "eig_floor", "eig_cap"):
        if key in out and not _is_number(out[key]):
            raise fail(f"{where}.{key} must be a finite number")
    if "blend" in out and not (0.0 <= float(out["blend"]) <= 1.0):
        raise fail(f"{where}.blend must be in [0, 1]")
    if "max_dim" in out and (isinstance(out["max_dim"], bool)
                             or not isinstance(out["max_dim"], int)
                             or out["max_dim"] < 1):
        raise fail(f"{where}.max_dim must be a positive integer")
    if "scale_sigma" in out and not isinstance(out["scale_sigma"], bool):
        raise fail(f"{where}.scale_sigma must be true or false")
    return out


def _validate_warm_start(block, *, algorithm: str, spec_dir: Path, where: str,
                         check_sources: bool = True) -> dict | None:
    if block is None:
        return None
    if not isinstance(block, dict):
        raise fail(f"{where}: warm_start must be a mapping or null")
    unknown = set(block) - WARM_START_KEYS
    if unknown:
        raise fail(f"{where}: unknown warm_start key(s) {sorted(unknown)} "
                   f"(allowed: {sorted(WARM_START_KEYS)})")
    runs = block.get("from_runs")
    if not isinstance(runs, list) or not runs or not all(isinstance(r, str) and r for r in runs):
        raise fail(f"{where}.from_runs must be a non-empty list of run-directory paths")
    resolved = []
    for r in runs:
        p = _resolve(r, spec_dir, Path.cwd(), REPO)
        if check_sources and (not p.is_dir() or not (p / "search.ndjson").is_file()
                              or not (p / "run.json").is_file()):
            raise fail(f"{where}.from_runs: not a started run directory "
                       f"(needs search.ndjson and run.json): {p}")
        resolved.append(str(p))
    top_k = block.get("top_k", 10)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise fail(f"{where}.top_k must be a positive integer")
    out = dict(block)
    out["from_runs"] = resolved
    out["top_k"] = int(top_k)
    for key in ("sigma_from_spread", "allow_cross_brief"):
        if key in out and not isinstance(out[key], bool):
            raise fail(f"{where}.{key} must be true or false")
    covariance = _validate_covariance(out["covariance"], f"{where}.covariance") \
        if "covariance" in out else None
    family = ALGORITHMS[algorithm]["family"]
    if family != "cma":
        raise fail(f"{where}: warm_start is a CMA mechanism, not valid for {algorithm}")
    if algorithm == "cma" and covariance is not None:
        raise fail(f"{where}: covariance transfer requires algorithm cma_warm_covariance")
    if algorithm == "cma_warm_mean" and covariance is not None:
        raise fail(f"{where}: covariance transfer requires algorithm cma_warm_covariance")
    if algorithm == "cma_warm_covariance" and covariance is None:
        raise fail(f"{where}: algorithm cma_warm_covariance needs a covariance block")
    if algorithm in ("cma_warm_mean", "cma_warm_covariance") \
            and bool(out.get("sigma_from_spread", True)):
        raise fail(f"{where}: {algorithm} is mean/mean+shape; declare sigma_from_spread: false")
    if covariance is not None:
        out["covariance"] = covariance
    return out


def _validate_restarts(block, where: str) -> dict:
    if not isinstance(block, dict):
        raise fail(f"{where}: restarts must be a mapping")
    unknown = set(block) - RESTART_KEYS
    if unknown:
        raise fail(f"{where}: unknown restart key(s) {sorted(unknown)}")
    for key in RESTART_KEYS:
        if key not in block:
            raise fail(f"{where}: missing required key {key!r}")
    if block["mode"] not in ("ipop", "bipop"):
        raise fail(f"{where}.mode must be 'ipop' or 'bipop'")
    mx = block["max"]
    if isinstance(mx, bool) or not isinstance(mx, int) or not (0 <= mx <= 64):
        raise fail(f"{where}.max must be an integer in [0, 64]")
    return {"mode": block["mode"], "max": int(mx)}


def _validate_qd(block, where: str) -> dict:
    if not isinstance(block, dict):
        raise fail(f"{where}: qd must be a mapping")
    unknown = set(block) - QD_KEYS
    if unknown:
        raise fail(f"{where}: unknown qd key(s) {sorted(unknown)}")
    for key in ("descriptor_h", "descriptor_v"):
        if block.get(key) not in QD_DESCRIPTORS:
            raise fail(f"{where}.{key} must be one of {list(QD_DESCRIPTORS)}")
    for key in ("bins_h", "bins_v"):
        v = block.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or not (2 <= v <= 64):
            raise fail(f"{where}.{key} must be an integer in [2, 64]")
    out = {k: block[k] for k in ("descriptor_h", "descriptor_v", "bins_h", "bins_v")}
    if block.get("maes") is not None:
        maes = block["maes"]
        if not isinstance(maes, dict) or set(maes) - {"learning_rate", "j_threshold"}:
            raise fail(f"{where}.maes must be a mapping with learning_rate/j_threshold")
        out["maes"] = dict(maes)
    return out


def _source_fingerprint(run_dir: Path) -> dict:
    rj = read_json(Path(run_dir) / "run.json") or {}
    return {
        "run_dir": str(Path(run_dir).resolve()),
        "config_sha": rj.get("config_sha"),
        "config_name": rj.get("config_name"),
        "family": rj.get("family"),
        "objective_version": rj.get("objective_version"),
        "cma_seed": rj.get("cma_seed", rj.get("bo_seed")),
    }


def _apply_arm(base_raw: dict, arm: dict, *, spec: dict, seeds: list[int],
               brief: dict, brief_path: Path, spec_dir: Path,
               check_sources: bool = True) -> tuple[dict, dict, dict]:
    """Return (derived config, applied overrides record, plan-level overrides record)."""
    arm_id = arm["id"]
    algorithm = _canonical_algorithm(arm.get("algorithm"), f"arm {arm_id!r}")
    meta = ALGORITHMS[algorithm]
    overrides = arm.get("overrides") or {}
    if not isinstance(overrides, dict):
        raise fail(f"arm {arm_id!r}: overrides must be a mapping")
    unknown = set(overrides) - set(OVERRIDE_KEYS)
    if unknown:
        raise fail(f"arm {arm_id!r}: unknown override key(s) {sorted(unknown)} "
                   f"(allowed: {sorted(OVERRIDE_KEYS)})")

    cfg = copy.deepcopy(base_raw)
    search = cfg.get("search")
    if not isinstance(search, dict):
        raise fail(f"arm {arm_id!r}: base config has no search block")
    applied: dict[str, Any] = {}
    plan_level: dict[str, Any] = {}

    if "bounds" in overrides:
        raise fail(f"arm {arm_id!r}: bounds are frozen for a matched optimizer comparison; "
                   "a bounds/sigma factorial is a different experiment")

    if "sigma0" in overrides:
        value = overrides["sigma0"]
        if not _is_number(value) or float(value) <= 0.0:
            raise fail(f"arm {arm_id!r}: sigma0 must be a finite number > 0")
        search["sigma0"] = float(value)
        applied["sigma0"] = float(value)

    if "bounds" in overrides:
        raise fail(f"arm {arm_id!r}: bounds are frozen for a matched optimizer comparison; "
                   "a bounds/sigma factorial is a different experiment")

    if "seed" in overrides:
        value = overrides["seed"]
        if isinstance(value, bool) or not isinstance(value, int):
            raise fail(f"arm {arm_id!r}: seed must be an integer")
        search["seed"] = int(value)
        applied["seed"] = int(value)

    if "algorithm" in overrides:
        declared = _canonical_algorithm(overrides["algorithm"], f"arm {arm_id!r}.algorithm")
        if declared != algorithm:
            raise fail(f"arm {arm_id!r}: overrides.algorithm {declared!r} contradicts "
                       f"arm.algorithm {algorithm!r}")
        applied["algorithm"] = declared

    if "policy" in overrides:
        if meta["family"] != "bo":
            raise fail(f"arm {arm_id!r}: policy is only meaningful for a BO arm")
        policy = overrides["policy"]
        if policy not in ("scalar", "turbo"):
            raise fail(f"arm {arm_id!r}: policy must be 'scalar' or 'turbo'")
        if policy != meta.get("policy"):
            raise fail(f"arm {arm_id!r}: policy {policy!r} contradicts algorithm {algorithm!r}")
        plan_level["policy"] = policy
        applied["policy"] = policy

    if "warm_start" in overrides:
        ws = _validate_warm_start(overrides["warm_start"], algorithm=algorithm,
                                  spec_dir=spec_dir,
                                  where=f"arm {arm_id!r}.warm_start",
                                  check_sources=check_sources)
        if ws is None:
            search.pop("warm_start", None)
            applied["warm_start"] = None
        else:
            search["warm_start"] = ws
            applied["warm_start"] = ws
    else:
        existing = search.get("warm_start")
        if algorithm == "cma" and existing:
            raise fail(f"arm {arm_id!r}: cold CMA but the base config has a warm_start; "
                       "declare overrides.warm_start: null to remove it explicitly")
        if algorithm in ("cma_warm_mean", "cma_warm_covariance"):
            raise fail(f"arm {arm_id!r}: {algorithm} needs an explicit overrides.warm_start")

    if "restarts" in overrides:
        search["restarts"] = _validate_restarts(overrides["restarts"], f"arm {arm_id!r}.restarts")
        applied["restarts"] = search["restarts"]

    if "qd" in overrides:
        search["qd"] = _validate_qd(overrides["qd"], f"arm {arm_id!r}.qd")
        applied["qd"] = search["qd"]

    # Plan-level budget applies to every arm; it is an information-parity declaration,
    # not an arm-specific treatment.
    search["budget"] = int(spec["budget"])
    if meta["config_algorithm"] is not None:
        search["algorithm"] = meta["config_algorithm"]
        applied.setdefault("config_algorithm", meta["config_algorithm"])
    if meta["family"] == "bo":
        plan_level["algorithm"] = algorithm
        plan_level["policy"] = meta["policy"]

    # Make the derived YAML self-contained: an absolute brief_file plus the embedded
    # resolved brief.  Keeping the base config's relative brief_file string would not
    # resolve from the output directory and would silently rely on the embedded copy.
    cfg["brief_file"] = str(Path(brief_path).resolve())
    cfg["brief"] = _brief_payload(brief)
    return cfg, applied, plan_level


def _launch_commands(arm_id: str, algorithm: str, config_path: Path, *, seeds: list[int],
                     budget: int, out: Path, info: dict) -> dict:
    family = ALGORITHMS[algorithm]["family"]
    if family == "cma":
        commands = [
            f' hornlab-search search --config "{config_path}" --mode screen '
            f'--budget {int(budget)} --cma-seed {int(seed)} '
            f'--runs-dir "{out / "runs" / arm_id}"'.strip()
            for seed in seeds
        ]
        return {"kind": "search", "executable": True, "commands": commands,
                "note": "CMA arms run through `hornlab-search search`; one run dir per seed."}
    cohort = info.get("training_cohort")
    profile = info.get("budget_profile")
    scores_sha = info.get("training_cohort_sha256")
    catalog_sha = info.get("catalog_sha256")
    policy = info.get("policy") or ALGORITHMS[algorithm].get("policy")
    executable = bool(cohort and profile and scores_sha and catalog_sha)
    commands = []
    for seed in seeds:
        c = (f' python tools\\night_queue\\run_bo_arm.py '
             f'--root "{out / "studies" / arm_id / f"seed-{seed}"}" '
             f'--cohort "{cohort if cohort else "<training_cohort_required>"}" '
             f'--config "{config_path}" --policy {policy} --seed {int(seed)} '
             f'--budget-profile "{profile if profile else "<budget_profile_required>"}" '
             f'--scores-sha256 "{scores_sha if scores_sha else "<scores_sha_required>"}" '
             f'--catalog-sha256 "{catalog_sha if catalog_sha else "<catalog_sha_required>"}"')
        commands.append(c.strip())
    note = ("BO/TuRBO arms run through the study runner; the derived YAML is the task "
            "config, not a `search.algorithm` value.")
    if not executable:
        note += (" Command contains a placeholder because the spec declares no "
                 "training_cohort / budget_profile / cohort hashes.")
    return {"kind": "study", "executable": executable, "commands": commands, "note": note}


# ------------------------------------------------------------------ plan


def validate_spec_file(spec_path: Path, *, check_sources: bool = True,
                       pilot: bool = True) -> dict:
    """Validate a spec structure and its real base config/brief without writing anything.

    The template regression test uses this with ``check_sources=False`` so a spec that
    names a local (gitignored) warm-source run still validates in a clean checkout.
    """
    spec_path = Path(spec_path)
    spec = load_spec(spec_path)
    spec_dir = spec_path.resolve().parent
    seeds, declared = _normalise_seeds(spec, pilot=pilot)
    budget = spec.get("budget")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        raise fail("spec.budget must be a positive integer (new valid evals)")
    version = spec.get("objective_version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise fail("spec.objective_version must be an integer")
    base_path = _resolve(spec["base_config"], spec_dir, REPO)
    if not base_path.is_file():
        raise fail(f"base config not found: {base_path}")
    brief_path = _resolve(spec["brief"], spec_dir, REPO) if spec.get("brief") else None
    if brief_path is not None and not brief_path.is_file():
        raise fail(f"brief not found: {brief_path}")
    try:
        cfg = load_config(base_path, brief=(str(brief_path) if brief_path else None))
        base_brief_path = cfg.raw.get("brief_file")
        if base_brief_path:
            resolved = _resolve(base_brief_path, base_path.parent, REPO)
            if brief_path is not None and resolved.resolve() != brief_path.resolve():
                raise fail(f"spec.brief {brief_path} is not the base config's brief_file {resolved}")
            brief_path = brief_path or resolved
        if brief_path is None:
            raise fail("base config has no brief_file and the spec declares no brief")
        brief = load_brief(brief_path)
    except ConfigError as exc:
        raise fail(f"cannot load base config/brief: {exc}") from None
    if int(cfg.objective_version) != int(version):
        raise fail(f"objective version mismatch: spec {version}, config/brief {cfg.objective_version}")
    if spec.get("family") is not None and str(spec["family"]) != str(cfg.family):
        raise fail(f"family mismatch: spec {spec['family']!r}, config {cfg.family!r}")

    base_raw = copy.deepcopy(cfg.raw)
    base_raw["brief"] = _brief_payload(brief)
    arm_ids: list[str] = []
    for arm in spec["arms"]:
        if not isinstance(arm, dict):
            raise fail("every arm must be a mapping")
        unknown = set(arm) - ARM_KEYS
        if unknown:
            raise fail(f"arm {arm.get('id')!r}: unknown field(s) {sorted(unknown)}")
        arm_id = arm.get("id")
        if not isinstance(arm_id, str) or not arm_id.strip():
            raise fail("every arm needs a non-empty string id")
        if arm_id in arm_ids:
            raise fail(f"duplicate arm id {arm_id!r}")
        arm_ids.append(arm_id)
        if not isinstance(arm.get("expected_information"), str) \
                or not arm["expected_information"].strip():
            raise fail(f"arm {arm_id!r}: expected_information must be a non-empty string")
        _apply_arm(base_raw, arm, spec=spec, seeds=seeds, brief=brief,
                   brief_path=brief_path, spec_dir=spec_dir,
                   check_sources=check_sources)
    for pair in spec.get("pairs") or []:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            a, b = pair
        elif isinstance(pair, dict):
            a, b = pair.get("a"), pair.get("b")
        else:
            raise fail(f"pair entry must be [a, b] or {{a, b, label}}, got {pair!r}")
        if a not in arm_ids or b not in arm_ids or a == b:
            raise fail(f"pair {a!r} vs {b!r} is not a valid declared arm pair")
    return {"spec": str(spec_path.resolve()), "task": spec["task"],
            "objective_version": int(version), "family": cfg.family,
            "base_config": str(base_path), "brief": str(brief_path),
            "seeds": seeds, "seeds_declared": declared,
            "arms": arm_ids, "pairs": list(spec.get("pairs") or [])}


def plan_spec(spec_path: Path, out: Path, *, pilot: bool = False) -> dict:
    """Validate a spec, derive arm configs and write the plan. Never dispatches."""
    spec_path = Path(spec_path)
    spec = load_spec(spec_path)
    spec_dir = spec_path.resolve().parent
    seeds, seeds_declared = _normalise_seeds(spec, pilot=pilot)

    for key in ("task", "base_config", "objective_version", "budget", "arms"):
        if spec.get(key) is None:
            raise fail(f"spec {spec_path}: missing required key {key!r}")
    if not isinstance(spec["task"], str) or not spec["task"].strip():
        raise fail("spec.task must be a non-empty string")
    budget = spec["budget"]
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        raise fail("spec.budget must be a positive integer (new valid evals)")
    objective_version = spec["objective_version"]
    if isinstance(objective_version, bool) or not isinstance(objective_version, int):
        raise fail("spec.objective_version must be an integer")
    for key in ("target_j", "practical_delta", "floor_j", "cost_budget_s"):
        if spec.get(key) is not None and not _is_number(spec[key]):
            raise fail(f"spec.{key} must be a finite number when present")

    base_path = _resolve(spec["base_config"], spec_dir, REPO)
    if not base_path.is_file():
        raise fail(f"base config not found: {base_path}")
    brief_declared = spec.get("brief")
    brief_path = None
    if brief_declared:
        brief_path = _resolve(brief_declared, spec_dir, REPO)
        if not brief_path.is_file():
            raise fail(f"brief not found: {brief_path}")

    try:
        cfg = load_config(base_path, brief=(str(brief_path) if brief_path else None))
        base_brief_path = cfg.raw.get("brief_file")
        if base_brief_path:
            resolved_base_brief = _resolve(base_brief_path, base_path.parent, REPO)
            if brief_path is not None and resolved_base_brief.resolve() != brief_path.resolve():
                raise fail(f"spec.brief {brief_path} is not the base config's brief_file "
                           f"{resolved_base_brief}")
            brief_path = brief_path or resolved_base_brief
        if brief_path is None:
            raise fail(f"base config {base_path} has no brief_file and the spec declares no brief")
        brief = load_brief(brief_path)
    except ConfigError as exc:
        raise fail(f"cannot load base config/brief: {exc}") from None
    if int(cfg.objective_version) != int(objective_version):
        raise fail(f"objective version mismatch: spec {objective_version}, config/brief "
                   f"{cfg.objective_version}")
    if spec.get("family") is not None and str(spec["family"]) != str(cfg.family):
        raise fail(f"family mismatch: spec {spec['family']!r}, config {cfg.family!r}")

    brief_sha = _sha256_file(brief_path)
    base_raw = copy.deepcopy(cfg.raw)
    base_raw["brief"] = _brief_payload(brief)
    identity = _config_identity(base_raw, brief)
    base_bounds = cfg.bounds_raw
    searched = bounds_of(base_raw)

    info_decl = spec.get("information_parity") or {}
    if not isinstance(info_decl, dict):
        raise fail("spec.information_parity must be a mapping")
    cohort = info_decl.get("training_cohort")
    cohort_sha = info_decl.get("training_cohort_sha256")
    if cohort:
        cp = _resolve(cohort, spec_dir, REPO)
        if not cp.exists():
            raise fail(f"training_cohort not found: {cp}; prepare it with "
                       "tools/analysis/study_cohort.py and record its sha256 "
                       "(a matched BO/TuRBO arm cannot run on an undeclared cohort)")
        cohort = str(cp)
        if not cohort_sha and cp.is_file():
            cohort_sha = _sha256_file(cp)
    info_base = {
        "training_cohort": cohort,
        "training_cohort_sha256": cohort_sha,
        "catalog_sha256": info_decl.get("catalog_sha256"),
        "incumbent_j": info_decl.get("incumbent_j"),
        "budget_profile": info_decl.get("budget_profile"),
        "target_j": spec.get("target_j"),
        "notes": info_decl.get("notes"),
    }

    _guard_output(out, inputs=[base_path, brief_path], spec_dir=spec_dir)
    out = Path(out).resolve()
    arms_in = spec["arms"]
    if not isinstance(arms_in, list) or not arms_in:
        raise fail("spec.arms must be a non-empty list")
    arm_ids: list[str] = []
    arm_records: list[dict] = []
    cfg_arms: dict[str, dict] = {}
    for arm in arms_in:
        if not isinstance(arm, dict):
            raise fail("every arm must be a mapping")
        unknown = set(arm) - ARM_KEYS
        if unknown:
            raise fail(f"arm {arm.get('id')!r}: unknown field(s) {sorted(unknown)} "
                       f"(allowed: {sorted(ARM_KEYS)})")
        arm_id = arm.get("id")
        if not isinstance(arm_id, str) or not arm_id.strip():
            raise fail("every arm needs a non-empty string id")
        if arm_id in arm_ids:
            raise fail(f"duplicate arm id {arm_id!r}")
        if arm.get("base") not in (None, "config"):
            raise fail(f"arm {arm_id!r}: base must be 'config' or omitted")
        expected = arm.get("expected_information")
        if not isinstance(expected, str) or not expected.strip():
            raise fail(f"arm {arm_id!r}: expected_information must be a non-empty string")
        algorithm = _canonical_algorithm(arm.get("algorithm"), f"arm {arm_id!r}")
        derived, applied, plan_level = _apply_arm(
            base_raw, arm, spec=spec, seeds=seeds, brief=brief, brief_path=brief_path,
            spec_dir=spec_dir)
        arm_identity = _config_identity(derived, brief)
        if arm_identity["hash"] != identity["hash"]:
            diff = sorted(k for k in identity["fields"]
                          if identity["fields"].get(k) != arm_identity["fields"].get(k))
            raise fail(f"arm {arm_id!r}: search override changed non-search identity "
                       f"field(s) {diff}")
        search = derived.get("search") or {}
        ws = search.get("warm_start") if isinstance(search.get("warm_start"), dict) else None
        warm_from_runs = list(ws.get("from_runs") or []) if ws else []
        parity = {
            **info_base,
            "warm_from_runs": warm_from_runs,
            "warm_sources": [_source_fingerprint(Path(p)) for p in warm_from_runs],
            "budget": int(budget),
            "budget_counts": search.get("budget_counts"),
            "policy": plan_level.get("policy"),
        }
        if ALGORITHMS[algorithm]["family"] != "bo":
            # The training cohort is BO-arm information, not CMA-arm information.
            parity["training_cohort"] = None
            parity["training_cohort_sha256"] = None
            parity["budget_profile"] = None
        arm_ids.append(arm_id)
        cfg_arms[arm_id] = derived
        arm_records.append({
            "id": arm_id,
            "algorithm": algorithm,
            "label": arm.get("label") or arm_id,
            "expected_information": expected,
            "config_file": str(out / "arms" / f"{arm_id}.yaml"),
            "config_sha256": _sha16(derived),
            "seeds": list(seeds),
            "budget": int(budget),
            "budget_counts": search.get("budget_counts"),
            "config_seed": search.get("seed"),
            "applied_overrides": applied,
            "plan_level_overrides": plan_level,
            "identity": arm_identity,
            "search_treatment": {"search": search,
                                 "bounds_hash": _sha16(derived.get("bounds") or {})},
            "information_parity": parity,
        })

    # Predeclared pairs: each entry is ["a", "b"] or {a: ..., b: ..., label: ...}.
    pairs_in = spec.get("pairs") or []
    if not isinstance(pairs_in, list):
        raise fail("spec.pairs must be a list")
    pairs: list[dict] = []
    seen = set()
    for item in pairs_in:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            a, b = item
            label = f"{a}_vs_{b}"
        elif isinstance(item, dict):
            unknown = set(item) - {"a", "b", "label"}
            if unknown:
                raise fail(f"pair {item!r}: unknown key(s) {sorted(unknown)}")
            a, b = item.get("a"), item.get("b")
            label = item.get("label") or f"{a}_vs_{b}"
        else:
            raise fail(f"pair entry must be [a, b] or {{a, b, label}}, got {item!r}")
        if a not in cfg_arms or b not in cfg_arms:
            raise fail(f"pair {label!r} references an undeclared arm")
        if a == b:
            raise fail(f"pair {label!r} compares an arm with itself")
        key = tuple(sorted((a, b)))
        if key in seen:
            raise fail(f"duplicate pair {label!r}")
        seen.add(key)
        pairs.append({"a": a, "b": b, "label": str(label)})

    # Write arm configs only after every validation passed.
    arms_dir = out / "arms"
    arms_dir.mkdir(parents=True, exist_ok=True)
    for arm_id in arm_ids:
        (arms_dir / f"{arm_id}.yaml").write_text(
            yaml.safe_dump(cfg_arms[arm_id], sort_keys=False, allow_unicode=True),
            encoding="utf-8")
    for rec in arm_records:
        rec["config_sha256"] = _sha256_file(Path(rec["config_file"]))
        rec["launch"] = _launch_commands(
            rec["id"], rec["algorithm"], Path(rec["config_file"]), seeds=seeds,
            budget=int(budget), out=out, info={**info_base, **rec["information_parity"]})

    payload = {
        "schema": PLAN_SCHEMA,
        "spec": str(spec_path.resolve()),
        "task": spec["task"],
        "description": spec.get("description"),
        "objective_version": int(objective_version),
        "family": cfg.family,
        "dispatched": False,
        "advisory_only": True,
        "advisory": ("This plan is advisory only. Nothing was launched, solved or queued. "
                     "Every command below is text for a human/queue operator."),
        "base_config": str(base_path),
        "brief": {"path": str(brief_path), "sha256": brief_sha,
                  "identity_sha16": _brief_identity(brief)},
        "seeds": list(seeds),
        "seeds_declared": seeds_declared,
        "pilot": bool(pilot or len(seeds) < 5),
        "seed_count": len(seeds),
        "budget": int(budget),
        "cost_budget_s": spec.get("cost_budget_s"),
        "target_j": spec.get("target_j"),
        "practical_delta": spec.get("practical_delta"),
        "floor_j": spec.get("floor_j"),
        "identity": {
            "hash": identity["hash"],
            "fields": identity["fields"],
            "bounds": base_bounds,
            "searched_bounds": {k: list(v) for k, v in searched.items()},
            "equal_across_arms": True,
        },
        "information_parity": info_base,
        "arms": arm_records,
        "pairs": pairs,
        "launch": {
            "dispatched": False,
            "advisory_only": True,
            "note": ("Text only. CMA arms use `hornlab-search search`; BO/TuRBO arms "
                     "use the study runner. No process was started."),
            "arms": {rec["id"]: rec["launch"] for rec in arm_records},
        },
    }
    md = _plan_md(payload)
    write_report(out, TOOL_PLAN, payload, md)
    return payload


def _plan_md(payload: dict) -> str:
    lines = [
        "# Matched benchmark plan (advisory)", "",
        f"**Task:** {payload['task']}  ",
        f"**Schema:** {payload['schema']}  ",
        f"**Objective version:** {payload['objective_version']}  ",
        f"**Family:** {payload['family']}  ",
        f"**Base config:** `{payload['base_config']}`  ",
        f"**Brief:** `{payload['brief']['path']}` (sha256 `{payload['brief']['sha256'][:16]}...`)  ",
        f"**Seeds:** {payload['seeds']} ({'declared' if payload['seeds_declared'] else 'derived'})  ",
        f"**Budget:** {payload['budget']} valid evaluations per arm  ",
        f"**Pilot:** {payload['pilot']}  ",
        f"**Target J:** {payload['target_j']}  ",
        f"**Practical delta:** {payload['practical_delta']}  ",
        f"**Identity floor:** {payload['floor_j']}  ",
        "", f"> {payload['advisory']}", "",
        f"Task identity hash: `{payload['identity']['hash']}` (equal across every arm).", "",
        "| arm | algorithm | config sha256 | config seed | budget | expected information |",
        "|---|---|---|---:|---:|---|",
    ]
    for arm in payload["arms"]:
        lines.append(f"| `{arm['id']}` | {arm['algorithm']} | `{arm['config_sha256'][:16]}` | "
                     f"{arm['config_seed']} | {arm['budget']} | {arm['expected_information']} |")
    lines += ["", "## Information parity", "",
              f"- training cohort: `{payload['information_parity']['training_cohort']}` "
              f"(sha256 `{payload['information_parity']['training_cohort_sha256']}`)",
              f"- incumbent J: {payload['information_parity']['incumbent_j']}",
              ""]
    for arm in payload["arms"]:
        p = arm["information_parity"]
        lines.append(f"- `{arm['id']}`: warm sources {p['warm_from_runs'] or 'none'}, "
                     f"budget {p['budget']} ({p['budget_counts']}), policy {p['policy']}")
    lines += ["", "## Launch commands (TEXT ONLY — NOT DISPATCHED)", ""]
    for arm in payload["arms"]:
        launch = arm["launch"]
        lines.append(f"### {arm['id']} (`{launch['kind']}`)")
        lines.append("")
        lines.append(f"_{launch['note']}_")
        lines.append("")
        lines.append("```powershell")
        lines.extend(launch["commands"])
        lines.append("```")
        lines.append("")
    if payload["pairs"]:
        lines += ["## Predeclared pairs", ""]
        for pair in payload["pairs"]:
            lines.append(f"- {pair['label']}: `{pair['a']}` vs `{pair['b']}`")
        lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------ report


def _ledger(run: dict) -> dict:
    rj = read_json(Path(run["run_dir"]) / "run.json") or {}
    return cost_ledger(run["rows"], stats=rj.get("stats"),
                       started_utc=rj.get("started_utc"),
                       finished_utc=rj.get("finished_utc"))


def _sum_ledgers(ledgers: list[dict]) -> dict:
    out = sum_cost_ledgers(ledgers)
    elapsed = dict(out.get("elapsed_seconds") or {})
    if any((led.get("elapsed_seconds") or {}).get("wall_span") is None for led in ledgers):
        elapsed["wall_span"] = None
        elapsed["unaccounted_overhead"] = None
        elapsed["partial_wall_span"] = True
    out["elapsed_seconds"] = elapsed
    return out


def _median_curve(curves: list[list[dict]]) -> list[dict]:
    n_max = max((len(c) for c in curves), default=0)
    out = []
    for n in range(1, n_max + 1):
        vals = [float(c[n - 1]["best"]) for c in curves if len(c) >= n]
        out.append({"n": n,
                    "median_best": float(np.median(vals)) if vals else None,
                    "n_observed": len(vals),
                    "n_censored": len(curves) - len(vals)})
    return out


def _parse_results(entries: list[str]) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {}
    for entry in entries:
        if "=" not in entry:
            raise fail(f"--results expects <arm>=<run_dir>[,<run_dir>...], got {entry!r}")
        arm, _, rest = entry.partition("=")
        arm = arm.strip()
        dirs = [Path(p.strip()) for p in rest.split(",") if p.strip()]
        if not arm or not dirs:
            raise fail(f"--results expects <arm>=<run_dir>[,<run_dir>...], got {entry!r}")
        if arm in out:
            raise fail(f"--results declares arm {arm!r} more than once")
        out[arm] = dirs
    return out


def _seed_of_run(run: dict) -> int | None:
    """The run's declared seed: ``cma_seed``, then the BO mirror's ``bo_seed``.

    Mirrored BO/TuRBO study runs write ``bo_seed`` (``tools/night_queue/
    mirror_bo_studies.py``); ordinary CMA runs write ``cma_seed``.  Both are the
    declared paired seed, so the report accepts either spelling.
    """
    rj = read_json(Path(run["run_dir"]) / "run.json") or {}
    for source in (rj, run.get("meta") if isinstance(run.get("meta"), dict) else {}):
        for key in ("cma_seed", "bo_seed", "seed"):
            value = source.get(key) if isinstance(source, dict) else None
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


def _observed_warm_sources(run: dict) -> list[str]:
    rj = read_json(Path(run["run_dir"]) / "run.json") or {}
    block = rj.get("warm_start")
    if not isinstance(block, dict):
        block = ((run.get("config") or {}).get("search") or {}).get("warm_start")
    if not isinstance(block, dict):
        return []
    runs = block.get("from_runs") or []
    return [str(Path(str(p)).resolve()) for p in runs]


def _observed_cohort_sha(run: dict) -> str | None:
    rj = read_json(Path(run["run_dir"]) / "run.json") or {}
    for key in ("training_cohort_sha256", "cohort_sha256"):
        if isinstance(rj.get(key), str) and rj[key]:
            return rj[key]
    study = rj.get("study")
    if isinstance(study, dict):
        for key in ("training_cohort_sha256", "cohort_sha256"):
            if isinstance(study.get(key), str) and study[key]:
                return study[key]
        cohort = study.get("cohort")
        if isinstance(cohort, dict) and isinstance(cohort.get("sha256"), str):
            return cohort["sha256"]
    return None


def _observed_incumbent(run: dict) -> float | None:
    rj = read_json(Path(run["run_dir"]) / "run.json") or {}
    for source in (rj, rj.get("study") if isinstance(rj.get("study"), dict) else {}):
        value = source.get("incumbent_j") if isinstance(source, dict) else None
        if _is_number(value):
            return float(value)
    return None


def _parity_check(arm: dict, runs: list[dict]) -> dict:
    declared = arm.get("information_parity") or {}
    declared_warm = {str(Path(p).resolve()) for p in (declared.get("warm_from_runs") or [])}
    declared_cohort = declared.get("training_cohort_sha256")
    declared_incumbent = declared.get("incumbent_j")
    blocking: list[str] = []
    disclosures: list[str] = []
    run_records = []
    for run in runs:
        run_id = Path(run["run_dir"]).name
        observed_warm = set(_observed_warm_sources(run))
        observed_cohort = _observed_cohort_sha(run)
        observed_incumbent = _observed_incumbent(run)
        rec = {
            "run_id": run_id,
            "seed": _seed_of_run(run),
            "observed": {
                "warm_from_runs": sorted(observed_warm),
                "training_cohort_sha256": observed_cohort,
                "incumbent_j": observed_incumbent,
            },
        }
        if declared_warm != observed_warm:
            blocking.append(f"{run_id}:warm_source_mismatch")
        if declared_cohort:
            if observed_cohort is None:
                disclosures.append(f"{run_id}:training_cohort_sha256_unverified")
            elif str(observed_cohort).lower() != str(declared_cohort).lower():
                blocking.append(f"{run_id}:training_cohort_sha256_mismatch")
        if _is_number(declared_incumbent):
            if observed_incumbent is None:
                disclosures.append(f"{run_id}:incumbent_j_unverified")
            elif float(observed_incumbent) != float(declared_incumbent):
                blocking.append(f"{run_id}:incumbent_j_mismatch")
        run_records.append(rec)
    return {
        "declared": {
            "warm_from_runs": sorted(declared_warm),
            "training_cohort_sha256": declared_cohort,
            "incumbent_j": declared_incumbent,
        },
        "runs": run_records,
        "blocking": sorted(set(blocking)),
        "disclosures": sorted(set(disclosures)),
        "status": "blocking" if blocking else "ok",
    }


def _floor_verdict(summary: dict | None, *, floor_j, n_pairs: int, blocked: bool,
                   evidence_class: str) -> dict:
    if blocked:
        return {"verdict": "no-verdict", "decisive_claim": False,
                "reason": "identity/compatibility/information-parity blocking",
                "evidence_class": "blocked"}
    if n_pairs == 0:
        return {"verdict": "no-verdict", "decisive_claim": False, "reason": "no pairs",
                "evidence_class": evidence_class}
    if n_pairs < 5:
        return {"verdict": "pilot_only", "decisive_claim": False,
                "reason": "fewer than five pairs: pilot only, not a significance guarantee",
                "evidence_class": "pilot_only"}
    if summary is None:
        return {"verdict": "no-verdict", "decisive_claim": False,
                "reason": "no paired summary", "evidence_class": evidence_class}
    mean = summary.get("mean")
    ci = summary.get("ci95_bootstrap_mean")
    direction = summary.get("direction")
    if floor_j is None:
        return {
            "verdict": "indicative" if direction else "no-verdict",
            "decisive_claim": False,
            "reason": ("identity floor (floor_j) absent: a decisive superiority claim is "
                       "refused; read this as indicative evidence only"),
            "effect": {"mean": mean, "ci95": ci},
            "evidence_class": evidence_class,
        }
    floor = abs(float(floor_j))
    if mean is None or ci is None:
        return {"verdict": "inconclusive", "decisive_claim": False,
                "reason": "paired summary is incomplete", "evidence_class": evidence_class}
    if mean < 0 and ci[1] < -floor:
        return {"verdict": "a-beats-b", "decisive_claim": True,
                "reason": f"95% CI upper bound {ci[1]:.6g} clears -floor_j ({-floor:.6g})",
                "effect": {"mean": mean, "ci95": ci}, "evidence_class": evidence_class}
    if mean > 0 and ci[0] > floor:
        return {"verdict": "b-beats-a", "decisive_claim": True,
                "reason": f"95% CI lower bound {ci[0]:.6g} clears +floor_j ({floor:.6g})",
                "effect": {"mean": mean, "ci95": ci}, "evidence_class": evidence_class}
    if abs(mean) <= floor:
        return {"verdict": "inconclusive", "decisive_claim": False,
                "reason": f"effect |{mean:.6g}| is within the identity floor {floor:.6g}",
                "effect": {"mean": mean, "ci95": ci}, "evidence_class": evidence_class}
    return {"verdict": "no-verdict", "decisive_claim": False,
            "reason": f"95% CI {ci} does not clear the identity floor {floor:.6g}",
            "effect": {"mean": mean, "ci95": ci}, "evidence_class": evidence_class}


def report(plan_path: Path, results: dict[str, list[Path]], out: Path) -> dict:
    plan_path = Path(plan_path)
    plan = read_json(plan_path)
    if not isinstance(plan, dict) or plan.get("schema") != PLAN_SCHEMA:
        raise fail(f"{plan_path}: not a {PLAN_SCHEMA} plan")
    plan_arms = {a["id"]: a for a in plan.get("arms") or []}
    if not plan_arms:
        raise fail(f"{plan_path}: plan declares no arms")
    undeclared = sorted(set(results) - set(plan_arms))
    if undeclared:
        raise fail(f"results declare undeclared arm(s) {undeclared}")
    input_dirs: list[Path] = []
    for dirs in results.values():
        input_dirs.extend(dirs)
    _guard_output(out, inputs=input_dirs)
    out = Path(out).resolve()

    seeds = [int(s) for s in plan.get("seeds") or []]
    if not seeds:
        raise fail(f"{plan_path}: plan declares no seeds")

    arm_records: list[dict] = []
    loaded: dict[str, dict[int, dict]] = {}
    for arm_id, arm in plan_arms.items():
        if arm_id not in results:
            # A partial report is allowed; every *reported* arm must carry its full
            # declared seed set, and a predeclared pair needs both arms below.
            continue
        runs: list[dict] = []
        by_seed: dict[int, dict] = {}
        for d in results[arm_id]:
            run = load_run(Path(d))
            seed = _seed_of_run(run)
            if seed is None:
                raise fail(f"{run['run_dir']}: run.json has no integer cma_seed "
                           "(and no BO mirror bo_seed)")
            # Keep the shared helpers (replicate_summary, ab_compare) seeing the same
            # declared seed for CMA and mirrored BO/TuRBO run dirs.
            run.setdefault("meta", {})["cma_seed"] = seed
            if seed in by_seed:
                raise fail(f"arm {arm_id!r}: seed {seed} appears in more than one run "
                           "(duplicate seed run dirs)")
            by_seed[seed] = run
            runs.append(run)
        missing = sorted(set(seeds) - set(by_seed))
        extra = sorted(set(by_seed) - set(seeds))
        if missing:
            raise fail(f"arm {arm_id!r}: missing declared seed(s) {missing}")
        if extra:
            raise fail(f"arm {arm_id!r}: run seed(s) {extra} are not in the declared seed set "
                       f"{seeds}")
        # sorted by seed so curves/pairs are deterministic
        runs = [by_seed[s] for s in seeds]
        loaded[arm_id] = by_seed

        run_identities = []
        for run in runs:
            ident = _config_identity(run.get("config") or {})
            if ident["hash"] != plan["identity"]["hash"]:
                diff = sorted(k for k in plan["identity"]["fields"]
                              if plan["identity"]["fields"].get(k)
                              != ident["fields"].get(k))
                raise fail(f"arm {arm_id!r} run {run['run_dir']}: identity mismatch in "
                           f"{diff}; cross-task/brief/version comparisons are refused")
            meta = run.get("meta") or {}
            if meta.get("objective_version") != plan.get("objective_version"):
                raise fail(f"arm {arm_id!r} run {run['run_dir']}: objective version "
                           f"{meta.get('objective_version')} != plan {plan.get('objective_version')}")
            if str(meta.get("family")) != str(plan.get("family")):
                raise fail(f"arm {arm_id!r} run {run['run_dir']}: family {meta.get('family')!r} "
                           f"!= plan {plan.get('family')!r}")
            run_identities.append({"run_id": Path(run["run_dir"]).name,
                                   "seed": by_seed_seed(run), "identity_sha16": ident["hash"],
                                   "fingerprint": run_fingerprint_safe(run)})

        curves = []
        for run in runs:
            curve = best_so_far_curve(run, include_failed_seconds=True)
            curves.append({"run_id": Path(run["run_dir"]).name,
                           "seed": by_seed_seed(run),
                           "curve": curve,
                           "final_best": curve[-1]["best"] if curve else None})
        finals = [c["final_best"] for c in curves if c["final_best"] is not None]
        ledgers = [_ledger(run) for run in runs]
        cost = _sum_ledgers(ledgers)
        parity = _parity_check(arm, runs)
        arm_records.append({
            "id": arm_id,
            "algorithm": arm.get("algorithm"),
            "expected_information": arm.get("expected_information"),
            "seeds": seeds,
            "n_runs": len(runs),
            "runs": [{"run_dir": str(run["run_dir"]), "seed": by_seed_seed(run),
                      "identity": ident} for run, ident in zip(runs, run_identities)],
            "identity_hash": plan["identity"]["hash"],
            "identity_equal": True,
            "final_best": {
                "median": float(np.median(finals)) if finals else None,
                "min": min(finals) if finals else None,
                "max": max(finals) if finals else None,
                "spread": (max(finals) - min(finals)) if len(finals) >= 2 else 0.0 if finals else None,
            },
            "curves": curves,
            "median_curve": _median_curve([c["curve"] for c in curves]),
            "cost": cost,
            "cost_per_run": [{"run_id": Path(run["run_dir"]).name,
                              "seed": by_seed_seed(run), "ledger": led} for run, led in zip(runs, ledgers)],
            "replicates": replicate_summary(runs),
            "information_parity": parity,
        })

    pair_records = []
    for pair in plan.get("pairs") or []:
        a, b = pair["a"], pair["b"]
        if a not in loaded or b not in loaded:
            raise fail(f"pair {pair.get('label')!r} references an arm with no loaded runs")
        a_dirs = [Path(loaded[a][s]["run_dir"]) for s in seeds]
        b_dirs = [Path(loaded[b][s]["run_dir"]) for s in seeds]
        pair_list = [(f"{pair.get('label', a + '_vs_' + b)}_s{s}", a_dirs[i], b_dirs[i])
                     for i, s in enumerate(seeds)]
        delegated = ab_compare.analyse(
            a_dirs, b_dirs, label_a=a, label_b=b, pairs=pair_list,
            target_j=plan.get("target_j"), budget=plan.get("budget"),
            cost_budget=plan.get("cost_budget_s"),
            practical_delta=plan.get("practical_delta"))
        summary = ((delegated.get("paired") or {}).get("summaries") or {}).get("summary")
        n_pairs = int((summary or {}).get("n_pairs") or 0)
        compat_blocked = bool((delegated.get("paired") or {}).get("compatibility_blocked")
                              or not (delegated.get("compatibility") or {}).get("compatible_for_inference"))
        parity_blocked = any(rec["information_parity"]["status"] == "blocking"
                             for rec in arm_records if rec["id"] in (a, b))
        evidence = (summary or {}).get("evidence_class") or (
            "pilot_only" if n_pairs < 5 else ("pilot" if n_pairs < 10 else "larger_pilot"))
        verdict = _floor_verdict(summary, floor_j=plan.get("floor_j"), n_pairs=n_pairs,
                                 blocked=compat_blocked or parity_blocked,
                                 evidence_class=evidence)
        pair_records.append({
            "pair": pair.get("label") or f"{a}_vs_{b}",
            "a": a,
            "b": b,
            "n_pairs": n_pairs,
            "identity_hash": plan["identity"]["hash"],
            "compatibility_blocked": compat_blocked,
            "information_parity_blocked": parity_blocked,
            "ab_compare": delegated,
            "verdict": verdict,
        })

    decisive = [{"pair": p["pair"], "verdict": p["verdict"]["verdict"]}
                for p in pair_records if p["verdict"].get("decisive_claim")]
    overall = {
        "floor_j": plan.get("floor_j"),
        "floor_present": plan.get("floor_j") is not None,
        "decisive_pairs": decisive,
        "any_decisive": bool(decisive),
        "evidence_class": ("pilot" if seeds and len(seeds) < 10 else "larger_pilot"),
        "note": ("A decisive claim requires a declared floor_j and at least five pairs; "
                 "absence of either yields indicative/pilot-only labels."),
    }
    payload = {
        "schema": REPORT_SCHEMA,
        "plan": {
            "path": str(plan_path.resolve()),
            "task": plan.get("task"),
            "objective_version": plan.get("objective_version"),
            "family": plan.get("family"),
            "base_config": plan.get("base_config"),
            "brief": plan.get("brief"),
            "seeds": seeds,
            "budget": plan.get("budget"),
            "cost_budget_s": plan.get("cost_budget_s"),
            "target_j": plan.get("target_j"),
            "practical_delta": plan.get("practical_delta"),
            "floor_j": plan.get("floor_j"),
            "identity": plan.get("identity"),
        },
        "dispatched": False,
        "advisory_only": True,
        "arms": arm_records,
        "pairs": pair_records,
        "overall": overall,
        "limitations": (
            "Advisory offline analysis only. No GPU work, search or solve was launched. "
            "Cost ledgers keep attempts separate from successful BEM calls; wall_span is "
            "null when run timestamps are absent or partial. J is never ranked across "
            "tasks, briefs, families or objective versions. Five pairs is a pilot, not a "
            "significance guarantee. A decisive superiority claim needs a declared "
            "identity floor (floor_j)."),
    }
    write_report(out, TOOL_REPORT, payload, _report_md(payload))
    return payload


def by_seed_seed(run: dict):
    return _seed_of_run(run)


def run_fingerprint_safe(run: dict) -> dict:
    """A small, JSON-able provenance record; never raises on a sparse synthetic run."""
    from _common import run_fingerprint

    try:
        fp = run_fingerprint(run)
    except Exception:  # noqa: BLE001 - provenance is best-effort, identity is the gate
        return {}
    return {k: fp.get(k) for k in ("brief", "family", "objective_version", "mode",
                                   "grid_hash", "target_hash", "config_sha",
                                   "software_hash", "software_unknown")}


def _report_md(payload: dict) -> str:
    p = payload["plan"]
    lines = [
        "# Matched benchmark report (advisory)", "",
        f"**Task:** {p['task']}  ",
        f"**Plan:** `{p['path']}`  ",
        f"**Objective version:** {p['objective_version']} · **Family:** {p['family']}  ",
        f"**Seeds:** {p['seeds']}  ",
        f"**Budget:** {p['budget']} · **Target J:** {p['target_j']} · "
        f"**Practical delta:** {p['practical_delta']} · **Floor J:** {p['floor_j']}  ",
        f"**Identity hash:** `{(p.get('identity') or {}).get('hash')}`", "",
        f"> {payload['limitations']}", "",
        "## Per-arm cost and outcome", "",
        "| arm | algorithm | runs | final best (median) | attempts new | valid new | "
        "cache hits | BEM observed | BEM inferred | BEM seconds | wall span | overhead |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in payload["arms"]:
        c = arm["cost"]
        e = c.get("elapsed_seconds") or {}
        lines.append(
            f"| `{arm['id']}` | {arm['algorithm']} | {arm['n_runs']} | "
            f"{fmt(arm['final_best']['median'])} | {c.get('attempts_new')} | "
            f"{c.get('valid_evaluations_new')} | {c.get('cache_hits')} | "
            f"{c.get('actual_bem_calls_observed')} | {c.get('actual_bem_calls_inferred')} | "
            f"{fmt(c.get('actual_bem_seconds'))} | {fmt(e.get('wall_span'))} | "
            f"{fmt(e.get('unaccounted_overhead'))} |")
    lines += ["", "## Information parity", "",
              "| arm | status | blocking | disclosures |", "|---|---|---|---|"]
    for arm in payload["arms"]:
        parity = arm["information_parity"]
        lines.append(f"| `{arm['id']}` | {parity['status']} | "
                     f"{', '.join(parity['blocking']) or '—'} | "
                     f"{', '.join(parity['disclosures']) or '—'} |")
    lines += ["", "## Predeclared paired comparisons", ""]
    if not payload["pairs"]:
        lines += ["No pairs were predeclared; no prospective paired inference is available.", ""]
    else:
        lines += ["| pair | n pairs | mean d (A−B) | 95% CI | verdict | decisive | evidence |",
                  "|---|---:|---:|---|---|---|---|"]
        for pair in payload["pairs"]:
            v = pair["verdict"]
            eff = v.get("effect") or {}
            lines.append(
                f"| {pair['pair']} | {pair['n_pairs']} | {fmt(eff.get('mean'))} | "
                f"{fmt(eff.get('ci95'))} | **{v['verdict']}** | {v['decisive_claim']} | "
                f"{v.get('evidence_class')} |")
        lines.append("")
        for pair in payload["pairs"]:
            lines.append(f"- {pair['pair']}: {pair['verdict'].get('reason')}")
        lines.append("")
    o = payload["overall"]
    lines += ["## Overall", "",
              f"- floor present: {o['floor_present']} (floor_j={o['floor_j']})",
              f"- decisive pairs: {o['decisive_pairs'] or 'none'}",
              f"- evidence class: {o['evidence_class']}",
              f"- {o['note']}", ""]
    return "\n".join(lines)


def fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(fmt(v) for v in value) + "]"
    try:
        return f"{float(value):.6g}"
    except (TypeError, ValueError):
        return str(value)


# ------------------------------------------------------------------ CLI


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("plan", help="validate a spec and derive a matched benchmark plan")
    pp.add_argument("--spec", required=True)
    pp.add_argument("--out", required=True)
    pp.add_argument("--pilot", action="store_true",
                    help="relabel a plan with fewer than five seeds as a pilot")

    rp = sub.add_parser("report", help="compare completed matched run directories offline")
    rp.add_argument("--plan", required=True)
    rp.add_argument("--results", action="append", required=True,
                    help="<arm>=<run_dir>[,<run_dir>...] (repeat per arm)")
    rp.add_argument("--out", required=True)

    args = ap.parse_args(argv)
    if args.cmd == "plan":
        plan_spec(Path(args.spec), Path(args.out), pilot=args.pilot)
        print(f"benchmark_plan OK: -> {Path(args.out).resolve()} (dispatched: false)")
        return 0
    results = _parse_results(args.results)
    report(Path(args.plan), results, Path(args.out))
    print(f"benchmark_report OK: {len(results)} arm(s) -> {Path(args.out).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
