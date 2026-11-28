"""Unified, typed evidence index over one snapshot: ranks, facets, back-links, query and diff.

Every evidence row (dose run, cohort, mesh class, canary pair, replicate, claim reconciliation and
finding) becomes one index entry with the SAME shape, so people and agents can search, filter, sort
and cross-reference without knowing each section's layout:

    {id, section, label, group, status, tone, identity, rank, rank_basis,
     metrics: {name: cell}, cited_by: [finding ids], cites: [row ids], text}

Ranks are explicit and never cross a score identity:

* dose runs rank inside (family, brief, objective version, mesh epw): predeclared PASS first, then J
  ascending (the project rule "rules first, then J"); controls are unranked;
* cohorts rank by admission readiness (pilot_eligible > needs_admission > hold > replay_mismatch >
  not_evaluated), then unique designs descending; J is never used across cohorts;
* mesh classes rank by solved-DOF reduction (acoustic evidence before mesh-only/unsupported);
* canary pairs rank by verify J (one verify identity); findings keep their severity order.

Pure functions over the snapshot dict; nothing here reads a source.
"""
from __future__ import annotations

from typing import Any, Iterable

TONE = {"pass": "good", "pilot_eligible": "good", "holdout_pass": "good", "agrees": "good", "acoustic": "good",
        "confirmation_pass_for_exploratory_pilot": "good", "ok": "good",
        "fail": "bad", "hold": "bad", "replay_mismatch": "bad", "status_conflict": "bad", "missing": "warn",
        "unknown": "warn", "needs_admission": "warn", "mesh_only": "warn", "not_comparable": "neutral",
        "not_evaluated": "neutral", "unsupported": "neutral", "control": "neutral",
        "decision": "good", "data_quality": "warn", "info": "neutral"}
READINESS = ["pilot_eligible", "confirmation_pass_for_exploratory_pilot", "needs_admission", "hold",
             "replay_mismatch", "unknown", "not_evaluated"]

#: Column catalogue for UIs and agents: metric name -> (label, unit, better). better is "low", "high" or None.
COLUMNS = {
    "dose": {"J": ("J", "", "low"), "H8k": ("H 8 kHz", "°", None), "min_re_z": ("min Re(z)", "", "high"),
             "epw": ("mesh epw", "", None), "bb_h": ("bb_h", "", None), "throat": ("throat", "", None),
             "rollin": ("roll-in", "", None), "n_dof": ("DOF", "", None)},
    "cohort": {"unique_designs": ("unique", "", "high"), "valid": ("valid rows", "", "high"),
               "failed_total": ("failed", "", "low"), "bem_hours": ("BEM h", "h", None),
               "treatment_variants": ("config revs", "", None), "best_J": ("best J (own identity)", "", None)},
    "mesh": {"dof_reduction_pct": ("DOF cut", "%", "high"), "max_bw_delta_deg": ("max BW Δ", "°", "low"),
             "f_hi_hz": ("f max", "Hz", None)},
    "canary": {"verify_J": ("verify J", "", "low"), "screen_J": ("screen J", "", "low")},
    "replicate": {"abs_delta": ("|ΔJ|", "", "low")},
    "reconciliation": {"claimed_unique": ("claimed unique", "", None), "unique_at_cutoff": ("unique now", "", None),
                       "unique_delta": ("Δ unique", "", None)},
    "finding": {},
}


def _v(c: Any):
    return c.get("v") if isinstance(c, dict) else None


def _num(c: Any) -> float | None:
    v = _v(c)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _entry(section, id_, label, group, status, identity, metrics, extra_text="", rank=None, basis=None, cites=None):
    metrics = {k: v for k, v in metrics.items() if isinstance(v, dict)}
    text = " ".join(str(x) for x in (id_, label, group, status, identity, extra_text) if x).lower()
    return {"id": id_, "section": section, "label": label, "group": group, "status": status,
            "tone": TONE.get(str(status), "neutral"), "identity": identity, "rank": rank, "rank_basis": basis,
            "metrics": metrics, "cited_by": [], "cites": list(cites or []), "text": text}


