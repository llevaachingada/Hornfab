"""D8 continuation rule (Fable plan §10.1 D8, WP 7.2 advisory) — CPU, read-only, no action taken.

Propose continuing a lane only when its best J improved over the last ``window`` (default 100) new
valid evaluations by MORE than the published frequency+mesh floor of that run's score identity.
Below the floor the gain is a tie with noise, so the advice is "do not propose". A run whose
identity has no published floor gets "no floor" (ADR D9: act on J only after a published floor).

Floors (combined, `docs/evidence/b1_mesh_2026-11-18/floor_record.json`; v7 re-pinned to the
stored-J protocol basis by senior verdict 2, `scratch/fable_architecture/SENIOR_VERDICTS_2026-11-19.md`).

    python tools/analysis/continuation_advice.py --run runs/<a> --run runs/<b> --out <dir>

Advisory output only: it never edits a queue, a config or a run (ADR D6).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from _common import best_so_far_curve, load_run

TOOL = "continuation_advice"
WINDOW = 100
#: combined floors per score identity (J units). Key = (objective_version, variant).
FLOORS = {(7, ""): 0.3105, (10, ""): 0.4677, (10, "slope5"): 0.4863}


def identity_key(meta: dict, cfg: dict) -> tuple[int | None, str]:
    v = meta.get("objective_version")
    brief = str(meta.get("brief") or cfg.get("brief_file") or "")
    return (int(v) if isinstance(v, int) else None, "slope5" if "slope5" in brief else "")


def advise(curve: list[dict], floor: float | None, window: int = WINDOW) -> dict:
    """Pure rule on a best-so-far curve (``[{"n": int, "best": float}, ...]``, n ascending)."""
    out = {"n_valid": len(curve), "window": window, "floor": floor,
           "best_final": curve[-1]["best"] if curve else None,
           "best_window_start": None, "improvement": None}
    if floor is None:
        return {**out, "advice": "no floor", "why": "identity has no published floor (ADR D9)"}
    if len(curve) <= window:
        return {**out, "advice": "too short",
                "why": f"{len(curve)} valid evals <= window {window}; rule needs a full window"}
    start_n = curve[-1]["n"] - window
    before = [p["best"] for p in curve if p["n"] <= start_n]
    b0 = min(before) if before else curve[0]["best"]
    gain = b0 - curve[-1]["best"]
    out.update(best_window_start=b0, improvement=gain)
    if not (math.isfinite(gain)):
        return {**out, "advice": "no data", "why": "non-finite J in curve"}
    if gain > floor:
        return {**out, "advice": "propose continuation",
                "why": f"last-{window} gain {gain:.4f} J > floor {floor:.4f} J"}
    return {**out, "advice": "do not propose",
            "why": f"last-{window} gain {gain:.4f} J <= floor {floor:.4f} J (a tie with noise)"}


def analyse(run_dir: Path, window: int = WINDOW) -> dict:
    run = load_run(Path(run_dir))
    key = identity_key(run["meta"], run["config"])
    res = advise(best_so_far_curve(run), FLOORS.get(key), window)
    return {"run": Path(run_dir).name, "identity": {"objective_version": key[0], "variant": key[1]},
            **res}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--window", type=int, default=WINDOW)
    a = ap.parse_args(argv)
    rows = [analyse(r, a.window) for r in a.run]
    for r in rows:
        print(f"{r['run']}: {r['advice']} — {r['why']}")
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "continuation_advice.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
