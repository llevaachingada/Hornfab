"""P4 compare data layer: recorded A/B acceptance, mismatch refusals, no solver.

Two layers:

* **live store** — the recorded motor A/B and G6 offset cases, skipped with a reason when the
  gitignored store is not on this machine (mirrors ``test_gui_hw_screen.py::_live_store``).
  These tests pin the ``data_hw_compare`` numbers to the recorded evidence files
  (``motor_axis_ab.json`` / ``g6_paired_delta.json``) and to the numbers quoted in
  ``docs/research/system_woofer_2026-11-18/FIRST_BEM_EVIDENCE.md``.
* **synthetic store** — a throwaway ``tmp_path`` store built from the committed BL result
  fixture, for the refusals and the no-solver guarantee.

Recorded statistic (read from the evidence, not the generic brief)
-------------------------------------------------------------------
``FIRST_BEM_EVIDENCE.md`` computes every paired delta as

    max|p_a(f) - p_b(f)| over the band  /  max|p_b(f)| over the same band

(``max_abs_delta_pa / max|B4|`` for G6; the motor rows are the same shape). That is
``data_hw_compare.relative_delta_percent`` divided by 100. The generic GUI brief's
per-frequency symmetric ratio does **not** reproduce the recorded numbers, so it is not used
for ``max_relative_delta_percent`` (see the module docstring).

The evidence split the spectrum as LF 200-500 Hz and XO 600-1200 Hz; the GUI's display bands
are LF < 500 / XO 500-1500 / HF > 1500 Hz. The LF display band equals the recorded LF band on
this grid; the recorded XO statistic is reproduced on its own 600-1200 Hz band with the same
statistic helper, because the display band is a different choice.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.gui import data_hw as HW  # noqa: E402
from hornlab_search.gui import data_hw_compare as CMP  # noqa: E402
from hornlab_search.gui.data import clean  # noqa: E402
from hornlab_search.system.boundarylab import bl_results as R  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FIXTURE_RUN = Path(__file__).resolve().parent / "fixtures" / "bl_results" / "reference_run"

MOTOR_REAL = "bl_motor12pr/20261119T010548Z-motor12pr-17944-fa37ab5e"
MOTOR_DEMO = "bl_motor12pr_demo_twin/20261119T013209Z-ref_case-11372-452574f9"
G6 = "bl_g6_offset30/20261118T235110Z-assembly-21668-c17f7cf6"
# The brief names the staged 20 mm project as the reference; its solved `run/` lives in the wide
# study that solved it (the wide manifest's `project` points at the staged project, see
# FIRST_BEM_EVIDENCE.md G4). `hw_compare` requires a solved run, so compare against that run.
G6_REF_STAGED = "bl_horn_assembly/20261118T224519Z-assembly-11000-4a85a0f8"
G6_REF_WIDE = "bl_smoke_wide/20261118T231115Z-g4wide-56836-b5d6490a"


# --------------------------------------------------------------------------- live store helper

def _live_store(*keys: str) -> Path:
    candidates: list[Path] = []
    env = os.environ.get("HORNLAB_SYSTEM_STORE")
    if env:
        candidates.append(Path(env))
    candidates += [REPO / "system_runs",
                   REPO.parent / "hornlab-woofer-system-wt" / "system_runs"]
    for store in candidates:
        if all((store / "system" / key).is_dir() for key in keys):
            return store
    pytest.skip(f"gitignored system store with {list(keys)} not on disk: "
                f"{[str(c) for c in candidates]}")


def _eid(res, per_input: str) -> str:
    conv = {c.excitation_id: c for c in res.conversion}
    for excitation_id in res.excitation_ids:
        if excitation_id in conv and conv[excitation_id].to_per_input == per_input:
            return excitation_id
    raise AssertionError(f"no excitation with per_input {per_input!r}: {res.excitation_ids}")


def _probe_bases(res, probe_id: str, per_input: str):
    return res.per_excitation_bases(f"observation:probe:{probe_id}")[_eid(res, per_input)][:, 0]


def _no_summed_field(payload) -> None:
    """No channel sum/combination field anywhere (R1: no calibration policy, never sum)."""
    def walk(obj) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                lowered = str(key).lower()
                assert "sum" not in lowered and "combined" not in lowered, key
                walk(value)
        elif isinstance(obj, (list, tuple)):
            for value in obj:
                walk(value)
    walk(payload)


# --------------------------------------------------------------------------- 1. motor A/B

def test_recorded_motor_ab_reproduces_evidence() -> None:
    store = _live_store(MOTOR_REAL, MOTOR_DEMO)
    result = CMP.hw_compare(REPO, store, MOTOR_REAL, MOTOR_DEMO)
    assert result["ok"] is True
    _no_summed_field(result)
    # 6: every real payload is JSON-serialisable with no NaN/Inf.
    json.dumps(clean(result), allow_nan=False)

    demo_dir = store / "system" / MOTOR_DEMO
    recorded = json.loads((demo_dir / "motor_axis_ab.json").read_text(encoding="utf-8"))
    ra = R.read_bl_headless_result(store / "system" / MOTOR_REAL / "run")
    rb = R.read_bl_headless_result(demo_dir / "run")
    by_probe = {p["probe_id"]: p for p in result["probes"]}

    for row in recorded["pressure_rows"]:
        probe = row["probe"]
        pa = _probe_bases(ra, probe, "V_rms")
        pb = _probe_bases(rb, probe, "V_rms")

        # whole grid: recorded max_rel_delta = 100*max|a-b|/max|b| (FIRST_BEM_EVIDENCE motor rows)
        whole = CMP.relative_delta_percent(pa, pb, ra.frequencies_hz)
        assert whole == pytest.approx(row["max_rel_delta"] * 100.0, abs=1e-6)

        # LF display band == the recorded 200-500 Hz band (the solved grid starts at 200 Hz).
        lf = next(b for b in by_probe[probe]["excitations"][0]["bands"] if b["band"] == "LF")
        assert lf["max_relative_delta_percent"] == pytest.approx(
            row["lf_200_500_rel_delta"] * 100.0, abs=1e-6)

        # The recorded XO band was 600-1200 Hz; reproduce it on its own band.
        xo = CMP.relative_delta_percent(pa, pb, ra.frequencies_hz, 600.0, 1200.0)
        assert xo == pytest.approx(row["xo_600_1200_rel_delta"] * 100.0, abs=1e-6)

        # The compare payload's whole-grid value is the same statistic.
        assert by_probe[probe]["excitations"][0]["max_relative_delta_percent"] == \
            pytest.approx(row["max_rel_delta"] * 100.0, abs=1e-6)

    # The quoted acceptance: LF 120 %, XO 140-149 % (FIRST_BEM_EVIDENCE.md motor addendum).
    assert all(row["lf_200_500_rel_delta"] * 100.0 == pytest.approx(120.0, abs=0.5)
               for row in recorded["pressure_rows"])
    xo_values = [row["xo_600_1200_rel_delta"] * 100.0 for row in recorded["pressure_rows"]]
    assert 140.0 <= min(xo_values) and max(xo_values) <= 149.5


# --------------------------------------------------------------------------- 2. G6 offset

def test_recorded_g6_offset_reproduces_evidence() -> None:
    store = _live_store(G6, G6_REF_STAGED, G6_REF_WIDE)
    # The named 20 mm staged project has no run of its own; the no-run rule refuses it.
    with pytest.raises(FileNotFoundError) as exc:
        CMP.hw_compare(REPO, store, G6, G6_REF_STAGED)
    assert "no solved run" in str(exc.value)

    result = CMP.hw_compare(REPO, store, G6, G6_REF_WIDE)
    assert result["ok"] is True
    _no_summed_field(result)
    json.dumps(clean(result), allow_nan=False)                 # 6: JSON-safe real payload

    recorded = json.loads((store / "system" / G6 / "g6_paired_delta.json")
                          .read_text(encoding="utf-8"))
    ra = R.read_bl_headless_result(store / "system" / G6 / "run")
    rb = R.read_bl_headless_result(store / "system" / G6_REF_WIDE / "run")
    per_input_by_channel = {"woofer_per_2.83V": "V_rms",
                            "horn_per_1_mps": "normal_velocity_mps"}
    payload_by_channel = {(p["probe_id"], e["per_input"]): e
                          for p in result["probes"] for e in p["excitations"]}

    for row in recorded["rows"]:
        per_input = per_input_by_channel[row["channel"]]
        pa = _probe_bases(ra, row["probe"], per_input)
        pb = _probe_bases(rb, row["probe"], per_input)

        whole = CMP.relative_delta_percent(pa, pb, ra.frequencies_hz)
        assert whole == pytest.approx(row["max_rel_delta"] * 100.0, abs=1e-6)
        assert row["freq_hz_at_max"] == pytest.approx(
            float(ra.frequencies_hz[int(np.argmax(np.abs(pa - pb)))]), abs=1e-6)

        xo = CMP.relative_delta_percent(pa, pb, ra.frequencies_hz, 600.0, 1200.0)
        assert xo == pytest.approx(row["rel_delta_600_1200Hz"] * 100.0, abs=1e-6)

        entry = payload_by_channel[(row["probe"], per_input)]
        assert entry["max_relative_delta_percent"] == \
            pytest.approx(row["max_rel_delta"] * 100.0, abs=1e-6)

    # Quoted acceptance: max relative delta 0.356-0.575, XO-band relative delta 0.064-0.371.
    whole_values = [row["max_rel_delta"] for row in recorded["rows"]]
    assert max(whole_values) == pytest.approx(0.575, abs=1e-3)
    # Five of the six recorded rows are >= 0.3558; the up30/woofer row is the recorded 0.2070.
    assert all(0.355 <= value <= 0.576 for value in whole_values if value >= 0.355)
    xo_values = [row["rel_delta_600_1200Hz"] for row in recorded["rows"]]
    assert min(xo_values) == pytest.approx(0.064, abs=1e-3)
    assert max(xo_values) == pytest.approx(0.371, abs=1e-3)


# --------------------------------------------------------------------------- synthetic pair

def _rewrite(path: Path, mutate) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _pair(tmp_path: Path) -> tuple[Path, str, str]:
    store = tmp_path / "system_runs"
    a = store / "system" / "exp_a" / "case_a"
    b = store / "system" / "exp_b" / "case_b"
    shutil.copytree(FIXTURE_RUN, a / "run")
    shutil.copytree(FIXTURE_RUN, b / "run")
    HW._CACHE.clear()
    return store, "exp_a/case_a", "exp_b/case_b"


def _drop_last_frequency(run: Path) -> None:
    def mutate(manifest: dict) -> None:
        manifest["frequencies_hz"] = manifest["frequencies_hz"][:1]
        manifest["completion_mask"] = manifest["completion_mask"][:1]
        manifest["results"] = manifest["results"][:1]
    _rewrite(run / "manifest.json", mutate)


def _rename_probe_domain(run: Path) -> None:
    old, new = "observation:probe:on_axis", "observation:probe:moved"

    def rename_domain(domains: dict) -> None:
        for domain in domains["domains"]:
            if domain["id"] == old:
                domain["id"] = new
                domain["metadata"]["probe_id"] = "moved"
    _rewrite(run / "domains.json", rename_domain)
    for meta in sorted((run / "frequencies").glob("*.json")):
        def rename_target(payload: dict) -> None:
            for quantity in payload["quantities"]:
                if quantity.get("target_id") == old:
                    quantity["target_id"] = new
        _rewrite(meta, rename_target)


def _change_excitation_conversion(run: Path) -> None:
    def mutate(compiled: dict) -> None:
        for port in compiled["excitation_ports"]:
            if port["id"] == "excitation:horn":
                port["kind"] = "voltage"                     # normal_velocity -> voltage (V_rms)
    _rewrite(run / "compiled-system.json", mutate)


def test_grid_mismatch_refused_with_detail(tmp_path: Path) -> None:
    store, a, b = _pair(tmp_path)
    _drop_last_frequency(store / "system" / b / "run")
    result = CMP.hw_compare(tmp_path, store, a, b)
    assert result["ok"] is False
    assert [m["token"] for m in result["mismatches"]] == ["GRID_MISMATCH"]
    detail = result["mismatches"][0]["detail"]
    assert "lengths A=2 B=1" in detail and "first differing frequency at index 1" in detail
    assert "probes" not in result and "bands" not in result
    _no_summed_field(result)
    json.dumps(clean(result), allow_nan=False)


def test_probe_set_mismatch_refused_with_detail(tmp_path: Path) -> None:
    store, a, b = _pair(tmp_path)
    _rename_probe_domain(store / "system" / b / "run")
    result = CMP.hw_compare(tmp_path, store, a, b)
    assert result["ok"] is False
    assert [m["token"] for m in result["mismatches"]] == ["PROBE_SET_MISMATCH"]
    detail = result["mismatches"][0]["detail"]
    assert "observation:probe:on_axis" in detail and "observation:probe:moved" in detail
    assert "probes" not in result and "bands" not in result
    _no_summed_field(result)
    json.dumps(clean(result), allow_nan=False)


def test_excitation_mismatch_refused_never_summed(tmp_path: Path) -> None:
    store, a, b = _pair(tmp_path)
    _change_excitation_conversion(store / "system" / b / "run")
    result = CMP.hw_compare(tmp_path, store, a, b)
    assert result["ok"] is False
    assert [m["token"] for m in result["mismatches"]] == ["EXCITATION_MISMATCH"]
    detail = result["mismatches"][0]["detail"]
    # The reference changed from normal_velocity_mps to V_rms: a refusal, never a sum.
    assert "V_rms" in detail and "normal_velocity_mps" in detail
    assert "probes" not in result and "bands" not in result
    _no_summed_field(result)
    json.dumps(clean(result), allow_nan=False)


# --------------------------------------------------------------------------- 4. precedence

def test_no_run_raises_and_bad_keys_are_refused(tmp_path: Path) -> None:
    store, a, b = _pair(tmp_path)
    empty = store / "system" / "exp_a" / "no_run"
    empty.mkdir(parents=True)
    with pytest.raises(FileNotFoundError) as exc:
        CMP.hw_compare(tmp_path, store, a, "exp_a/no_run")
    assert "no solved run" in str(exc.value)

    for bad in ["../x", "a/b/c", "exp_a/..", "..\\x/y", "exp_a/%2e%2e", ""]:
        with pytest.raises((ValueError, FileNotFoundError)):
            CMP.hw_compare(tmp_path, store, bad, b)
    with pytest.raises(ValueError):
        CMP.hw_compare_matrix(tmp_path, store, ["exp_a/../b"])


# --------------------------------------------------------------------------- 5. no solver

def test_no_solver_or_boundary_lab_is_touched(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    from hornlab_search.system.boundarylab import run as bl_run

    def boom(*_args, **_kwargs):
        raise AssertionError("the compare read path must not call Boundary Lab")
    for name in ("validate_project", "solve_project"):
        if hasattr(bl_run, name):
            monkeypatch.setattr(bl_run, name, boom)

    store, a, b = _pair(tmp_path)
    result = CMP.hw_compare(tmp_path, store, a, b)
    assert result["ok"] is True
    matrix = CMP.hw_compare_matrix(tmp_path, store, [a, b])
    assert matrix["edges"][0]["ok"] is True
    assert "blab" not in sys.modules


# --------------------------------------------------------------------------- matrix shape

def test_matrix_cells_edges_and_missing(tmp_path: Path) -> None:
    store, a, b = _pair(tmp_path)
    keys = [a, b, "exp_c/missing_case"]
    matrix = CMP.hw_compare_matrix(tmp_path, store, keys)
    assert matrix["keys"] == keys
    assert [cell["key"] for cell in matrix["cells"]] == keys          # the given order
    assert [cell["state"] for cell in matrix["cells"]] == ["solved", "solved", "missing"]
    assert matrix["cells"][2]["experiment"] == "exp_c"
    # Two edges: the first compares two identical solves, the second cannot (missing case).
    assert len(matrix["edges"]) == 2
    assert matrix["edges"][0]["ok"] is True and matrix["edges"][0]["mismatches"] == []
    assert matrix["edges"][1]["ok"] is False and matrix["edges"][1]["error"]
    json.dumps(clean(matrix), allow_nan=False)
    _no_summed_field(matrix)
