"""Geometric identifiability of a search space from the canonical record (senior plan stage 5,
WP 5.1/5.4; ADR §6 "geometric identifiability from the surface Jacobian").

For any family or generator config (native or generator, all record routes), this measures, at
several points of the searched box, how each knob moves the SURFACE the mesher will build:

* **surface Jacobian** ``J[:, k] = d record / d x_k`` by central differences in the optimizer's
  own unit coordinates (x in [0, 1]^k, exactly what CMA-ES and BoTorch see), reported in mm of
  surface RMS displacement per FULL knob range;
* **activity**: a knob whose column is ~0 is inactive at that point; a knob active at some points
  and not others is *conditional* (its effect depends on another knob);
* **coupling**: |cosine| between columns; near-parallel columns are redundant directions, so a
  link ``b = scale * a + offset`` (in knob units) is proposed from the column projection;
* **effective dimension**: singular values of the column-normalised Jacobian (how many
  independent surface directions the box really has);
* **shared descriptors**: the same differences on physical numbers every family shares (mouth W
  and H, depth, H/V/diagonal wall angles, mouth aspect, area): the common language in which
  different families' knobs can be compared and seeded, without a shared generator (SD-1);
* **feasible steps**: per knob and direction, the largest unit step that still yields a legal
  record inside the brief envelope (build box: inner + wall), by bisection on real records.

Everything is CPU-only, read-only, deterministic (Sobol seed), and never edits a config: the
results are evidence for an owner-reviewed space card (``tools/analysis/space_card.py``).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .record import RecordRefusal, descriptors, envelope_margins, record_for_design

#: Column RMS (mm per full knob range) below which a knob is "inactive" at a point.
INACTIVE_MM = 0.05
#: |cos| at or above which two knob columns are treated as the same surface direction.
COUPLED_COS = 0.95
#: Largest single-point displacement (mm per FULL knob range) below which a knob is "weak": its
#: whole range moves no surface point by more than the mesher's own fit error (~1 mm, X1B/N1b).
WEAK_MM = 1.0
#: Fraction of sample points where a knob must be active to count as "active" (else conditional).
ACTIVE_FRAC = 0.8
DESCRIPTOR_KEYS = ("mouth_width_mm", "mouth_height_mm", "depth_mm", "h_wall_angle_mouth_deg",
                   "v_wall_angle_mouth_deg", "diag_wall_angle_mouth_deg", "mouth_aspect",
                   "mouth_area_mm2", "h_halfwidth_mid_mm", "v_halfwidth_mid_mm")


# ------------------------------------------------------------------ space access

def searched_keys(space) -> list[str]:
    return list(space.keys())


def design_at(space, x):
    """Design at unit vector ``x`` (same denormalisation the optimizers use)."""
    return space.denormalize(np.asarray(x, dtype=float))


def seed_unit(space) -> np.ndarray:
    return np.asarray(space.normalize(space.seed), dtype=float)


def shared_descriptors(rec) -> dict:
    d = descriptors(rec)
    mid = len(d["h_halfwidth_mm"]) // 2
    return {"mouth_width_mm": d["mouth_width_mm"], "mouth_height_mm": d["mouth_height_mm"],
            "depth_mm": d["depth_mm"],
            "h_wall_angle_mouth_deg": float(d["h_wall_angle_deg"][-2]),
            "v_wall_angle_mouth_deg": float(d["v_wall_angle_deg"][-2]),
            "diag_wall_angle_mouth_deg": float(d["diag_wall_angle_deg"][-2]),
            "mouth_aspect": float(d["aspect"][-1]), "mouth_area_mm2": float(d["area_mm2"][-1]),
            "h_halfwidth_mid_mm": float(d["h_halfwidth_mm"][mid]),
            "v_halfwidth_mid_mm": float(d["v_halfwidth_mm"][mid])}


def record_at(space, cfg, x):
    """``(record, None)`` or ``(None, reason)``; a generator refusal is a reason, not a crash."""
    from ..design.generated import GENERATOR_ERROR_KEY
    try:
        d = design_at(space, x)
        if isinstance(d.params, dict) and GENERATOR_ERROR_KEY in d.params:
            return None, f"generator: {str(d.params[GENERATOR_ERROR_KEY])[:120]}"
        return record_for_design(d, cfg), None
    except RecordRefusal as exc:
        return None, f"record: {exc}"
    except Exception as exc:  # noqa: BLE001 - every failure is reported with its type
        return None, f"{type(exc).__name__}: {str(exc)[:120]}"


def _envelope(cfg) -> dict:
    env = (getattr(cfg, "brief", None) or {}).get("envelope") or {}
    return {k: float(env[v]) for k, v in (("width_mm", "max_mouth_w_mm"),
                                          ("height_mm", "max_mouth_h_mm"),
                                          ("depth_mm", "max_depth_mm")) if v in env}


def inside(rec, env: dict, tol_mm: float = 0.5) -> bool:
    m = envelope_margins(rec, env, include_wall=True)
    return all(v is None or v >= -tol_mm for v in m.values())


# ------------------------------------------------------------------ Jacobian at one point

@dataclass
class PointJacobian:
    x: np.ndarray
    keys: list[str]
    surface: np.ndarray            # (n_points*3, k) mm per unit step (= per full range)
    desc: np.ndarray               # (n_desc, k) descriptor units per full range
    col_rms_mm: np.ndarray         # (k,)
    col_max_mm: np.ndarray = None  # (k,) largest single-point displacement per full range
    failed: dict = field(default_factory=dict)   # knob -> reason (no difference available)

    def cosines(self) -> np.ndarray:
        n = np.linalg.norm(self.surface, axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            u = self.surface / np.where(n > 0, n, np.nan)
        c = np.nan_to_num(u.T @ u)
        np.fill_diagonal(c, 1.0)
        return c

    def singular_values(self) -> np.ndarray:
        n = np.linalg.norm(self.surface, axis=0)
        act = n > INACTIVE_MM * math.sqrt(self.surface.shape[0] / 3.0)
        if not act.any():
            return np.zeros(0)
        return np.linalg.svd(self.surface[:, act] / n[act], compute_uv=False)


def jacobian(space, cfg, x0, *, h: float = 0.02) -> PointJacobian:
    """Central differences in unit coordinates; one-sided at a bound. Column ``k`` is the surface
    change per FULL knob range (unit step 1). A knob whose perturbed design is refused on both
    sides is reported in ``failed`` with a zero column."""
    keys = searched_keys(space)
    x0 = np.clip(np.asarray(x0, float), 0.0, 1.0)
    base, why = record_at(space, cfg, x0)
    if base is None:
        raise ValueError(f"base point is not a legal record: {why}")
    v0 = base.inner.reshape(-1)
    d0 = np.array([shared_descriptors(base)[k] for k in DESCRIPTOR_KEYS])
    S = np.zeros((v0.size, len(keys)))
    D = np.zeros((len(DESCRIPTOR_KEYS), len(keys)))
    failed = {}
    for k in range(len(keys)):
        lo, hi = max(0.0, x0[k] - h), min(1.0, x0[k] + h)
        recs = {}
        for side, xv in (("lo", lo), ("hi", hi)):
            if xv == x0[k]:
                continue
            x = x0.copy()
            x[k] = xv
            r, why = record_at(space, cfg, x)
            if r is not None and r.inner.shape == base.inner.shape:
                recs[side] = (xv, r)
            else:
                failed.setdefault(keys[k], why or "shape changed")
        if "lo" in recs and "hi" in recs:
            (xa, ra), (xb, rb) = recs["lo"], recs["hi"]
        elif recs:
            side = next(iter(recs))
            xa, ra = (recs[side] if side == "lo" else (x0[k], base))
            xb, rb = ((x0[k], base) if side == "lo" else recs[side])
        else:
            continue
        failed.pop(keys[k], None)
        dx = xb - xa
        S[:, k] = (rb.inner.reshape(-1) - ra.inner.reshape(-1)) / dx
        da = np.array([shared_descriptors(ra)[q] for q in DESCRIPTOR_KEYS])
        db = np.array([shared_descriptors(rb)[q] for q in DESCRIPTOR_KEYS])
        D[:, k] = (db - da) / dx
    n_pts = v0.size // 3
    disp = np.sqrt(np.sum(S.reshape(n_pts, 3, -1) ** 2, axis=1))
    return PointJacobian(x=x0, keys=keys, surface=S, desc=D, col_rms_mm=np.sqrt((disp ** 2).mean(axis=0)),
                         col_max_mm=disp.max(axis=0), failed=failed)


# ------------------------------------------------------------------ feasibility along each knob

def feasible_steps(space, cfg, x0, *, iters: int = 6) -> dict:
    """Per knob: how far (in unit coordinates) one can move from ``x0`` toward each bound and
    still get a legal record inside the brief envelope (build box). 1.0 = the whole way to the
    bound. Bisection on real records, ``iters`` halvings (resolution 2**-iters of the gap)."""
    keys = searched_keys(space)
    env = _envelope(cfg)
    x0 = np.asarray(x0, float)
    out = {}

    def ok(x):
        r, _ = record_at(space, cfg, x)
        return r is not None and (not env or inside(r, env))

    for k, key in enumerate(keys):
        res = {}
        for side, target in (("lo", 0.0), ("hi", 1.0)):
            gap = abs(target - x0[k])
            if gap < 1e-12:
                res[side] = 1.0
                continue
            x = x0.copy()
            x[k] = target
            if ok(x):
                res[side] = 1.0
                continue
            good, bad = 0.0, 1.0
            for _ in range(iters):
                mid = 0.5 * (good + bad)
                x[k] = x0[k] + (target - x0[k]) * mid
                if ok(x):
                    good = mid
                else:
                    bad = mid
            res[side] = good
        out[key] = {"lo_frac": res["lo"], "hi_frac": res["hi"],
                    "feasible_unit_lo": float(x0[k] - res["lo"] * x0[k]),
                    "feasible_unit_hi": float(x0[k] + res["hi"] * (1.0 - x0[k]))}
    return out


# ------------------------------------------------------------------ multi-point analysis

def sample_points(space, n: int, *, seed: int = 20261117, include_seed: bool = True) -> list:
    k = len(searched_keys(space))
    pts = [seed_unit(space)] if include_seed else []
    if n > 0 and k > 0:
        from scipy.stats import qmc
        pts += list(qmc.Sobol(k, seed=seed).random(n))
    return pts


def analyze_space(space, cfg, *, n_points: int = 8, h: float = 0.02, feasibility: bool = True,
                  seed: int = 20261117) -> dict:
    """The space-card evidence: per-knob activity/coupling across sample points, effective
    dimension, descriptor sensitivities, and (optionally) feasible steps from the seed."""
    keys = searched_keys(space)
    pts = sample_points(space, n_points, seed=seed)
    jacs, refused = [], []
    for x in pts:
        try:
            jacs.append(jacobian(space, cfg, x, h=h))
        except ValueError as exc:
            refused.append({"x": [float(v) for v in x], "reason": str(exc)[:160]})
    if not jacs:
        return {"keys": keys, "n_points": len(pts), "legal_points": 0, "refused_points": refused}
    n_pts = jacs[0].surface.shape[0] // 3
    floor = INACTIVE_MM
    rms = np.array([j.col_rms_mm for j in jacs])                     # (P, k)
    mx = np.array([j.col_max_mm for j in jacs])                      # (P, k)
    active = rms > floor
    cos = np.array([np.abs(j.cosines()) for j in jacs])               # (P, k, k)
    desc = np.array([j.desc for j in jacs])                           # (P, n_desc, k)
    svals = [j.singular_values() for j in jacs]
    knobs = {}
    for i, key in enumerate(keys):
        frac = float(active[:, i].mean())
        label = "active" if frac >= ACTIVE_FRAC else ("inactive" if frac == 0.0 else "conditional")
        if label == "active" and float(np.median(mx[:, i])) < WEAK_MM:
            label = "weak"
        partners = []
        for jdx, other in enumerate(keys):
            if jdx == i:
                continue
            both = active[:, i] & active[:, jdx]
            if both.sum() == 0:
                continue
            c = cos[both, i, jdx]
            frac_c = float((c >= COUPLED_COS).mean())
            if frac_c >= ACTIVE_FRAC:
                partners.append({"knob": other, "median_abs_cos": float(np.median(c)),
                                 "frac_points_coupled": frac_c})
        sens = {q: float(np.median(desc[:, qi, i])) for qi, q in enumerate(DESCRIPTOR_KEYS)}
        knobs[key] = {"label": label, "active_frac": frac,
                      "median_rms_mm_per_range": float(np.median(rms[:, i])),
                      "max_rms_mm_per_range": float(rms[:, i].max()),
                      "median_max_disp_mm_per_range": float(np.median(mx[:, i])),
                      "coupled_with": partners, "descriptor_per_range": sens,
                      "failed_points": int(sum(key in j.failed for j in jacs))}
    eff = [int((s / s[0] > 0.05).sum()) if s.size else 0 for s in svals]
    result = {"keys": keys, "n_points": len(pts), "legal_points": len(jacs),
              "refused_points": refused, "record_points": n_pts,
              "effective_dimension": {"median": float(np.median(eff)), "min": int(min(eff)),
                                      "max": int(max(eff)), "searched": len(keys)},
              "knobs": knobs, "links": propose_links(jacs, keys, space)}
    if feasibility:
        result["feasible_from_seed"] = feasible_steps(space, cfg, seed_unit(space))
    return result


def _status(space, cfg, x, env) -> str:
    r, why = record_at(space, cfg, x)
    if r is None:
        return "refused"
    return "ok" if (not env or inside(r, env)) else "outside"


def box_feasibility(space, cfg, *, n: int = 64, seed: int = 20261117, bins: int = 5) -> dict:
    """Uniform (Sobol) scan of the WHOLE box: fraction legal-and-inside, and per knob the bad
    fraction in each of ``bins`` equal slices of its range. A side whose edge slice is mostly bad
    while the middle is fine is a re-bound candidate (the proposed cut is the slice edge)."""
    keys = searched_keys(space)
    env = _envelope(cfg)
    pts = sample_points(space, n, seed=seed, include_seed=False)
    st = [_status(space, cfg, x, env) for x in pts]
    X = np.asarray(pts)
    bad = np.array([s != "ok" for s in st])
    per = {}
    for i, key in enumerate(keys):
        idx = np.minimum((X[:, i] * bins).astype(int), bins - 1)
        rates = [float(bad[idx == b].mean()) if np.any(idx == b) else float("nan") for b in range(bins)]
        mid = np.nanmean(rates[1:-1]) if bins > 2 else np.nan
        prop = {}
        if rates[0] >= 0.5 and (np.isnan(mid) or rates[0] >= 2 * max(mid, 0.05)):
            prop["raise_lo_to_unit"] = 1.0 / bins
        if rates[-1] >= 0.5 and (np.isnan(mid) or rates[-1] >= 2 * max(mid, 0.05)):
            prop["lower_hi_to_unit"] = 1.0 - 1.0 / bins
        per[key] = {"bad_rate_by_slice": rates, **prop}
    counts = {k: st.count(k) for k in ("ok", "outside", "refused")}
    return {"n": len(pts), "counts": counts, "ok_frac": counts["ok"] / max(len(pts), 1),
            "per_knob": per}


def sigma_refusal_curve(space, cfg, *, sigmas=(0.05, 0.10, 0.15, 0.20, 0.25), n: int = 48,
                        seed: int = 20261117) -> dict:
    """Predicted bad-candidate rate (refused or outside the envelope) of the FIRST CMA-ES
    generations from the seed for each sigma0: isotropic N(x_seed, sigma0^2) in unit
    coordinates, clipped to the box (as ``search/cma.py`` runs it). No GPU; the measured
    2026-11-17 storm signature (sigma0 0.22-0.25 on wide boxes -> 25-48 % refusals) is the
    thing this predicts before a night is queued."""
    env = _envelope(cfg)
    x0 = seed_unit(space)
    rng = np.random.default_rng(seed)
    out = {}
    for sg in sigmas:
        xs = np.clip(x0 + sg * rng.standard_normal((n, x0.size)), 0.0, 1.0)
        st = [_status(space, cfg, x, env) for x in xs]
        out[f"{sg:.2f}"] = {"bad_rate": float(np.mean([s != "ok" for s in st])),
                            "refused": st.count("refused"), "outside": st.count("outside"), "n": n}
    return out


def margin_model(space, cfg, *, n: int = 96, seed: int = 20261117) -> dict:
    """WP 5.4, bounds as constraints: fit the BINDING build-box envelope margin (mm, + inside) as
    a linear function of the unit knob vector over a Sobol scan of legal records,
    ``margin(x) ~ m0 + g . x``. The half-space ``g . x >= -m0`` is a joint constraint the box
    alone cannot express (e.g. long AND wide). Reports the per-knob gradient in mm per FULL
    range, the fit R^2 and the sign agreement (how often the model calls inside/outside right).
    It is evidence for a proposal, never applied automatically."""
    keys = searched_keys(space)
    env = _envelope(cfg)
    if not env:
        return {"available": False, "reason": "brief has no envelope"}
    X, y, which = [], [], []
    for x in sample_points(space, n, seed=seed, include_seed=True):
        r, _ = record_at(space, cfg, x)
        if r is None:
            continue
        m = envelope_margins(r, env, include_wall=True)
        vals = {k: v for k, v in m.items() if v is not None}
        k_min = min(vals, key=vals.get)
        X.append(np.asarray(x, float))
        y.append(vals[k_min])
        which.append(k_min)
    if len(X) < len(keys) + 2:
        return {"available": False, "reason": f"only {len(X)} legal records"}
    X, y = np.asarray(X), np.asarray(y)
    A = np.c_[np.ones(len(X)), X]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    ss = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(((y - pred) ** 2).sum()) / ss if ss > 0 else float("nan")
    agree = float(np.mean((pred >= 0) == (y >= 0)))
    bounds = space.bounds
    grad = {k: {"mm_per_range": float(coef[i + 1]),
                "mm_per_knob_unit": float(coef[i + 1] / max(float(bounds[k].hi - bounds[k].lo), 1e-12))}
            for i, k in enumerate(keys)}
    return {"available": True, "n_legal": int(len(X)), "intercept_mm": float(coef[0]),
            "gradient": grad, "r2": r2, "sign_agreement": agree,
            "binding_axis_counts": {k: which.count(k) for k in set(which)},
            "inside_frac": float(np.mean(y >= 0)),
            "constraint": "sum_k g_k * x_k >= -intercept (x in unit coordinates)"}


def propose_links(jacs, keys, space) -> list:
    """Geometric link proposals for consistently coupled pairs.

    For each pair whose surface columns are parallel (|cos| >= COUPLED_COS at >= ACTIVE_FRAC of
    the points where both are active), fit ``col_follower ~ s * col_leader`` by least squares
    over the stacked points; moving the leader by ``dx`` then reproduces the follower's surface
    effect of ``s * dx``, so the follower is redundant. The follower is the knob with the SMALLER
    median surface authority. Proposals are greedy by coupling strength and form no chains (one
    level only, like ``search.links``). Converted to ``follower = scale * leader + offset`` in knob
    units through the seed. Geometric redundancy is not acoustic equivalence: confirm against
    data (``tools/analysis/links.py``) before applying."""
    x0 = seed_unit(space)
    bounds = space.bounds
    auth = np.median(np.array([J.col_rms_mm for J in jacs]), axis=0)
    cands = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            cs = []
            for J in jacs:
                a, b = J.surface[:, i], J.surface[:, j]
                na, nb = np.linalg.norm(a), np.linalg.norm(b)
                if na > 0 and nb > 0:
                    cs.append(abs(float(a @ b) / (na * nb)))
            if cs and np.mean(np.asarray(cs) >= COUPLED_COS) >= ACTIVE_FRAC:
                f, l = (i, j) if auth[i] <= auth[j] else (j, i)
                cands.append((float(np.median(cs)), f, l))
    used_f, used_l, out = set(), set(), []
    for c, f, l in sorted(cands, reverse=True):
        if f in used_f or f in used_l or l in used_f:
            continue
        num = sum(float(J.surface[:, f] @ J.surface[:, l]) for J in jacs)
        den = sum(float(J.surface[:, l] @ J.surface[:, l]) for J in jacs)
        if den <= 0:
            continue
        s_unit = num / den                      # dx_f(unit) equivalent per dx_l(unit)
        kf, kl = keys[f], keys[l]
        wf = float(bounds[kf].hi - bounds[kf].lo)
        wl = float(bounds[kl].hi - bounds[kl].lo)
        scale = s_unit * wf / wl
        f0 = float(bounds[kf].lo + x0[f] * wf)
        l0 = float(bounds[kl].lo + x0[l] * wl)
        used_f.add(f)
        used_l.add(l)
        out.append({"follower": kf, "from": kl, "scale": float(scale), "offset": float(f0 - scale * l0),
                    "median_abs_cos": c,
                    "authority_mm": {"follower": float(auth[f]), "leader": float(auth[l])},
                    "note": "geometric redundancy at the sampled points; confirm with data links "
                            "(tools/analysis/links.py) and acoustics before applying"})
    return out


__all__ = ["margin_model", "box_feasibility", "sigma_refusal_curve", "WEAK_MM", "analyze_space", "jacobian", "feasible_steps", "propose_links", "shared_descriptors",
           "record_at", "sample_points", "seed_unit", "DESCRIPTOR_KEYS", "INACTIVE_MM",
           "COUPLED_COS", "ACTIVE_FRAC", "PointJacobian"]
