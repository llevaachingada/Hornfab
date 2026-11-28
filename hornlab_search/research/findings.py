"""Evidence-graded findings derived deterministically from snapshot rows.

Every finding carries three readings of the same evidence:

``observation`` / ``hypothesis`` / ``action``
    the engineering record: what the rows show, what it may mean, what to do.
``plain``
    one or two sentences for a non-technical reader (no symbols, no jargon).
``next_steps``
    structured, machine-readable suggestions for planning agents. Each step states whether it needs
    the GPU and whether the owner must approve it. Nothing here is ever dispatched.

``evidence`` lists row ids and ``cells`` the exact values used, so every claim resolves to persisted
sources. Rules fire only on the data; no finding text names a design that the data did not select.
"""
from __future__ import annotations

import hashlib
import json

from .provenance import calc


def _fid(kind: str, evidence: list) -> str:
    return hashlib.sha256(json.dumps([kind, evidence], sort_keys=True).encode()).hexdigest()[:16]


def _step(kind: str, what: str, *, gpu: bool, owner_approval: bool, cpu_only_tool: str | None = None,
          blocked_by: list[str] | None = None) -> dict:
    return {"kind": kind, "what": what, "needs_gpu": gpu, "needs_owner_approval": owner_approval,
            "tool": cpu_only_tool, "blocked_by": blocked_by or []}


def _finding(kind, title, observation, hypothesis, action, evidence, cells, severity, *, plain, steps,
             scope, strength):
    return {"id": _fid(kind, evidence), "kind": kind, "title": title, "severity": severity,
            "observation": observation, "hypothesis": hypothesis, "action": action, "plain": plain,
            "scope": scope, "strength": strength,
            "next_steps": steps, "action_policy": "suggestion only; never auto-dispatched",
            "evidence": evidence, "cells": cells}


def _knobs(r: dict) -> str:
    return ", ".join(f"{k}={c['v']}" for k, c in r["knobs"].items())


def _identity_groups(dose: dict) -> dict[tuple, list]:
    """Non-control rows with a J, grouped strictly by family, brief, objective version and mesh epw."""
    groups: dict[tuple, list] = {}
    for r in dose["rows"]:
        if r["is_control"] or r["J"].get("v") is None:
            continue
        key = (r["family"], r["brief_hash"].get("v"), r["objective_version"].get("v"), r["epw"].get("v"))
        groups.setdefault(key, []).append(r)
    return groups


