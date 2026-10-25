"""Multi-family typology campaign (TYPOLOGY_PLAN.md s7, LANE B).

    hornlab-search campaign --brief PATH --families SPEC --tier dry-run|screen|compare
                            [--seeds N] [--budget N] [--runs-dir DIR]

Runs each family search as a FRESH SUBPROCESS so GPU workers are fully isolated.
Writes campaign.json + leaderboard.md under <runs-dir>/campaign_<UTC>/
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import yaml

log = logging.getLogger("hornlab_search.search.campaign")

REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "examples"

# Fixed CMA seed sequence (TYPOLOGY_PLAN.md s7)
CMA_SEED_LIST = [1234, 777, 4242, 9999, 31415, 271828, 65537, 12345]

TIER_DRY_RUN = "dry-run"
TIER_SCREEN = "screen"
TIER_COMPARE = "compare"
ALL_TIERS = (TIER_DRY_RUN, TIER_SCREEN, TIER_COMPARE)

# Groups the "--families" SPEC can name
GROUP_NAMES = ("classical", "magnus", "hybrid", "legacy")


# ------------------------------------------------------------------ brief loading


def load_brief(path) -> dict:
    """Load and validate a brief YAML file (TYPOLOGY_PLAN.md s3 schema).

    Returns the brief as a plain dict.  Raises ValueError for missing required fields.
    Delegates to ``hornlab_search.config.load_brief`` (one schema; ConfigError is a ValueError).
    """
    from hornlab_search.config import load_brief as _load_brief
    return _load_brief(path)


# ------------------------------------------------------------------ catalog loading


def load_catalog(catalog_path: Path | None = None) -> list[dict]:
    """Load examples/catalog.yaml and return the list of entries."""
    if catalog_path is None:
        catalog_path = EXAMPLES / "catalog.yaml"
    raw = yaml.safe_load(Path(catalog_path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "entries" not in raw:
        raise ValueError(f"{catalog_path}: expected a mapping with 'entries'")
    entries = raw["entries"]
    if not isinstance(entries, list):
        raise ValueError(f"{catalog_path}: 'entries' must be a list")
    return entries


def all_catalog_names(catalog: list[dict]) -> set[str]:
    return {e["name"] for e in catalog}


def catalog_by_name(catalog: list[dict]) -> dict[str, dict]:
    return {e["name"]: e for e in catalog}


# ------------------------------------------------------------------ family SPEC parsing


def resolve_families(spec: str, catalog: list[dict]) -> list[dict]:
    """Expand a comma-separated SPEC into a list of catalog entries.

    SPEC may contain catalog entry names, group names (classical/magnus/hybrid/legacy),
    or 'all'.  Unknown names raise ValueError listing valid ones.
    """
    if not spec or spec.strip().lower() == "all":
        return list(catalog)
    tokens = [t.strip() for t in spec.split(",") if t.strip()]
    by_name = catalog_by_name(catalog)
    all_groups = {e.get("group", "") for e in catalog}
    result: list[dict] = []
    seen_names: set[str] = set()
    unknown = []
    for token in tokens:
        if token in by_name:
            if token not in seen_names:
                result.append(by_name[token])
                seen_names.add(token)
        elif token in all_groups:
            for e in catalog:
                if e.get("group") == token and e["name"] not in seen_names:
                    result.append(e)
                    seen_names.add(e["name"])
        elif token in GROUP_NAMES:
            # Valid group name but no entries yet (e.g. 'classical' before the orchestrator adds them)
            # Not an error; just yields no entries.
            pass
        else:
            unknown.append(token)
    if unknown:
        valid = sorted(by_name) + sorted(all_groups)
        raise ValueError(
            f"unknown family name(s): {unknown}.\n"
            f"Valid names: {', '.join(sorted(set(valid)))}")
    return result


# ------------------------------------------------------------------ compatibility


def is_compatible(entry: dict, brief: dict) -> tuple[bool, str]:
    """Check if a catalog entry is compatible with a brief.

    Returns (ok, reason). Reason is empty when ok=True.

    Current checks:
    - An axisymmetric entry is incompatible with a brief whose coverage_h != coverage_v
      (TYPOLOGY_PLAN.md s7, R4).
    - WP2 (senior pass 2026-10-24): an entry tied to its own driver exit (catalog key
      ``driver_exit_mm``, e.g. osse_baseline's 1.4-inch throat) cannot compete under a brief with
      a different driver — the campaign SKIPs it with the reason printed, instead of comparing
      across different objectives.
    """
    entry_sym = entry.get("symmetry", "hv")
    brief_sym = brief.get("symmetry", "hv")
    target = brief.get("target", {})
    h = float(target.get("coverage_h_deg", 0))
    v = float(target.get("coverage_v_deg", 0))
    if entry_sym == "axisymmetric" and abs(h - v) > 1e-6:
        return False, (
            f"entry symmetry 'axisymmetric' is incompatible with brief coverage_h={h} != coverage_v={v}; "
            "axisymmetric families require coverage_h == coverage_v"
        )
    tied_exit = entry.get("driver_exit_mm")
    if tied_exit is not None:
        brief_exit = (brief.get("driver") or {}).get("exit_radius_mm")
        if isinstance(brief_exit, (int, float)) and abs(float(brief_exit) - float(tied_exit)) > 0.01:
            tied_brief = entry.get("brief_tied") or "its own brief"
            return False, (
                f"entry is tied to its {float(tied_exit):g} mm driver exit ({tied_brief}); the "
                f"campaign brief '{brief.get('name', '?')}' has a {float(brief_exit):g} mm exit; "
                "skip (WP2 driver fairness, senior pass 2026-10-24)"
            )
    return True, ""


# ------------------------------------------------------------------ budget / seeds


def budget_for_tier(tier: str, n_keys: int, budget_override: int | None = None) -> int:
    """Compute the search budget for a given tier and number of searchable keys.

    screen: max(40, 10*n_keys), 1 seed
    compare: max(150, 25*n_keys), 2 seeds
    dry-run: N/A (no budget needed)
    """
    if budget_override is not None:
        return int(budget_override)
    if tier == TIER_SCREEN:
        return max(40, 10 * n_keys)
    if tier == TIER_COMPARE:
        return max(150, 25 * n_keys)
    return 0  # dry-run tier doesn't need a budget


def seeds_for_tier(tier: str, n_seeds: int | None = None) -> list[int]:
    """Return the CMA seed list for a tier.

    screen: 1 seed (first from CMA_SEED_LIST)
    compare: default 2 seeds; n_seeds overrides the count
    dry-run: 1 seed (the first, used only for the dry-run subprocess)
    """
    if tier == TIER_DRY_RUN:
        return [CMA_SEED_LIST[0]]
    if tier == TIER_SCREEN:
        n = n_seeds if n_seeds is not None else 1
    else:  # compare
        n = n_seeds if n_seeds is not None else 2
    return CMA_SEED_LIST[: max(1, n)]


# ------------------------------------------------------------------ run dir location


_SEARCH_OK_RE = re.compile(r"search OK:.*rows in (.+search\.ndjson)", re.IGNORECASE)


def find_run_dir(stdout: str, runs_dir: Path, start_time: float) -> Path | None:
    """Locate a search run directory from subprocess stdout.

    Primary: parse the 'search OK: ... rows in <path>' line.
    Fallback: newest directory in runs_dir created after start_time.
    """
    for line in stdout.splitlines():
        m = _SEARCH_OK_RE.search(line)
        if m:
            p = Path(m.group(1).strip()).parent
            if p.is_dir():
                return p
    # fallback: newest dir created after start_time
    candidates = []
    for d in Path(runs_dir).glob("*"):
        if d.is_dir():
            try:
                ctime = d.stat().st_ctime
                if ctime >= start_time:
                    candidates.append((ctime, d))
            except OSError:
                pass
    if candidates:
        return max(candidates)[1]
    return None


# ------------------------------------------------------------------ leaderboard helpers


def read_run_json(run_dir: Path) -> dict:
    f = run_dir / "run.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {}


def read_ndjson(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows


def best_objective(rows: list[dict]) -> float | None:
    ok = [r for r in rows if r.get("ok") and r.get("objective") is not None]
    if not ok:
        return None
    return min(float(r["objective"]) for r in ok)


def _pinned_bounds(rows: list[dict], run_dir: Path) -> list[str]:
    """Return list of keys where >= 4 of the top-6 distinct designs lie within 2% of a bound.

    Reads bounds from run_dir/config.yaml.  For generator configs the row params are FREEFORM
    keys; if a row has a 'generator.knobs' block use those values instead (TYPOLOGY_PLAN.md s7).
    Returns [] when fewer than 4 successful rows or config cannot be read.
    """
    cfg_path = run_dir / "config.yaml"
    if not cfg_path.exists():
        return []
    try:
        cfg_raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        bounds_raw = cfg_raw.get("bounds", {})
    except Exception:  # noqa: BLE001
        return []
    ok_rows = [r for r in rows if r.get("ok") and r.get("objective") is not None]
    ok_rows.sort(key=lambda r: float(r["objective"]))
    # top-6 distinct designs
    seen, top6 = set(), []
    for r in ok_rows:
        h = r.get("design_hash") or str(r.get("params", {}))
        if h not in seen:
            seen.add(h)
            top6.append(r)
            if len(top6) == 6:
                break
    if len(top6) < 4:
        return []
    pinned = []
    for key, bspec in bounds_raw.items():
        lo = bspec.get("lo")
        hi = bspec.get("hi")
        if lo is None or hi is None or lo == hi:
            continue
        span = float(hi) - float(lo)
        if span <= 0:
            continue
        threshold = 0.02 * span
        n_near = 0
        for r in top6:
            # Try generator knobs first, then params
            gen = r.get("generator") or {}
            knobs = gen.get("knobs") if isinstance(gen, dict) else None
            source = knobs if knobs else r.get("params", {})
            val = source.get(key)
            if val is None:
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            if abs(v - float(lo)) <= threshold or abs(v - float(hi)) <= threshold:
                n_near += 1
        if n_near >= 4:
            pinned.append(key)
    return pinned


def _loading_scalars(rows: list[dict]) -> dict | None:
    """Extract loading scalars from the best row's metrics.scalars if present."""
    ok_rows = [r for r in rows if r.get("ok") and r.get("objective") is not None]
    if not ok_rows:
        return None
    best = min(ok_rows, key=lambda r: float(r["objective"]))
    metrics = best.get("metrics") or {}
    if isinstance(metrics, dict):
        scalars = metrics.get("scalars") or {}
        if isinstance(scalars, dict):
            out = {}
            for k in ("f_load_hz", "z_ripple", "z_mean_band"):
                if k in scalars:
                    out[k] = scalars[k]
            return out if out else None
    return None


# ------------------------------------------------------------------ per-entry result


@dataclass
class JobResult:
    entry_name: str
    seed: int
    run_dir: Path | None = None
    returncode: int = -1
    stdout: str = ""
    stderr: str = ""
    rows: list[dict] = field(default_factory=list)
    best_j: float | None = None
    error: str | None = None
    stats: dict = field(default_factory=dict)
    pinned: list[str] = field(default_factory=list)
    loading_scalars: dict | None = None
    wall_seconds: float = 0.0
    hygiene_before: dict = field(default_factory=dict)
    hygiene_after: dict = field(default_factory=dict)


@dataclass
class EntryResult:
    entry: dict
    jobs: list[JobResult] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""

    @property
    def best_j_values(self) -> list[float]:
        return [j.best_j for j in self.jobs if j.best_j is not None]

    def median_best_j(self) -> float | None:
        vals = sorted(self.best_j_values)
        if not vals:
            return None
        n = len(vals)
        mid = n // 2
        return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0

    def spread_best_j(self) -> float | None:
        vals = self.best_j_values
        if len(vals) < 2:
            return None
        return max(vals) - min(vals)


# ------------------------------------------------------------------ subprocess execution


#: Seconds a Ctrl-C'd child search gets to finish its own clean-up before it is killed.
INTERRUPT_GRACE_S = 60.0


class CampaignInterrupted(Exception):
    """Ctrl-C during a job; carries the partial job so the leaderboard can still be written."""

    def __init__(self, job):
        super().__init__("campaign interrupted")
        self.job = job


def _after_job_hygiene(hyg, entry: dict, seed: int) -> dict:
    """Snapshot what the search left behind, then clear this project's Julia / BEAT worker hosts
    (CLAUDE.md GPU rule 6: a run script ends by clearing its workers; each job starts clean)."""
    snap = hyg.hygiene_snapshot(f"after:{entry['name']}:{seed}")
    clear = getattr(hyg, "clear_julia", None)
    if callable(clear) and snap.get("julia_project_procs"):
        try:
            snap["cleared_pids"] = clear()
        except Exception as exc:  # noqa: BLE001 - hygiene must not end a campaign
            log.warning("campaign: clearing hosts failed: %s", exc)
    return snap


def _build_search_argv(entry: dict, brief_path: Path, budget: int, seed: int,
                       runs_dir: Path, mode: str = "screen") -> list[str]:
    """Build the argv for a search subprocess."""
    cfg = str(EXAMPLES / entry["config"])
    return [
        sys.executable, "-m", "hornlab_search.cli",
        "search",
        "--config", cfg,
        "--brief", str(brief_path),
        "--budget", str(budget),
        "--max-evals", str(budget),   # equal search per family: cached replays count too
        "--cma-seed", str(seed),
        "--mode", mode,
        "--runs-dir", str(runs_dir),
    ]


def _build_dry_run_argv(entry: dict, brief_path: Path, runs_dir: Path) -> list[str]:
    """Build the argv for a dry-run subprocess."""
    cfg = str(EXAMPLES / entry["config"])
    return [
        sys.executable, "-m", "hornlab_search.cli",
        "run",
        "--config", cfg,
        "--brief", str(brief_path),
        "--dry-run",
        "--runs-dir", str(runs_dir),
    ]


def run_job(entry: dict, brief_path: Path, seed: int, budget: int,
            runs_dir: Path, tier: str,
            hygiene_module=None) -> JobResult:
    """Run a single search (or dry-run) subprocess and collect its results."""
    from . import hygiene as _hygiene_default
    hyg = hygiene_module or _hygiene_default

    job = JobResult(entry_name=entry["name"], seed=seed)
    job.hygiene_before = hyg.hygiene_snapshot(f"before:{entry['name']}:{seed}")

    if tier == TIER_DRY_RUN:
        argv = _build_dry_run_argv(entry, brief_path, runs_dir)
    else:
        argv = _build_search_argv(entry, brief_path, budget, seed, runs_dir)

    log.info("campaign: running %s", " ".join(argv))
    t0 = time.time()
    interrupted = False
    try:
        with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
            try:
                out, err = proc.communicate()
            except KeyboardInterrupt:
                # Ctrl-C reaches the child too (same console): let it finish its own clean-up (run.json
                # 'interrupted', lock, detach) instead of killing it mid-write, as subprocess.run would.
                interrupted = True
                try:
                    out, err = proc.communicate(timeout=INTERRUPT_GRACE_S)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    out, err = proc.communicate()
        job.returncode, job.stdout, job.stderr = proc.returncode, out or "", err or ""
    except Exception as exc:  # noqa: BLE001
        job.returncode = -1
        job.error = str(exc)
        job.wall_seconds = time.time() - t0
        job.hygiene_after = _after_job_hygiene(hyg, entry, seed)
        return job
    job.wall_seconds = time.time() - t0

    job.hygiene_after = _after_job_hygiene(hyg, entry, seed)

    if interrupted:
        job.error = "interrupted (Ctrl-C)"
        job.run_dir = find_run_dir(job.stdout, runs_dir, t0)
        if job.run_dir is not None:
            job.rows = read_ndjson(job.run_dir / "search.ndjson")
            job.best_j = best_objective(job.rows)
        raise CampaignInterrupted(job)

    if job.returncode != 0:
        job.error = f"subprocess exited {job.returncode}"
        return job

    if tier == TIER_DRY_RUN:
        return job  # dry-run: no ndjson to read

    # locate run dir
    job.run_dir = find_run_dir(job.stdout, runs_dir, t0)
    if job.run_dir is None:
        job.error = "could not locate run directory from subprocess output"
        return job

    ndjson_path = job.run_dir / "search.ndjson"
    job.rows = read_ndjson(ndjson_path)
    job.best_j = best_objective(job.rows)

    run_json = read_run_json(job.run_dir)
    job.stats = run_json.get("stats", {})

    job.pinned = _pinned_bounds(job.rows, job.run_dir)
    job.loading_scalars = _loading_scalars(job.rows)
    return job


# ------------------------------------------------------------------ campaign runner


def run_campaign(
    brief_path: Path,
    families_spec: str,
    tier: str,
    runs_dir: Path,
    n_seeds: int | None = None,
    budget_override: int | None = None,
    catalog_path: Path | None = None,
    hygiene_module=None,
) -> dict:
    """Run the full campaign and return a results dict.

    Returns a dict with:
      - 'campaign_dir': Path of the campaign output directory
      - 'brief': the loaded brief dict
      - 'entries': list of EntryResult
      - 'catalog': list of catalog entries loaded
    """
    from . import hygiene as _hygiene_default
    hyg = hygiene_module or _hygiene_default

    brief = load_brief(brief_path)
    catalog = load_catalog(catalog_path)
    selected = resolve_families(families_spec, catalog)
    seeds = seeds_for_tier(tier, n_seeds)

    # Campaign directory
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    campaign_dir = runs_dir / f"campaign_{stamp}"
    campaign_dir.mkdir(parents=True, exist_ok=True)

    entry_results: list[EntryResult] = []

    for entry in selected:
        er = EntryResult(entry=entry)
        ok, reason = is_compatible(entry, brief)
        if not ok:
            er.skipped = True
            er.skip_reason = reason
            log.info("campaign: skipping %s — %s", entry["name"], reason)
            entry_results.append(er)
            continue

        # Count searchable keys
        n_keys = _count_keys(entry)
        budget = budget_for_tier(tier, n_keys, budget_override)

        try:
            for seed in seeds:
                log.info("campaign: %s seed %d budget %d tier %s", entry["name"], seed, budget, tier)
                job = run_job(entry, brief_path, seed, budget, runs_dir, tier,
                              hygiene_module=hyg)
                er.jobs.append(job)
        except CampaignInterrupted as ci:
            er.jobs.append(ci.job)
            entry_results.append(er)
            results = {"campaign_dir": campaign_dir, "brief": brief, "entries": entry_results,
                       "catalog": catalog, "tier": tier, "seeds": seeds, "interrupted": True}
            _write_campaign_output(results, campaign_dir)     # partial leaderboard, marked INTERRUPTED
            raise KeyboardInterrupt(str(campaign_dir)) from None

        entry_results.append(er)

    results = {
        "campaign_dir": campaign_dir,
        "brief": brief,
        "entries": entry_results,
        "catalog": catalog,
        "tier": tier,
        "seeds": seeds,
    }
    _write_campaign_output(results, campaign_dir)
    return results


def _count_keys(entry: dict) -> int:
    """Number of searchable keys of an entry, read straight from its YAML ``bounds`` (a bound is
    searchable unless ``search: false``). Brief-independent: loading the full config would need
    the brief for generator configs, and a silent fallback once gave them the wrong budget."""
    cfg_path = EXAMPLES / entry["config"]
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    bounds = raw.get("bounds") or {}
    return sum(1 for b in bounds.values() if isinstance(b, dict) and b.get("search", True))


# ------------------------------------------------------------------ output


def _write_campaign_output(results: dict, campaign_dir: Path) -> None:
    """Write campaign.json and leaderboard.md to campaign_dir."""
    _write_campaign_json(results, campaign_dir / "campaign.json")
    _write_leaderboard_md(results, campaign_dir / "leaderboard.md")
    log.info("campaign output: %s", campaign_dir)


def _write_campaign_json(results: dict, path: Path) -> None:
    entry_list = []
    for er in results["entries"]:
        jobs_data = []
        for j in er.jobs:
            jobs_data.append({
                "seed": j.seed,
                "run_dir": str(j.run_dir) if j.run_dir else None,
                "returncode": j.returncode,
                "best_j": j.best_j,
                "error": j.error,
                "stats": j.stats,
                "pinned_bounds": j.pinned,
                "loading_scalars": j.loading_scalars,
                "wall_seconds": j.wall_seconds,
                "hygiene_before": j.hygiene_before,
                "hygiene_after": j.hygiene_after,
            })
        entry_list.append({
            "name": er.entry["name"],
            "group": er.entry.get("group"),
            "symmetry": er.entry.get("symmetry"),
            "skipped": er.skipped,
            "skip_reason": er.skip_reason,
            "jobs": jobs_data,
            "median_best_j": er.median_best_j(),
            "spread_best_j": er.spread_best_j(),
        })

    out = {
        "tier": results["tier"],
        "brief_name": results["brief"].get("name"),
        "seeds": results["seeds"],
        "interrupted": bool(results.get("interrupted")),
        "entries": entry_list,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")


def _write_leaderboard_md(results: dict, path: Path) -> None:
    lines = [
        f"# Campaign leaderboard",
        f"",
        f"**Tier:** {results['tier']}  |  **Brief:** {results['brief'].get('name')}",
        f"**Seeds:** {results['seeds']}",
        f"",
    ]
    if results.get("interrupted"):
        lines += ["**INTERRUPTED (Ctrl-C): partial results; entries after the interrupted one did not run.**", ""]
    lines += [
        f"| Name | Group | Sym | Keys | Best J | Med J | Spread | Evals | Failures | Pinned | Note |",
        f"|------|-------|-----|------|--------|-------|--------|-------|----------|--------|------|",
    ]
    for er in results["entries"]:
        name = er.entry["name"]
        group = er.entry.get("group", "")
        sym = er.entry.get("symmetry", "")[:3]
        if er.skipped:
            lines.append(f"| {name} | {group} | {sym} | - | - | - | - | - | - | - | SKIP: {er.skip_reason[:40]} |")
            continue
        keys = _count_keys(er.entry)
        best_vals = er.best_j_values
        best_j = f"{min(best_vals):.5g}" if best_vals else "n/a"
        med_j = f"{er.median_best_j():.5g}" if er.median_best_j() is not None else "n/a"
        spread = f"{er.spread_best_j():.4g}" if er.spread_best_j() is not None else "n/a"
        # aggregate stats from first job
        evals = "n/a"
        failures = "n/a"
        if er.jobs:
            j0 = er.jobs[0]
            st = j0.stats
            evals = str(st.get("evaluations", "n/a"))
            fbr = st.get("failures_by_reason") or {}
            failures = ",".join(f"{k}:{v}" for k, v in fbr.items()) if fbr else "0"
        pinned = ",".join(er.jobs[0].pinned) if er.jobs else ""
        note = ""
        if er.jobs and er.jobs[0].error:
            note = f"ERR: {er.jobs[0].error[:30]}"
        elif not best_vals and er.jobs:
            # every evaluation invalid: CMA-ES stops on a flat penalty landscape after ~1 generation
            note = ("NO VALID DESIGN: seed is invalid under this brief (usually outside its size "
                    "envelope); needs a config sized for the brief")
        lines.append(f"| {name} | {group} | {sym} | {keys} | {best_j} | {med_j} | {spread} | {evals} | {failures} | {pinned} | {note} |")

    lines += ["", f"Generated {datetime.now(timezone.utc).isoformat()}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------------------ compact table print


def print_compact_table(results: dict) -> None:
    """Print a compact table of results to stdout."""
    brief = results["brief"]
    print(f"\ncampaign: tier={results['tier']} brief={brief.get('name')} "
          f"seeds={results['seeds']}")
    header = f"{'Name':<20} {'Sym':5} {'Keys':4} {'Best J':>10} {'Evals':>6} {'Err':>4}"
    print(header)
    print("-" * len(header))
    for er in results["entries"]:
        name = er.entry["name"]
        sym = (er.entry.get("symmetry", ""))[:3]
        if er.skipped:
            print(f"  {name:<18} {sym:5}  {'SKIPPED':>28}  {er.skip_reason[:40]}")
            continue
        keys = _count_keys(er.entry)
        best_j = er.best_j_values
        best_str = f"{min(best_j):.5g}" if best_j else "n/a"
        evals = "n/a"
        err_count = sum(1 for j in er.jobs if j.error or j.returncode != 0)
        if er.jobs:
            j0 = er.jobs[0]
            evals = str(j0.stats.get("evaluations", "n/a"))
        print(f"  {name:<18} {sym:5} {keys:4} {best_str:>10} {evals:>6} {err_count:>4}")
    print(f"\ncampaign: output in {results['campaign_dir']}")
