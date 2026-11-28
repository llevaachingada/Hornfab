"""Run page "Score breakdown: start vs best": every weighted term of the run's objective version.

The run page used to draw a fixed six-term list (``cov rip di dislope flat load``) with the brief's
top-level ``weights``. That is the v1-v4 term set: for v9+ runs ``cov`` is ``cov_profile``, ``di`` is
gone, and ``flat_cv``/``di_roughness`` are weighted; v11 adds the CD matrix (``cd_lw``,
``cd_di_std``, ``cd_nacc``, ``offaxis_smooth``) whose weights live ONLY in ``objective.cd``. The
2026-11-20 FAV-001 run (v11, J 4.9965) showed under half its J in the old chart.

:func:`score_breakdown` resolves the weighted key set and weights through the objective package's
own resolvers (no score mathematics is copied), multiplies them with the STORED terms of the start
and best rows, and reports any gap to the stored ``total`` (a failure ``penalty``, v7's
``oa_excess`` add-on, or an unknown version) as an explicit ``unattributed`` row so the bars always
sum to J. Pure; never raises (a run the resolvers cannot read gets ``available: False``).
"""
from __future__ import annotations

import math
from typing import Any

#: v11 CD weights come only from ``objective.cd.<block>.weight`` (scalar_v11.resolve_v11_weights).
_V11_CD_WEIGHT_BLOCKS = (("cd_lw", "lw"), ("cd_di_std", "di_std"), ("cd_nacc", "nacc"),
                         ("offaxis_smooth", "offaxis"))
#: |sum - total| at or below this is rounding, not a missing term.
_SUM_TOL = 1e-6


