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


def _line_of(text: str, needle: str) -> int | None:
    """1-based line of the first line containing ``needle`` (pointers are searched, never hard-coded)."""
    for i, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return i
    return None


#: analyze.py's bin sets (PREDECLARED.md "Bin set" table), used only to re-evaluate the three
#: control-relative rules against a fidelity-matched control.
HF_BINS = (6085, 6325, 6977, 7113, 8000)


def _matched_fidelity_rules(cand: dict, ctl: dict, src: str, cptr: str, kptr: str) -> dict:
    """V-not-narrower, loading and J rules re-evaluated against a control at the same mesh fidelity
    (analyze.check's formulas, PREDECLARED rules 3, 5, 6)."""
    idx = {round(x): i for i, x in enumerate(cand.get("freqs") or [])}
    try:
        dv = min(cand["V"][idx[b]] - ctl["V"][idx[b]] for b in HF_BINS)
    except (KeyError, IndexError, TypeError):
        dv = None
    ins = [f"{src}#{cptr}", f"{src}#{kptr}"]
    return {
        "V_HF_not_narrower": calc(None if dv is None else bool(dv >= 0.0), "min_HF(V_cand - V_ctl) >= 0", ins),
        "min_re_z_ok": calc(bool(cand["min_re_z_from_900"] >= ctl["min_re_z_from_900"] - 0.1),
                            "minRe(z)_cand >= minRe(z)_ctl - 0.1", ins),
        "J_ok": calc(bool(cand["J"] <= ctl["J"]), "J_cand <= J_ctl", ins),
    }


def dose_experiment(reg: Registry, cutoff: datetime) -> dict:
    root = reg.root
    pre_src = f"{DOSE_DIR}/PREDECLARED.md"
    pre = reg.git_text(pre_src) or ""
    m = re.search(r"Written (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})Z", pre)
    predeclared_at = parse_utc(m.group(1) + ":00Z") if m else None
    pre_cell = cell(iso(predeclared_at), pre_src, f"line:{_line_of(pre, 'Written ')}/text:Written") if m \
        else missing("PREDECLARED.md has no 'Written' timestamp")
    ln_epw9 = _line_of(pre, "epw-9 controls")
    ctx = {"predeclared_at": predeclared_at, "pre_cell": pre_cell,
           "epw9_control_cell": cell(9.0, pre_src, f"line:{ln_epw9}/text:epw-9 controls") if ln_epw9
           else missing("epw-9 control not named in PREDECLARED.md")}

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
            runs, checks = (block.get(k) or {} for k in ("runs", "checks"))
            base = "" if fam is None else json_pointer(fam)
            gate = ((data.get("mesh_gate") or {}).get(fam) or {}) if fam else {}
            for job in list(dict.fromkeys(list(runs) + list(checks))):
                rows.append(_dose_row(reg, root, cutoff, fam_name, job, block, src, base, ctx, gate))
    kept = [r for r in rows if r is not None]
    ln1, ln5 = _line_of(pre, "H ≥ 62° at all five"), _line_of(pre, "**Loading:**")
    h_floor = cell(62.0, pre_src, f"line:{ln1}/text:H ≥ 62° at all five") if ln1 else missing("rule 1 text not found")
    gates = {}
    for r in kept:
        if r["job"] in ("control", f"{r['family']}_bb_control") and r["min_re_z"].get("v") is not None:
            gates[r["family"]] = {
                "H_HF_floor_deg": h_floor,
                "min_re_z": calc(r["min_re_z"]["v"] - 0.1, "control min Re(z) - 0.1 (rule 5)",
                                 [r["min_re_z"], f"{pre_src}#line:{ln5}/text:**Loading:**"])}
    return {"gates": gates, "title": "CD wall-angle backbone: fixed-candidate verifies (2026-11-25)",
            "readme": f"{DOSE_DIR}/README.md", "predeclared": pre_src,
            "predeclared_at": pre_cell, "rules": [{"key": k, "label": l} for k, l in RULES],
            "families": fams, "rows": kept,
            "scope": "Simulated matched verifies (BEAT CUDA, 29-frequency verify grid, 36 mm / 2 deg "
                     "assumed source, freestanding quarter model). Not physical-driver measurements. "
                     "Pass rules are predeclared for this CD backbone experiment only."}


