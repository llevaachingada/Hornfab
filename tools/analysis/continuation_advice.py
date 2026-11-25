"""D8 continuation rule (Fable plan §10.1 D8, WP 7.2 advisory) — CPU, read-only, no action taken.

Propose continuing a lane only when its best J improved over the last ``window`` (default 100)
new valid evaluations by MORE than the published frequency+mesh floor of that run's *resolved
identity*. Below the floor the gain is a tie with noise, so the advice is "do not propose".

Identity is no longer ``(objective_version, "slope5")``: ``floor_registry`` resolves the brief
sha256 (or exact path+name when the file is unavailable), the score identity hash, solver,
fidelity and comparison grid. A run whose identity is unknown or mismatched gets
"no applicable published floor" and names the missing/mismatched fields (ADR D9: act on J only
after a published floor of the same identity; never borrow another brief's threshold).

A gain inside the declared uncertainty band around the floor (floor/1.25 .. floor*1.25) gets a
common-grid verification decision instead of a decisive continue/stop. The output keeps the
three uncertainty components separate: deterministic fidelity bias, measured uncertainty and
stochastic variability (where the source provides them).

    python tools/analysis/continuation_advice.py --run runs/<a> --run runs/<b> --out <dir>

Advisory output only: it never edits a queue, a config or a run (ADR D6).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from _common import best_so_far_curve, load_run
from floor_registry import BORDERLINE_MULTIPLIER, identity_from_run, identity_summary, resolve

TOOL = "continuation_advice"
WINDOW = 100

_UNSET_UNCERTAINTY = {
    "deterministic_fidelity_bias": None,
    "measured_uncertainty": None,
    "stochastic_variability": None,
    "note": "no registry uncertainty supplied (pure advise call)",
}


def _uncertainty_block(uncertainty) -> dict:
    if isinstance(uncertainty, dict):
        out = dict(uncertainty)
        for key in ("deterministic_fidelity_bias", "measured_uncertainty",
                    "stochastic_variability"):
            out.setdefault(key, None)
        return out
    return dict(_UNSET_UNCERTAINTY)


def advise(curve: list[dict], floor: float | None, window: int = WINDOW, *,
           uncertainty=None) -> dict:
    """Pure rule on a best-so-far curve (``[{"n": int, "best": float}, ...]``, n ascending).

    ``floor`` is the combined published floor in J units for the run's resolved identity, or
    ``None`` when no applicable floor exists. ``uncertainty`` is the registry's three-component
    decomposition (optional so the historical ``advise(curve, floor, window)`` call still works).
    """
    out = {"n_valid": len(curve), "window": window, "floor": floor,
           "best_final": curve[-1]["best"] if curve else None,
           "best_window_start": None, "improvement": None,
           "borderline": None, "floor_band": None,
           "uncertainty": _uncertainty_block(uncertainty)}
    if floor is None:
        return {**out, "advice": "no floor",
                "why": "identity has no published floor (ADR D9)"}
    if len(curve) <= window:
        return {**out, "advice": "too short",
                "why": f"{len(curve)} valid evals <= window {window}; rule needs a full window"}
    try:
        floor_val = float(floor)
    except (TypeError, ValueError):
        return {**out, "advice": "no floor", "why": "floor is not numeric (ADR D9)"}
    if not math.isfinite(floor_val) or floor_val < 0.0:
        return {**out, "advice": "no floor", "why": "floor is not a finite non-negative J"}

    start_n = curve[-1]["n"] - window
    before = [p["best"] for p in curve if p["n"] <= start_n]
    b0 = min(before) if before else curve[0]["best"]
    gain = b0 - curve[-1]["best"]
    lower = floor_val / BORDERLINE_MULTIPLIER
    upper = floor_val * BORDERLINE_MULTIPLIER
    borderline = bool(lower <= gain <= upper)
    out.update(best_window_start=b0, improvement=gain,
               borderline=borderline, floor_band=[lower, upper])
    if not (math.isfinite(gain)):
        return {**out, "advice": "no data", "why": "non-finite J in curve"}
    if gain > upper:
        return {**out, "advice": "propose continuation",
                "why": (f"last-{window} gain {gain:.4f} J > floor {floor_val:.4f} J "
                        f"by more than the {BORDERLINE_MULTIPLIER:g}x uncertainty band")}
    if borderline:
        return {**out, "advice": "verify on common grid",
                "why": (f"last-{window} gain {gain:.4f} J is inside the declared band "
                        f"[{lower:.4f}, {upper:.4f}] around floor {floor_val:.4f} J; "
                        "verify both runs on one common grid before a continue/stop decision")}
    return {**out, "advice": "do not propose",
            "why": (f"last-{window} gain {gain:.4f} J < band lower edge {lower:.4f} J "
                    f"(floor {floor_val:.4f} J; a tie with noise)")}


def analyse(run_dir: Path, window: int = WINDOW) -> dict:
    run = load_run(Path(run_dir))
    identity = identity_from_run(run)
    resolution = resolve(identity)
    floor = resolution.get("floor_J") if resolution["status"] == "matched" else None
    result = advise(best_so_far_curve(run), floor, window,
                    uncertainty=resolution.get("uncertainty"))
    if floor is None:
        result["advice"] = "no applicable published floor"
        result["why"] = resolution["why"]
    return {"run": Path(run_dir).name, "identity": identity_summary(identity),
            "resolution": resolution, **result}


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
        (a.out / "continuation_advice.json").write_text(json.dumps(rows, indent=1),
                                                        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