def _as_dict(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def _objective_block(cfg: dict) -> dict:
    return _as_dict(cfg.get("objective")) or _as_dict(_as_dict(cfg.get("brief")).get("objective"))


def _brief_weights(cfg: dict) -> dict:
    return _as_dict(cfg.get("weights")) or _as_dict(_as_dict(cfg.get("brief")).get("weights"))


def _v11_weights(weights: dict, block: dict) -> tuple[tuple[str, ...], dict, str]:
    """v11 = v10 base keys/weights + the four CD terms. Uses scalar_v11 when it is importable."""
    try:
        from hornlab_search.objective.scalar_v11 import (V11_CD_TERM_KEYS, V11Params,
                                                         resolve_v11_weights)
    except ImportError:
        V11Params = None  # noqa: N806 - the v11 module is not on this checkout
    if V11Params is not None:
        p = V11Params.from_block(dict(block))
        w = resolve_v11_weights(weights, p)
        return tuple(p.weighted_keys()) + tuple(V11_CD_TERM_KEYS), w, "scalar_v11.resolve_v11_weights"
    # Fallback (checkouts without objective/scalar_v11.py): the documented v11 rule, built from
    # the v10 resolver plus the objective.cd weights. The sum check below still guards it.
    from hornlab_search.objective.scalar_v9 import resolve_v9_weights
    from hornlab_search.objective.scalar_v10 import V10Params
    cd = _as_dict(block.get("cd"))
    p10 = V10Params.from_block({k: v for k, v in block.items() if k != "cd"} | {"version": 10})
    w = resolve_v9_weights(weights, p10.v9)
    keys = list(p10.weighted_keys())
    for key, sub in _V11_CD_WEIGHT_BLOCKS:
        w[key] = float(_as_dict(cd.get(sub)).get("weight", 0.0))
        keys.append(key)
    return tuple(keys), w, "v10 resolver + objective.cd weights (scalar_v11 not importable)"


def resolve_breakdown_weights(version: int, cfg: dict) -> tuple[tuple[str, ...], dict, str]:
    """(weighted keys, resolved weights, source) for ``version`` from a run's config.

    Raises ``ValueError``/``ImportError`` when the objective block does not validate; the caller
    turns that into ``available: False``.
    """
    weights = _brief_weights(cfg)
    block = _objective_block(cfg)
    if version == 11:
        return _v11_weights(weights, block)
    if version == 10:
        from hornlab_search.objective.scalar_v9 import resolve_v9_weights
        from hornlab_search.objective.scalar_v10 import V10Params
        p = V10Params.from_block(dict(block))
        return tuple(p.weighted_keys()), resolve_v9_weights(weights, p.v9), "scalar_v9.resolve_v9_weights (v10)"
    if version == 9:
        from hornlab_search.objective.scalar_v9 import V9Params, resolve_v9_weights
        p = V9Params.from_block(dict(block))
        return tuple(p.weighted_keys()), resolve_v9_weights(weights, p), "scalar_v9.resolve_v9_weights"
    if version == 7:
        from hornlab_search.objective.scalar_v7 import V7_WEIGHTED_KEYS, resolve_v7_weights
        return tuple(V7_WEIGHTED_KEYS), resolve_v7_weights(weights), "scalar_v7.resolve_v7_weights"
    if version == 6:
        from hornlab_search.objective.scalar_v6 import V6_WEIGHTED_KEYS, resolve_v6_weights
        return tuple(V6_WEIGHTED_KEYS), resolve_v6_weights(weights), "scalar_v6.resolve_v6_weights"
    if version == 4:
        from hornlab_search.objective.scalar_v4 import V4_WEIGHTED_KEYS, resolve_v4_weights
        return tuple(V4_WEIGHTED_KEYS), resolve_v4_weights(weights), "scalar_v4.resolve_v4_weights"
    if version in (1, 2, 3):
        from hornlab_search.objective.terms import WEIGHTED_KEYS
        from hornlab_search.objective.scalar import resolve_weights
        return tuple(WEIGHTED_KEYS), resolve_weights(weights), "scalar.resolve_weights"
    raise ValueError(f"no breakdown resolver for objective version {version}")


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    return f if math.isfinite(f) else None


def _side(terms: dict | None, keys: tuple[str, ...], w: dict) -> dict | None:
    """Per-key contributions of one stored term row, plus its stored total and the gap."""
    if not isinstance(terms, dict):
        return None
    contrib = {}
    for k in keys:
        t = _num(terms.get(k))
        contrib[k] = float(w.get(k, 0.0)) * t if t is not None else None
    s = math.fsum(v for v in contrib.values() if v is not None)
    total = _num(terms.get("total"))
    gap = (total - s) if total is not None else None
    return {"contrib": contrib, "sum": s, "total": total,
            "unattributed": gap if gap is not None and abs(gap) > _SUM_TOL else 0.0}


#: Brief ``envelope.soft_penalty`` term stored on solved rows (weight 1: it is already in J units).
SIZE_PENALTY_KEY = "size_penalty"


def _with_size_total(terms: dict | None) -> dict | None:
    """A copy whose ``total`` is the row's J: acoustic total (``J_acoustic`` else ``total``) + size."""
    if not isinstance(terms, dict):
        return terms
    sp = _num(terms.get(SIZE_PENALTY_KEY))
    acoustic = _num(terms.get("J_acoustic"))
    if acoustic is None:
        acoustic = _num(terms.get("total"))
    if sp is None or acoustic is None:
        return terms
    return {**terms, "total": acoustic + sp}


def score_breakdown(cfg: dict, version: int, terms_seed: dict | None,
                    terms_best: dict | None) -> dict:
    """The run page breakdown: one row per weighted term of ``version`` (see module doc).

    Shape::

        {available, version, source, keys, weights,
         rows: [{key, weight, seed_raw, best_raw, seed, best}],
         seed: {sum, total, unattributed} | None, best: {...} | None}

    ``rows`` keep every weighted key (w=0 included, so a switched-off term is visible) and end
    with an ``unattributed`` row only when a side's stored total differs from its term sum.
    """
    try:
        keys, w, source = resolve_breakdown_weights(int(version), cfg or {})
    except Exception as exc:  # noqa: BLE001 - the run page must render without the breakdown
        return {"available": False, "version": version,
                "reason": f"{type(exc).__name__}: {exc}"}
    # Opt-in soft size cost (objective/size_penalty.py, 2026-11-25): added to J AFTER the objective,
    # so the row stores ``size_penalty`` + ``J_acoustic`` while ``terms.total`` stays acoustic. Show
    # it as its own weight-1 row and reconcile against the row's real J (acoustic + size).
    if any(isinstance(t, dict) and _num(t.get(SIZE_PENALTY_KEY)) is not None
           for t in (terms_seed, terms_best)):
        keys = tuple(keys) + (SIZE_PENALTY_KEY,)
        w = {**w, SIZE_PENALTY_KEY: 1.0}
        terms_seed, terms_best = _with_size_total(terms_seed), _with_size_total(terms_best)
    seed = _side(terms_seed, keys, w)
    best = _side(terms_best, keys, w)
    rows = []
    for k in keys:
        rows.append({
            "key": k, "weight": float(w.get(k, 0.0)),
            "seed_raw": _num((terms_seed or {}).get(k)), "best_raw": _num((terms_best or {}).get(k)),
            "seed": seed["contrib"][k] if seed else None,
            "best": best["contrib"][k] if best else None,
        })
    if any(s and s["unattributed"] for s in (seed, best)):
        rows.append({"key": "unattributed", "weight": None, "seed_raw": None, "best_raw": None,
                     "seed": seed["unattributed"] if seed else None,
                     "best": best["unattributed"] if best else None})
    strip = (lambda s: None if s is None else {k: s[k] for k in ("sum", "total", "unattributed")})
    return {"available": True, "version": int(version), "source": source, "keys": list(keys),
            "weights": {k: float(w.get(k, 0.0)) for k in keys}, "rows": rows,
            "seed": strip(seed), "best": strip(best)}
