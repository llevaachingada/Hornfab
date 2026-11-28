"""M1 research snapshot acceptance tests (ADR: docs/research/research_view_2026-11-27/).

Dose-experiment tests read the REAL committed 2026-11-25 evidence through git (``HEAD``);
cohort, determinism and canary tests use small synthetic run trees in ``tmp_path`` because
``runs/`` is not committed. No solver, no GPU, no network.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from hornlab_search.research import build as B
from hornlab_search.research import findings as F
from hornlab_search.research import sources as S
from hornlab_search.research.provenance import Registry, parse_utc

REPO = Path(__file__).resolve().parents[1]
CUT = parse_utc("2026-11-25T23:59:59Z")


@pytest.fixture(scope="module")
def head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True,
                          check=True).stdout.strip()


@pytest.fixture(scope="module")
def dose(head):
    return S.dose_experiment(Registry(REPO, head), CUT)


def _row(dose, job):
    return next(r for r in dose["rows"] if r["job"] == job and r["family"] == "rolled")


# ------------------------------------------------------------------ A1 provenance of numbers

_STRUCTURAL = {"line", "claim_line", "n_pairs", "n_identities", "bytes", "lines_total",
               "lines_included", "lines_after_cutoff", "lines_unparseable", "objective_version",
               "split", "counts", "scan", "n_sources", "train_n", "eval_n"}


def _unsourced_numbers(obj, path="", parent=None, out=None):
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _STRUCTURAL:
                continue
            _unsourced_numbers(v, f"{path}/{k}", obj, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _unsourced_numbers(v, f"{path}/{i}", None, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if not (parent and ("src" in parent or "calc" in parent) and path.endswith("/v")):
            out.append(path)
    return out


def test_a1_every_dose_number_is_sourced(dose):
    assert _unsourced_numbers(dose) == []


def test_a1_every_src_has_exactly_one_pointer(dose):
    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("src"), str):
                assert o["src"].count("#") == 1, o["src"]
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(dose)


def test_a1_cohort_and_mesh_numbers_are_sourced(tmp_path, head):
    _fake_runs(tmp_path)
    inv = S.cohort_inventory(Registry(tmp_path, "0" * 40), CUT)
    mesh = S.mesh_fidelity(Registry(REPO, head))
    assert inv["cohorts"] and mesh["rows"]
    assert _unsourced_numbers(inv["cohorts"]) == []
    assert _unsourced_numbers(mesh["rows"]) == []


# ------------------------------------------------------------------ A2 attribution reconciles

def test_a2_attribution_residual_is_exact(dose):
    rows = [r for r in dose["rows"] if r["attribution"].get("status") == "ok"]
    assert len(rows) >= 20
    for r in rows:
        a = r["attribution"]
        assert a["residual"]["v"] == a["stored_total"]["v"] - a["sum"]["v"], r["id"]
        assert abs(a["residual"]["v"]) < 1e-9, r["id"]
        assert a["objective_version"] == 11
        assert a["stored_total"]["v"] == r["J"]["v"]   # the stored total IS the stored J


def test_a2_attribution_uses_the_objective_resolver(dose):
    a = _row(dose, "rolled_bb_h065")["attribution"]
    keys = {c["key"] for c in a["components"]}
    assert {"cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth"} <= keys   # v11 CD terms present
    assert "scalar_v11" in a["resolver"] or "objective.cd" in a["resolver"]


# ------------------------------------------------------------------ A3 decision derived from data

def test_a3_lowest_j_dose_fails_and_throat_correction_passes(dose):
    h065, th025 = _row(dose, "rolled_bb_h065"), _row(dose, "rolled_bb_h065_th025")
    assert h065["verdict"]["v"] == "fail" and h065["verdict"]["failed_rules"] == ["min_re_z_ok"]
    assert th025["verdict"]["v"] == "pass"
    assert h065["J"]["v"] < th025["J"]["v"]
    assert h065["knobs"]["g_bb_throat_frac"]["v"] == 0.15 and th025["knobs"]["g_bb_throat_frac"]["v"] == 0.25
    found = {f["kind"]: f for f in F.dose_findings(dose)}
    mp = found["matched_pair"]
    assert mp["evidence"] == [h065["id"], th025["id"]]
    assert abs(mp["cells"]["delta_J"]["v"] - (th025["J"]["v"] - h065["J"]["v"])) < 1e-15
    assert "scalar_not_gate" in found and "attribution_reconciles" in found


def test_a3_refined_mesh_rows_are_a_separate_fidelity(dose):
    epw9 = _row(dose, "rolled_bb_h050_epw9")
    assert epw9["epw"]["v"] == 9.0 and _row(dose, "rolled_bb_h050")["epw"]["v"] == 6.0
    for f in F.dose_findings(dose):        # no finding mixes mesh fidelities
        if f["kind"] in ("matched_pair", "scalar_not_gate"):
            assert not any("epw9" in e for e in f["evidence"])


# ------------------------------------------------------------------ A4 cutoff excludes the future

def test_a4_cutoff_drops_later_batches_and_records_them(head):
    reg = Registry(REPO, head)
    early = S.dose_experiment(reg, parse_utc("2026-11-25T15:39:00Z"))
    jobs = {r["job"] for r in early["rows"]}
    assert "rolled_bb_h065" in jobs and "rolled_bb_h065_th025" not in jobs
    excluded = {e["what"] for e in reg.exclusions if e["reason"] == "after cutoff"}
    assert "dose:rolled:rolled_bb_h065_th025" in excluded
    for f in F.dose_findings(early):             # no finding may cite an excluded row
        assert "dose:rolled:rolled_bb_h065_th025" not in f["evidence"]


# ------------------------------------------------------------------ synthetic run tree

def _run(root: Path, name: str, cfg_name: str, brief: dict, rows: list[dict], version=11, mode="screen"):
    d = root / "runs" / name
    d.mkdir(parents=True)
    (d / "run.json").write_text(json.dumps({
        "objective_version": version, "config_name": cfg_name, "mode": mode, "backend": "beat_cuda",
        "started_utc": rows[0]["created_utc"] if rows else "2026-11-24T00:00:00Z",
        "config_sha": "abc", "config": {"brief": brief}}), encoding="utf-8")
    (d / "search.ndjson").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _rows(n, j0=3.0, t="2026-11-24T0{}:00:00Z", fail=0):
    out = [{"ok": True, "objective": j0 + i / 10, "design_hash": f"h{i:03d}", "created_utc": t.format(i % 10)}
           for i in range(n)]
    out += [{"ok": False, "kind": "invalid_geometry", "objective": None, "created_utc": t.format(0)}] * fail
    return out


def _fake_runs(root: Path):
    _run(root, "20261124T000000Z-screen-aaaaaa", "alpha", {"name": "b1"}, _rows(5, fail=2))
    _run(root, "20261124T010000Z-screen-bbbbbb", "alpha", {"name": "b2"}, _rows(3))
    _run(root, "20261124T020000Z-screen-cccccc", "beta", {"name": "b1"}, _rows(4))
    _run(root, "20261124T030000Z-screen-dddddd", "old", {"name": "b1"}, _rows(4), version=7)
    plan = root / "runs" / "v11_bo_day_planning"
    (plan / "cohort_beta_2026-11-24").mkdir(parents=True)
    (plan / "cohort_beta_2026-11-24" / "offline_scores.json").write_text(json.dumps(
        {"cohort": {"native_config": "beta"}, "counts": {"exact_complete": 1}, "selection": {"available": 4},
         "no_backend_calls": True}), encoding="utf-8")
    bh = S.brief_hash({"name": "b1"})
    (plan / "cohort_beta_2026-11-24" / "catalog.csv").write_text(f"brief_hash,x\n{bh},1\n", encoding="utf-8")
    (plan / "cohort_alpha_2026-11-24").mkdir(parents=True)
    (plan / "cohort_alpha_2026-11-24" / "offline_scores.json").write_text(json.dumps(
        {"cohort": {"native_config": "alpha"}, "counts": {"exact_complete": 5}, "selection": {"available": 5},
         "no_backend_calls": True}), encoding="utf-8")
    (plan / "cohort_alpha_2026-11-24" / "catalog.csv").write_text(f"brief_hash,x\n{bh},1\n", encoding="utf-8")
    before = CUT.timestamp() - 86400            # admission artifacts are placed by mtime
    for f in plan.rglob("*.*"):
        os.utime(f, (before, before))


# ------------------------------------------------------------------ A7/A8 strict grouping, states

def test_a7_config_name_with_two_briefs_splits(tmp_path):
    _fake_runs(tmp_path)
    inv = S.cohort_inventory(Registry(tmp_path, "0" * 40), CUT)
    alpha = [c for c in inv["cohorts"] if c["config_name"] == "alpha"]
    assert len(alpha) == 2 and all(c["mixed_identity"] for c in alpha)
    assert {c["unique_designs"]["v"] for c in alpha} == {5, 3}
    assert inv["scan"]["other_version"] == 1            # the v7 run is counted, not pooled
    a5 = next(c for c in alpha if c["unique_designs"]["v"] == 5)
    assert a5["failed"]["invalid_geometry"]["v"] == 2 and a5["failed_total"]["v"] == 2   # negative evidence kept


def test_a8_status_vocabulary_is_distinct(tmp_path):
    _fake_runs(tmp_path)
    inv = S.cohort_inventory(Registry(tmp_path, "0" * 40), CUT)
    st = {(c["config_name"], c["brief_hash"]): c["status"] for c in inv["cohorts"]}
    bh1, bh2 = S.brief_hash({"name": "b1"}), S.brief_hash({"name": "b2"})
    assert st[("beta", bh1)] == "replay_mismatch"       # 1/4 replay
    assert st[("alpha", bh1)] == "needs_admission"      # replay ok, holdout missing
    assert st[("alpha", bh2)] == "not_evaluated"        # no artifact for this identity
    beta = next(c for c in inv["cohorts"] if c["config_name"] == "beta")
    assert beta["admission"]["holdout"]["verdict"]["status"] == "missing"


def test_a8_claims_reconcile_and_conflicts_surface(tmp_path):
    _fake_runs(tmp_path)
    inv = S.cohort_inventory(Registry(tmp_path, "0" * 40), CUT)
    claims = {"claims": [{"config_name": "beta", "line": 7, "unique": {"v": 4, "src": "x#line:7"},
                          "claimed_status": "pilot_eligible"}]}
    rec = S.reconcile_claims(claims, inv)
    assert rec[0]["result"] == "status_conflict" and rec[0]["artifact_status"] == "replay_mismatch"
    assert "claim_conflict" in {f["kind"] for f in F.cohort_findings(inv, rec, {"v": 1, "src": "x.md#line:1/text:x"})}


# ------------------------------------------------------------------ A5/A6 frozen, deterministic

def test_a5_a6_snapshot_is_deterministic_and_frozen(tmp_path):
    _fake_runs(tmp_path)
    s1 = B.build_snapshot(tmp_path, "2026-11-25T23:59:59Z", "0" * 40)
    s2 = B.build_snapshot(tmp_path, "2026-11-25T23:59:59Z", "0" * 40)
    assert B._dumps(s1) == B._dumps(s2)
    # a row appended AFTER the cutoff does not change the snapshot
    nd = tmp_path / "runs" / "20261124T020000Z-screen-cccccc" / "search.ndjson"
    with nd.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ok": True, "objective": 1.0, "design_hash": "late",
                             "created_utc": "2026-11-26T05:00:00Z"}) + "\n")
    s3 = B.build_snapshot(tmp_path, "2026-11-25T23:59:59Z", "0" * 40)
    assert s3["snapshot_id"] == s1["snapshot_id"]
    # a changed input row before the cutoff does
    lines = nd.read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace('"objective": 3.0', '"objective": 2.5')
    nd.write_text("\n".join(lines) + "\n", encoding="utf-8")
    s4 = B.build_snapshot(tmp_path, "2026-11-25T23:59:59Z", "0" * 40)
    assert s4["snapshot_id"] != s1["snapshot_id"]
    # missing committed sources are explicit, not silent
    assert S.DOSE_DIR + "/results.json" in s1["missing_evidence"]["sources_missing"]


# ------------------------------------------------------------------ A9 replicate negative control

def test_a9_canary_replicates_and_rank(tmp_path):
    for label, rel in S.CANARY_PACKAGES.items():
        for mode, rows in (("screen", [("d1", 5.12), ("d2", 5.38)]), ("verify", [("d1", 4.79), ("d2", 5.51)])):
            d = tmp_path / S.CANARY / rel / mode
            d.mkdir(parents=True)
            (d / "run.json").write_text(json.dumps({"config": {"brief": {"m": mode}}}), encoding="utf-8")
            eps = 2e-6 if label == "rehearsal" else 0.0
            (d / "search.ndjson").write_text("".join(json.dumps(
                {"ok": True, "objective": j + eps, "design_hash": h, "created_utc": "2026-11-24T09:00:00Z"}) + "\n"
                for h, j in rows), encoding="utf-8")
    can = S.canary(Registry(tmp_path, "0" * 40), CUT)
    assert can["rank_preserved"]["v"] is True and can["n_pairs"] == 2
    assert can["identities"]["screen_brief"] != can["identities"]["verify_brief"]
    assert len(can["replicates"]) == 4 and can["replicate_max_abs_delta"]["v"] < 1e-5


# ------------------------------------------------------------------ A10 html is a view of the JSON

def test_a10_html_embeds_the_snapshot_bytes(tmp_path):
    _fake_runs(tmp_path)
    snap = B.build_snapshot(tmp_path, "2026-11-25T23:59:59Z", "0" * 40)
    out = tmp_path / "out"
    B.write_snapshot(snap, out)
    text = (out / "snapshot.json").read_text(encoding="utf-8")
    html = (out / "index.html").read_text(encoding="utf-8")
    assert text.replace("</", "<\\/") in html
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8"))["snapshot_id"] == snap["snapshot_id"]
    tpl = B.TEMPLATE.read_text(encoding="utf-8")
    for literal in ("4.676", "4.679", "0.864", "0.993", "291", "Compact400"):   # mockup numbers
        assert literal not in tpl


# ------------------------------------------------------------------ hardening (2026-11-27 senior pass)

def _resolve(src: str, head: str):
    """Mechanically resolve one ``src`` against the committed bytes (the agent-guide pointer grammar)."""
    import csv
    import io

    import yaml
    path, ptr = src.split("#", 1)
    raw = subprocess.run(["git", "show", f"{head}:{path}"], cwd=REPO, capture_output=True, check=True).stdout
    text = raw.decode("utf-8-sig")
    if ptr.startswith("line:"):
        head_, _, rest = ptr[5:].partition("/")
        line = text.splitlines()[int(head_) - 1]
        if rest.startswith("text:"):
            assert rest[5:] in line, (src, line)
            return rest[5:]
        if rest.startswith("col:"):
            hdr_line = next(l for l in text.splitlines()[: int(head_)][::-1] if l.startswith("| ") and "---" not in l
                            and rest[4:] in [c.strip() for c in l.strip("|").split("|")])
            cols = [c.strip() for c in hdr_line.strip("|").split("|")]
            return [c.strip() for c in line.strip("|").split("|")][cols.index(rest[4:])].strip("*`")
        return json.loads(line)[rest]
    if ptr.startswith("row:"):
        n, _, col = ptr[4:].partition("/")
        return list(csv.DictReader(io.StringIO(text)))[int(n) - 1][col]
    node = yaml.safe_load(text) if path.endswith((".yaml", ".yml")) else json.loads(text)
    for part in ptr.strip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def _cells(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("src"), str) and "v" in obj and obj.get("status") is None:
            yield obj
        for v in obj.values():
            yield from _cells(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _cells(v)


def test_every_committed_src_resolves_mechanically(dose, head):
    reg = Registry(REPO, head)
    claims = S.handoff_claims(reg)
    mesh = S.mesh_fidelity(reg)
    cells = [c for c in _cells([dose, claims, mesh]) if not c["src"].startswith("runs/")]
    assert len(cells) > 300
    for c in cells:
        got = _resolve(c["src"], head)
        if "/text:" in c["src"]:
            continue                                          # phrase anchor: presence checked in _resolve
        if isinstance(c["v"], float) and isinstance(got, str):
            assert float(got) == c["v"], c["src"]
        elif isinstance(c["v"], int) and not isinstance(c["v"], bool) and isinstance(got, str):
            assert int(got) == c["v"], c["src"]
        else:
            assert got == c["v"], c["src"]


def test_run_time_is_a_calculation_not_a_raw_cell(dose):
    r = _row(dose, "rolled_bb_h065")
    assert "calc" in r["time"] and r["time"]["v"] == "2026-11-25T13:11:11Z"


def test_refined_mesh_rows_use_the_matched_fidelity_control(dose):
    r = _row(dose, "rolled_bb_h065_th025_epw9")
    v = r["verdict"]
    assert v["v"] == "pass" and "mesh_delta_rule" in v["rules"]
    for k in ("V_HF_not_narrower", "min_re_z_ok", "J_ok"):
        assert "control_epw9" in " ".join(v["rules"][k]["inputs"]), k          # epw-9 control, not epw-6
    assert v["epw6_control_checks"]["note"].startswith("analyze.py compared")
    ctl9 = next(x for x in dose["rows"] if x["job"] == "control_epw9")
    assert ctl9["is_control"] and ctl9["epw"]["v"] == 9.0 and ctl9["attribution"]["status"] == "missing"


def test_unknown_pass_verdict_is_not_promoted():
    adm = {"replay": {"exact_complete": {"v": 10}, "available": {"v": 10}},
           "holdout": {"verdict": {"v": "PASS_SOMETHING_NEW"}}}
    assert S._cohort_status(adm) == "unknown"
    adm["holdout"]["verdict"]["v"] = "PASS_FOR_EXPLORATORY_PILOT"
    assert S._cohort_status(adm) == "pilot_eligible"


def test_corroboration_checks_j_and_config(tmp_path):
    run = tmp_path / "runs" / "20261125T131111Z-verify-1f727a"
    run.mkdir(parents=True)
    cfg = {"brief": {"name": "b"}, "mesh": {"epw": 6}}
    (run / "best.json").write_text(json.dumps({"objective": 4.5}), encoding="utf-8")
    (run / "run.json").write_text(json.dumps({"config": cfg}), encoding="utf-8")
    reg = Registry(tmp_path, "0" * 40)
    row = {"J": {"v": 4.5, "src": "x#/J"}, "config": "c.yaml"}
    ok = S._corroborate(reg, tmp_path, {"run": r"C:\x\runs" + "\\" + run.name}, row, cfg)   # Windows path as recorded
    assert ok["status"] == "match" and ok["config_equal"]["v"] is True
    bad = S._corroborate(reg, tmp_path, {"run": run.name}, row, {**cfg, "mesh": {"epw": 9}})
    assert bad["status"] == "mismatch" and bad["config_equal"]["v"] is False


def test_fidelity_policy_splits_mesh_changes(tmp_path):
    _fake_runs(tmp_path)
    d = tmp_path / "runs" / "20261124T040000Z-screen-eeeeee"
    _run(tmp_path, d.name, "beta", {"name": "b1"}, _rows(2))
    meta = json.loads((d / "run.json").read_text(encoding="utf-8"))
    meta["config"]["mesh"] = {"rear_res_factor": 1.5}
    (d / "run.json").write_text(json.dumps(meta), encoding="utf-8")
    inv = S.cohort_inventory(Registry(tmp_path, "0" * 40), CUT)
    beta = [c for c in inv["cohorts"] if c["config_name"] == "beta"]
    assert len(beta) == 2 and len({c["fidelity_policy"] for c in beta}) == 2


def test_brief_hash_matches_the_canonical_rule():
    from hornlab_search.design.generated import brief_hash as canonical
    b = {"name": "x", "path": "ignored.yaml", "target": {"h": [1, 2]}}
    assert S.brief_hash(b) == canonical(b)


def test_findings_serve_three_audiences(dose, tmp_path):
    _fake_runs(tmp_path)
    finds = F.dose_findings(dose)
    for f in finds:
        assert f["plain"] and not any(t in f["plain"] for t in ("Re(z)", "J ", "epw", "_bb_"))
        assert f["scope"] and f["strength"]
        for s in f["next_steps"]:
            assert isinstance(s["needs_gpu"], bool) and isinstance(s["needs_owner_approval"], bool)
    snap = B.build_snapshot(tmp_path, "2026-11-25T23:59:59Z", "0" * 40)
    out = tmp_path / "out"
    B.write_snapshot(snap, out)
    summ = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summ["snapshot_id"] == snap["snapshot_id"] and summ["plain_summary"]
    guide = (out / "AGENT_GUIDE.md").read_text(encoding="utf-8")
    assert "Never compare or rank J" in guide and "## Suggested next steps" in guide
    assert not list(out.glob("*.tmp"))
    # GPU steps sort after CPU steps and always ask for the owner
    steps = summ["next_steps"]
    assert steps == sorted(steps, key=lambda s: (s["needs_gpu"], s["needs_owner_approval"], s["finding_kind"], s["what"]))
    assert all(s["needs_owner_approval"] for s in steps if s["needs_gpu"])


def test_optimizer_evidence_adapter_respects_cutoff_and_totals(tmp_path, monkeypatch):
    _fake_runs(tmp_path)
    # a beta row after the cutoff: that run must not be carded (the tool reads whole runs)
    nd = tmp_path / "runs" / "20261124T020000Z-screen-cccccc" / "search.ndjson"
    with nd.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ok": True, "objective": 1.0, "design_hash": "z", "created_utc": "2026-11-26T01:00:00Z"}) + "\n")
    reg = Registry(tmp_path, "0" * 40)
    inv = S.cohort_inventory(reg, CUT)
    seen = []

    class FakeOE:
        @staticmethod
        def build_report(run_dirs):
            seen.extend(Path(p).name for p in run_dirs)
            return {"schema": "optimizer-evidence-v1", "advisory_only": True, "dispatches_work": False,
                    "run_cards": [{"run_id": Path(p).name,
                                   "key_numbers": {"attempts_new": 10, "actual_bem_seconds": 1800.0,
                                                   "recorded_total_seconds": 2000.0, "failure_fraction": 0.1},
                                   "outcome_counts": {"valid": 9}, "walls": [{"key": "g_a", "wall_lo": True}],
                                   "continuation": {"advice": "x"}, "progress": {"stalled": False}} for p in run_dirs],
                    "cross_run": {"compatible_for_inference": True, "blocking": []}, "decision": {}, "alternatives": []}

    monkeypatch.setattr(S, "_load_optimizer_evidence", lambda root: FakeOE)
    out = S.optimizer_evidence(reg, inv, {"v": 1})
    assert out["status"] == "ok"
    beta = next(c for c in inv["cohorts"] if c["config_name"] == "beta")
    assert beta["optimizer_evidence"]["status"] == "missing"          # its only run continues past the cutoff
    assert "20261124T020000Z-screen-cccccc" not in seen
    alpha = next(c for c in inv["cohorts"] if c["config_name"] == "alpha" and c["unique_designs"]["v"] == 5)
    o = alpha["optimizer_evidence"]
    assert o["status"] == "ok" and o["totals"]["bem_hours"]["v"] == 0.5 and o["totals"]["attempts"]["v"] == 10
    assert o["runs"][0]["pinned_walls"] == ["g_a"]
    low = S.optimizer_evidence(Registry(tmp_path, "0" * 40), S.cohort_inventory(Registry(tmp_path, "0" * 40), CUT),
                               {"v": 10_000})
    assert low["status"] == "ok"