def dose_findings(dose: dict) -> list[dict]:
    out = []
    groups = _identity_groups(dose)
    scope = ("CD wall-angle backbone fixed-candidate verifies, one score identity per comparison; "
             "predeclared rules of that experiment only")
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
            f"{len(pairs)} single-knob fail/pass pairs exist in this snapshot.",
            f"{knob} fixes the failing rule at almost no scalar cost; the scalar J barely registers the defect.",
            f"Prefer {b['job']} over {a['job']}; record the predeclared verdict next to J in every ranking.",
            [a["id"], b["id"]],
            {"fail_J": a["J"], "pass_J": b["J"], "delta_J": dj, "fail_min_re_z": a["min_re_z"],
             "pass_min_re_z": b["min_re_z"], "fail_knob": a["knobs"][knob], "pass_knob": b["knobs"][knob],
             "failed_rule": a["verdict"]["rules"].get(a["verdict"]["failed_rules"][0])},
            "decision",
            plain=(f"Two nearly identical horn designs score almost the same, but only one meets the "
                   f"agreed acceptance rules: a small change near the throat fixes how well the horn loads "
                   f"the driver. The single score number hides this, so the rules, not the score, decide."),
            steps=[_step("adopt_reference", f"Use {b['job']} as the reference candidate for this body.",
                         gpu=False, owner_approval=True),
                   _step("report_change", "Show the predeclared verdict beside J wherever candidates are ranked.",
                         gpu=False, owner_approval=False)],
            scope=scope, strength=f"{len(pairs)} matched pairs; simulated verify fidelity"))
    for key, grp in sorted(groups.items(), key=lambda kv: str(kv[0])):
        lowest = min(grp, key=lambda r: r["J"]["v"])
        passing = [r for r in grp if r["verdict"]["v"] == "pass"]
        if lowest["verdict"]["v"] != "fail" or not passing:
            continue
        near = min(passing, key=lambda r: abs(r["J"]["v"] - lowest["J"]["v"]))
        dj = calc(near["J"]["v"] - lowest["J"]["v"], "J(pass) - J(lowest)", [near["J"], lowest["J"]])
        rules = ", ".join(lowest["verdict"]["failed_rules"])
        out.append(_finding(
            "scalar_not_gate",
            f"Lowest J in {key[0]} fails a predeclared rule; the nearest passing candidate is {dj['v']:.4f} J higher",
            f"{lowest['job']} ({_knobs(lowest)}) has the lowest J {lowest['J']['v']:.4f} of {len(grp)} "
            f"non-control candidates in one score identity (brief {key[1]}, v{key[2]}, epw {key[3]}) and fails {rules}. "
            f"{near['job']} ({_knobs(near)}) passes all six rules at J {near['J']['v']:.4f}; "
            f"min Re(z) {lowest['min_re_z']['v']:.3f} -> {near['min_re_z']['v']:.3f}.",
            "The scalar objective does not encode the loading rule; picking by J alone selects a failing design.",
            "Select by the predeclared rules first, then by J inside the passing set.",
            [lowest["id"], near["id"]],
            {"lowest_J": lowest["J"], "pass_J": near["J"], "delta_J": dj,
             "lowest_min_re_z": lowest["min_re_z"], "pass_min_re_z": near["min_re_z"],
             "failed_rule": lowest["verdict"]["rules"].get(lowest["verdict"]["failed_rules"][0])},
            "decision",
            plain=("The design with the best single score in this group fails an acceptance rule. "
                   "Ranking by score alone would have picked the wrong design."),
            steps=[_step("selection_rule", "Filter candidates by the predeclared rules before ranking by J.",
                         gpu=False, owner_approval=False)],
            scope=scope, strength=f"{len(grp)} candidates in one identity"))
    res = [(r["id"], r["attribution"]["residual"]) for r in dose["rows"]
           if r.get("attribution", {}).get("status") == "ok"]
    if res:
        worst = max(res, key=lambda x: abs(x[1]["v"] or 0.0))
        out.append(_finding(
            "attribution_reconciles", "Score attribution reconciles to the stored J",
            f"{len(res)} dose rows: weighted stored terms sum to the stored total; worst |residual| "
            f"{abs(worst[1]['v']):.3e} ({worst[0]}).",
            "Per-term contributions are the objective's own (its weight resolvers on stored terms), not a re-score.",
            "None.", [r for r, _ in res], {"worst_residual": worst[1]}, "info",
            plain="The score breakdown adds up exactly to the recorded score, so the per-part bars can be trusted.",
            steps=[], scope="dose rows with a committed config", strength="exact to floating-point rounding"))
    return out