def _dose_row(reg, root, cutoff, fam, job, block, src, base, ctx, gate):
    runs, jobs, checks = (block.get(k) or {} for k in ("runs", "jobs", "checks"))
    is_control = job in ("control", "control_epw9") or job.endswith("_bb_control")
    jobrec = jobs.get(job) or {}
    when = parse_utc(re.split(r"[\\/]", jobrec.get("run", ""))[-1]) if jobrec.get("run") else None
    when_cell = calc(iso(when), "UTC from the run-dir name prefix YYYYMMDDTHHMMSSZ",
                     [f"{src}#{base}{json_pointer('jobs', job, 'run')}"]) if when else None
    if when is None and is_control:      # controls were solved before the predeclaration
        when, when_cell = ctx["predeclared_at"], dict(ctx["pre_cell"], note="upper bound: solved before predeclaration")
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
        row["knobs"] = {}
        row["epw"] = ctx["epw9_control_cell"] if job == "control_epw9" else missing("no committed config for this run key")
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
            if cfg else {"status": "missing", "reason": "no committed config: weights unknown (not inferred from a sibling)"}
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
    if job.endswith("_epw9") and not is_control:
        row["verdict"] = _refined_mesh_verdict(row["verdict"], job, runs, gate, src, base)
    # cost: persisted job log fields only (no inference)
    if jobrec:
        jp = base + json_pointer("jobs", job)
        pk = re.search(r"peak (\d+) MiB", jobrec.get("note") or "")
        row["cost"] = {"wall_s": cell(jobrec.get("seconds"), src, jp + "/seconds"),
                       "vram_baseline_mb": cell(jobrec.get("vram_baseline_mb"), src, jp + "/vram_baseline_mb"),
                       "peak_vram_mib": calc(int(pk.group(1)), "regex 'peak <N> MiB' in the job note",
                                             [f"{src}#{jp}/note"]) if pk
                       else missing("peak not in job note"),
                       "lane": "gpu (beat_cuda)"}
    else:
        row["cost"] = {"status": "missing", "reason": "no job record in the evidence packet (control solved earlier)"}
    row["corroboration"] = _corroborate(reg, root, jobrec, row, cfg)
    return row


def _refined_mesh_verdict(v6: dict, job: str, runs: dict, gate: dict, src: str, base: str) -> dict:
    """PREDECLARED refined-mesh gate = delta rule (analyze.mesh_gate) AND the six rules at epw 9.
    analyze.check scored epw-9 rows against the epw-6 control; the three control-relative rules are
    re-evaluated here against the epw-9 control so no verdict mixes mesh fidelities."""
    stem = job[: -len("_epw9")]
    g = gate.get(stem) or {}
    gptr = json_pointer("mesh_gate", base.strip("/"), stem, "passes_predeclared_mesh_rule")
    delta_ok = g.get("passes_predeclared_mesh_rule")
    ctl9, cand = runs.get("control_epw9"), runs.get(job)
    rules = dict(v6.get("rules") or {})
    out = {"basis": "refined-mesh gate: delta rule AND six rules vs the epw-9 control",
           "epw6_control_checks": {"rules": rules, "v": v6.get("v"),
                                   "note": "analyze.py compared this epw-9 row with the epw-6 control "
                                           "(cross-fidelity); informational only"}}
    if not isinstance(delta_ok, bool) or not isinstance(ctl9, dict) or not isinstance(cand, dict):
        out.update(v="unknown", failed_rules=[], rules=rules,
                   reason="mesh_gate row or epw-9 control missing")
        return out
    matched = _matched_fidelity_rules(cand, ctl9, src, base + json_pointer("runs", job),
                                      base + json_pointer("runs", "control_epw9"))
    rules.update(matched)
    rules["mesh_delta_rule"] = cell(delta_ok, src, gptr)
    failed = [k for k, c in rules.items() if c.get("v") is False]
    unknown = [k for k, c in rules.items() if c.get("v") is None]
    out.update(v="fail" if failed else "unknown" if unknown else "pass", failed_rules=failed, rules=rules,
               calc="all six rules (epw-9 control) and the mesh delta rule true")
    return out


