"""Read-only evidence adapters for the M1 research snapshot.

Each adapter turns persisted artifacts into rows of cells (see ``provenance``). None of them
imports a solver or mesher, writes outside the caller's output directory, or re-scores anything:
score attribution reuses ``gui.data_breakdown`` (which calls the objective package's own weight
resolvers) on STORED terms.

Adapters
--------
``dose_experiment``   CD-backbone fixed-candidate verifies (2026-11-25), committed ``results*.json``
                      + the committed run configs; local run dirs only corroborate.
``cohort_inventory``  v11 runs under ``runs/`` grouped strictly by score identity, positive and
                      negative rows counted, joined to the existing admission artifacts.
``handoff_claims``    the 2026-11-24 handoff §3 table, parsed as *claims* to reconcile.
``mesh_fidelity``     variable-mesh audit CSVs (rear coarsening 1.0 -> 1.5).
``canary``            metric-BO Fold canary screen/verify rows, with the rehearsal package as a
                      replicate (solve-noise negative control).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .provenance import Registry, calc, cell, finite, iso, json_pointer, missing, parse_utc

# ------------------------------------------------------------------ dose experiment

DOSE_DIR = "docs/evidence/cd_backbone_2026-11-25"
DOSE_CFG_DIR = "examples/typologies/cd_backbone_2026-11-25"
#: results.json run key -> committed config stem for the controls (analyze.py LABELS).
CONTROL_CFG = {"rolled": "rolled_bb_control", "lame": "lame_bb_control_m040"}
#: The six predeclared rules (PREDECLARED.md), as stored by analyze.py in ``checks``.
RULES = (("H_HF_all_ge_62", "H >= 62 deg at the five 6-8 kHz bins"),
         ("H_MID_all_65_85", "H 65-85 deg at 2-4 kHz"),
         ("V_HF_not_narrower", "V at 6-8 kHz not narrower than control"),
         ("no_multilobe", "no multilobe bin"),
         ("min_re_z_ok", "min Re(z) from 900 Hz >= control - 0.1"),
         ("J_ok", "J <= control"))
KNOBS = ("g_bb_h", "g_bb_throat_frac", "g_bb_rollin_frac", "g_morph_frac")


def brief_hash(brief: Any) -> str | None:
    """sha256[:12] of the brief without ``path`` (same rule as design.generated.brief_hash)."""
    if not isinstance(brief, dict):
        return None
    body = {k: v for k, v in brief.items() if k != "path"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _knob(cfg: dict, cfg_src: str, key: str) -> dict | None:
    b = (cfg.get("bounds") or {}).get(key)
    if isinstance(b, dict) and b.get("lo") == b.get("hi") and finite(b.get("lo")) is not None:
        return cell(float(b["lo"]), cfg_src, json_pointer("bounds", key, "lo"))
    sp = cfg.get("seed_params") or {}
    for path in (("grid", "knobs", key), (key,)):
        node = sp
        for p in path:
            node = node.get(p) if isinstance(node, dict) else None
        if finite(node) is not None:
            return cell(float(node), cfg_src, json_pointer("seed_params", *path))
    return None


def _attribution(cfg: dict, cfg_src: str, terms: dict, terms_src: str, terms_ptr: str) -> dict:
    from hornlab_search.gui.data_breakdown import score_breakdown

    ver = (cfg.get("objective") or {}).get("version")
    if ver is None:
        return {"status": "missing", "reason": "config has no objective.version"}
    bd = score_breakdown(cfg, int(ver), None, terms)
    if not bd.get("available"):
        return {"status": "unknown", "reason": bd.get("reason")}
    comps, total = [], finite(terms.get("total"))
    for row in bd["rows"]:
        k = row["key"]
        if k == "unattributed":
            continue
        raw = cell(row["best_raw"], terms_src, terms_ptr + json_pointer(k)) if row["best_raw"] is not None \
            else missing(f"term {k} not stored", f"{terms_src}#{terms_ptr}")
        w = calc(row["weight"], bd["source"], [f"{cfg_src}#/objective", f"{cfg_src}#/weights"])
        comps.append({"key": k, "weight": w, "raw": raw,
                      "contribution": calc(row["best"], "weight*raw", [w, raw])})
    s = math.fsum(c["contribution"]["v"] for c in comps if c["contribution"]["v"] is not None)
    tot = cell(total, terms_src, terms_ptr + "/total")
    return {"status": "ok", "objective_version": int(ver), "resolver": bd["source"],
            "components": comps,
            "sum": calc(s, "fsum(contributions)", [c["contribution"] for c in comps]),
            "stored_total": tot,
            "residual": calc((total - s) if total is not None else None, "stored_total-sum", [tot])}


def _verdict(checks: dict | None, src: str, ptr: str, is_control: bool) -> dict:
    ptr_src = f"{src}#{ptr}"
    if is_control:
        return {"v": "control", "failed_rules": [], "rules": {}}
    if not isinstance(checks, dict):
        return {"v": "missing", "failed_rules": [], "rules": {}, "reason": "no predeclared check row"}
    rules, failed = {}, []
    for key, _label in RULES:
        val = checks.get(key)
        rules[key] = cell(val, src, ptr + json_pointer(key)) if isinstance(val, bool) \
            else missing(f"rule {key} not recorded", ptr_src)
        if val is False:
            failed.append(key)
    unknown = [k for k, _ in RULES if not isinstance(checks.get(k), bool)]
    v = "fail" if failed else ("unknown" if unknown else "pass")
    return {"v": v, "failed_rules": failed, "rules": rules,
            "calc": "all six predeclared rules true", "calc_inputs": [ptr_src]}


def _run_dir_local(root: Path, recorded: str | None) -> Path | None:
    if not recorded:
        return None
    name = re.split(r"[\\/]", recorded.rstrip("\\/"))[-1]
    p = root / "runs" / name
    return p if p.is_dir() else None


def dose_experiment(reg: Registry, cutoff: datetime) -> dict:
    root = reg.root
    pre = reg.git_text(f"{DOSE_DIR}/PREDECLARED.md") or ""
    m = re.search(r"Written (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})Z", pre)
    predeclared_at = parse_utc(m.group(1) + ":00Z") if m else None
    pre_cell = cell(iso(predeclared_at), f"{DOSE_DIR}/PREDECLARED.md", "line:3") if m \
        else missing("PREDECLARED.md has no 'Written' timestamp")

    rows, fams = [], []
    packets = [("results.json", ("rolled", "lame")), ("results_transfer.json", (None,))]
    for fname, families in packets:
        src = f"{DOSE_DIR}/{fname}"
        data = reg.git_json(src)
        if data is None:
            fams.append({"source": src, "status": "missing"})
            continue
        for fam in families:
            block = data if fam is None else data.get(fam) or {}
            fam_name = fam or "rolled2"
            fams.append({"family": fam_name, "source": src, "status": "ok"})
            runs, jobs, checks = (block.get(k) or {} for k in ("runs", "jobs", "checks"))
            base = "" if fam is None else json_pointer(fam)
            for job in list(dict.fromkeys(list(runs) + list(checks))):
                rows.append(_dose_row(reg, root, cutoff, fam_name, job, block, src, base,
                                      predeclared_at, pre_cell))
    kept = [r for r in rows if r is not None]
    pre_src = f"{DOSE_DIR}/PREDECLARED.md"
    h_floor = cell(62.0, pre_src, "line:89/rule-1") if "H ≥ 62°" in pre else missing("rule 1 text not found")
    gates = {}
    for r in kept:
        if r["is_control"] and r["min_re_z"].get("v") is not None:
            gates[r["family"]] = {
                "H_HF_floor_deg": h_floor,
                "min_re_z": calc(r["min_re_z"]["v"] - 0.1, "control min Re(z) - 0.1 (rule 5, line 93)",
                                 [r["min_re_z"], f"{pre_src}#line:93/rule-5"])}
    return {"gates": gates,"title": "CD wall-angle backbone: fixed-candidate verifies (2026-11-25)",
            "readme": f"{DOSE_DIR}/README.md", "predeclared": f"{DOSE_DIR}/PREDECLARED.md",
            "predeclared_at": pre_cell, "rules": [{"key": k, "label": l} for k, l in RULES],
            "families": fams, "rows": kept,
            "scope": "Simulated matched verifies (BEAT CUDA, 29-frequency verify grid, 36 mm / 2 deg "
                     "assumed source, freestanding quarter model). Not physical-driver measurements."}


def _dose_row(reg, root, cutoff, fam, job, block, src, base, predeclared_at, pre_cell):
    runs, jobs, checks = (block.get(k) or {} for k in ("runs", "jobs", "checks"))
    is_control = job == "control" or job.endswith("_bb_control")
    jobrec = jobs.get(job) or {}
    when = parse_utc(Path(re.split(r"[\\/]", jobrec.get("run", ""))[-1]).name) if jobrec.get("run") else None
    when_cell = cell(iso(when), src, base + json_pointer("jobs", job, "run")) if when else None
    if when is None and is_control:      # controls were solved before the predeclaration
        when, when_cell = predeclared_at, dict(pre_cell, note="upper bound: solved before predeclaration")
    rid = f"dose:{fam}:{job}"
    if when is None:
        reg.exclude(rid, "no timestamp: cannot place against the cutoff")
        return None
    if when > cutoff:
        reg.exclude(rid, "after cutoff", iso(when))
        return None

    stem = CONTROL_CFG.get(fam) if job == "control" else (None if job == "control_epw9" else job)
    cfg, cfg_src = None, None
    if stem:
        cfg_src = f"{DOSE_CFG_DIR}/{stem}.yaml"
        text = reg.git_text(cfg_src)
        cfg = yaml.safe_load(text) if text else None
    run = runs.get(job)
    rptr = base + json_pointer("runs", job)
    row: dict[str, Any] = {"id": rid, "kind": "dose_run", "family": fam, "job": job,
                           "is_control": is_control, "time": when_cell,
                           "config": cfg_src or None}
    if cfg:
        row["knobs"] = {k: v for k in KNOBS if (v := _knob(cfg, cfg_src, k)) is not None}
        epw = (cfg.get("mesh") or {}).get("epw")
        row["epw"] = cell(epw, cfg_src, "/mesh/epw") if epw is not None else missing("mesh.epw not set")
        row["brief_hash"] = calc(brief_hash(cfg.get("brief")), "sha256[:12](brief - path)", [f"{cfg_src}#/brief"])
        row["objective_version"] = cell((cfg.get("objective") or {}).get("version"), cfg_src, "/objective/version")
    else:
        row["knobs"], row["epw"] = {}, missing("no committed config for this run key")
        row["brief_hash"] = missing("no committed config")
        row["objective_version"] = missing("no committed config")
    if isinstance(run, dict):
        row["J"] = cell(run.get("J"), src, rptr + "/J")
        freqs = run.get("freqs") or []
        if 8000.0 in freqs and isinstance(run.get("H"), list):
            i = freqs.index(8000.0)
            row["H8k"] = cell(run["H"][i], src, rptr + f"/H/{i}")
            row["V8k"] = cell(run["V"][i], src, rptr + f"/V/{i}") if isinstance(run.get("V"), list) else missing("V not stored")
        else:
            row["H8k"] = row["V8k"] = missing("8000 Hz not in the stored grid", f"{src}#{rptr}/freqs")
        row["min_re_z"] = cell(run.get("min_re_z_from_900"), src, rptr + "/min_re_z_from_900")
        row["n_dof"] = cell(run.get("n_dof"), src, rptr + "/n_dof") if run.get("n_dof") is not None \
            else missing("n_dof not stored")
        row["attribution"] = _attribution(cfg, cfg_src, run.get("terms") or {}, src, rptr + "/terms") \
            if cfg else {"status": "missing", "reason": "no committed config: weights unknown"}
    else:
        ck = checks.get(job) or {}
        row["J"] = dict(cell(ck.get("J"), src, base + json_pointer("checks", job, "J")),
                        note="rounded value from the check row; full run row not stored") \
            if ck.get("J") is not None else missing("no run row", f"{src}#{rptr}")
        row["H8k"] = row["V8k"] = missing("no run row in results file", f"{src}#{rptr}")
        row["min_re_z"] = cell(ck.get("min_re_z"), src, base + json_pointer("checks", job, "min_re_z")) \
            if ck.get("min_re_z") is not None else missing("no run row")
        row["n_dof"] = missing("no run row")
        row["attribution"] = {"status": "missing", "reason": "stored terms absent (check row only)"}
    row["verdict"] = _verdict(checks.get(job), src, base + json_pointer("checks", job), is_control)
    # cost: persisted job log fields only (no inference)
    if jobrec:
        jp = base + json_pointer("jobs", job)
        pk = re.search(r"peak (\d+) MiB", jobrec.get("note") or "")
        row["cost"] = {"wall_s": cell(jobrec.get("seconds"), src, jp + "/seconds"),
                       "vram_baseline_mb": cell(jobrec.get("vram_baseline_mb"), src, jp + "/vram_baseline_mb"),
                       "peak_vram_mib": cell(int(pk.group(1)), src, jp + "/note") if pk
                       else missing("peak not in job note"),
                       "lane": "gpu (beat_cuda)"}
    else:
        row["cost"] = {"status": "missing", "reason": "no job record (control solved earlier)"}
    # corroboration against the local run dir (optional; absent in CI)
    local = _run_dir_local(root, jobrec.get("run"))
    if local is None:
        row["corroboration"] = {"status": "run_dir_missing"}
    else:
        best = reg.disk_json(local / "best.json")
        j_local = finite((best or {}).get("objective"))
        j_res = finite(row["J"].get("v"))
        if j_local is None or j_res is None:
            row["corroboration"] = {"status": "unknown"}
        else:
            d = j_local - j_res
            row["corroboration"] = {"status": "match" if abs(d) <= 1e-9 else "mismatch",
                                    "best_json_J": cell(j_local, reg.rel(local / "best.json"), "/objective"),
                                    "delta": calc(d, "best.json - results.json", [])}
    return row


# ------------------------------------------------------------------ cohort inventory

PLANNING = "runs/v11_bo_day_planning"
PENALTY_J = 900.0


def _cfg_name(meta: dict) -> str:
    n = meta.get("config_name")
    return n if isinstance(n, str) and n else str(meta.get("config_path") or "?")


def cohort_inventory(reg: Registry, cutoff: datetime, objective_version: int = 11) -> dict:
    root = reg.root
    groups: dict[tuple, dict] = {}
    scan = {"run_dirs": 0, "no_run_json": 0, "unreadable_run_json": 0, "other_version": 0,
            "runs_after_cutoff": 0, "rows_after_cutoff": 0, "rows_time_unknown": 0}
    runs_root = root / "runs"
    run_dirs = sorted(d for d in runs_root.iterdir() if d.is_dir() and d.name[:8].isdigit()) \
        if runs_root.is_dir() else []
    run_to_key: dict[str, tuple] = {}
    for d in run_dirs:
        scan["run_dirs"] += 1
        rj = d / "run.json"
        if not rj.is_file():
            scan["no_run_json"] += 1
            continue
        try:
            meta = json.loads(rj.read_bytes().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            scan["unreadable_run_json"] += 1
            continue
        if int(meta.get("objective_version") or 0) != objective_version:
            scan["other_version"] += 1
            continue
        started = parse_utc(meta.get("started_utc")) or parse_utc(d.name)
        if started is None or started > cutoff:
            scan["runs_after_cutoff"] += 1
            reg.exclude(f"run:{d.name}", "after cutoff" if started else "no start time", iso(started))
            continue
        reg.disk_bytes(rj)
        cfg = meta.get("config") or {}
        key = (_cfg_name(meta), objective_version, brief_hash(cfg.get("brief")) or "unknown",
               str(meta.get("mode") or "?"), str(meta.get("backend") or "?"))
        g = groups.setdefault(key, {"runs": [], "rows": 0, "valid": 0, "penalty": 0, "cached": 0,
                                    "failed": {}, "unique": set(), "dup_valid": 0, "best": None,
                                    "config_shas": set(), "first": None, "last": None})
        g["runs"].append(d.name)
        run_to_key[d.name] = key
        g["config_shas"].add(meta.get("config_sha"))
        nd = d / "search.ndjson"

        def keep(row, _started=started):
            t = parse_utc(row.get("created_utc"))
            if t is None:
                scan["rows_time_unknown"] += 1
                return _started <= cutoff
            return t <= cutoff
        rows = reg.disk_ndjson(nd, keep)
        scan["rows_after_cutoff"] += reg.sources.get(reg.rel(nd), {}).get("lines_after_cutoff", 0)
        for line, row in rows:
            g["rows"] += 1
            t = parse_utc(row.get("created_utc"))
            if t is not None:
                g["first"] = t if g["first"] is None or t < g["first"] else g["first"]
                g["last"] = t if g["last"] is None or t > g["last"] else g["last"]
            if row.get("cached") is True:
                g["cached"] += 1
            j = finite(row.get("objective"))
            if row.get("ok") is True and j is not None and j < PENALTY_J:
                g["valid"] += 1
                h = row.get("design_hash")
                if h in g["unique"]:
                    g["dup_valid"] += 1
                elif h:
                    g["unique"].add(h)
                if g["best"] is None or j < g["best"][0]:
                    g["best"] = (j, reg.rel(nd), line, h)
            elif row.get("ok") is True:
                g["penalty"] += 1
            else:
                kind = str(row.get("kind") or "unknown")
                g["failed"][kind] = g["failed"].get(kind, 0) + 1

    by_name: dict[str, list] = {}
    for key in groups:
        by_name.setdefault(key[0], []).append(key)
    admissions = _admissions(reg, cutoff, run_to_key)
    cohorts = []
    for key, g in groups.items():
        name, ver, bh, mode, backend = key
        cid = f"cohort:{name}|v{ver}|{bh}|{mode}|{backend}"
        best = g["best"]
        adm = admissions.get((name, bh)) or admissions.get((name, None))
        ins = [f"runs/{r}/search.ndjson" for r in sorted(g["runs"])]
        cohorts.append({
            "id": cid, "config_name": name, "objective_version": ver, "brief_hash": bh,
            "mode": mode, "backend": backend,
            "mixed_identity": len(by_name[name]) > 1,
            "n_runs": calc(len(g["runs"]), "count(run dirs)", [f"runs/{r}/run.json" for r in g["runs"]]),
            "runs": sorted(g["runs"]),
            "inputs": ins,
            "config_shas": sorted(s for s in g["config_shas"] if s),
            "rows": calc(g["rows"], "count(rows <= cutoff)", ins),
            "valid": calc(g["valid"], f"count(ok and J < {PENALTY_J})", ins),
            "unique_designs": calc(len(g["unique"]), "count(distinct design_hash | valid)", ins),
            "duplicate_valid": calc(g["dup_valid"], "valid - unique", ins),
            "penalty": calc(g["penalty"], f"count(ok and J >= {PENALTY_J})", ins),
            "cached": calc(g["cached"], "count(cached)", ins),
            "failed": {k: calc(v, "count(ok false by kind)", ins) for k, v in sorted(g["failed"].items())},
            "failed_total": calc(sum(g["failed"].values()), "sum(failed)", ins),
            "best_J": cell(best[0], best[1], f"line:{best[2]}/objective") if best else missing("no valid row"),
            "best_design": best[3] if best else None,
            "first_row": iso(g["first"]), "last_row": iso(g["last"]),
            "admission": adm or {"status": "missing", "reason": "no admission artifact for this cohort"},
            "status": _cohort_status(adm),
        })
    cohorts.sort(key=lambda c: (-(c["unique_designs"]["v"]), c["config_name"], c["brief_hash"]))
    return {"objective_version": objective_version, "grouping": ["config_name", "objective_version",
            "brief_hash", "mode", "backend"], "scan": scan, "cohorts": cohorts,
            "admission_sources": sorted({a["source"] for a in admissions.values() if a.get("source")})}


def _cohort_status(adm: dict | None) -> str:
    if not adm:
        return "not_evaluated"
    if adm.get("kind") == "acquisition_confirmation":
        return "confirmation_" + str(adm.get("verdict", {}).get("v", "unknown")).lower()
    rep = adm.get("replay") or {}
    if (rep.get("exact_complete") or {}).get("v") is not None and (rep.get("available") or {}).get("v"):
        frac = rep["exact_complete"]["v"] / rep["available"]["v"]
        if frac < 0.95:
            return "replay_mismatch"
    hv = (adm.get("holdout") or {}).get("verdict", {}).get("v")
    if hv is None:
        return "needs_admission"
    if str(hv).startswith("PASS"):
        return "holdout_pass"
    if str(hv) == "HOLD":
        return "hold"
    return "unknown"


def _admissions(reg: Registry, cutoff: datetime, run_to_key: dict) -> dict:
    out: dict = {}
    base = reg.root / PLANNING
    if not base.is_dir():
        return out
    for d in sorted(base.glob("cohort_*")):
        off_p, hold_p, cat_p = d / "offline_scores.json", d / "holdout_comparison.json", d / "catalog.csv"
        newest = max((p.stat().st_mtime for p in (off_p, hold_p, cat_p) if p.is_file()), default=None)
        if newest is not None and datetime.fromtimestamp(newest).astimezone() > cutoff:
            reg.exclude(reg.rel(d), "admission artifact written after cutoff (mtime)")
            continue
        off = reg.disk_json(off_p) if off_p.is_file() else None
        if not isinstance(off, dict):
            continue
        name = (off.get("cohort") or {}).get("native_config")
        osrc = reg.rel(off_p)
        sel = off.get("selection") or {}
        rec = {"source": osrc, "kind": "cohort_admission", "dir": reg.rel(d),
               "replay": {"exact_complete": cell((off.get("counts") or {}).get("exact_complete", 0), osrc,
                                                 "/counts/exact_complete"),
                          "available": cell(sel.get("available"), osrc, "/selection/available"),
                          "counts": off.get("counts")},
               "no_backend_calls": off.get("no_backend_calls")}
        bh = None
        if cat_p.is_file():
            raw = reg.disk_bytes(cat_p) or b""
            first = next(csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace"))), None)
            bh = (first or {}).get("brief_hash") or None
            rec["brief_hash"] = cell(bh, reg.rel(cat_p), "row:1/brief_hash") if bh else missing("catalog has no brief_hash")
        if hold_p.is_file():
            h = reg.disk_json(hold_p) or {}
            hsrc = reg.rel(hold_p)
            dec = h.get("decision") or {}
            rec["holdout"] = {"verdict": cell(dec.get("verdict"), hsrc, "/decision/verdict"),
                              "checks": {k: cell(v, hsrc, json_pointer("decision", "checks", k))
                                         for k, v in (dec.get("checks") or {}).items()},
                              "split": h.get("split"),
                              "identity_brief_hash": cell((h.get("identity") or {}).get("brief_hash"), hsrc,
                                                          "/identity/brief_hash")}
            hb = (h.get("identity") or {}).get("brief_hash")
            if bh and hb and hb != bh:
                rec["identity_conflict"] = f"catalog brief {bh} != holdout brief {hb}"
            bh = bh or hb
        else:
            rec["holdout"] = {"verdict": missing("no holdout_comparison.json", reg.rel(d))}
        out[(name, bh)] = rec
    # Fold: the acquisition confirmation is linked through its evaluation run id (persisted).
    conf_p = base / "acquisition_confirmation_2026-11-23" / "confirmation.json"
    if conf_p.is_file():
        c = reg.disk_json(conf_p) or {}
        csrc = reg.rel(conf_p)
        key = run_to_key.get(c.get("eval_run_id") or "")
        if key:
            out[(key[0], key[2])] = {
                "source": csrc, "kind": "acquisition_confirmation",
                "linked_by": cell(c.get("eval_run_id"), csrc, "/eval_run_id"),
                "verdict": cell((c.get("decision") or {}).get("verdict"), csrc, "/decision/verdict"),
                "checks": {k: cell(v, csrc, json_pointer("decision", "checks", k))
                           for k, v in ((c.get("decision") or {}).get("checks") or {}).items()},
                "note": "one confirmation seed; the 2-of-3 release rule lives in the handoff (claim)"}
    return out


# ------------------------------------------------------------------ inherited claims

HANDOFF = "docs/research/metric_bo_2026-11-22/12_HANDOFF_2026-11-24.md"
_ROW = re.compile(r"^\|\s*`([^`]+)`[^|]*\|\s*\**(\d+)\**\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*(.*?)\s*\|\s*$")


def _claimed_status(text: str) -> str:
    t = text.lower()
    if "1/180 replay" in t or "projection mismatch" in t:
        return "replay_mismatch"
    if "holdout **hold" in t or "holdout **hold**" in t or "**hold**" in t:
        return "hold"
    if "pass" in t and "holdout" in t:
        return "holdout_pass"
    if "needs strict artifact" in t:
        return "needs_admission"
    if "live loop" in t:
        return "live_loop"
    if "solves" in t:
        return "needs_more_solves"
    return "unknown"


def handoff_claims(reg: Registry) -> dict:
    text = reg.git_text(HANDOFF)
    if text is None:
        return {"source": HANDOFF, "status": "missing", "claims": []}
    claims, in_sec = [], False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## 3."):
            in_sec = True
            continue
        if in_sec and line.startswith("## "):
            break
        m = _ROW.match(line) if in_sec else None
        if m:
            claims.append({"config_name": m.group(1), "line": i,
                           "unique": cell(int(m.group(2)), HANDOFF, f"line:{i}/unique"),
                           "runs": cell(int(m.group(3)), HANDOFF, f"line:{i}/runs"),
                           "best_J": cell(float(m.group(4)), HANDOFF, f"line:{i}/best_J"),
                           "status_text": m.group(5),
                           "claimed_status": _claimed_status(m.group(5))})
    return {"source": HANDOFF, "status": "ok", "grade": "inherited claim (not re-measured)",
            "snapshot_label": "2026-11-24", "claims": claims}


def reconcile_claims(claims: dict, inventory: dict) -> list[dict]:
    by_name: dict[str, list] = {}
    for c in inventory["cohorts"]:
        by_name.setdefault(c["config_name"], []).append(c)
    out = []
    for cl in claims.get("claims", []):
        cs = by_name.get(cl["config_name"], [])
        screen = [c for c in cs if c["mode"] == "screen"] or cs
        if not screen:
            out.append({"config_name": cl["config_name"], "claim_line": cl["line"],
                        "result": "missing", "detail": "no v11 cohort at the cutoff"})
            continue
        top = max(screen, key=lambda c: c["unique_designs"]["v"])
        artifact_status = top["status"]
        claimed = cl["claimed_status"]
        comparable = claimed in ("holdout_pass", "hold", "replay_mismatch", "needs_admission")
        status_ok = (claimed == artifact_status) if comparable else None
        out.append({"config_name": cl["config_name"], "claim_line": cl["line"], "cohort": top["id"],
                    "claimed_unique": cl["unique"], "unique_at_cutoff": top["unique_designs"],
                    "unique_delta": calc(top["unique_designs"]["v"] - cl["unique"]["v"],
                                         "unique_at_cutoff - claimed", [cl["unique"]]),
                    "n_identities": len(screen),
                    "claimed_status": claimed, "artifact_status": artifact_status,
                    "status_agrees": status_ok,
                    "result": ("status_conflict" if status_ok is False else
                               "agrees" if status_ok else "not_comparable")})
    return out


# ------------------------------------------------------------------ numerical fidelity

MESH_DIR = "docs/evidence/variable_mesh_2026-11-23"


def mesh_fidelity(reg: Registry) -> dict:
    pol_src, ac_src = f"{MESH_DIR}/MESH_POLICY_AB.csv", f"{MESH_DIR}/ACOUSTIC_CONVERGENCE.csv"
    pol = reg.git_text(pol_src)
    ac = reg.git_text(ac_src)
    reg.git_bytes(f"{MESH_DIR}/ADOPTION_DECISION.md")
    if pol is None:
        return {"status": "missing", "rows": []}
    prow = list(csv.DictReader(io.StringIO(pol)))
    arow = list(csv.DictReader(io.StringIO(ac or "")))
    rows = []
    for case in dict.fromkeys(r["acoustic_case"] for r in arow):
        a = {r["arm"]: (i, r) for i, r in enumerate(arow, start=1) if r["acoustic_case"] == case}
        if "rear1_epw1" not in a or "rear1.5_epw1" not in a:
            continue
        (ib, rb), (ia, ra) = a["rear1_epw1"], a["rear1.5_epw1"]
        before = cell(int(rb["n_dof_solved"]), ac_src, f"row:{ib}/n_dof_solved")
        after = cell(int(ra["n_dof_solved"]), ac_src, f"row:{ia}/n_dof_solved")
        dev = {k: cell(float(ra[k]), ac_src, f"row:{ia}/{k}") for k in
               ("bw_h_max_abs_deg", "bw_v_max_abs_deg", "on_axis_max_abs_db", "di_max_abs_db",
                "z_real_max_abs")}
        rows.append({"id": f"mesh:{case}", "class": ra["geometry_class"], "label": ra["geometry_label"],
                     "f_hi_hz": cell(float(ra["f_hi_hz"]), ac_src, f"row:{ia}/f_hi_hz"),
                     "scope": f"acoustic A/B vs finer reference {ra['reference']} ({ra['solver']})",
                     "evidence": "acoustic", "dof_before": before, "dof_after": after,
                     "dof_reduction_pct": calc(100.0 * (1 - after["v"] / before["v"]), "100*(1-after/before)",
                                               [before, after]),
                     "max_bw_delta_deg": calc(max(dev["bw_h_max_abs_deg"]["v"], dev["bw_v_max_abs_deg"]["v"]),
                                              "max(bw_h, bw_v)", [dev["bw_h_max_abs_deg"], dev["bw_v_max_abs_deg"]]),
                     "deviations": dev, "lane": "cpu (beat_cpu)"})
    solved = {r["class"] for r in rows}
    for cls in dict.fromkeys(r["geometry_class"] for r in prow):
        if cls in solved:
            continue
        p = {r["arm"]: (i, r) for i, r in enumerate(prow, start=1) if r["geometry_class"] == cls}
        if "rear1_epw1" not in p or "rear1.5_epw1" not in p:
            continue
        (ib, rb), (ia, ra) = p["rear1_epw1"], p["rear1.5_epw1"]
        before = cell(int(rb["n_vertices"]), pol_src, f"row:{ib}/n_vertices")
        after = cell(int(ra["n_vertices"]), pol_src, f"row:{ia}/n_vertices")
        inert = before["v"] == after["v"]
        rows.append({"id": f"mesh:{cls}", "class": cls, "label": ra["geometry_label"],
                     "f_hi_hz": cell(float(ra["f_max_hz"]), pol_src, f"row:{ia}/f_max_hz"),
                     "scope": "mesh only (vertices); not solved",
                     "evidence": "unsupported" if inert else "mesh_only",
                     "dof_before": before, "dof_after": after,
                     "dof_reduction_pct": calc(100.0 * (1 - after["v"] / before["v"]), "100*(1-after/before)",
                                               [before, after]),
                     "max_bw_delta_deg": missing("not solved: no acoustic comparison"),
                     "deviations": {}, "lane": "none (mesh build only)"})
    return {"status": "ok", "factor": "rear_res_factor 1.0 -> 1.5 at epw x1",
            "decision": f"{MESH_DIR}/ADOPTION_DECISION.md", "rows": rows,
            "unmeasured": ["GPU wall time and VRAM at factor 1.5 (not measured: the 12 kHz queue owned the GPU)"]}


# ------------------------------------------------------------------ canary

CANARY = "runs/metric_bo_canary_2026-11-23"
CANARY_PACKAGES = {"v4": "work_v4/runs/study-3bf53815e1ab78bb", "rehearsal": "work/runs/study-3e16eab7f8d70457"}


def canary(reg: Registry, cutoff: datetime) -> dict:
    base = reg.root / CANARY
    if not base.is_dir():
        return {"status": "missing", "reason": f"{CANARY} not on this machine"}
    pk = {}
    for label, rel in CANARY_PACKAGES.items():
        for mode in ("screen", "verify"):
            d = base / rel / mode
            meta = reg.disk_json(d / "run.json") or {}
            rows = reg.disk_ndjson(d / "search.ndjson",
                                   lambda r: (parse_utc(r.get("created_utc")) or cutoff) <= cutoff)
            src = reg.rel(d / "search.ndjson")
            pk[(label, mode)] = {
                "brief_hash": brief_hash((meta.get("config") or {}).get("brief")),
                "rows": [{"design": r.get("design_hash"), "ok": r.get("ok"),
                          "J": cell(r.get("objective"), src, f"line:{ln}/objective")} for ln, r in rows]}
    v4s, v4v = pk[("v4", "screen")], pk[("v4", "verify")]
    screen_j = {r["design"]: r["J"] for r in v4s["rows"] if r["ok"]}
    ver = []
    for r in v4v["rows"]:
        if r["design"] in screen_j:
            ver.append({"design": r["design"], "screen_J": screen_j[r["design"]], "verify_J": r["J"]})
    rank_s = sorted(ver, key=lambda x: x["screen_J"]["v"])
    rank_v = sorted(ver, key=lambda x: x["verify_J"]["v"])
    same_rank = [x["design"] for x in rank_s] == [x["design"] for x in rank_v]
    # replicate: same design solved in both packages (independent processes)
    reps = []
    for mode in ("screen", "verify"):
        a = {r["design"]: r["J"] for r in pk[("v4", mode)]["rows"] if r["ok"]}
        b = {r["design"]: r["J"] for r in pk[("rehearsal", mode)]["rows"] if r["ok"]}
        for h in sorted(set(a) & set(b)):
            reps.append({"mode": mode, "design": h, "v4": a[h], "rehearsal": b[h],
                         "abs_delta": calc(abs(a[h]["v"] - b[h]["v"]), "|v4 - rehearsal|", [a[h], b[h]])})
    return {"status": "ok", "study_v4": CANARY_PACKAGES["v4"],
            "identities": {"screen_brief": v4s["brief_hash"], "verify_brief": v4v["brief_hash"],
                           "note": "screen and verify are separate score identities (grid/fidelity); "
                                   "J is shown side by side, never differenced or pooled"},
            "screen_rows": v4s["rows"], "verify_pairs": ver,
            "rank_preserved": calc(same_rank, "order(screen J) == order(verify J)",
                                   [x["screen_J"] for x in ver] + [x["verify_J"] for x in ver]),
            "n_pairs": len(ver), "replicates": reps,
            "replicate_max_abs_delta": calc(max((r["abs_delta"]["v"] for r in reps), default=None),
                                            "max |v4 - rehearsal|", [r["abs_delta"] for r in reps])}