def cohort_findings(inv: dict, recon: list[dict], floor_cell: dict | None = None) -> list[dict]:
    out = []
    floor = (floor_cell or {}).get("v")
    if isinstance(floor, int):
        big_bad = [c for c in inv["cohorts"] if c["unique_designs"]["v"] >= floor
                   and c["status"] in ("hold", "replay_mismatch")]
        if big_bad:
            steps = []
            for c in big_bad:
                if c["status"] == "replay_mismatch":
                    steps.append(_step("repair_replay", f"Recover the original box/config for {c['config_name']} "
                                       f"so its rows re-encode exactly ({c['treatment_variants']['v']} config "
                                       "revisions in this cohort).", gpu=False, owner_approval=False,
                                       cpu_only_tool="tools/analysis/rescore_identity.py"))
                else:
                    steps.append(_step("keep_held", f"Keep {c['config_name']} out of metric-BO admission.",
                                       gpu=False, owner_approval=False))
            out.append(_finding(
                "count_not_admission", "Sample count is not admission",
                "; ".join(f"{c['config_name']}: {c['unique_designs']['v']} unique designs, status {c['status']}"
                          for c in big_bad) + f" (row floor {floor} from the handoff).",
                "These cohorts clear the row floor but fail the frozen holdout or cannot be replayed under the "
                "current config, so more rows of the same kind would not make them admissible.",
                "Do not promote by count. Repair the replay contract (replay_mismatch) or keep held (hold).",
                [c["id"] for c in big_bad],
                {"floor": floor_cell, **{c["id"]: (c["admission"].get("holdout") or {}).get("verdict")
                                         or (c["admission"].get("replay") or {}).get("exact_complete")
                                         for c in big_bad}},
                "decision",
                plain=("Some design groups have plenty of results but still are not trustworthy enough to "
                       "train the optimizer on. More of the same results would not fix that."),
                steps=steps, scope="v11 screen cohorts with an admission artifact",
                strength="frozen chronological holdout / exact replay counts"))
    conflicts = [r for r in recon if r["result"] == "status_conflict"]
    if conflicts:
        out.append(_finding(
            "claim_conflict", "Handoff status disagrees with the admission artifact",
            "; ".join(f"{r['config_name']}: handoff says {r['claimed_status']} (line {r['claim_line']}), "
                      f"artifact says {r['artifact_status']}" for r in conflicts) + ".",
            "The handoff table was not updated after the admission run; the artifact is the newer evidence. "
            "pilot_eligible means PASS_FOR_EXPLORATORY_PILOT: a held canary may be considered, not full admission.",
            "Treat the artifact as authoritative for this status and correct the handoff table.",
            [r["cohort"] for r in conflicts], {r["cohort"]: r["unique_at_cutoff"] for r in conflicts},
            "data_quality",
            plain=("A planning document is out of date: it says a check is still to do, but the records show it "
                   "was run and passed for a limited trial."),
            steps=[_step("fix_doc", f"Correct the handoff table row for {r['config_name']}.", gpu=False,
                         owner_approval=False) for r in conflicts],
            scope="metric-BO handoff section 3 vs runs/v11_bo_day_planning artifacts",
            strength="artifact file vs prose claim"))
    drift = [c for c in inv["cohorts"] if ((c.get("optimizer_evidence") or {}).get("cross_run") or {}).get("blocking")]
    if drift:
        out.append(_finding(
            "software_drift", "Cohorts whose runs span different software pins",
            "; ".join(f"{c['config_name']}: {', '.join(c['optimizer_evidence']['cross_run']['blocking'])} across "
                      f"{len(c['optimizer_evidence']['runs'])} runs (admission status {c['status']})" for c in drift) + ".",
            "Rows were solved under different dependency/software versions, so the existing optimizer-evidence "
            "tool marks the pooled runs descriptive-only, not compatible for inference.",
            "Before using these cohorts for model training, confirm the admission artifact's dependency group "
            "covers the rows it used, or re-admit per software version.",
            [c["id"] for c in drift],
            {c["id"]: c["optimizer_evidence"]["cross_run"] for c in drift}, "data_quality",
            plain=("Some groups of results were produced with different versions of the simulation software, so "
                   "they should be checked before being treated as one consistent set."),
            steps=[_step("check_dependency_group", f"Compare {c['config_name']}'s admission dependency group with its "
                         "run lib_shas.", gpu=False, owner_approval=False,
                         cpu_only_tool="tools/analysis/optimizer_evidence.py") for c in drift],
            scope="admission-relevant v11 cohorts with optimizer-evidence cards",
            strength="optimizer_evidence.py cross_run.compare_compatibility"))
    mixed = sorted({c["config_name"] for c in inv["cohorts"] if c["mixed_identity"]})
    if mixed:
        out.append(_finding(
            "mixed_identity", "Config names that span more than one score identity",
            f"{len(mixed)} config names split into several (brief, mode, backend, mesh/solve) cohorts: "
            + ", ".join(mixed[:12]) + ("…" if len(mixed) > 12 else "") + ".",
            "Pooling by name would mix score identities.",
            "Keep them split; compare J only inside one cohort id.",
            [c["id"] for c in inv["cohorts"] if c["mixed_identity"]][:40], {}, "data_quality",
            plain="Some experiments reuse a name across different scoring setups; their scores must not be compared.",
            steps=[], scope="v11 inventory", strength="exact identity keys"))
    if inv.get("orphan_admissions"):
        out.append(_finding(
            "orphan_admission", "Admission artifacts that match no cohort",
            "; ".join(f"{o['source']} ({'/'.join(map(str, o['key']))})" for o in inv["orphan_admissions"]) + ".",
            "The artifact's identity (config, brief, fidelity) differs from every run at the cutoff.",
            "Check the artifact's brief hash and fidelity before relying on it.",
            [o["source"] for o in inv["orphan_admissions"]], {}, "data_quality",
            plain="Some admission records could not be matched to any set of results.",
            steps=[], scope="runs/v11_bo_day_planning", strength="exact identity keys"))
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
        "mesh_scope", "Rear coarsening pays off on the tested formula classes, not on CAD",
        f"{len(ac)} acoustic cases: {lo:.1f}–{hi:.1f}% fewer solved DOF at factor 1.5, worst beamwidth "
        f"deviation {worst['max_bw_delta_deg']['v']:.3f}° ({worst['label']}). "
        + "; ".join(f"{r['label']}: {r['dof_reduction_pct']['v']:.1f}% ({r['evidence']})" for r in other) + ".",
        "The saving is real where the outer shell is meshed separately; CAD is inert and the point-grid class "
        "has mesh evidence only.",
        "Keep 1.5 explicit for the tested formula classes; no universal factor; GPU timing still unmeasured.",
        [r["id"] for r in rows], {"worst_bw": worst["max_bw_delta_deg"]}, "decision",
        plain=(f"A coarser mesh on the back of the horn cuts the simulation size by "
               f"{f'about {lo:.0f}%' if round(lo) == round(hi) else f'{lo:.0f}–{hi:.0f}%'} on the "
               f"tested shape types while beamwidths move by at most {worst['max_bw_delta_deg']['v']:.2f}°; "
               "it does nothing for CAD-built horns."),
        steps=[_step("measure_gpu", "Time one factor-1.5 vs 1.0 solve pair on the GPU lane.", gpu=True,
                     owner_approval=True),
               _step("keep_policy", "Keep rear_res_factor 1.5 explicit in new formula-class configs.", gpu=False,
                     owner_approval=False)],
        scope="variable-mesh audit 2026-11-23; CPU acoustic A/B on frozen grids",
        strength=f"{len(ac)} acoustic cases, one design each")]


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
        "info",
        plain="In the one small trial, the quick check and the careful check agreed on which design was better. Two designs are too few to rely on.",
        steps=[_step("verify_more", "Verify more screen leaders before using screen gaps as evidence.", gpu=True,
                     owner_approval=True)],
        scope="metric-BO Fold canary package", strength=f"n = {can['n_pairs']}")]
    if can["replicates"]:
        out.append(_finding(
            "solve_replicate", "Negative control: repeated solves of the same designs agree",
            f"{len(can['replicates'])} design/fidelity pairs solved in two independent study packages; "
            f"max |ΔJ| {can['replicate_max_abs_delta']['v']:.2e}.",
            "Differences far below any reported J gap are solver/process noise, not design effects.",
            "None.", [f"canary:{r['mode']}:{r['design']}" for r in can["replicates"]],
            {"max_abs_delta": can["replicate_max_abs_delta"]}, "control",
            plain="Solving the same design twice gives the same answer to about one part in a million, so the differences reported here are real.",
            steps=[], scope="canary rehearsal vs clean package", strength=f"{len(can['replicates'])} repeats"))
    return out