def _corroborate(reg, root, jobrec: dict, row: dict, cfg: dict | None) -> dict:
    """Optional check against the local run dir: best.json J equals the packet J, and the committed
    config equals the config the run recorded (absent in CI, where runs/ is not committed)."""
    local = _run_dir_local(root, jobrec.get("run"))
    if local is None:
        return {"status": "run_dir_missing"}
    best = reg.disk_json(local / "best.json")
    meta = reg.disk_json(local / "run.json") or {}
    j_local, j_res = finite((best or {}).get("objective")), finite(row["J"].get("v"))
    if j_local is None or j_res is None:
        return {"status": "unknown"}
    d = j_local - j_res
    rcfg = meta.get("config")
    cfg_equal = (rcfg == cfg) if isinstance(rcfg, dict) and cfg is not None else None
    ok = abs(d) <= 1e-9 and cfg_equal is not False
    return {"status": "match" if ok else "mismatch",
            "best_json_J": cell(j_local, reg.rel(local / "best.json"), "/objective"),
            "delta": calc(d, "best.json J - packet J", [reg.rel(local / "best.json") + "#/objective",
                                                         row["J"].get("src") or ""]),
            "config_equal": calc(cfg_equal, "run.json config == committed config",
                                 [reg.rel(local / "run.json") + "#/config", row.get("config") or ""])}


# ------------------------------------------------------------------ cohort inventory

PLANNING = "runs/v11_bo_day_planning"
PENALTY_J = 900.0
#: Below this exact-replay fraction a cohort cannot form the strict admission artifact (snapshot policy).
REPLAY_MIN = 0.95


