"""Model diagnostics artifact ``study-model-diagnostics-v1`` (kind ``diagnostics``).

Per-model, read-only diagnostics computed with BoTorch from a refit of the stored training set:
hyperparameters/relevance, efficient leave-one-out (no refit per row), 1-D slices through the
incumbent, and (Pareto studies) the non-dominated front plus a hypervolume trace.  All values are
on the J scale shown to the user (J = -posterior mean of Y).  BoTorch is imported lazily.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import numpy as np

SCHEMA = "study-model-diagnostics-v1"
KIND = "diagnostics"
GRID_N = 25
LOO_ROW_CAP = 400
MAX_BYTES = 128 * 1024
LOO_METHOD = "efficient_loo_cv (no refit)"
BOUND_REL_TOL = 0.01
#: This artifact is built by refitting the stored training set after the proposals were made.
#: It is NOT a per-proposal historical prediction and must never be relabelled as one.
PREDICTION_SOURCE = "refit_from_stored_training_set"
RETROSPECTIVE_NOTE = (
    "Diagnostics are a retrospective refit of the stored training set; they are not the "
    "per-proposal predictions recorded when each candidate was proposed.")
INTERVAL_NOTE = (
    "±2σ is the model's credible interval. It is not an empirically calibrated 95% interval "
    "unless the recorded coverage evidence in interval_evidence supports that claim.")
SLICE_LABELS = {
    "caveat": "model sensitivity, not a proven physical effect",
    "anchor": "other knobs held at incumbent",
    "band": "mean ±2σ model credible interval",
    "invalid": ("a 1-D slice can pass through geometrically invalid combinations; the "
                "feasibility flag says whether that was checked"),
}
# Prefix hypervolume is mathematically non-decreasing, but BoTorch's box decomposition sums
# boxes in an order that depends on how many points the prefix holds, so a dominated point can
# move the float result by a few ulps.  Clamp to the running maximum and coalesce sub-tolerance
# steps so the trace stays monotone and does not record noise-level "changes".
HV_REL_TOL = 1e-12


def _f(x):
    x = float(x)
    return x if math.isfinite(x) else None


def _fl(a):
    return [_f(v) for v in np.asarray(a, dtype=float).reshape(-1)]


def _unavailable(study_id, revision, policy, reason, **extra):
    return {"schema": SCHEMA, "study_id": study_id, "revision": revision, "policy": policy,
            "generated_utc": datetime.now(timezone.utc).isoformat(), "status": "unavailable",
            "reason": str(reason), "retrospective": True,
            "model_revision": revision, "prediction_source": PREDICTION_SOURCE,
            "retrospective_note": RETROSPECTIVE_NOTE, **extra}


def _hyper(fit, keys):
    h = fit.hyperparameters or {}
    ls = [float(v) for v in h.get("lengthscales", [])]
    lo, hi = h.get("lengthscale_bounds", [None, None])
    names = list(keys) if keys and len(keys) == len(ls) else [f"x{i}" for i in range(len(ls))]
    rel = []
    for k, l in zip(names, ls):
        at = bool(lo is not None and (l <= lo * (1 + BOUND_REL_TOL) or l >= hi * (1 - BOUND_REL_TOL)))
        rel.append({"key": k, "inv_lengthscale": _f(1.0 / l), "rank": 0, "at_bound": at})
    order = sorted(range(len(rel)), key=lambda i: -(rel[i]["inv_lengthscale"] or 0.0))
    for r, i in enumerate(order, 1):
        rel[i]["rank"] = r
    hyper = {"active_keys": names, "lengthscales": _fl(ls), "outputscale": _f(h.get("outputscale", float("nan"))),
             "noise": _f(fit.train_Yvar_original) if fit.train_Yvar_original is not None else None,
             "noise_transformed": h.get("noise_transformed"),
             "lengthscale_bounds": [lo, hi]}
    return hyper, rel


def _accuracy(residuals):
    r = np.asarray(residuals, dtype=float).reshape(-1)
    if r.size == 0:
        return {"rmse": None, "mae": None, "mean_error": None}
    return {"rmse": _f(np.sqrt(np.mean(r ** 2))), "mae": _f(np.mean(np.abs(r))),
            "mean_error": _f(np.mean(r))}


def _loo(fit, ids, sign=-1.0):
    """LOO on the J scale.  sign=-1 maps Y=-J back to J (both scalar and Pareto outputs)."""
    from botorch.cross_validation import efficient_loo_cv
    res = efficient_loo_cv(fit.model, observation_noise=True, untransform=True)
    mu = res.posterior.mean.detach().cpu().numpy().reshape(-1)
    sd = res.posterior.variance.clamp_min(0.0).sqrt().detach().cpu().numpy().reshape(-1)
    yo = res.observed_Y.detach().cpu().numpy().reshape(-1)
    j_obs, j_mu = sign * yo, sign * mu
    z = (j_obs - j_mu) / np.where(sd > 0, sd, np.nan)
    residual = j_obs - j_mu
    summary = {"rmse": _f(np.sqrt(np.mean(residual ** 2))), "spearman": None,
               "coverage_95": _f(np.nanmean(np.abs(z) <= 1.96)),
               "mean_z": _f(np.nanmean(z)), "sd_z": _f(np.nanstd(z))}
    if len(j_obs) > 2:
        try:
            from scipy.stats import spearmanr
            summary["spearman"] = _f(spearmanr(j_obs, j_mu)[0])
        except Exception:  # noqa: BLE001
            pass
    n = len(j_obs)
    rows = [{"id": str(ids[i]) if i < len(ids) else str(i), "j_obs": _f(j_obs[i]),
             "j_mean": _f(j_mu[i]), "j_sd": _f(sd[i])} for i in range(min(n, LOO_ROW_CAP))]
    # Empirical coverage is recorded evidence; a large-sample near-95% result is the only
    # thing that may support calling the interval calibrated, and even then only for this
    # LOO cohort (not for later proposal predictions).
    coverage = summary["coverage_95"]
    supported = bool(coverage is not None and n >= 30 and abs(coverage - 0.95) <= 0.10)
    return {"method": LOO_METHOD, "n": n, "rows": rows, "truncated": n > LOO_ROW_CAP,
            "label": "Efficient leave-one-out on the original training cohort",
            "cohort": "original training cohort; hyperparameters held fixed (no refit per row)",
            "error": _accuracy(residual), "rank_correlation": summary["spearman"],
            "summary": summary,
            "interval_evidence": {
                "declared_interval": "±1.96σ efficient-LOO posterior sd",
                "claimed_level": 0.95,
                "empirical_coverage": coverage,
                "n": n,
                "calibrated_95_supported": supported,
                "basis": ("efficient-LOO residual coverage on the training cohort"
                          if n else "not recorded"),
                "note": INTERVAL_NOTE}}


def _raw(u, tr):
    if not tr:
        return list(u)
    lo, hi = tr["lo"], tr["hi"]
    if tr.get("log"):
        a, b = math.log10(lo), math.log10(hi)
        return [10.0 ** (a + v * (b - a)) for v in u]
    return [lo + v * (hi - lo) for v in u]


def slice_feasibility_block(values):
    """Presentation block for an optional cheap-feasibility evaluation of a slice.

    ``values`` is a per-grid-point sequence of ``True`` (valid), ``False`` (invalid) or
    ``None`` (not evaluated).  No value means the check was not run, so the block says
    ``unknown`` rather than implying the slice is valid.
    """
    if not isinstance(values, (list, tuple)) or not values:
        return {"checked": False, "status": "unknown", "invalid_count": None,
                "reason": ("cheap feasibility was not evaluated for this slice; a 1-D slice can "
                           "pass through geometrically invalid combinations")}
    flags = [bool(v) if isinstance(v, bool) else None for v in values]
    invalid = sum(1 for v in flags if v is False)
    unchecked = sum(1 for v in flags if v is None)
    status = "warned" if invalid else ("unknown" if unchecked else "clear")
    return {"checked": True, "status": status, "invalid_count": int(invalid),
            "unchecked_count": int(unchecked),
            "reason": ("some grid points pass through invalid geometry" if invalid else
                       ("some grid points were not checked" if unchecked else
                        "all evaluated grid points are cheap-feasible"))}


def _slices(fit, anchor_idx, anchor_id, keys, transforms, sign=-1.0, feasibility=None):
    import torch
    X = np.asarray(fit.train_X, dtype=float)
    anchor = X[anchor_idx]
    grid = np.linspace(0.0, 1.0, GRID_N)
    feasibility = feasibility if isinstance(feasibility, dict) else {}
    with torch.no_grad():
        anchor_post = fit.model.posterior(
            torch.as_tensor(anchor.reshape(1, -1), dtype=torch.float64),
            observation_noise=False)
        anchor_j_mean = sign * float(
            anchor_post.mean.detach().cpu().numpy().reshape(-1)[0])
    per_key = {}
    for k in range(X.shape[1]):
        G = np.tile(anchor, (GRID_N, 1))
        G[:, k] = grid
        with torch.no_grad():
            post = fit.model.posterior(torch.as_tensor(G, dtype=torch.float64),
                                       observation_noise=False)
            mu = post.mean.detach().cpu().numpy().reshape(-1)
            sd = post.variance.clamp_min(0.0).sqrt().detach().cpu().numpy().reshape(-1)
        name = keys[k] if k < len(keys) else f"x{k}"
        tr = transforms.get(name)
        j_mean = sign * mu
        per_key[name] = {
            "x": _fl(_raw(grid, tr)), "x_unit": _fl(grid),
            "j_mean": _fl(j_mean), "j_sd": _fl(sd),
            "j_lower": _fl(j_mean - 2.0 * sd), "j_upper": _fl(j_mean + 2.0 * sd),
            "anchor_x": _f(_raw([anchor[k]], tr)[0]),
            "anchor_x_unit": _f(anchor[k]), "anchor_j_mean": _f(anchor_j_mean),
            "unit": (tr or {}).get("unit"),
            "feasibility": slice_feasibility_block(feasibility.get(name)),
            "labels": dict(SLICE_LABELS),
        }
    return {"anchor": "incumbent", "anchor_id": anchor_id, "grid_n": GRID_N,
            "other_knobs": "held at incumbent", "labels": dict(SLICE_LABELS),
            "per_key": per_key}


def _model_block(fit, keys, transforms, j_train, ids, feasibility=None):
    hyper, rel = _hyper(fit, keys)
    anchor_idx = int(np.argmin(np.asarray(j_train, dtype=float)))
    return {"hyperparameters": hyper, "relevance": rel, "loo": _loo(fit, ids),
            "slices": _slices(fit, anchor_idx, str(ids[anchor_idx]) if ids else None,
                              hyper["active_keys"], transforms, feasibility=feasibility)}


def _pareto_block(pareto):
    import torch
    from botorch.utils.multi_objective.hypervolume import Hypervolume
    from botorch.utils.multi_objective.pareto import is_non_dominated
    pt = pareto["training"]
    errors = np.asarray(pt.errors, dtype=float)
    ref = np.asarray(pt.reference["ref_point"], dtype=float)
    Y = torch.as_tensor(-errors, dtype=torch.float64)       # maximisation space
    ids = [str(i) for i in pt.ids]
    inside = (Y > torch.as_tensor(ref, dtype=torch.float64)).all(dim=-1)
    front = is_non_dominated(Y)
    hv = Hypervolume(ref_point=torch.as_tensor(ref, dtype=torch.float64))
    trace, last = [], None
    for s in range(len(ids)):
        sel = inside[:s + 1]
        v = float(hv.compute(Y[:s + 1][sel])) if bool(sel.any()) else 0.0
        if last is not None and v < last:                 # prefix HV cannot shrink; float jitter can
            v = last
        if last is None or v > last * (1.0 + HV_REL_TOL) or s == len(ids) - 1:
            trace.append({"seq": s + 1, "hv": _f(v)})
        last = v
    return {"objectives": ["coverage_err_deg", "ripple_db"], "ref_point": _fl(ref),
            "front_ids": [ids[i] for i in range(len(ids)) if bool(front[i])],
            "hv_trace": trace, "hv_trace_note": "seq is the training-row order; rows beyond the "
            "frozen reference add no hypervolume; the running value is clamped at its maximum so "
            "box-decomposition round-off cannot make the trace decrease"}


def build_diagnostics(fit, training_set, policy, pareto=None, *, study_id=None, revision=None,
                      encoding=None, training_set_id=None, slice_feasibility=None):
    """Build the diagnostics payload.

    ``fit``: scalar :class:`ModelFitResult` (``bo.model.fit_model``).  ``pareto`` (Pareto studies
    only): ``{"fit": ParetoFit, "training": ParetoTraining}``; hyperparameters/LOO/slices are then
    reported per objective under ``per_objective`` as well.  ``slice_feasibility`` is an optional
    ``{active_key: [True|False|None, ...]}`` cheap-feasibility evaluation of each slice grid; no
    value marks the slice ``unknown`` instead of implying validity.
    """
    if fit is None or not getattr(fit, "ok", False):
        return _unavailable(study_id, revision, policy, getattr(fit, "reason", "no_fit"),
                            detail=getattr(fit, "detail", None), training_set_id=training_set_id)
    transforms = {}
    keys = list(getattr(training_set, "active_keys", ()) or ())
    if encoding is not None:
        keys = list(encoding.active_keys)
        try:
            transforms = {k: v for k, v in encoding.key_transforms().items()}
        except Exception:  # noqa: BLE001
            transforms = {}
    ids = list(fit.train_ids)
    j_train = np.asarray(training_set.J, dtype=float).reshape(-1)
    out = {"schema": SCHEMA, "study_id": study_id, "revision": revision,
           "training_set_id": training_set_id, "policy": policy,
           "generated_utc": datetime.now(timezone.utc).isoformat(),
           "library_versions": dict(fit.library_versions or {}), "status": "ok", "reason": "ok",
           "seed": int(fit.seed), "model_policy": fit.model_policy,
           # This artifact is always a refit of the stored training set (see diagnose_study);
           # surface that so the GUI never relabels it as a historical per-proposal prediction.
           "retrospective": True, "model_revision": revision,
           "prediction_source": PREDICTION_SOURCE, "retrospective_note": RETROSPECTIVE_NOTE,
           "interval_note": INTERVAL_NOTE,
           "sections": {
               "efficient_loo_cv": ("original training cohort; leave-one-out, hyperparameters "
                                    "held fixed; not sequential tracking of later proposals"),
               "posterior_slices": ("1-D through the incumbent; other knobs held at incumbent; "
                                    "model sensitivity, not a proven physical effect")}}
    out.update(_model_block(fit, keys, transforms, j_train, ids,
                            feasibility=slice_feasibility))
    out["pareto"] = None
    if pareto is not None and pareto.get("fit") is not None and pareto["fit"].status == "ok":
        per = {}
        for name, o, col in zip(("coverage", "ripple"), pareto["fit"].outputs, (0, 1)):
            j = np.asarray(pareto["training"].errors, dtype=float)[:, col]
            idx = {str(i): n for n, i in enumerate(pareto["training"].ids)}
            sub = [j[idx[i]] for i in o.train_ids]
            per[name] = _model_block(o, keys, transforms, sub, list(o.train_ids),
                                     feasibility=slice_feasibility)
        out["per_objective"] = per
        out["pareto"] = _pareto_block(pareto)
    elif pareto is not None:
        out["pareto_unavailable"] = str(getattr(pareto.get("fit"), "reason", "no_pareto_fit"))
    return _fit_size(out)


def _fit_size(payload):
    def size():
        return len(json.dumps(payload, allow_nan=False, separators=(",", ":")).encode())
    blocks = lambda: [payload] + list((payload.get("per_objective") or {}).values())  # noqa: E731
    while size() > MAX_BYTES:
        longest = max(blocks(), key=lambda b: len(b["loo"]["rows"]))
        rows = longest["loo"]["rows"]
        if len(rows) <= 10:
            break
        del rows[len(rows) // 2:]
        longest["loo"]["truncated"] = True
    payload["size_bytes"] = size()
    return payload


def diagnose_study(service, study_id, *, root, seed=None, policy=None):
    """Refit from the stored training artifacts, build and attach the ``diagnostics`` artifact."""
    from ..studies import builders as B
    from ..studies.schema import Unavailable
    from . import policy as policy_mod
    from .data import TrainingSet
    from .model import fit_model

    study, effective = B._study_spec(service, study_id, None)
    revision = study["revision"]
    existing = B._existing(service, study_id, revision, KIND)
    if existing is not None:
        return {"status": "ok", "revision": revision, "idempotent": True, "artifact": existing}
    training_meta = B._require(service, study_id, "training")
    manifest_meta = B._require(service, study_id, "training_manifest")
    spec_policy = effective.get("policy") if isinstance(effective.get("policy"), dict) else {}
    chosen = (policy or spec_policy.get("proposal_policy")
              or (spec_policy.get("mode") if spec_policy.get("mode") in policy_mod.PROPOSAL_POLICIES
                  else None) or "scalar")
    if seed is None:
        seed = spec_policy.get("seed", spec_policy.get("acq_seed", 0))
    manifest = B._load_json(service.store.artifacts / manifest_meta["sha256"], "training manifest")
    with np.load(service.store.artifacts / training_meta["sha256"], allow_pickle=False) as a:
        ts = TrainingSet(
            status=manifest["status"], d=int(manifest["d"]), n=int(manifest["n"]),
            X=np.asarray(a["X"], dtype=np.float64),
            J=np.asarray(a["J"], dtype=np.float64).reshape(-1, 1),
            Y=np.asarray(a["Y"], dtype=np.float64).reshape(-1, 1), Y_phys=None, G=None,
            ids=tuple(manifest["ids"]), selected_ids=tuple(manifest["selected_ids"]),
            excluded_ids=tuple(manifest["excluded_ids"]), elite_ids=tuple(manifest["elite_ids"]),
            maximin_ids=tuple(manifest["maximin_ids"]), n_eligible=int(manifest["n_eligible"]),
            n_unique=int(manifest["n_unique"]), n_min=int(manifest["n_min"]),
            n_max=int(manifest["n_max"]), active_keys=tuple(manifest["active_keys"]),
            projection_version=manifest.get("projection_version"), preparation=None,
            meta=dict(manifest.get("meta") or {}))
    encoding = None
    try:
        from ..config import load_config
        from ..design.space import DesignSpace
        task = B._read_task(effective.get("task"), root=root,
                            config=(effective.get("task") or {}).get("config")
                            if isinstance(effective.get("task"), dict) else None)
        encoding = B._task_encoding(DesignSpace.from_config(load_config(task["config"])))
    except Exception:  # noqa: BLE001 - raw-unit axes are best-effort
        encoding = None
    fit = fit_model(ts, seed=int(seed))
    pareto = None
    if chosen == "pareto":
        try:
            from .pareto import fit_pareto_training
            B.build_pareto_metrics(service, study_id, root=root)
            pm = B._require(service, study_id, B.PARETO_METRICS_KIND)
            payload = B._load_json(service.store.artifacts / pm["sha256"], "pareto metrics")
            pt = B.pareto_training_from_artifacts(ts, payload)
            pareto = {"fit": fit_pareto_training(pt, seed=int(seed)), "training": pt}
        except Unavailable as exc:
            pareto = {"fit": None, "training": None, "reason": str(exc)}
    payload = build_diagnostics(fit, ts, chosen, pareto, study_id=study_id, revision=revision,
                                encoding=encoding, training_set_id=manifest.get("training_set_id"))
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    meta = service.attach_artifact(study_id, revision, KIND, content,
                                   {"training": training_meta["sha256"],
                                    "training_manifest": manifest_meta["sha256"]},
                                   f"diagnostics:{revision}:{chosen}:{int(seed)}")
    return {"status": payload["status"], "reason": payload["reason"], "revision": revision,
            "idempotent": False, "artifact": meta, "size_bytes": payload.get("size_bytes")}
