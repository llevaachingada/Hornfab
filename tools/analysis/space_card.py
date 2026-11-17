"""Space cards: owner-reviewable parameter-space evidence per lane (senior plan stage 5, 2026-11-17).

For each config, CPU only (records, no mesh, no solve), from ``hornlab_search.geometry.sensitivity``:

1. **Geometry**: per-knob surface activity (active / weak / conditional / inactive), largest point
   displacement and RMS per full range, coupled knobs, effective dimension, geometric link
   proposals, shared-descriptor sensitivities.
2. **Feasibility**: Sobol box scan (fraction legal and inside the envelope; per-knob bad-rate by
   slice -> re-bound proposals), feasible step from the seed toward each bound, the linear
   envelope-margin constraint (WP 5.4), and the predicted bad-candidate rate per sigma0.
3. **Data** (optional ``--run``): the existing ``walls`` and ``links`` tools' verdicts from a real
   search, so geometric and empirical evidence are shown side by side (X4's agreement gate).
4. **Recommendations**, each with the evidence that produced it. NOTHING is applied: a person or
   the orchestrator edits the config after reading the card (ADR D6).

    python tools/analysis/space_card.py --config <cfg.yaml> [--config ...] [--run runs/<r>] \\
        --out scratch/space_cards [--points 8] [--box 64] [--sigma-n 32]

With several ``--config`` it also writes ``shared_map.md``: for every lane, which shared physical
descriptor each knob mainly drives, so knobs of different families can be read in one language.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
for p in (REPO, REPO / "tools" / "analysis"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

SIGMA_BAD_MAX = 0.15     # a sigma0 is "safe" when its predicted bad rate is at most this


def _data_evidence(run: Path | None) -> dict:
    if run is None:
        return {}
    out = {}
    for tool in ("walls", "links"):
        try:
            mod = __import__(tool)
            res = mod.analyse_run(run) if hasattr(mod, "analyse_run") else None
            out[tool] = res if res is not None else {"note": f"{tool}.py has no analyse_run(); run it separately"}
        except Exception as exc:  # noqa: BLE001
            out[tool] = {"error": f"{type(exc).__name__}: {str(exc)[:160]}"}
    return out


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def _links_payload(data: dict | None) -> dict | None:
    """The empirical ``links`` payload when the run was actually analysed, else None."""
    if not isinstance(data, dict):
        return None
    payload = data.get("links")
    if not isinstance(payload, dict) or not payload:
        return None
    if "error" in payload or "note" in payload:
        return None
    return payload


def _data_agreement(link: dict, data: dict | None) -> bool | str:
    """True/False when ``--run`` links evidence is available, "unknown" otherwise.

    True: ``proposed_links`` has the same unordered pair {from, follower} with the same scale
    sign (a reversed proposal is inverted first: ``sign(1 / proposal_scale)``).
    False: links evidence is available but the pair is absent or its scale sign is opposite.
    """
    payload = _links_payload(data)
    if payload is None:
        return "unknown"
    a, b = link["from"], link["follower"]
    link_sign = _sign(link["scale"])
    for p in payload.get("proposed_links") or []:
        if not isinstance(p, dict) or p.get("scale") is None:
            continue
        pa, pb, scale = p.get("knob_a"), p.get("knob_b"), p["scale"]
        if pa == a and pb == b:
            if _sign(scale) == link_sign:
                return True
        elif pa == b and pb == a:
            inverted = 1.0 / scale if scale else 0.0
            if _sign(inverted) == link_sign:
                return True
    return False


def recommend(geo: dict, box: dict, sigma: dict, margin: dict,
              data: dict | None = None) -> list[dict]:
    recs = []
    for k, v in (geo.get("knobs") or {}).items():
        if v["label"] == "inactive":
            recs.append({"knob": k, "action": "fix", "why": "moves no surface point at any sampled point",
                         "evidence": {"active_frac": v["active_frac"]}})
        elif v["label"] == "weak":
            recs.append({"knob": k, "action": "fix_or_widen",
                         "why": f"whole range moves the surface <= {v['median_max_disp_mm_per_range']:.2f} mm "
                                f"(below the ~1 mm mesher fit): CMA spends a dimension on mesh noise",
                         "evidence": {"median_max_disp_mm_per_range": v["median_max_disp_mm_per_range"]}})
        elif v["label"] == "conditional":
            recs.append({"knob": k, "action": "check_condition",
                         "why": "active at some sampled points only: its effect depends on another knob "
                                "(split the lane or link the condition)",
                         "evidence": {"active_frac": v["active_frac"]}})
    for link in geo.get("links") or []:
        agrees = _data_agreement(link, data)
        why = (f"surface direction parallel to {link['from']} "
               f"(|cos| {link['median_abs_cos']:.3f})")
        rec = {"knob": link["follower"],
               "action": "link" if agrees is not False else "link_rejected_by_data",
               "why": why, "proposal": {"from": link["from"], "scale": link["scale"],
                                        "offset": link["offset"]},
               "data_agrees": agrees}
        if agrees is False:
            rec["why"] += "; rejected: the empirical links payload has no same-sign matching pair"
        recs.append(rec)
    for k, v in (box.get("per_knob") or {}).items():
        for key in ("raise_lo_to_unit", "lower_hi_to_unit"):
            if key in v:
                recs.append({"knob": k, "action": "rebound", "why": "edge slice mostly refused/outside "
                             "while the middle is not", "proposal": {key: v[key]},
                             "evidence": {"bad_rate_by_slice": v["bad_rate_by_slice"]}})
    safe = [float(s) for s, v in sigma.items() if v["bad_rate"] <= SIGMA_BAD_MAX]
    if sigma:
        recs.append({"knob": "*", "action": "sigma0",
                     "why": f"predicted bad-candidate rate <= {SIGMA_BAD_MAX:.0%} from the seed",
                     "proposal": {"max_safe_sigma0": max(safe) if safe else None},
                     "evidence": {s: v["bad_rate"] for s, v in sigma.items()}})
    if margin.get("available") and margin.get("r2", 0) >= 0.7 and margin.get("inside_frac", 1) < 0.8:
        recs.append({"knob": "*", "action": "constraint",
                     "why": f"envelope binds jointly; linear margin model R^2 {margin['r2']:.2f}, "
                            f"sign right {margin['sign_agreement']:.0%}, only {margin['inside_frac']:.0%} "
                            f"of the box inside",
                     "proposal": {"intercept_mm": margin["intercept_mm"],
                                  "gradient_mm_per_range": {k: g["mm_per_range"] for k, g in margin["gradient"].items()}}})
    return recs


def card_for(config: Path, *, run: Path | None, points: int, box_n: int, sigma_n: int) -> dict:
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.geometry import sensitivity as S
    cfg = load_config(config)
    space = DesignSpace.from_config(cfg)
    geo = S.analyze_space(space, cfg, n_points=points)
    box = S.box_feasibility(space, cfg, n=box_n)
    sigma = S.sigma_refusal_curve(space, cfg, n=sigma_n)
    margin = S.margin_model(space, cfg, n=max(box_n, len(space.keys()) + 8))
    card = {"config": str(config), "name": cfg.name, "family": cfg.family,
            "generator": bool(getattr(cfg, "generator", None)), "keys": geo["keys"],
            "geometry": geo, "box": box, "sigma": sigma, "margin_model": margin,
            "data": _data_evidence(run)}
    card["recommendations"] = recommend(geo, box, sigma, margin, card["data"])
    return card


def _md(card: dict) -> str:
    g = card["geometry"]
    L = [f"# Space card: `{card['name']}`", "",
         f"Config `{card['config']}`; family {card['family']}; generator {card['generator']}. "
         f"CPU only; evidence for a person, nothing applied.", "",
         f"- Legal sample points: {g.get('legal_points')}/{g.get('n_points')}; effective dimension "
         f"{g.get('effective_dimension')}",
         f"- Box scan: {card['box']['counts']} (ok fraction {card['box']['ok_frac']:.0%})",
         f"- Predicted bad rate by sigma0: " + ", ".join(f"{s}: {v['bad_rate']:.0%}" for s, v in card["sigma"].items()),
         "", "| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |",
         "|---|---|---:|---:|---|---|"]
    feas = g.get("feasible_from_seed") or {}
    for k, v in (g.get("knobs") or {}).items():
        f = feas.get(k, {})
        L.append(f"| `{k}` | {v['label']} | {v['median_max_disp_mm_per_range']:.2f} | "
                 f"{v['median_rms_mm_per_range']:.2f} | {', '.join(c['knob'] for c in v['coupled_with']) or '-'} | "
                 f"{f.get('lo_frac', float('nan')):.2f} / {f.get('hi_frac', float('nan')):.2f} |")
    m = card["margin_model"]
    if m.get("available"):
        L += ["", f"Envelope margin model: R^2 {m['r2']:.2f}, sign agreement {m['sign_agreement']:.0%}, "
                  f"inside {m['inside_frac']:.0%}, binding {m['binding_axis_counts']}"]
    L += ["", "## Recommendations (not applied)", ""]
    for r in card["recommendations"]:
        agree = (f"; data_agrees={str(r['data_agrees']).lower()}"
                 if "data_agrees" in r else "")
        L.append(f"- **{r['action']}** `{r['knob']}`: {r['why']}" + agree
                 + (f"; proposal `{json.dumps(r['proposal'], default=float)}`" if r.get("proposal") else ""))
    return "\n".join(L) + "\n"


def shared_map(cards: list[dict]) -> str:
    from hornlab_search.geometry.sensitivity import DESCRIPTOR_KEYS
    L = ["# Shared descriptor map", "",
         "Each knob's strongest shared descriptor (median change per full range, at the sampled "
         "points). Knobs of different families that drive the same descriptor are the shared "
         "language for seeding and comparison (SD-1: one description, plural generators).", "",
         "| lane | knob | main descriptor | change per range | second |", "|---|---|---|---:|---|"]
    scale = {"mouth_width_mm": 1.0, "mouth_height_mm": 1.0, "depth_mm": 1.0, "h_wall_angle_mouth_deg": 5.0,
             "v_wall_angle_mouth_deg": 5.0, "diag_wall_angle_mouth_deg": 5.0, "mouth_aspect": 0.01,
             "mouth_area_mm2": 1000.0, "h_halfwidth_mid_mm": 1.0, "v_halfwidth_mid_mm": 1.0}
    for c in cards:
        for k, v in (c["geometry"].get("knobs") or {}).items():
            d = v["descriptor_per_range"]
            ranked = sorted(DESCRIPTOR_KEYS, key=lambda q: -abs(d[q]) / scale[q])
            L.append(f"| `{c['name']}` | `{k}` | {ranked[0]} | {d[ranked[0]]:+.2f} | {ranked[1]} |")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", action="append", type=Path, required=True)
    ap.add_argument("--run", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--points", type=int, default=8)
    ap.add_argument("--box", type=int, default=64)
    ap.add_argument("--sigma-n", type=int, default=32)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    cards, failures = [], []
    for c in a.config:
        try:
            card = card_for(c, run=a.run, points=a.points, box_n=a.box, sigma_n=a.sigma_n)
        except Exception as exc:  # noqa: BLE001 - one bad config must not hide the others
            failures.append({"config": str(c), "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
            continue
        cards.append(card)
        stem = Path(c).stem
        (a.out / f"{stem}.json").write_text(json.dumps(card, indent=1, default=float), encoding="utf-8")
        (a.out / f"{stem}.md").write_text(_md(card), encoding="utf-8")
    if len(cards) > 1:
        (a.out / "shared_map.md").write_text(shared_map(cards), encoding="utf-8")
    summary = {"cards": [c["name"] for c in cards], "failures": failures,
               "recommendations": {c["name"]: [f"{r['action']}:{r['knob']}" for r in c["recommendations"]] for c in cards}}
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