def fidelity_policy(cfg: dict) -> str:
    """sha256[:8] of the run's mesh + solve blocks: cohorts never pool across mesh/solve settings."""
    body = {"mesh": cfg.get("mesh"), "solve": cfg.get("solve")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:8]


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
               str(meta.get("mode") or "?"), str(meta.get("backend") or "?"), fidelity_policy(cfg))
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
    used: set = set()
    cohorts = []
    for key, g in groups.items():
        name, ver, bh, mode, backend, fid = key
        cid = f"cohort:{name}|v{ver}|{bh}|{mode}|{backend}|{fid}"
        best = g["best"]
        adm = admissions.get((name, bh, mode))
        if adm:
            used.add((name, bh, mode))
        ins = [f"runs/{r}/search.ndjson" for r in sorted(g["runs"])]
        cohorts.append({
            "id": cid, "config_name": name, "objective_version": ver, "brief_hash": bh,
            "mode": mode, "backend": backend,
            "mixed_identity": len(by_name[name]) > 1,
            "n_runs": calc(len(g["runs"]), "count(run dirs)", [f"runs/{r}/run.json" for r in g["runs"]]),
            "runs": sorted(g["runs"]),
            "inputs": ins,
            "fidelity_policy": fid,
            "config_shas": sorted(s for s in g["config_shas"] if s),
            "treatment_variants": calc(len({s for s in g["config_shas"] if s}),
                                       "count(distinct run.json config_sha)", [f"runs/{r}/run.json" for r in g["runs"]]),
            "rows": calc(g["rows"], "count(rows <= cutoff)", ins),
            "valid": calc(g["valid"], f"count(ok and J < {PENALTY_J}; cached replays included)", ins),
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
    orphans = [{"key": list(k), "source": a.get("source"), "reason": "no cohort with this config, brief and mode"}
               for k, a in sorted(admissions.items(), key=lambda kv: str(kv[0])) if k not in used]
    return {"objective_version": objective_version,
            "grouping": ["config_name", "objective_version", "brief_hash", "mode", "backend", "fidelity_policy"],
            "scan": scan, "cohorts": cohorts, "orphan_admissions": orphans,
            "policy": {"penalty_J": PENALTY_J, "replay_min_fraction": REPLAY_MIN,
                       "note": "snapshot policy values, not project rules: J >= penalty_J is a refusal penalty; "
                               "a cohort below replay_min_fraction exact replay is reported as replay_mismatch"},
            "admission_sources": sorted({a["source"] for a in admissions.values() if a.get("source")})}


def _cohort_status(adm: dict | None) -> str:
    if not adm:
        return "not_evaluated"
    if adm.get("kind") == "acquisition_confirmation":
        return "confirmation_" + str(adm.get("verdict", {}).get("v", "unknown")).lower()
    rep = adm.get("replay") or {}
    if (rep.get("exact_complete") or {}).get("v") is not None and (rep.get("available") or {}).get("v"):
        frac = rep["exact_complete"]["v"] / rep["available"]["v"]
        if frac < REPLAY_MIN:
            return "replay_mismatch"
    hv = (adm.get("holdout") or {}).get("verdict", {}).get("v")
    if hv is None:
        return "needs_admission"
    if str(hv) == "PASS_FOR_EXPLORATORY_PILOT":
        return "pilot_eligible"
    if str(hv).startswith("PASS"):
        return "unknown"                  # an unrecognised PASS_* verdict is never silently promoted
    if str(hv) == "HOLD":
        return "hold"
    return "unknown"


def _admissions(reg: Registry, cutoff: datetime, run_to_key: dict) -> dict:
    out: dict = {}
    base = reg.root / PLANNING
    if not base.is_dir():
        return out
    for d in sorted(p for p in base.glob("cohort_*") if p.is_dir()):
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
        bh, cat_fid = None, None
        if cat_p.is_file():
            raw = reg.disk_bytes(cat_p) or b""
            first = next(csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace"))), None)
            bh = (first or {}).get("brief_hash") or None
            cat_fid = (first or {}).get("fidelity") or None
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
            fid_mode = str((h.get("identity") or {}).get("fidelity") or "screen")
        else:
            rec["holdout"] = {"verdict": missing("no holdout_comparison.json", reg.rel(d))}
            fid_mode = cat_fid or "screen"     # the catalog's fidelity column; screen when absent
        rec["fidelity"] = fid_mode
        out[(name, bh, fid_mode)] = rec
    # Fold: the acquisition confirmation is linked through its evaluation run id (persisted).
    conf_p = base / "acquisition_confirmation_2026-11-23" / "confirmation.json"
    if conf_p.is_file():
        c = reg.disk_json(conf_p) or {}
        csrc = reg.rel(conf_p)
        key = run_to_key.get(c.get("eval_run_id") or "")
        if key:
            out[(key[0], key[2], key[3])] = {
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
        return "pilot_eligible"
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
    mf = re.search(r"exceed the (\d+) floor", text)
    ln = next((i for i, ln_ in enumerate(text.splitlines(), start=1) if mf and mf.group(0) in ln_), None)
    floor = cell(int(mf.group(1)), HANDOFF, f"line:{ln}/text:{mf.group(0)}") if mf else missing("no row floor stated in the handoff")
    for i, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## 3."):
            in_sec = True
            continue
        if in_sec and line.startswith("## "):
            break
        m = _ROW.match(line) if in_sec else None
        if m:
            claims.append({"config_name": m.group(1), "line": i,
                           "unique": cell(int(m.group(2)), HANDOFF, f"line:{i}/col:unique"),
                           "runs": cell(int(m.group(3)), HANDOFF, f"line:{i}/col:runs"),
                           "best_J": cell(float(m.group(4)), HANDOFF, f"line:{i}/col:best J"),
                           "status_text": m.group(5),
                           "claimed_status": _claimed_status(m.group(5))})
    return {"source": HANDOFF, "status": "ok", "grade": "inherited claim (not re-measured)",
            "snapshot_label": "2026-11-24", "claims": claims, "admission_floor": floor}


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
        comparable = claimed in ("pilot_eligible", "hold", "replay_mismatch", "needs_admission")
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


# ------------------------------------------------------------------ existing optimizer-evidence adapter

OE_TOOLS = ("tools/analysis/optimizer_evidence.py", "tools/analysis/optimizer_switch.py",
            "tools/analysis/continuation_advice.py", "tools/analysis/_common.py",
            "tools/analysis/floor_registry.py")


def _load_optimizer_evidence(root: Path):
    import importlib
    import sys
    tool_dir = str(Path(root) / "tools" / "analysis")
    if tool_dir not in sys.path:
        sys.path.insert(0, tool_dir)
    return importlib.import_module("optimizer_evidence")


def optimizer_evidence(reg: Registry, inv: dict, floor_cell: dict | None) -> dict:
    """Attach the existing ``tools/analysis/optimizer_evidence.py`` (schema optimizer-evidence-v1)
    report to every admission-relevant cohort: outcome buckets, cost ledger (BEM seconds), failure
    signal, pinned walls, continuation advice and cross-run compatibility. Read-only, advisory.

    The tool reads whole run dirs, so a run with rows after the cutoff is NOT carded (recorded as
    excluded) rather than letting future rows leak in."""
    floor = (floor_cell or {}).get("v")
    tool_digests = []
    for t in OE_TOOLS:
        reg.git_bytes(t)
        tool_digests.append(t)
    try:
        OE = _load_optimizer_evidence(reg.root)
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}", "tools": tool_digests}
    n_cards = 0
    for c in inv["cohorts"]:
        relevant = c["admission"].get("kind") or (isinstance(floor, int) and c["unique_designs"]["v"] >= floor)
        if not relevant:
            c["optimizer_evidence"] = {"status": "not_computed",
                                       "reason": "below the row floor and no admission artifact"}
            continue
        usable, skipped = [], []
        for r in c["runs"]:
            src = reg.sources.get(f"runs/{r}/search.ndjson") or {}
            if src.get("lines_after_cutoff"):
                skipped.append({"run": r, "reason": "run has rows after the cutoff"})
            elif src.get("status") == "missing":
                skipped.append({"run": r, "reason": "no search.ndjson"})
            else:
                usable.append(r)
        if not usable:
            c["optimizer_evidence"] = {"status": "missing", "reason": "no run usable at the cutoff", "skipped": skipped}
            continue
        try:
            rep = OE.build_report(run_dirs=[reg.root / "runs" / r for r in usable])
        except BaseException as exc:  # noqa: BLE001 - the tool exits via SystemExit on refusal
            c["optimizer_evidence"] = {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}
            continue
        cards = []
        for card in rep.get("run_cards") or []:
            k, oc = card.get("key_numbers") or {}, card.get("outcome_counts") or {}
            ref = f"tools/analysis/optimizer_evidence.py::run_cards[{card['run_id']}]"
            cards.append({
                "run": card["run_id"],
                "attempts_new": calc(k.get("attempts_new"), "optimizer_switch.cost_ledger.attempts_new", [ref]),
                "bem_seconds": calc(k.get("actual_bem_seconds"), "optimizer_switch.cost_ledger.actual_bem_seconds", [ref]),
                "recorded_seconds": calc(k.get("recorded_total_seconds"), "cost_ledger.elapsed_seconds.recorded_total", [ref]),
                "failure_fraction": calc(k.get("failure_fraction"), "optimizer_switch.failure_signal.fraction", [ref]),
                "outcomes": {b: oc.get(b) for b in ("index_rows", "valid", "cached", "geometry_refusal",
                                                    "envelope_refusal", "resource_refusal", "solver_failure",
                                                    "pipeline_failure", "unknown")},
                "pinned_walls": [w.get("key") for w in card.get("walls") or [] if w.get("wall_lo") or w.get("wall_hi")],
                "continuation": {k2: (card.get("continuation") or {}).get(k2) for k2 in ("advice", "status", "floor_J")},
                "stalled": (card.get("progress") or {}).get("stalled"),
            })
        n_cards += len(cards)
        tot = lambda key: math.fsum(x[key]["v"] for x in cards if isinstance(x[key]["v"], (int, float)))  # noqa: E731
        cr = rep.get("cross_run") or {}
        c["optimizer_evidence"] = {
            "status": "ok" if not skipped else "partial", "schema": rep.get("schema"),
            "advisory_only": rep.get("advisory_only"), "dispatches_work": rep.get("dispatches_work"),
            "runs": cards, "skipped": skipped,
            "totals": {"bem_hours": calc(tot("bem_seconds") / 3600.0, "sum(bem_seconds)/3600", [x["bem_seconds"] for x in cards]),
                       "recorded_hours": calc(tot("recorded_seconds") / 3600.0, "sum(recorded_seconds)/3600",
                                              [x["recorded_seconds"] for x in cards]),
                       "attempts": calc(int(tot("attempts_new")), "sum(attempts_new)", [x["attempts_new"] for x in cards])},
            "cross_run": {"compatible_for_inference": cr.get("compatible_for_inference"),
                          "compatible_for_descriptive": cr.get("compatible_for_descriptive"),
                          "blocking": cr.get("blocking")},
            "decision": rep.get("decision"),
            "alternatives": [{"action": a.get("action"), "why": a.get("why"), "confidence": a.get("confidence"),
                              "run_id": a.get("run_id")} for a in rep.get("alternatives") or []],
        }
    return {"status": "ok", "tools": tool_digests, "n_cards": n_cards, "schema": "optimizer-evidence-v1",
            "note": "existing advisory tool; cards only for admission-relevant cohorts with no rows after the cutoff"}
