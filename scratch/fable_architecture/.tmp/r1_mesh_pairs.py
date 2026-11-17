"""R1: mesh-fidelity pairs. Read-only. Writes MESH_FIDELITY_PAIRS.md."""
from __future__ import annotations

import collections
import glob
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
import yaml

sys.path.insert(0, r"C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp")
import fable_replay_harness as H

REPO = H.REPO
OUT = REPO / "scratch" / "fable_architecture" / "MESH_FIDELITY_PAIRS.md"
DATA = REPO / "dataset"
GRID = H.GRID_58
STOP_PAIRS = 30


def head_sha():
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def load_dataset_index():
    recs = []
    for shard in sorted(DATA.glob("shard-*.jsonl")):
        si = int(shard.stem.split("-")[1])
        for row, line in enumerate(shard.read_text(encoding="utf-8").splitlines()):
            try:
                recs.append((si, row, json.loads(line)))
            except Exception:
                continue
    return recs


def npz_path(si, row):
    return DATA / f"shard-{si:04d}" / f"rec-{row:04d}.npz"


def load_rec_response(path):
    with np.load(path, allow_pickle=False) as z:
        return {k: np.array(z[k]) for k in z.files}


def resp_from_arrays(a):
    from hornlab_search.types import Response
    kw = {k: a.get(k) for k in ("freqs_hz", "h_angles_deg", "v_angles_deg", "spl_h_db",
                                "spl_v_db", "balloon_dirs", "spl_balloon_db", "z_throat",
                                "p_h", "p_v", "p_balloon")}
    kw["backend"] = "beat_cuda"
    kw["meta"] = {}
    return Response(**kw)


def covers(band_lo, band_hi, freqs):
    f = np.asarray(freqs, float)
    return f.min() <= band_lo + 1e-6 and f.max() >= band_hi - 1e-6