def _rank(entries: list[dict], key, basis: str, group_key=lambda e: None) -> None:
    groups: dict = {}
    for e in entries:
        groups.setdefault(group_key(e), []).append(e)
    for grp in groups.values():
        ranked = [e for e in grp if key(e) is not None]
        for i, e in enumerate(sorted(ranked, key=key), start=1):
            e["rank"], e["rank_basis"] = i, basis


def build_index(snap: dict) -> list[dict]:
    out: list[dict] = []
    dose = []
    for r in snap["dose"]["rows"]:
        k = r.get("knobs") or {}
        ident = f"{r['family']}|{_v(r.get('brief_hash'))}|v{_v(r.get('objective_version'))}|epw{_v(r.get('epw'))}"
        e = _entry("dose", r["id"], r["job"], r["family"], r["verdict"]["v"], ident,
                   {"J": r.get("J"), "H8k": r.get("H8k"), "min_re_z": r.get("min_re_z"), "epw": r.get("epw"),
                    "bb_h": k.get("g_bb_h"), "throat": k.get("g_bb_throat_frac"), "rollin": k.get("g_bb_rollin_frac"),
                    "n_dof": r.get("n_dof")},
                   " ".join(r["verdict"].get("failed_rules") or []))
        e["is_control"] = r["is_control"]
        dose.append(e)
    _rank(dose, lambda e: None if e.get("is_control") or _num(e["metrics"].get("J")) is None
          else (0 if e["status"] == "pass" else 1, _num(e["metrics"]["J"])),
          "within score identity: predeclared pass first, then J ascending", lambda e: e["identity"])
    out += dose

    coh = []
    for c in snap["inventory"]["cohorts"]:
        oe = c.get("optimizer_evidence") or {}
        coh.append(_entry("cohort", c["id"], c["config_name"], c["mode"], c["status"], c["id"],
                          {"unique_designs": c["unique_designs"], "valid": c["valid"], "failed_total": c["failed_total"],
                           "bem_hours": (oe.get("totals") or {}).get("bem_hours"),
                           "treatment_variants": c.get("treatment_variants"), "best_J": c["best_J"]},
                          f"brief {c['brief_hash']} {' '.join(c['failed'])}"))
    _rank(coh, lambda e: (READINESS.index(e["status"]) if e["status"] in READINESS else len(READINESS),
                          -(_num(e["metrics"]["unique_designs"]) or 0), e["label"]),
          "admission readiness, then unique designs descending (J never compared across cohorts)")
    out += coh

    mesh = []
    for r in snap["mesh"].get("rows", []):
        mesh.append(_entry("mesh", r["id"], r["label"], r["class"], r["evidence"], None,
                           {"dof_reduction_pct": r["dof_reduction_pct"], "max_bw_delta_deg": r["max_bw_delta_deg"],
                            "f_hi_hz": r["f_hi_hz"]}, r["scope"]))
    _rank(mesh, lambda e: (0 if e["status"] == "acoustic" else 1, -(_num(e["metrics"]["dof_reduction_pct"]) or 0)),
          "acoustic evidence first, then DOF reduction descending")
    out += mesh

    can = snap["canary"]
    if can.get("status") == "ok":
        pairs = [_entry("canary", f"canary:{p['design']}", p["design"], "verify pair", "ok",
                        can["identities"]["verify_brief"], {"verify_J": p["verify_J"], "screen_J": p["screen_J"]})
                 for p in can["verify_pairs"]]
        _rank(pairs, lambda e: _num(e["metrics"]["verify_J"]), "verify J ascending (one verify identity)")
        out += pairs
        out += [_entry("replicate", f"canary:{r['mode']}:{r['design']}", r["design"], r["mode"], "control", None,
                       {"abs_delta": r["abs_delta"]}) for r in can["replicates"]]

    for r in snap["reconciliation"]:
        out.append(_entry("reconciliation", f"recon:{r['config_name']}", r["config_name"],
                          f"handoff line {r.get('claim_line')}", r["result"], r.get("cohort"),
                          {"claimed_unique": r.get("claimed_unique"), "unique_at_cutoff": r.get("unique_at_cutoff"),
                           "unique_delta": r.get("unique_delta")},
                          f"{r.get('claimed_status')} {r.get('artifact_status')}",
                          cites=[r["cohort"]] if r.get("cohort") else []))

    for i, f in enumerate(snap["findings"], start=1):
        out.append(_entry("finding", f"finding:{f['id']}", f["title"], f["kind"], f["severity"], None, {},
                          f"{f['plain']} {f['observation']}", rank=i, basis="severity order (decision first)",
                          cites=f["evidence"]))

    by_id = {e["id"]: e for e in out}
    for f in snap["findings"]:
        for ev in f["evidence"]:
            if ev in by_id:
                by_id[ev]["cited_by"].append(f"finding:{f['id']}")
    return out


