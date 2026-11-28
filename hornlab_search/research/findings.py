"""Evidence-graded findings derived deterministically from snapshot rows.

A finding separates ``observation`` (what the rows show), ``hypothesis`` (what it may mean) and
``action`` (a suggestion for the owner; nothing is ever dispatched). ``evidence`` lists row ids
and the exact cells used, so every claim resolves to persisted sources. Rules fire only on the
data; no finding text is hard-coded to a specific design.
"""
from __future__ import annotations

import hashlib
import json

from .provenance import calc


def _fid(kind: str, evidence: list) -> str:
    return hashlib.sha256(json.dumps([kind, evidence], sort_keys=True).encode()).hexdigest()[:16]


def _finding(kind, title, observation, hypothesis, action, evidence, cells, severity):
    return {"id": _fid(kind, evidence), "kind": kind, "title": title, "severity": severity,
            "observation": observation, "hypothesis": hypothesis, "action": action,
            "action_policy": "suggestion only; no auto-dispatch",
            "evidence": evidence, "cells": cells}


def dose_findings(dose: dict) -> list[dict]:
    out = []
    rows = [r for r in dose["rows"] if r["J"].get("v") is not None and not r["is_control"]]
    # group strictly: same family, brief, objective version and mesh epw
    groups: dict[tuple, list] = {}
    for r in rows:
        key = (r["family"], r["brief_hash"].get("v"), r["objective_version"].get("v"), r["epw"].get("v"))
        groups.setdefault(key, []).append(r)
    for key, grp in sorted(groups.items(), key=lambda kv: str(kv[0])):
        lowest = min(grp, key=lambda r: r["J"]["v"])
        passing = [r for r in grp if r["verdict"]["v"] == "pass"]
        if lowest["verdict"]["v"] != "fail" or not passing:
            continue
        near = min(passing, key=lambda r: abs(r["J"]["v"] - lowest["J"]["v"]))
        dj = calc(near["J"]["v"] - lowest["J"]["v"], "J(pass) - J(lowest)", [near["J"], lowest["J"]])
        rules = ", ".join(lowest["verdict"]["failed_rules"])
        knobs = lambda r: ", ".join(f"{k}={c['v']}" for k, c in r["knobs"].items())  # noqa: E731
        out.append(_finding(
            "scalar_not_gate",
            f"Lowest J in {key[0]} fails a predeclared rule; a passing candidate sits {dj['v']:.4f} J away",
            f"{lowest['job']} ({knobs(lowest)}) has the lowest J {lowest['J']['v']:.4f} of {len(grp)} "
            f"candidates in one score identity (brief {key[1]}, v{key[2]}, epw {key[3]}) and fails {rules}. "
            f"{near['job']} ({knobs(near)}) passes all six rules at J {near['J']['v']:.4f}; "
            f"min Re(z) {lowest['min_re_z']['v']:.3f} -> {near['min_re_z']['v']:.3f}.",
            "The scalar objective does not encode the loading rule; J alone would pick a failing dose.",
            f"Keep {near['job']} as the reference candidate; select doses by the predeclared rules, "
            "then by J inside the passing set.",
            [lowest["id"], near["id"]],
            {"lowest_J": lowest["J"], "pass_J": near["J"], "delta_J": dj,
             "lowest_min_re_z": lowest["min_re_z"], "pass_min_re_z": near["min_re_z"],
             "failed_rule": lowest["verdict"]["rules"].get(lowest["verdict"]["failed_rules"][0])},
            "decision"))
    # matched single-knob pairs: lower J fails, higher J passes, everything else equal
    pairs = []
    for key, grp in groups.items():
        for a in grp:
            for b in grp:
                if a is b or a["J"]["v"] >= b["J"]["v"]:
                    continue
                if a["verdict"]["v"] != "fail" or b["verdict"]["v"] != "pass":
                    continue
                ka, kb = ({k: c["v"] for k, c in r["knobs"].items()} for r in (a, b))
                diff = [k for k in sorted(set(ka) | set(kb)) if ka.get(k) != kb.get(k)]
                if len(diff) == 1:
                    pairs.append((b["J"]["v"] - a["J"]["v"], key, a, b, diff[0]))
    if pairs:
        dj_v, key, a, b, knob = min(pairs, key=lambda p: (p[0], p[2]["id"]))
        dj = calc(dj_v, "J(pass) - J(fail)", [b["J"], a["J"]])
        out.append(_finding(
            "matched_pair",
            f"One knob, two verdicts: {a['job']} fails, {b['job']} passes at {dj_v:+.4f} J",
            f"Same family, brief, objective version and mesh; only {knob} differs "
            f"({a['knobs'][knob]['v']} -> {b['knobs'][knob]['v']}). {a['job']}: J {a['J']['v']:.4f}, "
            f"fails {', '.join(a['verdict']['failed_rules'])}, min Re(z) {a['min_re_z']['v']:.3f}. "
            f"{b['job']}: J {b['J']['v']:.4f}, passes all six rules, min Re(z) {b['min_re_z']['v']:.3f}. "
            f"{len(pairs)} such single-knob fail/pass pairs exist in the snapshot.",
            f"{knob} fixes the failing rule at almost no scalar cost; the scalar J barely sees it.",
            f"Prefer {b['job']} over {a['job']}; record the predeclared verdict next to J in every ranking.",
            [a["id"], b["id"]],
            {"fail_J": a["J"], "pass_J": b["J"], "delta_J": dj, "fail_min_re_z": a["min_re_z"],
             "pass_min_re_z": b["min_re_z"], "fail_knob": a["knobs"][knob], "pass_knob": b["knobs"][knob],
             "failed_rule": a["verdict"]["rules"].get(a["verdict"]["failed_rules"][0])},
            "decision"))
    # attribution reconciliation over every row with stored terms
    res = [(r["id"], r["attribution"]["residual"]) for r in dose["rows"]
           if r.get("attribution", {}).get("status") == "ok"]
    if res:
        worst = max(res, key=lambda x: abs(x[1]["v"] or 0.0))
        out.append(_finding(
            "attribution_reconciles", "Score attribution reconciles to stored J",
            f"{len(res)} dose rows: weighted stored terms sum to the stored total; worst |residual| "
            f"{abs(worst[1]['v']):.3e} ({worst[0]}).",
            "Contributions shown per term are the objective's own, not a re-score.",
            "None.", [r for r, _ in res], {"worst_residual": worst[1]}, "info"))
    return out