def main():
    t0 = time.time()
    sha = head_sha()
    recs = load_dataset_index()
    groups = collections.defaultdict(list)
    for si, row, d in recs:
        groups[d.get("design_hash")].append((si, row, d))

    multi = {k: v for k, v in groups.items() if len({d.get("mesh_hash") for _, _, d in v}) > 1}

    # unique physical variants per design (mesh, solve, target, ok)
    candidates = []
    for dh, rows in multi.items():
        variants = {}
        for si, row, d in rows:
            tgt = json.dumps(d.get("target"), sort_keys=True)
            key = (d.get("mesh_hash"), d.get("solve_hash"), tgt, bool(d.get("ok")))
            variants.setdefault(key, (si, row, d))
        vv = list(variants.values())
        meshes = {d.get("mesh_hash") for _, _, d in vv}
        if len(meshes) < 2:
            continue
        for i in range(len(vv)):
            for j in range(i + 1, len(vv)):
                a, b = vv[i], vv[j]
                da, db = a[2], b[2]
                if da.get("mesh_hash") == db.get("mesh_hash"):
                    continue
                if not (da.get("ok") and db.get("ok")):
                    continue
                if json.dumps(da.get("target"), sort_keys=True) != json.dumps(db.get("target"), sort_keys=True):
                    continue
                pa, pb = npz_path(a[0], a[1]), npz_path(b[0], b[1])
                if not (pa.is_file() and pb.is_file()):
                    continue
                t = da.get("target") or {}
                try:
                    lo, hi = float(t["band_lo_hz"]), float(t["band_hi_hz"])
                except Exception:
                    continue
                fa = da.get("solve", {}).get("freqs_hz") or []
                fb = db.get("solve", {}).get("freqs_hz") or []
                if not (covers(lo, hi, fa) and covers(lo, hi, fb)):
                    continue
                candidates.append((dh, a, b))
    candidates.sort(key=lambda x: (x[0], x[1][2].get("mesh_hash"), x[2][2].get("mesh_hash")))

    b7 = H.landscape_brief()
    scored = []
    skipped = []
    resp_cache = {}
    for idx, (dh, a, b) in enumerate(candidates):
        try:
            da, db = a[2], b[2]
            target = H.target_from_record(da["target"])
            key_a, key_b = npz_path(a[0], a[1]), npz_path(b[0], b[1])
            if key_a not in resp_cache:
                resp_cache[key_a] = resp_from_arrays(load_rec_response(key_a))
            if key_b not in resp_cache:
                resp_cache[key_b] = resp_from_arrays(load_rec_response(key_b))
            ra, rb = resp_cache[key_a], resp_cache[key_b]
            ia = H.interp_response(ra, GRID, method="pchip")
            ib = H.interp_response(rb, GRID, method="pchip")
            ma = H.metrics_parity(ia, target)
            mb = H.metrics_parity(ib, target)
            ja, ta = H.score_v7(ma, ia, target, b7.weights, b7.objective_params)
            jb, tb = H.score_v7(mb, ib, target, b7.weights, b7.objective_params)
            dof_a = da.get("mesh", {}).get("n_dof") or da.get("solve", {}).get("n_dof")
            dof_b = db.get("mesh", {}).get("n_dof") or db.get("solve", {}).get("n_dof")
            if not (dof_a and dof_b):
                skipped.append((dh, "no dof"))
                continue
            scored.append(dict(design=dh, mesh_a=da.get("mesh_hash"), mesh_b=db.get("mesh_hash"),
                               dof_a=int(dof_a), dof_b=int(dof_b), ratio=max(dof_a, dof_b) / min(dof_a, dof_b),
                               j_a=ja, j_b=jb, dj=jb - ja,
                               terms_a={k: ta.get(k) for k in ("cov", "rip", "di", "dislope", "flat",
                                                               "load", "distd", "diag", "flat_cv")},
                               terms_b={k: tb.get(k) for k in ("cov", "rip", "di", "dislope", "flat",
                                                               "load", "distd", "diag", "flat_cv")},
                               target=f"{target.coverage_h_deg:.0f}x{target.coverage_v_deg:.0f} "
                                      f"{target.band_lo_hz:.0f}-{target.band_hi_hz:.0f}"))
            if (idx + 1) % 50 == 0:
                print(f"scored {idx+1}/{len(candidates)} candidates, kept {len(scored)}", flush=True)
        except Exception as e:
            skipped.append((dh, repr(e)[:120]))

    # Stop at 30 pairs, but make the sample informative for the J<5 question:
    # all low-J pairs first (lowest J), then the remaining lowest-J pairs.
    scored.sort(key=lambda p: (min(p["j_a"], p["j_b"]), p["design"]))
    low_all = [p for p in scored if min(p["j_a"], p["j_b"]) < 5.0]
    pairs = scored[:STOP_PAIRS]
    if len(low_all) and not any(min(p["j_a"], p["j_b"]) < 5.0 for p in pairs):
        pairs = (low_all + [p for p in scored if p not in low_all])[:STOP_PAIRS]

    # run/study scans: report whether any exist
    run_multi = 0
    study_diff = 0
    for rd in sorted((REPO / "runs").iterdir()):
        ndp = rd / "search.ndjson"
        if not rd.is_dir() or not ndp.is_file():
            continue
        g = collections.defaultdict(set)
        for line in ndp.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("ok"):
                g[r.get("design_hash")].add(r.get("mesh_hash"))
        run_multi += sum(1 for s in g.values() if len(s) > 1)
    for S in sorted((REPO / "runs").glob("study-*")):
        sd, vd = S / "screen", S / "verify"
        if not (sd / "designs").is_dir() or not (vd / "designs").is_dir():
            continue
        for h in {p.name for p in (sd / "designs").iterdir() if p.is_dir()} & \
                 {p.name for p in (vd / "designs").iterdir() if p.is_dir()}:
            try:
                a = H.json_load(sd / "designs" / h / "status.json").get("mesh_hash")
                b = H.json_load(vd / "designs" / h / "status.json").get("mesh_hash")
                study_diff += int(a != b)
            except Exception:
                pass

    # config mode differences (res_mm / DOF cap)
    mode_rows = []
    res_keys = set()
    for rd in sorted((REPO / "runs").iterdir()):
        cfgp = rd / "config.yaml"
        if not rd.is_dir() or not cfgp.is_file():
            continue
        try:
            cfg = yaml.safe_load(cfgp.read_text(encoding="utf-8"))
        except Exception:
            continue
        mesh = cfg.get("mesh") or {}
        res_keys.update(k for k in mesh if str(k).startswith("res_mm"))
        cs, cv, cf = mesh.get("dof_cap_screen"), mesh.get("dof_cap_verify"), mesh.get("dof_cap_final")
        if cs is None or cv is None:
            continue
        if cs != cv or (cf is not None and cf != cs):
            mode_rows.append((str(cfg.get("name")), rd.name, mesh.get("epw"), cs, cv, cf))

    lines = []
    lines.append("# MESH_FIDELITY_PAIRS")
    lines.append("")
    lines.append(f"- Repo HEAD at run: `{sha}`")
    lines.append(f"- Timestamp: `{time.strftime('%Y-%m-%dT%H:%M:%S%z')}`")
    lines.append("- Read-only against `runs/` and `dataset/`; no solve, mesher, GPU, queue or config write.")
    lines.append(f"- Common scorer: v7 landscape brief `{b7.name}` "
                 "(weights/objective block from the standard 80x50 brief; target from the stored record).")
    lines.append("- Grid: one 58-point log grid, 350-8000 Hz (`np.geomspace(350, 8000, 58)`), PCHIP in log f.")
    lines.append("- Metrics are regenerated with the parity-exact DI rule (sin-theta balloon quadrature, "
                 "`search/evaluate.metrics_from_response` semantics).")
    lines.append("")
    lines.append("## Pair count")
    lines.append("")
    lines.append(f"- Dataset design hashes with more than one `mesh_hash`: **{len(multi)}**")
    lines.append(f"- Same-target, both-ok, both-response, band-covering candidate pairs: **{len(candidates)}**")
    lines.append(f"- Candidate pairs scored (all candidates): **{len(scored)}**")
    lines.append(f"- Candidate pairs with J below 5 (either mesh): **{len(low_all)}**")
    lines.append(f"- Pairs shown (stop at {STOP_PAIRS}): **{len(pairs)}**")
    lines.append(f"- `runs/**/search.ndjson` multi-mesh design hashes: **{run_multi}** "
                 "(one response per design dir, so no run pair can be scored)")
    lines.append(f"- Study `screen` vs `verify` pairs with a different `mesh_hash`: **{study_diff}** "
                 "(same mesh in every study pair)")
    lines.append("")
    if not pairs:
        lines.append("No scoreable mesh pairs exist. Stop: nothing was solved.")
    else:
        lines.append("## Delta table")
        lines.append("")
        lines.append("| # | design | mesh A (dof) | mesh B (dof) | DOF B/A | J A | J B | dJ (B-A) | d cov | d rip | d di | d dislope | d flat | d load | d distd | d diag | d flat_cv | target |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for i, p in enumerate(pairs, 1):
            da = p["terms_a"]; db = p["terms_b"]
            def d(k):
                va, vb = da.get(k), db.get(k)
                try:
                    return f"{float(vb) - float(va):+.3f}"
                except Exception:
                    return "n/a"
            lines.append(
                f"| {i} | `{p['design']}` | `{p['mesh_a']}` ({p['dof_a']}) | `{p['mesh_b']}` ({p['dof_b']}) | "
                f"{p['ratio']:.3f} | {p['j_a']:.3f} | {p['j_b']:.3f} | {p['dj']:+.3f} | "
                f"{d('cov')} | {d('rip')} | {d('di')} | {d('dislope')} | {d('flat')} | {d('load')} | "
                f"{d('distd')} | {d('diag')} | {d('flat_cv')} | {p['target']} |")
        lines.append("")
        low = [p for p in pairs if min(p["j_a"], p["j_b"]) < 5.0]
        if len(low) >= 2:
            djs = np.array([p["dj"] for p in low], float)
            lines.append(f"- **Standard deviation of dJ among designs with J below 5:** "
                         f"**{np.std(djs, ddof=1):.3f} J** (n={len(low)}; mean {np.mean(djs):+.3f}, "
                         f"min {np.min(djs):+.3f}, max {np.max(djs):+.3f}).")
        else:
            lines.append(f"- Designs with J below 5: **{len(low)}**; too few for a standard deviation.")
        all_dj = np.array([p["dj"] for p in pairs], float)
        lines.append(f"- All pairs: mean dJ {np.mean(all_dj):+.3f}, sd {np.std(all_dj, ddof=1):.3f}, "
                     f"min {np.min(all_dj):+.3f}, max {np.max(all_dj):+.3f}.")
        lines.append("")
        lines.append("## Decision reading")
        lines.append("")
        sd_low = np.std([p["dj"] for p in low], ddof=1) if len(low) >= 2 else float("nan")
        if np.isfinite(sd_low) and sd_low < 0.10:
            lines.append(f"The J change from mesh pairs is below 0.10 J (sd {sd_low:.3f}); the specification "
                         "should lead with grid-invariant scoring.")
        elif np.isfinite(sd_low) and sd_low > 0.17:
            lines.append(f"The J change from mesh pairs is above 0.17 J (sd {sd_low:.3f}); a mesh-fidelity "
                         "ladder is the honest lead.")
        else:
            lines.append(f"The J change is between the two thresholds or the low-J sample is too small "
                         f"(sd {sd_low:.3f}); neither lead is established by this table.")
        lines.append("")
        lines.append("Caveat: the dataset pairs are historical records (2026-10-13 onward). Mesh and frequency "
                     "support often co-vary; only same-target pairs whose two responses both cover the stored "
                     "band are scored. The score is a common v7 re-score, not the historical J of either row.")
    lines.append("")
    lines.append("## Verify/confirm mode differences")
    lines.append("")
    lines.append(f"- Explicit `res_mm*` keys in any run config: **{sorted(res_keys) if res_keys else 'none'}**; "
                 "mesh resolution is set by `mesh.epw` (no mode-specific res key exists).")
    lines.append("- Modes present in run configs: `screen` and `verify` (no `confirm` mode config was found).")
    lines.append(f"- Run configs whose verify/final DOF cap differs from the screen cap: **{len(mode_rows)}**.")
    lines.append("")
    if mode_rows:
        groups2 = collections.defaultdict(list)
        for name, run, epw, cs, cv, cf in mode_rows:
            groups2[(name, epw, cs, cv, cf)].append(run)
        lines.append("| config | epw | DOF screen | DOF verify | DOF final | n runs | run dirs |")
        lines.append("|---|---|---|---|---|---|---|")
        for (name, epw, cs, cv, cf), runs in sorted(groups2.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))):
            lines.append(f"| `{name}` | {epw} | {cs} | {cv} | {cf} | {len(runs)} | "
                         + ", ".join(f"`{r}`" for r in sorted(runs)) + " |")
    lines.append("")
    lines.append(f"_Script: `scratch/fable_architecture/.tmp/r1_mesh_pairs.py`; runtime {time.time()-t0:.1f}s._")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} pairs={len(pairs)} candidates={len(candidates)} multi={len(multi)} "
          f"mode_rows={len(mode_rows)} run_multi={run_multi} study_diff={study_diff} skipped={len(skipped)}")
    if skipped:
        print("skipped examples", skipped[:5])


if __name__ == "__main__":
    main()
