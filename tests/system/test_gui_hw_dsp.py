"""P7 crossover preview: per-channel filtered curves, locked sum, no combine call.

The solved run is the committed BL headless fixture, so this is hermetic: no solver, no GPU, no
Boundary Lab.  The DSP point/ranges come from the committed example spec, never a JS constant.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.gui import data_hw_dsp as DSPP  # noqa: E402
from hornlab_search.system import provenance  # noqa: E402

FIXTURE_RUN = Path(__file__).resolve().parent / "fixtures" / "bl_results" / "reference_run"
KEY = "bl_src/20261119T000000Z-solved-1-aaaa"


@pytest.fixture()
def env(tmp_path: Path):
    root = tmp_path / "repo"
    store = root / "system_runs"
    case = store / "system" / KEY
    case.mkdir(parents=True)
    provenance.write_manifest(case, {"kind": "bl_motor_stage_project",
                                     "project_sha256": "cd" * 32,
                                     "result": {"ok": True}})
    shutil.copytree(FIXTURE_RUN, case / "run")
    # The committed fixture is a pure-horn basis; label the woofer port as voltage so the
    # preview exercises both channel references (the same mutation the compare tests use).
    compiled = case / "run" / "compiled-system.json"
    body = json.loads(compiled.read_text(encoding="utf-8"))
    for port in body.get("excitation_ports", []):
        if port.get("id") == "excitation:woofer":
            port["kind"] = "voltage"
    compiled.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return root, store


def _keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _keys(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _keys(value)


def test_preview_is_per_channel_and_never_summed(env) -> None:
    root, store = env
    out = DSPP.hw_dsp_preview(root, store, KEY)
    assert out["ok"] is True
    assert out["frequencies_hz"] == [100.0, 200.0]
    assert {c["channel"] for c in out["channels"]} == {"woofer", "horn"}
    assert len(out["channels"]) == 2
    for channel in out["channels"]:
        assert len(channel["spl_db"]) == len(channel["phase_deg"]) == \
            len(channel["phase_unwrapped_deg"]) == 2
        assert channel["per_input"] in ("V_rms", "normal_velocity_mps")
    assert out["verdicts"][0]["ok"] is True
    assert out["locked"]["locked"] is True and out["locked"]["decision"] == 3
    assert "Woofer: Pa per 2.83 V" in out["locked"]["reason"]
    assert out["captions"] == list(DSPP.CAPTIONS)
    # No summed or combined DATA field exists (the locked panel is a value, not a curve).
    bad = [k for k in _keys(out)
           if any(token in k.lower() for token in ("sum", "combined", "p_total"))]
    assert bad == [], bad


def test_combine_is_never_called(env, monkeypatch: pytest.MonkeyPatch) -> None:
    root, store = env
    from hornlab_search.system import combine

    def boom(*args, **kwargs):
        raise AssertionError("the crossover preview must never combine channels")

    monkeypatch.setattr(combine, "combine", boom)
    monkeypatch.setattr(combine, "recombine_with_dsp", boom)
    out = DSPP.hw_dsp_preview(root, store, KEY)
    assert out["ok"] is True and len(out["channels"]) == 2


def test_a_crossover_type_outside_the_spec_is_refused(env) -> None:
    root, store = env
    out = DSPP.hw_dsp_preview(root, store, KEY, {"point": {"crossover_type": "LR2"}})
    assert out["ok"] is False and out["channels"] == []
    assert "LR2" in out["verdicts"][0]["detail"]


def test_an_out_of_range_xo_is_refused(env) -> None:
    root, store = env
    out = DSPP.hw_dsp_preview(root, store, KEY, {"point": {"xo_hz": 5000.0}})
    assert out["ok"] is False and out["channels"] == []
    assert "outside" in out["verdicts"][0]["detail"]


def test_partial_point_uses_the_spec_defaults(env) -> None:
    root, store = env
    out = DSPP.hw_dsp_preview(root, store, KEY, {"point": {"xo_hz": 800.0}})
    assert out["ok"] is True
    point = out["dsp"]["point"]
    assert point["xo_hz"] == 800.0
    assert point["crossover_type"] == "LR4"          # the committed spec's only allowed type
    assert out["dsp"]["source"] == DSPP.DEFAULT_SPEC_REL.as_posix()