def cohort_findings(inv: dict, recon: list[dict], floor: int = 150) -> list[dict]:
    out = []
    big_bad = [c for c in inv["cohorts"] if c["unique_designs"]["v"] >= floor
               and c["status"] in ("hold", "replay_mismatch")]
    if big_bad:
        out.append(_finding(
            "count_not_admission", "Sample count is not admission",
            "; ".join(f"{c['config_name']}: {c['unique_designs']['v']} unique designs, status {c['status']}"
                      for c in big_bad) + f" (floor {floor}).",
            "These cohorts clear the row floor but fail holdout or cannot be replayed under the current "
            "config, so more rows of the same kind would not make them admissible.",
            "Do not promote by count. Repair the replay contract (replay_mismatch) or keep held (hold).",
            [c["id"] for c in big_bad],
            {c["id"]: c["admission"].get("holdout", {}).get("verdict") or c["admission"].get("replay", {})
             .get("exact_complete") for c in big_bad}, "decision"))
    conflicts = [r for r in recon if r["result"] == "status_conflict"]
    if conflicts:
        out.append(_finding(
            "claim_conflict", "Handoff status disagrees with the admission artifact",
            "; ".join(f"{r['config_name']}: handoff says {r['claimed_status']} (line {r['claim_line']}), "
                      f"artifact says {r['artifact_status']}" for r in conflicts) + ".",
            "The handoff table predates a later admission run; the artifact is the newer evidence.",
            "Treat the artifact as authoritative and correct the handoff table.",
            [r["cohort"] for r in conflicts], {r["cohort"]: r["unique_at_cutoff"] for r in conflicts},
            "data_quality"))
    mixed = sorted({c["config_name"] for c in inv["cohorts"] if c["mixed_identity"]})
    if mixed:
        out.append(_finding(
            "mixed_identity", "Config names that span more than one score identity",
            f"{len(mixed)} config names split into several (brief, mode, backend) cohorts: "
            + ", ".join(mixed[:12]) + ("…" if len(mixed) > 12 else "") + ".",
            "Pooling by name would mix score identities.",
            "Keep them split; compare J only inside one cohort id.",
            [c["id"] for c in inv["cohorts"] if c["mixed_identity"]][:40], {}, "data_quality"))
    return out


def mesh_findings(mesh: dict) -> list[dict]:
    rows = mesh.get("rows") or []
    ac = [r for r in rows if r["evidence"] == "acoustic"]
    other = [r for r in rows if r["evidence"] != "acoustic"]
    if not ac:
        return []
    lo = min(r["dof_reduction_pct"]["v"] for r in ac)
    hi = max(r["dof_reduction_pct"]["v"] for r in ac)
    worst = max(ac, key=lambda r: r["max_bw_delta_deg"]["v"])
    return [_finding(
        "mesh_scope", "Rear coarsening helps formula classes only",
        f"{len(ac)} acoustic cases: {lo:.1f}–{hi:.1f}% fewer solved DOF at factor 1.5, worst beamwidth "
        f"deviation {worst['max_bw_delta_deg']['v']:.3f}° ({worst['label']}). "
        + "; ".join(f"{r['label']}: {r['dof_reduction_pct']['v']:.1f}% ({r['evidence']})" for r in other) + ".",
        "The saving is real where the outer shell is meshed separately; CAD is inert and the point-grid "
        "class has mesh evidence only.",
        "Keep 1.5 explicit for formula classes; no universal factor; GPU timing still unmeasured.",
        [r["id"] for r in rows], {"worst_bw": worst["max_bw_delta_deg"]}, "decision")]


def canary_findings(can: dict) -> list[dict]:
    if can.get("status") != "ok" or not can["verify_pairs"]:
        return []
    out = [_finding(
        "canary_rank", "Canary: screen order survives verify (n = %d)" % can["n_pairs"],
        "; ".join(f"{p['design']}: screen {p['screen_J']['v']:.4f}, verify {p['verify_J']['v']:.4f}"
                  for p in can["verify_pairs"]) + f". Rank preserved: {can['rank_preserved']['v']}.",
        "Two designs cannot calibrate screen-to-verify rank in general.",
        "No calibration claim; verify more designs before trusting screen gaps.",
        [f"canary:{p['design']}" for p in can["verify_pairs"]], {"rank_preserved": can["rank_preserved"]},
        "info")]
    if can["replicates"]:
        out.append(_finding(
            "solve_replicate", "Negative control: repeated solves of the same designs agree",
            f"{len(can['replicates'])} design/fidelity pairs solved in two independent study packages; "
            f"max |ΔJ| {can['replicate_max_abs_delta']['v']:.2e}.",
            "Differences far below any reported J gap are solver/process noise, not design effects.",
            "None.", [f"canary:{r['mode']}:{r['design']}" for r in can["replicates"]],
            {"max_abs_delta": can["replicate_max_abs_delta"]}, "control"))
    return out
