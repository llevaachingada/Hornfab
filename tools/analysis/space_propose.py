"""Turn a space card into a PROPOSED config next to the original (senior plan WP 5.1, 2026-11-17).

Reads ``<card>.json`` (from ``space_card.py``) and the config it describes, and writes
``<stem>__space_v1.yaml`` beside ``--out`` with the card's recommendations applied:

* ``link``   -> ``search.links: {follower: {from, scale, offset}}`` (generator configs supported
               since WP 0.2); the follower leaves the CMA dimension;
* ``fix``    -> ``bounds.<k>.search: false`` (value stays the seed's);
* ``fix_or_widen`` (weak) -> fixed only with ``--fix-weak`` (otherwise listed for a person);
* ``rebound``-> ``lo``/``hi`` moved to the proposed unit fraction of the old range;
* ``sigma0`` -> ``search.sigma0 = min(current, max_safe)`` when a safe value exists;
* ``constraint`` -> NOT expressible in a config yet; written into the header for a person.

The original config is never edited. The proposal is re-analysed (box scan + sigma curve) and a
before/after table is printed and saved, so the change is reviewed on evidence (ADR D6). Bounds
moves keep the seed inside the box; a link whose follower is also a leader is skipped.

    python tools/analysis/space_propose.py --card scratch/space_cards/<stem>.json --out <dir> [--fix-weak]
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def apply_card(raw: dict, card: dict, *, fix_weak: bool = False) -> tuple[dict, list[str]]:
    new = copy.deepcopy(raw)
    bounds = new.setdefault("bounds", {})
    search = new.setdefault("search", {})
    notes: list[str] = []
    seed = new.get("seed_params") or {}
    links = dict(search.get("links") or {})
    leaders = {v["from"] for v in links.values()}
    for r in card.get("recommendations", []):
        k, act = r["knob"], r["action"]
        if act == "link":
            p = r["proposal"]
            if k in leaders or p["from"] in links or k not in bounds or p["from"] not in bounds:
                notes.append(f"skipped link {k}<-{p['from']} (chain or unknown knob)")
                continue
            links[k] = {"from": p["from"], "scale": round(float(p["scale"]), 6),
                        "offset": round(float(p["offset"]), 6)}
            leaders.add(p["from"])
            notes.append(f"linked {k} = {links[k]['scale']} * {p['from']} + {links[k]['offset']}")
        elif act == "fix" or (act == "fix_or_widen" and fix_weak):
            if k in bounds:
                bounds[k] = {**bounds[k], "search": False}
                notes.append(f"fixed {k} at its seed ({r['why']})")
        elif act == "fix_or_widen":
            notes.append(f"REVIEW {k}: {r['why']} (not fixed; pass --fix-weak or widen by hand)")
        elif act == "rebound" and k in bounds:
            b = dict(bounds[k])
            lo, hi = float(b["lo"]), float(b["hi"])
            sv = seed.get(k) if isinstance(seed, dict) else None
            if "lower_hi_to_unit" in r["proposal"]:
                nh = lo + r["proposal"]["lower_hi_to_unit"] * (hi - lo)
                if sv is None or float(sv) <= nh:
                    b["hi"] = round(nh, 6)
                    notes.append(f"{k}.hi {hi} -> {b['hi']}")
                else:
                    notes.append(f"skipped {k}.hi cut (seed {sv} above it)")
            if "raise_lo_to_unit" in r["proposal"]:
                nl = lo + r["proposal"]["raise_lo_to_unit"] * (hi - lo)
                if sv is None or float(sv) >= nl:
                    b["lo"] = round(nl, 6)
                    notes.append(f"{k}.lo {lo} -> {b['lo']}")
                else:
                    notes.append(f"skipped {k}.lo raise (seed {sv} below it)")
            bounds[k] = b
        elif act == "sigma0":
            safe = r["proposal"].get("max_safe_sigma0")
            cur = search.get("sigma0")
            if safe is not None and (cur is None or float(cur) > float(safe)):
                search["sigma0"] = float(safe)
                notes.append(f"sigma0 {cur} -> {safe}")
            elif safe is None:
                notes.append("REVIEW sigma0: no tested value kept the predicted bad rate <= 15 %")
        elif act == "constraint":
            notes.append(f"REVIEW joint envelope constraint (not expressible in config): {r['why']}")
    if links:
        search["links"] = links
    return new, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--card", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fix-weak", action="store_true")
    ap.add_argument("--box", type=int, default=32)
    ap.add_argument("--sigma-n", type=int, default=24)
    a = ap.parse_args(argv)
    card = json.loads(a.card.read_text(encoding="utf-8"))
    src = Path(card["config"])
    raw = yaml.safe_load(src.read_text(encoding="utf-8"))
    new, notes = apply_card(raw, card, fix_weak=a.fix_weak)
    bf = new.get("brief_file")
    if bf and not Path(bf).is_absolute():
        new["brief_file"] = str((src.parent / bf).resolve().relative_to(REPO)) \
            if (src.parent / bf).resolve().is_relative_to(REPO) else str((src.parent / bf).resolve())
    new["name"] = f"{raw.get('name', src.stem)}__space_v1"
    a.out.mkdir(parents=True, exist_ok=True)
    dst = a.out / f"{src.stem}__space_v1.yaml"
    header = ["# PROPOSED by tools/analysis/space_propose.py from " + str(a.card),
              "# Review before use; the original config is unchanged. Changes:"] + [f"#   - {n}" for n in notes]
    dst.write_text("\n".join(header) + "\n" + yaml.safe_dump(new, sort_keys=False), encoding="utf-8")
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.geometry import sensitivity as S
    from hornlab_search.search.links import reduce_space
    cfg = load_config(dst)
    space, _ = reduce_space(DesignSpace.from_config(cfg), cfg)
    after = {"searched": len(space.keys()), "box": S.box_feasibility(space, cfg, n=a.box)["counts"],
             "sigma": {s: v["bad_rate"] for s, v in S.sigma_refusal_curve(space, cfg, n=a.sigma_n).items()}}
    from hornlab_search.geometry.record import record_for_design
    try:
        cfg0 = load_config(src)
        r0 = record_for_design(DesignSpace.from_config(cfg0).seed, cfg0)
        r1 = record_for_design(space.seed, cfg)
        after["seed_shift_max_mm"] = r0.max_deviation_mm(r1)
    except Exception as exc:  # noqa: BLE001
        after["seed_shift_max_mm"] = f"not measured: {type(exc).__name__}: {str(exc)[:120]}"
    before = {"searched": len(card["keys"]), "box": card["box"]["counts"],
              "sigma": {s: v["bad_rate"] for s, v in card["sigma"].items()}}
    report = {"proposal": str(dst), "notes": notes, "before": before, "after": after}
    (a.out / f"{src.stem}__space_v1.report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
