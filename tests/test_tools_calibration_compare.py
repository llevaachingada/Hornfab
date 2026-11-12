"""Tests for tools/calibration/compare_calibration.py (C.2) -- synthetic fixtures only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "calibration"))

import compare_calibration as cmp_mod  # noqa: E402
import plan_calibration as plan  # noqa: E402  (same constants source)

from hornlab_search.config import freq_grid  # noqa: E402

DAY = "2026-11-12"
NIGHT = f"calibration_{DAY}"
BAND = (700.0, 5500.0)
FREQS = freq_grid(700.0, 5500.0, 12)          # synthetic verify-grid stand-in
H1, H2, H3, H4 = "1111111111111111", "2222222222222222", "3333333333333333", "4444444444444444"

SCREEN_J = {H1: 0.50, H2: 0.60, H3: 0.70, H4: 0.80}


def _base_metrics() -> dict:
    return {
        "freqs_hz": list(FREQS),
        "bw_h_deg": [40.0] * len(FREQS),
        "bw_v_deg": [30.0] * len(FREQS),
        "di_db": [8.0] * len(FREQS),
        "di_source": "balloon",
        "ripple_h_db": [0.5] * len(FREQS),
        "ripple_v_db": [0.4] * len(FREQS),
        "on_axis_db": [90.0] * len(FREQS),
        "z_throat_real": [0.4] * len(FREQS),
        "scalars": {},
    }


def _variant_metrics(base: dict, *, di_shift: float = 0.0, bw_shift: float = 0.0,
                     z_shift: float = 0.0) -> dict:
    m = json.loads(json.dumps(base))
    for k, shift in (("di_db", di_shift), ("z_throat_real", z_shift)):
        m[k] = [v + shift for v in m[k]]
    m["bw_h_deg"] = [v + bw_shift for v in m["bw_h_deg"]]
    return m


def _run_dir(root: Path, name: str) -> Path:
    """The base run dir per source run. Each variant gets its OWN verify dir below it
    (``<base>__<variant>/verify``), matching the planner layout: the night job runs
    ``verify --run <variants_dir>/<run>__<variant>``, so the runner records that dir --
    variants never share one verify/search.ndjson."""
    run = root / "runs" / name
    run.mkdir(parents=True, exist_ok=True)
    return run


def _write_verify(run: Path, variant: str, metrics: dict, j_by_hash: dict) -> None:
    verify = run.parent / f"{run.name}__{variant}" / "verify"
    verify.mkdir(parents=True, exist_ok=True)
    with open(verify / "search.ndjson", "w", encoding="utf-8", newline="\n") as fh:
        for n, (h, j) in enumerate(sorted(j_by_hash.items()), 1):
            fh.write(json.dumps({
                "n": n, "mode": "verify", "design_hash": h, "family": "OSSE",
                "params": {}, "objective": j, "ok": True, "error": "",
                "metrics": metrics,
            }, allow_nan=False, separators=(",", ":")) + "\n")


@pytest.fixture()
def night(tmp_path):
    """A synthetic night dir: plan YAML + summary.jsonl + four verify dirs.

    All variants score the same J ORDER as the screen except one design in dist_10m, and every
    band-split/epw metric is IDENTICAL to the control (PASS), while dist_10m shifts DI by +0.5 dB
    (FAIL: DI limit 0.2) and dist_2m is identical.
    """
    root = tmp_path
    base = _base_metrics()
    runs = {}
    # ---- run 1: metrics identical across variants (all PASS)
    run = _run_dir(root, "20261112T010101Z-screen-abcdef")
    _write_verify(run, "single_mesh", base, {h: j for h, j in SCREEN_J.items()})
    _write_verify(run, "band_split", _variant_metrics(base), {h: j for h, j in SCREEN_J.items()})
    _write_verify(run, "dist_2m", _variant_metrics(base), {h: j for h, j in SCREEN_J.items()})
    # dist_10m: same metrics (PASS) but reordered J? keep same order, just shifted J values
    _write_verify(run, "dist_10m", _variant_metrics(base),
                  {h: j + 0.05 for h, j in SCREEN_J.items()})
    _write_verify(run, "epw_6", _variant_metrics(base), {h: j for h, j in SCREEN_J.items()})
    _write_verify(run, "epw_9", _variant_metrics(base), {h: j + 0.01 for h, j in SCREEN_J.items()})
    runs["20261112T010101Z-screen-abcdef"] = run
    # ---- run 2: dist_10m moves DI by 0.5 dB (FAIL) and flips H1/H2 order (rho < 1)
    run2 = _run_dir(root, "20261112T020202Z-screen-bcdef1")
    j2 = {h: j for h, j in SCREEN_J.items()}
    j2_flipped = dict(j2)
    j2_flipped[H1], j2_flipped[H2] = j2[H2], j2[H1]     # rank flip of the top two
    _write_verify(run2, "single_mesh", base, j2)
    _write_verify(run2, "band_split", _variant_metrics(base), j2)
    _write_verify(run2, "dist_2m", _variant_metrics(base), j2)
    _write_verify(run2, "dist_10m", _variant_metrics(base, di_shift=0.5), j2_flipped)
    _write_verify(run2, "epw_6", _variant_metrics(base), j2)
    _write_verify(run2, "epw_9", _variant_metrics(base), j2)
    runs["20261112T020202Z-screen-bcdef1"] = run2

    # ---- plan yaml with metadata (written by plan_calibration in real life)
    designs_meta = []
    for run_name in sorted(runs):
        for h, j in SCREEN_J.items():
            designs_meta.append({"hash": h, "screen_j": j, "run": str(runs[run_name]),
                                 "job_run": run_name})
    doc = {
        "night": NIGHT, "lane": "gpu",
        "calibration": {
            "date": DAY, "thresholds": dict(plan.THRESHOLDS),
            "aspect_pairs": {k: list(v) for k, v in plan.ASPECT_PAIRS.items()},
            "variants_dir": "scratch/unused", "runs": {
                str(runs[n]): {"band_lo_hz": BAND[0], "band_hi_hz": BAND[1]} for n in runs},
            "designs": designs_meta},
        "jobs": [{"id": f"c_{v}__{n}", "kind": "command", "argv": ["x"]}
                 for n in sorted(runs) for v in plan.VARIANT_ORDER],
    }
    (root / "night.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    (root / NIGHT / "summary.jsonl").parent.mkdir(parents=True, exist_ok=True)
    with open(root / NIGHT / "summary.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        for n in sorted(runs):
            for v in plan.VARIANT_ORDER:
                fh.write(json.dumps({"id": f"c_{v}__{n}", "kind": "command", "seconds": 1.0,
                                     "exit_code": 0,
                                     "run_dir": str(runs[n].parent
                                                    / f"{runs[n].name}__{v}" / "verify"),
                                     "evals_ndjson": 4, "best_J": None, "note": "ok"},
                                    separators=(",", ":")) + "\n")
    return root


def test_compare_pass_fail_and_spearman(night, tmp_path):
    out = tmp_path / "cmp"
    collected = cmp_mod.collect(night / NIGHT, night / "night.yaml")
    report = cmp_mod.compare(collected)
    out.mkdir()
    cmp_mod.write_md(out / "COMPARE.md", report, report["thresholds"])
    (out / "compare.json").write_text(json.dumps(report, indent=1, allow_nan=False), "utf-8")

    run1 = report["runs"]["20261112T010101Z-screen-abcdef"]
    run2 = report["runs"]["20261112T020202Z-screen-bcdef1"]
    # run 1: every metric identical -> every pair PASS
    for aspect, pair in run1["pairs"].items():
        assert pair["pass_all"], aspect
        assert pair["n_designs"] == 4
        for d in pair["designs"]:
            assert d["pass"] and d["re_z"] == pytest.approx(0.0, abs=1e-12)
    # run 2: mesh_policy + mesh_resolution PASS, observation_distance FAILS on DI
    assert run2["pairs"]["mesh_policy"]["pass_all"]
    assert run2["pairs"]["mesh_resolution"]["pass_all"]
    dist = run2["pairs"]["observation_distance"]
    assert not dist["pass_all"]
    by_hash = {d["design"]: d for d in dist["designs"]}
    for h in (H1, H2, H3, H4):        # the +0.5 dB shift hits every design
        assert by_hash[h]["verdict"]["di_db"]["pass"] is False
        assert by_hash[h]["di_db"] == pytest.approx(0.5)
        assert by_hash[h]["verdict"]["re_z"]["pass"] is True
        assert by_hash[h]["verdict"]["beamwidth_deg"]["pass"] is True
    # all_pairs verdict reflects run 2's failure
    assert report["all_pairs_pass"] is False

    # ---- Spearman: run 1 rankings unchanged -> screen-vs-verify rho = 1.0 for every variant
    for key, s in run1["spearman"].items():
        assert s["rho"] == pytest.approx(1.0), key
    # run 2: dist_10m flipped the top two => rho < 1 there; identical variants stay at 1.0
    assert run2["spearman"]["screen__vs__dist_10m"]["rho"] == pytest.approx(0.8)
    assert run2["spearman"]["screen__vs__single_mesh"]["rho"] == pytest.approx(1.0)
    assert run2["spearman"]["dist_2m__vs__dist_10m"]["rho"] == pytest.approx(0.8)
    # screen ranking verdict: run 1 survives (all rho 1.0), run 2 does not (0.8 < criterion 1.0 set
    # to SCREEN_SURVIVES_RHO = 0.8 -> 0.8 >= 0.8 survives; the FLIPPED variant pair is what fails)
    assert run1["screen_ranking"]["survives"] is True
    assert run2["screen_ranking"]["survives"] is True
    # the dist_2m-vs-dist_10m rank agreement is the signal the screen hides:
    assert run2["spearman"]["dist_2m__vs__dist_10m"]["rho"] < 1.0

    # ---- finalists ranked by verify J only (control variant)
    ranked = run1["finalists_by_verify_j"]
    assert [e["design"] for e in ranked[:2]] == [H1, H2]
    assert ranked[0]["verify_j"] == pytest.approx(0.50)
    assert ranked[0]["screen_j"] == pytest.approx(0.50)

    md = (out / "COMPARE.md").read_text(encoding="utf-8")
    assert "FAIL" in md and "PASS" in md and "Spearman" in md


def test_spearman_ties_and_edge_cases():
    assert cmp_mod.spearman([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)
    assert cmp_mod.spearman([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(-1.0)
    assert cmp_mod.spearman([1.0, 1.0, 2.0], [1.0, 2.0, 1.0]) == pytest.approx(-0.5)
    assert cmp_mod.spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None
    assert cmp_mod.spearman([1.0, float("nan")], [1.0, 2.0]) is None
    assert cmp_mod.spearman([1.0], [1.0]) is None


def test_collect_falls_back_to_variants_dir_layout(tmp_path):
    """summary.jsonl with run_dir=null: the documented variants_dir layout is used."""
    root = tmp_path
    run = _run_dir(root, "runs-x")  # noqa: F841 - base dir; the variant dir is what matters
    vdir = root / "scratch" / "calibration_v" / "runs-x__single_mesh"
    # _write_verify derives the variant dir from the base name: runs-x -> runs-x__single_mesh
    _write_verify(root / "scratch" / "calibration_v" / "runs-x",
                  "single_mesh", _base_metrics(), {H1: 0.4})
    assert (vdir / "verify" / "search.ndjson").is_file()  # fixture sanity
    (root / "night.yaml").write_text(yaml.safe_dump({
        "night": "calib", "jobs": [{"id": "c_single_mesh__runs-x", "kind": "command"}],
        "calibration": {"thresholds": dict(plan.THRESHOLDS),
                        "aspect_pairs": {k: list(v) for k, v in plan.ASPECT_PAIRS.items()},
                        "variants_dir": "scratch/calibration_v",
                        "runs": {}, "designs": []}}), encoding="utf-8")
    (root / "calib" / "summary.jsonl").parent.mkdir(parents=True)
    with open(root / "calib" / "summary.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"id": "c_single_mesh__runs-x", "kind": "command", "exit_code": 0,
                             "run_dir": None}, separators=(",", ":")) + "\n")
    collected = cmp_mod.collect(root / "calib", root / "night.yaml")
    (job,) = collected["jobs"]
    assert job["designs_found"] == [H1]
    assert job["verify_dir"].endswith("runs-x__single_mesh\\verify") or \
        job["verify_dir"].endswith("runs-x__single_mesh/verify")


def test_collect_errors_without_night_dir(tmp_path):
    with pytest.raises(ValueError, match="not a directory"):
        cmp_mod.collect(tmp_path / "does-not-exist")


def test_missing_plan_file_uses_default_pairing(tmp_path):
    """Without metadata, defaults (ASPECT_PAIRS/THRESHOLDS) still pair the variants."""
    root = tmp_path
    run = _run_dir(root, "r1")
    _write_verify(run, "single_mesh", _base_metrics(), {H1: 0.4})
    _write_verify(run, "band_split", _variant_metrics(_base_metrics(), di_shift=0.3), {H1: 0.4})
    (root / "n" / "summary.jsonl").parent.mkdir(parents=True)
    with open(root / "n" / "summary.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        for v in ("single_mesh", "band_split"):
            fh.write(json.dumps({"id": f"c_{v}__r1", "kind": "command", "exit_code": 0,
                                 "run_dir": str(run.parent / f"r1__{v}" / "verify")},
                                separators=(",", ":")) + "\n")
    collected = cmp_mod.collect(root / "n", None)
    assert collected["plan_file"] is None
    report = cmp_mod.compare(collected)
    pair = report["runs"]["r1"]["pairs"]["mesh_policy"]
    assert pair["pass_all"] is False            # DI 0.3 > 0.2 limit, caught via defaults
    assert run.is_dir() and (root / "n" / "summary.jsonl").is_file()  # fixture sanity
