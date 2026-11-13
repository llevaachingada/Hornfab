"""S8 provenance-checked experiment cards. Offline preparation; no acoustic claims.

Input is a JSON spec with ``parents`` (id, source, family, params, design_hash),
``identity`` (task_id, scoring_context_id, objective_version, physical_spec_id),
``expected_band_hz``, ``trade_off``, ``unknowns``, ``features``, ``constraints``,
and ``experiments``. Each experiment has role, config path, and parent_ids.
Roles must include parent_a, parent_b, combination, ablate_a, ablate_b, broad_control.
Configs use existing legal generators and are materialized and validated, without meshing.
Parent source files must be JSON objects containing the recorded family/params/hash.
The card describes a proposed experiment; only later normal-evaluator verification can
establish whether a feature helps. All output is under --out.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.config import load_config
from hornlab_search.design.families import validate
from hornlab_search.design.space import DesignSpace
from hornlab_search.types import Design

ROLES = {"parent_a", "parent_b", "combination", "ablate_a", "ablate_b", "broad_control"}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty")
    return value


def _legal(design):
    p = design.params
    if str(design.family).upper() == "MEH" or "mid_ports" in p or (
        isinstance(p.get("cad"), dict) and "meh" in str(p["cad"].get("tool", "")).lower()
    ):
        raise ValueError("MEH stays paused")
    validate(design)


def build_card(spec: dict, *, base: Path) -> dict:
    """Validate actual parents and materialized candidate/ablation configs, return a card."""
    identity = spec.get("identity", {})
    for name in ("task_id", "scoring_context_id", "physical_spec_id"):
        _text(identity.get(name), name)
    if type(identity.get("objective_version")) is not int:
        raise ValueError("objective_version must be explicit")
    band = spec.get("expected_band_hz")
    if not isinstance(band, list) or len(band) != 2 or not all(
        type(v) in (int, float) and math.isfinite(v) for v in band
    ) or not 0 < band[0] < band[1]:
        raise ValueError("expected_band_hz must be a finite increasing positive band")
    for name in ("trade_off",):
        _text(spec.get(name), name)
    for name in ("unknowns", "features", "constraints"):
        values = spec.get(name)
        if not isinstance(values, list) or not values:
            raise ValueError(f"{name} must be a nonempty list")
        for value in values:
            _text(value, name)
    parents = []
    for parent in spec.get("parents", []):
        parent_id = _text(parent.get("id"), "parent id")
        path = (base / _text(parent.get("source"), "parent source")).resolve()
        raw = json.loads(path.read_text(encoding="utf-8"))
        recorded = raw.get("design", raw)
        design = Design(recorded["family"], recorded["params"])
        _legal(design)
        if recorded.get("design_hash", recorded.get("hash")) != design.hash():
            raise ValueError("parent source lacks a matching recorded design hash")
        if parent.get("design_hash") != design.hash():
            raise ValueError("parent design_hash disagrees with source")
        # An ID must be a recorded ID or the geometry hash itself, never an invented alias.
        if parent_id not in {design.hash(), raw.get("row_id"), raw.get("id")}:
            raise ValueError("parent id is not present in its source")
        parents.append({"id": parent_id, "design_hash": design.hash(),
                        "source": str(path), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "family": design.family, "params": design.params})
    ids = {p["id"] for p in parents}
    if len(parents) != 2 or len(ids) != 2 or len({p["design_hash"] for p in parents}) != 2:
        raise ValueError("two distinct real parents are required")
    experiments = []
    roles = set()
    contexts = set()
    geometry_cache = {}
    for item in spec.get("experiments", []):
        role = item.get("role")
        if role not in ROLES or role in roles:
            raise ValueError("experiment roles must be known and unique")
        roles.add(role)
        refs = item.get("parent_ids", [])
        if not refs or not set(refs) <= ids:
            raise ValueError("experiment must reference actual parents")
        if role == "combination" and set(refs) != ids:
            raise ValueError("combination must reference both parents")
        path = (base / _text(item.get("config"), "config")).resolve()
        cfg = load_config(path)
        if cfg.objective_version != identity["objective_version"]:
            raise ValueError("declared objective_version disagrees with experiment config")
        contexts.add(_digest({k: cfg.raw.get(k) for k in
                              ("target", "weights", "objective", "brief", "mesh", "solve", "gates")}))
        if str((getattr(cfg, "generator", None) or {}).get("name", "")).lower() == "meh":
            raise ValueError("MEH stays paused")
        design = DesignSpace.from_config(cfg).seed
        _legal(design)
        if design.hash() not in geometry_cache:
            from geometry_descriptors import geometry_descriptors
            geometry_cache[design.hash()] = geometry_descriptors(design)
        experiments.append({"role": role, "parent_ids": refs, "config": str(path),
                            "config_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "design_hash": design.hash(), "family": design.family,
                            "params": design.params, "validation": "canonical_geometry_resolved",
                            "geometry_descriptors": geometry_cache[design.hash()],
                            "physical_feasibility": "unverified_requires_normal_evaluator"})
    if roles != ROLES:
        raise ValueError(f"missing ablations/controls: {sorted(ROLES - roles)}")
    if len(contexts) != 1:
        raise ValueError("experiment configs disagree on physical/scoring context")
    by_role = {e["role"]: e for e in experiments}
    for role, parent in zip(("parent_a", "parent_b"), parents):
        if by_role[role]["design_hash"] != parent["design_hash"]:
            raise ValueError(f"{role} config does not reconstruct its recorded parent")
    lo = float(cfg.target_raw["band_lo_hz"])
    hi = float(cfg.target_raw["band_hi_hz"])
    if not lo <= band[0] < band[1] <= hi:
        raise ValueError("expected band is outside the frozen acoustic task band")
    combo_hash = by_role["combination"]["design_hash"]
    if combo_hash in {p["design_hash"] for p in parents}:
        raise ValueError("combination must differ from both parents")
    for role in ("ablate_a", "ablate_b"):
        if by_role[role]["design_hash"] == combo_hash:
            raise ValueError("an ablation must change the combination geometry")
        _text(next(e for e in spec["experiments"] if e["role"] == role).get("removed_feature"), "removed_feature")
        by_role[role]["removed_feature"] = next(e for e in spec["experiments"] if e["role"] == role)["removed_feature"]
    card = {"tool": "hypothesis_cards", "schema_version": 1, "status": "proposed",
            "identity": identity, "resolved_context_sha256": next(iter(contexts)),
            "parents": parents, "experiments": experiments,
            **{k: spec[k] for k in ("expected_band_hz", "trade_off", "unknowns", "features", "constraints")},
            "evidence": "hypothesis only; acoustic effects and mesh feasibility unmeasured"}
    card["card_id"] = _digest(card)
    return card


def markdown(card):
    lines = ["# Hypothesis " + card["card_id"], "", card["evidence"], "",
             "Parents: " + ", ".join(p["id"] for p in card["parents"]), "",
             f"Expected band: {card['expected_band_hz']} Hz", "", "Trade-off: " + card["trade_off"]]
    lines += ["", "Resolved task/scoring context: " + card["resolved_context_sha256"], "",
              "Parent sources:", ""] + [f"- {p['id']}: {p['source']} (sha256 {p['source_sha256']})"
                                        for p in card["parents"]]
    for key in ("features", "unknowns", "constraints"):
        lines += ["", key.capitalize() + ":", ""] + ["- " + v for v in card[key]]
    lines += ["", "Experiments:", ""] + [f"- {e['role']}: {e['design_hash']} ({e['config']}); removed feature: {e.get('removed_feature', 'n/a')}"
                                                for e in card["experiments"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        out = args.out.resolve()
        if any(part.lower() in {"runs", "dataset", "dataset_cpu", "cache", "cache_cpu"} for part in out.parts):
            raise ValueError("output must be outside live runs/dataset/cache roots")
        if args.spec.resolve() in {out / "hypothesis_cards.json", out / "hypothesis_cards.md"}:
            raise ValueError("output would overwrite the input specification")
        card = build_card(json.loads(args.spec.read_text(encoding="utf-8")), base=args.spec.resolve().parent)
        card["generated_utc"] = datetime.now(timezone.utc).isoformat()
        out.mkdir(parents=True, exist_ok=True)
        (out / "hypothesis_cards.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (out / "hypothesis_cards.md").write_text(markdown(card), encoding="utf-8")
    except (ValueError, KeyError, OSError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