def facets(index: list[dict]) -> dict:
    fac: dict[str, dict[str, int]] = {"section": {}, "status": {}, "tone": {}}
    for e in index:
        for k in fac:
            fac[k][str(e[k])] = fac[k].get(str(e[k]), 0) + 1
    fac["cited"] = {"cited_by_a_finding": sum(1 for e in index if e["cited_by"])}
    return {k: dict(sorted(v.items())) for k, v in fac.items()}


def query(index: Iterable[dict], *, section: str | None = None, status: str | None = None, tone: str | None = None,
          text: str | None = None, cited: bool | None = None, sort: str | None = None, desc: bool = False,
          limit: int | None = None) -> list[dict]:
    """Filter + sort. ``sort`` is ``rank``, ``label``, ``status`` or a metric name; rows without the key last."""
    rows = list(index)
    if section:
        rows = [e for e in rows if e["section"] == section]
    if status:
        rows = [e for e in rows if str(e["status"]) == status]
    if tone:
        rows = [e for e in rows if e["tone"] == tone]
    if text:
        terms = text.lower().split()
        rows = [e for e in rows if all(t in e["text"] for t in terms)]
    if cited is not None:
        rows = [e for e in rows if bool(e["cited_by"]) == cited]
    key = sort or "rank"

    def val(e):
        if key in ("rank", "label", "status", "section", "group"):
            return e.get(key)
        return _v(e["metrics"].get(key))
    present = [e for e in rows if val(e) is not None]
    absent = [e for e in rows if val(e) is None]
    present.sort(key=lambda e: (val(e) if not isinstance(val(e), bool) else int(val(e))), reverse=desc)
    rows = present + absent
    return rows[:limit] if limit else rows


def diff(a: dict, b: dict) -> dict:
    """What changed from snapshot ``a`` (older) to ``b`` (newer), by stable ids (never by raw J across identities)."""
    ia, ib = {e["id"]: e for e in a["index"]}, {e["id"]: e for e in b["index"]}
    fa = {(f["kind"], tuple(f["evidence"])): f for f in a["findings"]}
    fb = {(f["kind"], tuple(f["evidence"])): f for f in b["findings"]}
    status_changes, metric_changes = [], []
    for i in sorted(set(ia) & set(ib)):
        x, y = ia[i], ib[i]
        if x["status"] != y["status"]:
            status_changes.append({"id": i, "section": y["section"], "label": y["label"],
                                   "from": x["status"], "to": y["status"]})
        for m in sorted(set(x["metrics"]) | set(y["metrics"])):
            vx, vy = _v(x["metrics"].get(m)), _v(y["metrics"].get(m))
            if vx != vy:
                metric_changes.append({"id": i, "section": y["section"], "label": y["label"], "metric": m,
                                       "from": vx, "to": vy})
    return {"from": {"snapshot_id": a["snapshot_id"], "cutoff_utc": a["cutoff_utc"]},
            "to": {"snapshot_id": b["snapshot_id"], "cutoff_utc": b["cutoff_utc"]},
            "rows_added": sorted(set(ib) - set(ia)), "rows_removed": sorted(set(ia) - set(ib)),
            "findings_added": [{"kind": f["kind"], "title": f["title"], "id": f["id"]} for k, f in fb.items() if k not in fa],
            "findings_resolved": [{"kind": f["kind"], "title": f["title"], "id": f["id"]} for k, f in fa.items() if k not in fb],
            "status_changes": status_changes, "metric_changes": metric_changes,
            "note": "rows are matched by stable id; a metric change is within the same row/identity only"}
