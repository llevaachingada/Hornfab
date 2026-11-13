r"""Deterministic offline fake-evaluator harness for S9 / bo-study-v1.1.

This tool is **preparation only**. It never imports a solver or a mesher, never
starts a process, and never writes an acoustic record. It synthesises
``search.ndjson``-shaped rows and ``stage_timing.ndjson``-shaped rows from a seed,
then replays them through the S3 cost ledger (``tools/analysis/_common.cost_ledger``,
read-only) and a stage reconciliation.

    .\.venv\Scripts\python.exe tools\bench\fake_harness.py --dry-run --seed 7 ^
        --candidates 24 --out scratch\bo_m0\s9\example_dry_run_timing.json

Why it exists: the later A/B matrix (current serial evaluate vs the study-runner
serial path at matched total cost) needs a *rehearsal* of the accounting before a
live lane is authorised. The harness answers "do the counts and seconds reconcile?"
not "how fast is the solver?". Every number it emits is fabricated and labelled
``synthetic``; it is not a throughput, speedup or physics measurement.

Stage rows follow the opt-in ``HORNLAB_STAGE_TIMING`` format written by
``hornlab_search/profiling.py`` (``stage``, ``seconds``, ``design_hash``, ``key``,
``thread``, ``unix_time``). The timer code itself is read-only inspiration and is
not modified. A ``--dry-run`` run writes only the timing JSON (no fixture files,
zero solve processes, zero acoustic records).

Reconciliation rule (also emitted in the JSON):

    elapsed = candidate_total_sum + run_overhead_s + prefetch_wait_s

``candidate_total`` already contains ``mesh_build``, ``solve``, ``metrics``,
``score``, ``cache_store`` and ``persist``; ``solver_path`` and
``meh_inner_optimize`` are nested subsets; ``mesh_prefetch`` runs on another
thread and overlaps the main loop. Summing every stage row therefore overcounts.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.profiling import ENV_FLAG as STAGE_TIMING_ENV  # noqa: E402
from hornlab_search.profiling import FILE_NAME as STAGE_TIMING_FILE  # noqa: E402

SCHEMA = "s9-fake-harness-v1"
STAGE_SCHEMA = "s9-stage-reconciliation-v1"

#: Top-level stages that are already represented by one ``candidate_total`` row.
TOP_LEVEL_STAGES = ("mesh_build", "solve", "metrics", "score", "cache_store", "persist")
#: Stages nested inside another stage; never add them to a candidate total.
NESTED_STAGES = ("solver_path", "meh_inner_optimize")
#: Work measured on a separate thread; it overlaps the main loop.
OVERLAP_STAGES = ("mesh_prefetch",)

REFUSAL_KINDS = ("invalid_geometry", "invalid_envelope", "mesh_too_large")
FIXED_EPOCH = 1_700_000_000.0  # deterministic synthetic timestamps (not wall time)

#: Fabricated per-class stage seconds. These are fixture shapes, NOT measurements.
_CLASSES = {
    "screen_small": {"mesh_build": 0.80, "solve": 4.20, "metrics": 1.10,
                     "score": 0.05, "cache_store": 0.02, "persist": 0.08},
    "screen_mid": {"mesh_build": 1.30, "solve": 8.60, "metrics": 1.60,
                   "score": 0.07, "cache_store": 0.03, "persist": 0.12},
    "verify": {"mesh_build": 1.50, "solve": 17.50, "metrics": 2.80,
               "score": 0.10, "cache_store": 0.04, "persist": 0.15},
}
_CLASS_ORDER = ("screen_small", "screen_mid", "verify")


def _hash(seed, salt: str) -> str:
    return hashlib.sha256(f"{seed}:{salt}".encode("utf-8")).hexdigest()[:16]


_COMMON = None


def _common():
    """Import the S3 cost-ledger module by file path (``tools/`` is not a package)."""
    global _COMMON
    if _COMMON is None:
        path = REPO / "tools" / "analysis" / "_common.py"
        spec = importlib.util.spec_from_file_location("s9_analysis_common", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load S3 ledger helpers from {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _COMMON = module
    return _COMMON


def _ledger(rows: list[dict]) -> dict:
    """Replay the S3 cost-ledger semantics exactly by consuming its public function."""
    cost_ledger = _common().cost_ledger
    cache_hits = sum(1 for r in rows if r.get("cached") is True)
    attempts_new = len(rows) - cache_hits
    failures = sum(1 for r in rows
                   if r.get("cached") is not True and r.get("ok") is not True)
    stats = {
        "evaluations": len(rows),
        "non_cached": attempts_new,
        "cache_hits": cache_hits,
        "failures": failures,
        "total_gpu_seconds": round(sum(float((r.get("seconds") or {}).get("solve") or 0.0)
                                       for r in rows), 9),
        "total_mesh_seconds": round(sum(float((r.get("seconds") or {}).get("mesh") or 0.0)
                                       for r in rows), 9),
    }
    return cost_ledger(rows, stats)


def _durations(rng: random.Random, fixture_class: str, batch_size: int) -> dict:
    base = _CLASSES[fixture_class]
    jitter = rng.uniform(0.95, 1.05)
    # Synthetic batching shape only: it demonstrates a lower solve time, it is not a claim.
    batch_factor = {1: 1.0, 4: 0.65, 12: 0.5}.get(int(batch_size), 0.5)
    out = {}
    for stage in TOP_LEVEL_STAGES:
        value = base[stage] * jitter
        if stage == "solve":
            value *= batch_factor
        out[stage] = round(value, 6)
    return out


def _emit(rows: list[dict], cursor: list[float], stage: str, seconds: float, *,
          design_hash: str, key: str, thread: str = "MainThread",
          advance: bool = True, **meta) -> None:
    if advance:
        cursor[0] = round(cursor[0] + float(seconds), 6)
    row = {
        "stage": stage,
        "seconds": round(float(seconds), 6),
        "design_hash": design_hash,
        "key": key,
        "thread": thread,
        "unix_time": cursor[0],
    }
    row.update(meta)
    rows.append(row)


def synthesize(*, seed: int = 0, candidates: int = 24, cache_hit_rate: float = 0.20,
               refusal_rate: float = 0.15, solver_failure_rate: float = 0.08,
               pipeline_failure_rate: float = 0.04, prefetch_depth: int = 0,
               batch_size: int = 12, meh: bool = False) -> dict:
    """Build one deterministic synthetic run fixture. No file, process or solve is touched."""
    rates = (cache_hit_rate, refusal_rate, solver_failure_rate, pipeline_failure_rate)
    if any(not math.isfinite(float(x)) or x < 0 or x > 1 for x in rates):
        raise ValueError("rates must be finite and in [0, 1]")
    if refusal_rate + solver_failure_rate + pipeline_failure_rate > 1 + 1e-9:
        raise ValueError("refusal + solver_failure + pipeline_failure rates must sum to <= 1")
    if int(candidates) < 0:
        raise ValueError("candidates must be nonnegative")
    if int(batch_size) < 1:
        raise ValueError("batch_size must be >= 1")

    rng = random.Random(int(seed))
    rows: list[dict] = []
    stage_rows: list[dict] = []
    attempts: list[dict] = []
    main_cursor = [FIXED_EPOCH]
    prefetch_cursor = [FIXED_EPOCH]
    candidate_totals: list[float] = []
    first_new = True

    def note_attempt(*, cache: str, outcome: str) -> None:
        nonlocal first_new
        attempts.append({
            "n": len(attempts),
            "cache": cache,
            "outcome": outcome,
            "thermal": "hit" if cache == "hit" else ("cold" if first_new else "warm"),
            # Verification is operator-supplied, never inferred from a synthetic row.
            "verified_useful": None,
        })
        if cache != "hit":
            first_new = False

    for i in range(int(candidates)):
        design_hash = _hash(seed, f"design-{i}")
        key = f"{design_hash}-{_hash(seed, f'key-{i}')}"
        fixture_class = _CLASS_ORDER[i % len(_CLASS_ORDER)]

        if rng.random() < cache_hit_rate:
            replay_s = round(rng.uniform(0.02, 0.12), 6)
            rows.append({
                "n": i, "mode": "screen", "key": key, "design_hash": design_hash,
                "ok": True, "kind": "", "error": "", "cached": True,
                "seconds": {"mesh": 0.0, "solve": 0.0, "total": replay_s},
                "fixture_class": fixture_class, "synthetic": True,
            })
            note_attempt(cache="hit", outcome="cached_valid")
            continue

        draw = rng.random()
        refuse_cut = refusal_rate
        solver_cut = refuse_cut + solver_failure_rate
        pipeline_cut = solver_cut + pipeline_failure_rate

        if draw < refuse_cut:
            kind = REFUSAL_KINDS[i % len(REFUSAL_KINDS)]
            mesh = round(_CLASSES[fixture_class]["mesh_build"] * rng.uniform(0.95, 1.05), 6)
            total = mesh
            rows.append({
                "n": i, "mode": "screen", "key": key, "design_hash": design_hash,
                "ok": False, "kind": kind, "error": f"{kind}: synthetic refusal",
                "cached": False,
                "seconds": {"mesh": mesh, "solve": 0.0, "total": total},
                "fixture_class": fixture_class, "synthetic": True,
            })
            _emit(stage_rows, main_cursor, "mesh_build", mesh,
                  design_hash=design_hash, key=key)
            _emit(stage_rows, main_cursor, "candidate_total", total,
                  design_hash=design_hash, key=key)
            note_attempt(cache="new", outcome="refusal")
            candidate_totals.append(total)
            if prefetch_depth > 0:
                _emit(stage_rows, prefetch_cursor, "mesh_prefetch", mesh,
                      design_hash=design_hash, key=key, thread="prefetch")
            continue

        durations = _durations(rng, fixture_class, batch_size)

        if draw < solver_cut:
            # Alternate a positive solve time (observed BEM work) with a recorded
            # failure that has no positive seconds (an inferred BEM attempt).
            solve = durations["solve"] if i % 2 == 0 else 0.0
            mesh = durations["mesh_build"]
            total = round(mesh + solve, 6)
            rows.append({
                "n": i, "mode": "screen", "key": key, "design_hash": design_hash,
                "ok": False, "kind": "solve_failed",
                "error": "solve_failed: synthetic solver failure",
                "cached": False,
                "seconds": {"mesh": mesh, "solve": solve, "total": total},
                "fixture_class": fixture_class, "synthetic": True,
            })
            _emit(stage_rows, main_cursor, "mesh_build", mesh,
                  design_hash=design_hash, key=key)
            _emit(stage_rows, main_cursor, "solve", solve,
                  design_hash=design_hash, key=key)
            if solve > 0:
                _emit(stage_rows, main_cursor, "solver_path", 0.0,
                      design_hash=design_hash, key=key, advance=False,
                      assembly_path="fused_cuda",
                      timings={"assembly": round(solve * 0.55, 6),
                               "lu": round(solve * 0.20, 6),
                               "field": round(solve * 0.15, 6),
                               "solve": round(solve * 0.10, 6)})
            _emit(stage_rows, main_cursor, "candidate_total", total,
                  design_hash=design_hash, key=key)
            note_attempt(cache="new", outcome="solver_failure")
            candidate_totals.append(total)
            if prefetch_depth > 0:
                _emit(stage_rows, prefetch_cursor, "mesh_prefetch", mesh,
                      design_hash=design_hash, key=key, thread="prefetch")
            continue

        if draw < pipeline_cut:
            mesh = durations["mesh_build"]
            solve = durations["solve"]
            total = round(mesh + solve, 6)
            rows.append({
                "n": i, "mode": "screen", "key": key, "design_hash": design_hash,
                "ok": False, "kind": "exception",
                "error": "exception: synthetic pipeline failure",
                "cached": False,
                "seconds": {"mesh": mesh, "solve": solve, "total": total},
                "fixture_class": fixture_class, "synthetic": True,
            })
            _emit(stage_rows, main_cursor, "mesh_build", mesh,
                  design_hash=design_hash, key=key)
            _emit(stage_rows, main_cursor, "solve", solve,
                  design_hash=design_hash, key=key)
            _emit(stage_rows, main_cursor, "solver_path", 0.0,
                  design_hash=design_hash, key=key, advance=False,
                  assembly_path="fused_cuda",
                  timings={"assembly": round(solve * 0.55, 6),
                           "lu": round(solve * 0.20, 6),
                           "field": round(solve * 0.15, 6),
                           "solve": round(solve * 0.10, 6)})
            _emit(stage_rows, main_cursor, "candidate_total", total,
                  design_hash=design_hash, key=key)
            note_attempt(cache="new", outcome="pipeline_failure")
            candidate_totals.append(total)
            if prefetch_depth > 0:
                _emit(stage_rows, prefetch_cursor, "mesh_prefetch", mesh,
                      design_hash=design_hash, key=key, thread="prefetch")
            continue

        # Valid new attempt: every top-level stage runs.
        total = round(sum(durations.values()), 6)
        rows.append({
            "n": i, "mode": "screen", "key": key, "design_hash": design_hash,
            "objective": round(10.0 + i * 0.01, 6), "ok": True, "kind": "",
            "error": "", "cached": False,
            "seconds": {"mesh": durations["mesh_build"], "solve": durations["solve"],
                        "total": total},
            "fixture_class": fixture_class, "synthetic": True,
        })
        for stage in TOP_LEVEL_STAGES:
            _emit(stage_rows, main_cursor, stage, durations[stage],
                  design_hash=design_hash, key=key)
        _emit(stage_rows, main_cursor, "solver_path", 0.0,
              design_hash=design_hash, key=key, advance=False,
              assembly_path="fused_cuda",
              timings={"assembly": round(durations["solve"] * 0.55, 6),
                       "lu": round(durations["solve"] * 0.20, 6),
                       "field": round(durations["solve"] * 0.15, 6),
                       "solve": round(durations["solve"] * 0.10, 6)})
        if meh:
            _emit(stage_rows, main_cursor, "meh_inner_optimize",
                  round(durations["solve"] * 0.15, 6),
                  design_hash=design_hash, key=key, advance=False)
        _emit(stage_rows, main_cursor, "candidate_total", total,
              design_hash=design_hash, key=key)
        note_attempt(cache="new", outcome="valid")
        candidate_totals.append(total)
        if prefetch_depth > 0:
            _emit(stage_rows, prefetch_cursor, "mesh_prefetch", durations["mesh_build"],
                  design_hash=design_hash, key=key, thread="prefetch")

    candidate_total_sum = round(sum(candidate_totals), 9)
    run_overhead_s = round(0.35 + 0.01 * int(candidates), 6)
    prefetch_wait_s = 0.0  # modelled ideal: prefetch overlaps and does not extend the run
    elapsed_s = round(candidate_total_sum + run_overhead_s + prefetch_wait_s, 6)

    return {
        "schema": SCHEMA,
        "synthetic": True,
        "seed": int(seed),
        "candidates": int(candidates),
        "fixture_class_counts": {
            cls: sum(1 for r in rows if r.get("fixture_class") == cls)
            for cls in _CLASS_ORDER
        },
        "rows": rows,
        "stage_rows": stage_rows,
        "attempts": attempts,
        "elapsed_s": elapsed_s,
        "candidate_total_sum_s": candidate_total_sum,
        "run_overhead_s": run_overhead_s,
        "prefetch_depth": int(prefetch_depth),
        "prefetch_wait_s": prefetch_wait_s,
        "identity": {
            "fixture": True,
            "spec_hash": _hash(seed, "spec"),
            "cache_identity": _hash(seed, "cache"),
            "lib_shas": {
                "beat": _hash(seed, "lib-beat"),
                "mesher": _hash(seed, "lib-mesher"),
                "bempp": _hash(seed, "lib-bempp"),
            },
            "frequency_array_sha": _hash(seed, "freqs"),
            "batch_size": int(batch_size),
            "note": "synthetic identity; never a real design, mesh or solve identity",
        },
    }


def reconcile_stages(fixture: dict, ledger: dict) -> dict:
    """Reconcile whole-run elapsed against candidate totals, nested stages and prefetch."""
    stage_rows = fixture["stage_rows"]
    totals: dict[str, float] = {}
    candidate_rows = 0
    nested_solver: dict[str, float] = {}
    for row in stage_rows:
        name = str(row["stage"])
        totals[name] = round(totals.get(name, 0.0) + float(row["seconds"]), 9)
        if name == "candidate_total":
            candidate_rows += 1
        if name == "solver_path" and isinstance(row.get("timings"), dict):
            for key, value in row["timings"].items():
                nested_solver[str(key)] = round(
                    nested_solver.get(str(key), 0.0) + float(value), 9)

    top_level_sum = round(sum(totals.get(s, 0.0) for s in TOP_LEVEL_STAGES), 9)
    candidate_total_sum = round(totals.get("candidate_total", 0.0), 9)
    nested = {s: totals.get(s, 0.0) for s in NESTED_STAGES if totals.get(s, 0.0)}
    prefetch_seconds = round(totals.get("mesh_prefetch", 0.0), 9)
    naive_all = round(sum(totals.values()), 9)

    elapsed = float(fixture["elapsed_s"])
    overhead = float(fixture["run_overhead_s"])
    wait = float(fixture["prefetch_wait_s"])
    prefetch_overlap = (round(min(prefetch_seconds, candidate_total_sum), 9)
                        if prefetch_seconds > 0 else 0.0)
    prefetch_adds = round(max(0.0, prefetch_seconds - prefetch_overlap), 9)
    unaccounted = round(elapsed - (candidate_total_sum + overhead + wait), 9)

    def close(a: float, b: float) -> bool:
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-6)

    checks = {
        "candidate_total_rows_equal_new_attempts":
            candidate_rows == int(ledger.get("attempts_new") or 0),
        "top_level_stages_equal_candidate_total":
            close(top_level_sum, candidate_total_sum),
        "elapsed_equals_candidate_total_plus_overhead_plus_wait":
            close(elapsed, candidate_total_sum + overhead + wait),
        "unaccounted_seconds_is_zero": close(unaccounted, 0.0),
        "naive_stage_sum_overcounts_elapsed":
            not close(naive_all, elapsed),
    }
    return {
        "schema": STAGE_SCHEMA,
        "source": "synthetic_fixture",
        "stage_env_flag": STAGE_TIMING_ENV,
        "stage_file_name": STAGE_TIMING_FILE,
        "elapsed_s": elapsed,
        "candidate_total_sum_s": candidate_total_sum,
        "run_overhead_s": overhead,
        "prefetch_wait_s": wait,
        "prefetch_seconds": prefetch_seconds,
        "prefetch_overlap_s": prefetch_overlap,
        "prefetch_adds_to_elapsed_s": prefetch_adds,
        "top_level_stage_sum_s": top_level_sum,
        "nested_stage_seconds": nested,
        "nested_solver_seconds": dict(sorted(nested_solver.items())),
        "naive_all_stage_sum_s": naive_all,
        "naive_overcount_vs_elapsed_s": round(naive_all - elapsed, 9),
        "unaccounted_s": unaccounted,
        "stage_seconds": dict(sorted(totals.items())),
        "stage_rows": len(stage_rows),
        "candidate_total_rows": candidate_rows,
        "checks": checks,
        "additive_rule": ("elapsed = candidate_total_sum + run_overhead_s + "
                          "prefetch_wait_s; top-level stages are inside "
                          "candidate_total, nested stages are subsets, and "
                          "mesh_prefetch overlaps the main loop"),
    }


def replay(*, seed: int = 0, candidates: int = 24, cache_hit_rate: float = 0.20,
           refusal_rate: float = 0.15, solver_failure_rate: float = 0.08,
           pipeline_failure_rate: float = 0.04, prefetch_depth: int = 0,
           batch_size: int = 12, meh: bool = False, dry_run: bool = False,
           fixtures_dir: Path | str | None = None,
           out: Path | str | None = None) -> dict:
    """Synthesize, replay and (optionally) persist one fixture; never solves anything."""
    fixture = synthesize(
        seed=seed, candidates=candidates, cache_hit_rate=cache_hit_rate,
        refusal_rate=refusal_rate, solver_failure_rate=solver_failure_rate,
        pipeline_failure_rate=pipeline_failure_rate, prefetch_depth=prefetch_depth,
        batch_size=batch_size, meh=meh,
    )
    ledger = _ledger(fixture["rows"])
    stages = reconcile_stages(fixture, ledger)

    fixture_files = 0
    if fixtures_dir is not None and not dry_run:
        target = Path(fixtures_dir)
        target.mkdir(parents=True, exist_ok=True)
        (target / "search_fixture.ndjson").write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in fixture["rows"]),
            encoding="utf-8")
        (target / STAGE_TIMING_FILE).write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in fixture["stage_rows"]),
            encoding="utf-8")
        manifest = {
            "source": "synthetic",
            "elapsed_s": fixture["elapsed_s"],
            "stage_files": [STAGE_TIMING_FILE],
            "identity": fixture["identity"],
            "attempts": fixture["attempts"],
            "overhead_seconds": {"run_startup_and_dataset": fixture["run_overhead_s"]},
        }
        (target / "timing_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        fixture_files = 3

    result = {
        "schema": SCHEMA,
        "synthetic": True,
        "dry_run": bool(dry_run),
        "seed": int(seed),
        "candidates": int(candidates),
        "identity": fixture["identity"],
        "guards": {
            "solve_processes_started": 0,
            "acoustic_records_written": 0,
            "solver_or_mesher_imported": False,
            "fixture_files_written": fixture_files,
        },
        "ledger": ledger,
        "stage_timing": stages,
        "attempts": fixture["attempts"],
        "notes": [
            "All rows and seconds are fabricated; this is an accounting rehearsal, "
            "not a solver timing or a speedup claim.",
            "verified_useful is null for every synthetic attempt; verified-useful/hour "
            "is withheld by the S3 ledger until an operator decides it.",
            "The S3 ledger is consumed as-is from tools/analysis/_common.py (read-only); "
            "this harness adds stage/prefetch reconciliation only.",
        ],
    }

    if out is not None:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False),
                        encoding="utf-8")
    return result


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=0, help="deterministic fixture seed")
    p.add_argument("--candidates", type=int, default=24)
    p.add_argument("--cache-hit-rate", type=float, default=0.20)
    p.add_argument("--refusal-rate", type=float, default=0.15)
    p.add_argument("--solver-failure-rate", type=float, default=0.08)
    p.add_argument("--pipeline-failure-rate", type=float, default=0.04)
    p.add_argument("--prefetch-depth", type=int, default=0,
                   help="0 = serial; >0 emits overlapping mesh_prefetch rows")
    p.add_argument("--batch-size", type=int, default=12)
    p.add_argument("--meh", action="store_true",
                   help="emit a nested meh_inner_optimize stage")
    p.add_argument("--fixtures-dir", type=Path, default=None,
                   help="write synthetic fixture files here (suppressed by --dry-run)")
    p.add_argument("--dry-run", action="store_true",
                   help="in-memory only: zero fixture files, zero solves, zero acoustic records")
    p.add_argument("--out", type=Path, default=None,
                   help="write the timing JSON here; otherwise print it")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = replay(
        seed=args.seed, candidates=args.candidates,
        cache_hit_rate=args.cache_hit_rate, refusal_rate=args.refusal_rate,
        solver_failure_rate=args.solver_failure_rate,
        pipeline_failure_rate=args.pipeline_failure_rate,
        prefetch_depth=args.prefetch_depth, batch_size=args.batch_size,
        meh=args.meh, dry_run=args.dry_run, fixtures_dir=args.fixtures_dir,
        out=args.out,
    )
    if args.out is None:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(json.dumps({"out": str(args.out),
                          "dry_run": result["dry_run"],
                          "guards": result["guards"],
                          "ledger_attempts_new": result["ledger"]["attempts_new"],
                          "checks": result["stage_timing"]["checks"]},
                         indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
