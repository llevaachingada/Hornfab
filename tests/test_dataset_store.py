"""Tests for dataset/store.py: the append-only store and the phase-2 exporter. Offline."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.dataset.record import build_record
from hornlab_search.dataset.store import (DatasetStore, export_training_npz, stats_report,
                                          to_training_arrays, verify_store)
from test_dataset_factory import (GRID, LIB_SHAS, LIB_SHAS_B, TARGET, make_eval, solve_spec,
                                  trace_arrays)

FREQS12 = solve_spec().freqs_hz


def rec(i: int, family: str = "OSSE", ok: bool = True, *, nf: int | None = None, lib=LIB_SHAS,
        traces=None, created="2026-10-13T00:00:00Z"):
    """(meta, arrays) for synthetic record i."""
    spec = solve_spec(freqs=FREQS12[:nf]) if nf else solve_spec()
    return build_record(make_eval(i, family, ok, nf=nf), TARGET, lib, solve_spec=spec, grid=GRID,
                        area_m2=0.125, traces=traces, created_utc=created)


def fast_factory(nf: int = 3):
    """Many distinct records cheaply: one build, then clone the metadata with a new hash."""
    base_meta, base_arrays = rec(0, nf=nf)
    fail_meta, _ = rec(0, ok=False)

    def make(i: int, ok: bool = True):
        meta = copy.deepcopy(base_meta if ok else fail_meta)
        meta["design_hash"] = f"{i:012x}"
        return (meta, base_arrays if ok else {})
    return make


def assert_arrays_identical(a: dict, b: dict):
    assert set(a) == set(b)
    for k in a:
        assert a[k].dtype == b[k].dtype, k
        assert a[k].shape == b[k].shape, k
        assert a[k].tobytes() == b[k].tobytes(), k          # bit-identical, NaN payloads included


# 7
def test_append_then_read_round_trips_metadata_and_every_array_bit_identically(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    meta, arrays = rec(1)
    arrays["spl_h_db"] = arrays["spl_h_db"].astype(np.float32)        # a non-default dtype
    assert np.isnan(arrays["ripple_h_db"][0])                          # NaN must survive
    arrays_with_none = dict(arrays, balloon_dirs=None)                 # a None array is simply absent
    s, r = st.append(meta, arrays_with_none)
    assert (s, r) == (0, 0)
    m2, a2 = st.read(0, 0)
    assert m2 == meta
    expect = {k: v for k, v in arrays.items() if k != "balloon_dirs"}
    assert_arrays_identical(a2, expect)
    assert a2["z_throat"].dtype == np.complex128
    assert a2["spl_h_db"].dtype == np.float32
    # None / null fields of the metadata come back as None
    assert m2["mesh"]["grid"]["available"] is True and m2["traces"]["path"] is None
    # a failed record: no arrays at all
    fm, fa = rec(2, ok=False)
    s, r = st.append(fm, fa)
    m3, a3 = st.read(s, r)
    assert m3 == fm and a3 == {} and m3["ok"] is False and m3["mesh"]["n_triangles"] is None


def test_every_append_fsyncs_all_three_files(tmp_path, monkeypatch):
    st = DatasetStore(tmp_path / "ds")
    calls = []
    real = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: (calls.append(fd), real(fd))[1])
    st.append(*rec(1))
    assert len(calls) >= 3                                             # npz, shard jsonl, index
    calls.clear()
    st.append(*rec(2, ok=False))
    assert len(calls) >= 2                                             # shard jsonl, index


def test_append_rejects_a_bad_record_before_writing_anything(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    meta, arrays = rec(1)
    del meta["excitation"]
    with pytest.raises(ValueError, match="excitation"):
        st.append(meta, arrays)
    meta, arrays = rec(1)
    with pytest.raises(ValueError, match="unknown array key"):
        st.append(meta, dict(arrays, surprise=np.zeros(3)))
    with pytest.raises(ValueError, match="object"):
        st.append(meta, {"spl_h_db": np.array([object()], dtype=object)})
    assert len(st) == 0 and not st.index_path.exists() and not st.shard_jsonl(0).exists()


# 8
def test_1200_appends_roll_into_shards_of_500_500_200(tmp_path):
    st = DatasetStore(tmp_path / "ds", max_records_per_shard=500)
    make = fast_factory()
    for i in range(1200):
        st.append(*make(i, ok=(i % 10 != 0)))
    assert len(st) == 1200
    counts = {}
    for e in st.index:
        counts[e["shard"]] = counts.get(e["shard"], 0) + 1
    assert counts == {0: 500, 1: 500, 2: 200}
    assert [e["row"] for e in st.index if e["shard"] == 1][:3] == [0, 1, 2]
    for s in (0, 1, 2):
        assert st.shard_jsonl(s).exists()
    assert not st.shard_jsonl(3).exists()
    assert len(st.shard_jsonl(0).read_bytes().splitlines()) == 500


def test_shard_rolls_on_size_too(tmp_path):
    st = DatasetStore(tmp_path / "ds", max_records_per_shard=10_000, max_shard_mb=1)
    make = fast_factory(nf=12)                       # ~100 KB of arrays per record
    for i in range(30):
        st.append(*make(i))
    shards = sorted({e["shard"] for e in st.index})
    assert len(shards) >= 3, shards


# 9
def test_index_has_one_parseable_line_per_record_in_append_order(tmp_path):
    st = DatasetStore(tmp_path / "ds", max_records_per_shard=7)
    make = fast_factory()
    for i in range(25):
        st.append(*make(i, ok=(i != 4)))
    lines = st.index_path.read_text().splitlines()
    assert len(lines) == 25
    entries = [json.loads(ln) for ln in lines]
    assert [e["design_hash"] for e in entries] == [f"{i:012x}" for i in range(25)]
    assert all(set(["design_hash", "shard", "row", "objective", "ok"]) <= set(e) for e in entries)
    assert entries[4]["ok"] is False
    assert [(e["shard"], e["row"]) for e in entries[:9]] == [(0, i) for i in range(7)] + [(1, 0), (1, 1)]


# 10
def test_crash_mid_index_line_recovers_every_complete_line_and_appends_cleanly(tmp_path):
    root = tmp_path / "ds"
    st = DatasetStore(root)
    make = fast_factory()
    for i in range(20):
        st.append(*make(i))
    del st
    ip = root / "index.jsonl"
    data = ip.read_bytes()
    ip.write_bytes(data[:-37])                      # kill mid-way through the last index line
    assert not ip.read_bytes().endswith(b"\n")

    st = DatasetStore(root)                         # reopen
    assert st.recovery["partial_index_line_bytes"] > 0          # the partial line is reported
    assert st.recovery["index_rebuilt_rows"] == 1               # its record was in the shard: rebuilt
    assert len(st) == 20
    for e in st.index:
        meta, arrays = st.read(e["shard"], e["row"])
        assert meta["design_hash"] == e["design_hash"] and arrays
    assert st.read(0, 19)[0]["design_hash"] == f"{19:012x}"

    assert st.append(*make(20)) == (0, 20)          # appends correctly afterwards
    lines = ip.read_bytes().splitlines()
    assert len(lines) == 21 and ip.read_bytes().endswith(b"\n")
    assert [json.loads(ln)["row"] for ln in lines] == list(range(21))   # every line parses
    assert DatasetStore(root).recovery == {}                    # and the next open is clean


def test_crash_after_shard_write_before_index_write_is_repaired(tmp_path):
    root = tmp_path / "ds"
    st = DatasetStore(root)
    make = fast_factory()
    for i in range(5):
        st.append(*make(i))
    del st
    ip = root / "index.jsonl"
    lines = ip.read_bytes().splitlines(keepends=True)
    ip.write_bytes(b"".join(lines[:-2]))            # the last two index writes never happened
    st = DatasetStore(root)
    assert st.recovery["index_rebuilt_rows"] == 2 and len(st) == 5
    assert [e["row"] for e in st.index] == [0, 1, 2, 3, 4]


def test_torn_shard_line_is_truncated_on_reopen(tmp_path):
    root = tmp_path / "ds"
    st = DatasetStore(root)
    make = fast_factory()
    for i in range(3):
        st.append(*make(i))
    del st
    with open(root / "shard-0000.jsonl", "ab") as f:
        f.write(b'{"schema_version":1,"design_hash":"torn')     # half a line, no newline
    st = DatasetStore(root)
    assert st.recovery["partial_shard_line_bytes"] > 0
    assert len(st) == 3
    assert st.append(*make(3)) == (0, 3)
    assert [json.loads(ln)["design_hash"] for ln in (root / "shard-0000.jsonl").read_bytes().splitlines()] \
        == [f"{i:012x}" for i in range(4)]


def test_reopening_a_clean_store_continues_where_it_left_off(tmp_path):
    root = tmp_path / "ds"
    make = fast_factory()
    st = DatasetStore(root, max_records_per_shard=4)
    for i in range(6):
        st.append(*make(i))
    st2 = DatasetStore(root, max_records_per_shard=4)
    assert st2.recovery == {} and len(st2) == 6
    assert st2.append(*make(6)) == (1, 2)
    assert st2.append(*make(7)) == (1, 3)
    assert st2.append(*make(8)) == (2, 0)


# 11
def test_closed_shard_stays_readable_and_is_never_touched_again(tmp_path):
    st = DatasetStore(tmp_path / "ds", max_records_per_shard=5)
    make = fast_factory()
    st.append(*rec(100))
    for i in range(1, 5):
        st.append(*make(i))
    assert st.shard_jsonl(1).exists() is False and st._cur == 1       # shard 0 is now closed

    def digest(shard):
        h = hashlib.sha256()
        h.update(st.shard_jsonl(shard).read_bytes())
        for p in sorted(st.shard_dir(shard).iterdir()):
            h.update(p.name.encode())
            h.update(p.read_bytes())
        return h.hexdigest()

    before = digest(0)
    for i in range(5, 18):
        st.append(*make(i))
    assert digest(0) == before                                        # append only: never rewritten
    meta, arrays = st.read(0, 0)
    assert meta["design_hash"] == f"{100:012x}" and "spl_h_db" in arrays
    assert st.read(0, 4)[0]["design_hash"] == f"{4:012x}"
    assert st.read(2, 0)[0]["design_hash"] == f"{10:012x}"
    with pytest.raises(KeyError):
        st.read(0, 5)


# 12
def test_stats_counts_across_two_families_and_two_lib_shas(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    spec = [("OSSE", LIB_SHAS, True), ("OSSE", LIB_SHAS, False), ("ICW", LIB_SHAS_B, True),
            ("ICW", LIB_SHAS_B, True), ("OSSE", LIB_SHAS_B, False)]
    for j in range(8):
        for i, (fam, lib, ok) in enumerate(spec):
            st.append(*rec(j * 10 + i, fam, ok, lib=lib, nf=3,
                           created=f"2026-10-{10 + j:02d}T12:00:00Z"))
    s = st.stats()
    assert s["n"] == 40 and s["n_ok"] == 24 and s["n_failed"] == 16
    assert s["by_family"] == {"OSSE": 24, "ICW": 16}
    assert s["by_backend"] == {"beat_cuda": 40}
    assert sorted(s["by_lib_sha"].values()) == [16, 24]
    assert len(s["by_lib_sha"]) == 2
    assert s["date_first"] == "2026-10-10T12:00:00Z" and s["date_last"] == "2026-10-17T12:00:00Z"
    assert s["total_gpu_seconds"] == pytest.approx(5.0 * 24)           # only beat_cuda, only solves that ran
    assert s["disk_mb"] > 0 and s["n_shards"] == 1
    assert "records 40" in stats_report(st)


def test_stats_reads_only_the_index(tmp_path, monkeypatch):
    st = DatasetStore(tmp_path / "ds")
    make = fast_factory()
    for i in range(10):
        st.append(*make(i))

    def boom(*a, **k):
        raise AssertionError("stats() opened a shard")

    monkeypatch.setattr(st, "_read_meta", boom)
    monkeypatch.setattr(st, "_read_arrays", boom)
    assert st.stats()["n"] == 10 and st.family_balance()["OSSE"] == 10 and st.trace_fraction() == 0.0


# 13
def test_to_training_arrays_shapes_key_order_and_excitation(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    for i in range(50):
        st.append(*rec(i, "OSSE", nf=12))
    d = to_training_arrays(st)
    k = len(d["key_names"])
    assert d["X"].shape == (50, k) and d["X"].dtype == np.float32
    assert d["key_names"] == sorted(d["key_names"])
    assert d["key_names"] == sorted(make_eval(0).design.params)       # == DesignSpace.keys() order
    assert d["y_metrics"]["bw_h_deg"].shape == (50, 12)
    assert set(d["y_metrics"]) >= {"bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db",
                                   "on_axis_db", "z_throat_real"}
    assert d["freqs_hz"].shape == (12,) and np.allclose(d["freqs_hz"], FREQS12)
    assert d["design_hash"].shape == (50,) and d["design_hash"][3] == f"{3:012x}"
    assert d["meta"]["skipped_grid_mismatch"] == 0 and d["meta"]["n_selected"] == 50
    assert d["y_scalars"]["objective"].shape == (50,) and "di_slope_db_per_dec" in d["y_scalars"]
    # X values are the parameters, in key order
    j = d["key_names"].index("r0_mm")
    assert d["X"][7, j] == pytest.approx(make_eval(7).design.params["r0_mm"], rel=1e-6)
    # y really is the stored array
    _, a = st.read(0, 7)
    assert np.array_equal(d["y_metrics"]["bw_h_deg"][7], a["bw_h_deg"])
    assert np.isnan(d["y_metrics"]["ripple_h_db"][7, 0])               # the NaN survives export
    # test 23: the excitation fields come out with X
    ex = d["excitation"]
    assert ex["port_tag"].shape == (50,) and (ex["port_tag"] == 2).all()
    assert (ex["port_name"] == "SD1D1001").all() and (ex["kind"] == "uniform_normal_velocity").all()
    assert (ex["amplitude"] == 1.0).all() and (ex["units"] == "m/s").all()
    assert ex["frequency_dependent"].dtype == bool and not ex["frequency_dependent"].any()
    assert (d["di_source"] == "balloon").all()


def test_explicit_keys_keep_the_callers_order_and_non_numeric_defaults_are_reported(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    for i in range(6):
        st.append(*rec(i, "OSSE", nf=3))
    for i in range(6, 12):
        st.append(*rec(i, "ICW", nf=3))
    d = to_training_arrays(st)
    assert "termination" in d["meta"]["skipped_keys"] and "termination" not in d["key_names"]
    assert d["X"].shape[0] == 12 and np.isnan(d["X"]).any()           # keys absent from a family
    d = to_training_arrays(st, family="OSSE", keys=["s", "k", "L_mm"])
    assert d["key_names"] == ["s", "k", "L_mm"] and d["X"].shape == (6, 3)
    with pytest.raises(ValueError, match="not numeric"):
        to_training_arrays(st, family="ICW", keys=["termination"])


# 14
def test_two_frequency_grids_return_only_the_majority_grid(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    for i in range(10):
        st.append(*rec(i, nf=12))
    for i in range(10, 14):
        st.append(*rec(i, nf=8))                                       # a different grid
    d = to_training_arrays(st)
    assert d["X"].shape[0] == 10 and d["freqs_hz"].shape == (12,)
    assert d["meta"]["skipped_grid_mismatch"] == 4
    assert d["y_metrics"]["di_db"].shape == (10, 12)
    assert not np.isnan(d["y_metrics"]["di_db"]).any()


# 15
def test_ok_only_excludes_failures_and_ok_only_false_returns_them_with_nan_labels(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    for i in range(12):
        st.append(*rec(i, nf=12))
    for i in range(12, 16):
        st.append(*rec(i, ok=False))
    d = to_training_arrays(st)
    assert d["X"].shape[0] == 12 and d["ok"].all()
    d = to_training_arrays(st, ok_only=False)
    assert d["X"].shape[0] == 16 and d["ok"].sum() == 12
    bad = ~d["ok"]
    assert np.isnan(d["y_metrics"]["bw_h_deg"][bad]).all()
    assert np.isnan(d["y_scalars"]["bw_h_mean_deg"][bad]).all()
    assert not np.isnan(d["X"][bad]).all()                             # where the failure was is kept
    assert np.isfinite(d["y_scalars"]["objective"][bad]).all()         # the penalty is a label too
    assert (d["excitation"]["port_tag"] == 2).all()


# 16
def test_lib_sha_filter(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    for i in range(6):
        st.append(*rec(i, nf=3, lib=LIB_SHAS))
    for i in range(6, 10):
        st.append(*rec(i, nf=3, lib=LIB_SHAS_B))
    assert to_training_arrays(st)["X"].shape[0] == 10
    key_b = next(k for k in st.stats()["by_lib_sha"] if k.endswith("ffffffffff"))
    for sel in (key_b, "ffffffffffff", LIB_SHAS_B["hornlab_beat_bem"]):
        d = to_training_arrays(st, lib_sha=sel)
        assert d["X"].shape[0] == 4, sel
        assert all(h in {f"{i:012x}" for i in range(6, 10)} for h in d["design_hash"])
    assert to_training_arrays(st, lib_sha=LIB_SHAS["hornlab_beat_bem"][:12])["X"].shape[0] == 6
    assert to_training_arrays(st, lib_sha="nonesuch")["X"].shape[0] == 0
    assert to_training_arrays(st, family="ICW")["X"].shape[0] == 0


# 17
def test_append_500_typical_records_is_fast(tmp_path, capsys):
    st = DatasetStore(tmp_path / "ds")
    make = fast_factory(nf=12)                                         # screen-sized arrays
    t0 = time.perf_counter()
    for i in range(500):
        st.append(*make(i))
    dt = time.perf_counter() - t0
    with capsys.disabled():
        print(f"\n[CP-5 test 17] 500 appends (12 freqs, 73 angles, 512-pt balloon; 3 fsyncs each): "
              f"{dt:.2f} s = {1000 * dt / 500:.1f} ms per record")
    assert len(st) == 500
    assert dt < 5.0, f"500 appends took {dt:.2f} s"


# 18
def test_disk_usage_for_500_typical_records_with_and_without_traces(tmp_path, capsys):
    make = fast_factory(nf=12)
    plain = DatasetStore(tmp_path / "plain")
    for i in range(500):
        plain.append(*make(i))
    traced = DatasetStore(tmp_path / "traced")
    tr = trace_arrays()
    n_tr = 0
    for i in range(500):
        meta, arrays = make(i)
        if i % 20 == 0:                                                # 1 record in 20
            path = traced.append_traces(meta["design_hash"], tr)
            meta = copy.deepcopy(meta)
            meta["traces"] = {"captured": True, "path": path, "kind": "p1_pressure+dp0_neumann",
                              "sample_fraction": 0.05}
            n_tr += 1
        traced.append(meta, arrays)
    base_mb, traced_mb = plain.stats()["disk_mb"], traced.stats()["disk_mb"]
    per_trace_mb = (traced_mb - base_mb) / n_tr
    with capsys.disabled():
        print(f"\n[CP-5 test 18] disk per 500 records: {base_mb:.1f} MB without traces; "
              f"{traced_mb:.1f} MB with traces at 1 in 20 ({n_tr} captured, "
              f"{per_trace_mb:.2f} MB per captured trace at 12 freqs x 2,369 dofs)")
        print(f"[CP-5 test 18] projected 10,000 records: {base_mb * 20:.0f} MB "
              f"({base_mb * 20 / 1024:.2f} GB) without traces; "
              f"{traced_mb * 20:.0f} MB ({traced_mb * 20 / 1024:.2f} GB) with traces")
    assert base_mb > 1 and traced_mb > base_mb
    assert traced.trace_fraction() == pytest.approx(0.05)


# 20
def test_append_traces_writes_a_readable_npz_and_read_returns_both_together(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    tr = trace_arrays(nf=2, n_vertices=50, n_faces=80)
    meta0, arrays = rec(9, nf=12)
    path = st.append_traces(meta0["design_hash"], tr)
    assert path == f"traces/{meta0['design_hash']}.npz"
    assert (st.root / path).exists()
    meta, arrays = build_record(make_eval(9), TARGET, LIB_SHAS, solve_spec=solve_spec(), grid=GRID,
                                traces={"path": path, "kind": "p1_pressure+dp0_neumann"})
    s, r = st.append(meta, arrays)
    m2, a2 = st.read(s, r, with_traces=True)
    assert m2["traces"]["captured"] is True and m2["traces"]["path"] == path
    assert np.array_equal(a2["traces/surface_pressure_complex"], tr["surface_pressure_complex"])
    assert a2["traces/surface_neumann_complex"].dtype == np.complex128
    assert "spl_h_db" in a2                                            # both together
    assert "traces/surface_pressure_complex" not in st.read(s, r)[1]
    # a second capture for the same design never overwrites the first
    path2 = st.append_traces(meta0["design_hash"], trace_arrays(nf=1, n_vertices=5, n_faces=8))
    assert path2 != path and (st.root / path).stat().st_size > (st.root / path2).stat().st_size
    with pytest.raises(ValueError):
        st.append_traces("../evil", tr)


# 21
def test_trace_fraction_is_measured_from_the_records(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    assert st.trace_fraction() == 0.0
    make = fast_factory()
    for i in range(100):
        meta, arrays = make(i)
        if i % 20 == 3:
            meta["traces"] = {"captured": True, "path": f"traces/{meta['design_hash']}.npz",
                              "kind": "k", "sample_fraction": 0.05}
        st.append(meta, arrays)
    assert st.trace_fraction() == 0.05
    assert st.stats()["trace_fraction"] == 0.05


# 22
def test_family_balance_and_the_80_percent_warning(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    mix = ["OSSE"] * 30 + ["R-OSSE"] * 10 + ["ICW"] * 20 + ["FREEFORM"] * 40
    for i, fam in enumerate(mix):
        st.append(*rec(i, fam, nf=3))
    assert st.family_balance() == {"OSSE": 30, "R-OSSE": 10, "ICW": 20, "FREEFORM": 40}
    assert st.stats()["family_warning"] is None
    assert st.stats()["family_balance"] == st.family_balance()

    skewed = DatasetStore(tmp_path / "skewed")
    for i in range(100):
        skewed.append(*rec(i, "OSSE" if i < 90 else "ICW", nf=3))
    assert skewed.family_balance() == {"OSSE": 90, "R-OSSE": 0, "ICW": 10, "FREEFORM": 0}
    w = skewed.stats()["family_warning"]
    assert w and "90%" in w and "OSSE" in w
    assert "WARNING" in stats_report(skewed)


# CLI hooks
def test_verify_store_finds_a_damaged_record(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    make = fast_factory()
    for i in range(6):
        st.append(*make(i, ok=(i != 2)))
    rep = verify_store(st)
    assert rep["n"] == 6 and rep["n_bad"] == 0
    st.record_npz(0, 4).unlink()                                       # lose one record's arrays
    rep = verify_store(DatasetStore(tmp_path / "ds"))
    assert rep["n_bad"] == 1 and rep["bad"][0]["row"] == 4 and "no arrays" in rep["bad"][0]["problem"]


def test_export_training_npz_round_trips(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    for i in range(8):
        st.append(*rec(i, nf=12))
    d = export_training_npz(st, tmp_path / "train.npz", family="OSSE")
    with np.load(tmp_path / "train.npz", allow_pickle=False) as z:
        assert z["X"].shape == d["X"].shape and list(z["key_names"]) == d["key_names"]
        assert z["y_metrics/bw_h_deg"].shape == (8, 12)
        assert (z["excitation/port_tag"] == 2).all() and z["freqs_hz"].shape == (12,)
        assert json.loads(str(z["meta_json"]))["n_selected"] == 8


def test_arrays_of_an_uncommitted_row_are_deleted_on_reopen(tmp_path):
    root = tmp_path / "ds"
    st = DatasetStore(root)
    make = fast_factory()
    for i in range(3):
        st.append(*make(i))
    del st
    (root / "shard-0000" / "rec-0003.npz").write_bytes(b"torn half-written arrays")   # npz, no jsonl line
    st = DatasetStore(root)
    assert st.recovery["orphan_array_files"] == 1 and len(st) == 3
    assert not (root / "shard-0000" / "rec-0003.npz").exists()
    assert st.append(*make(3)) == (0, 3)
    assert st.read(0, 3)[1]                                            # the new row's own arrays


# ---- small data-pipeline fixes (senior review queue) ------------------------------------------

def test_stats_reports_duplicate_designs_and_missing_families(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    for i in range(3):
        st.append(*rec(i, nf=3))
    st.append(*rec(0, nf=3))                       # design_hash 0 twice
    st.append(*rec(1, nf=3))
    st.append(*rec(1, nf=3))                       # design_hash 1 three times
    s = st.stats()
    assert s["n_duplicate_designs"] == 2           # distinct hashes seen more than once
    assert s["missing_families"] == ["R-OSSE", "ICW", "FREEFORM"]
    rep = stats_report(st)
    assert "duplicate designs 2" in rep
    assert "missing families ['R-OSSE', 'ICW', 'FREEFORM']" in rep
    # an empty store is not a special case: every family is missing, no duplicates
    empty = DatasetStore(tmp_path / "empty").stats()
    assert empty["n_duplicate_designs"] == 0
    assert empty["missing_families"] == ["OSSE", "R-OSSE", "ICW", "FREEFORM"]


def test_verify_store_reports_bad_metric_array_shapes_separately(tmp_path):
    st = DatasetStore(tmp_path / "ds")
    st.append(*rec(1, nf=12))
    st.append(*rec(2, nf=12))
    p = st.record_npz(0, 0)                        # record 0 == design_hash 000000000001
    with np.load(p, allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}
    arrays["bw_h_deg"] = arrays["bw_h_deg"][None, :]      # (1, 12): no longer 1-D
    with open(p, "wb") as f:
        np.savez(f, **arrays)

    rep = verify_store(DatasetStore(tmp_path / "ds"))
    assert rep["n_bad"] == 0                       # the record itself is still valid
    assert rep["n_bad_arrays"] == 1
    b = rep["bad_arrays"][0]
    assert (b["shard"], b["row"], b["design_hash"]) == (0, 0, f"{1:012x}")
    assert "bw_h_deg" in b["problem"] and "1-D" in b["problem"]
    # the shape problem is exactly what to_training_arrays would otherwise silently drop
    assert to_training_arrays(DatasetStore(tmp_path / "ds"))["meta"]["skipped_bad_arrays"] == 1
    # a wrong LENGTH (still 1-D) is caught too; start from fresh arrays so only di_db is wrong
    _, fresh = rec(1, nf=12)
    fresh = {k: v for k, v in fresh.items() if v is not None}
    fresh["di_db"] = np.zeros(5)
    with open(p, "wb") as f:
        np.savez(f, **fresh)
    rep2 = verify_store(DatasetStore(tmp_path / "ds"))
    assert rep2["n_bad_arrays"] == 1 and "di_db" in rep2["bad_arrays"][0]["problem"]


def test_search_resume_refuses_a_changed_config(tmp_path, capsys):
    """The resume guard: a stored run.json config_sha that disagrees with the current config must
    REFUSE (exit 1, both SHAs named) before any backend/solver is touched. The escape hatch
    --allow-config-change is deliberately NOT exercised here (it would reach the backend)."""
    from hornlab_search.cli import main
    ex = Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml"
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run.json").write_text(json.dumps({"config_sha": "deadbeef0000"}))
    (run_dir / "config.yaml").write_text(ex.read_text(encoding="utf-8"))
    common = ["--runs-dir", str(tmp_path / "runs"), "--cache-dir", str(tmp_path / "cache"),
              "--dataset-dir", str(tmp_path / "dataset")]
    rc = main(["search", "--resume", str(run_dir), "--config", str(ex), "--budget", "0", *common])
    out = capsys.readouterr().out
    assert rc == 1
    assert "REFUSED" in out and "deadbeef0000" in out and "--allow-config-change" in out

def _freeform_params(i: int) -> dict:
    return {"profileH": {"points": [[0.0, 12.7], [60.0, 40.0 + i], [120.0, 150.0]],
                         "mouthAngleDeg": 50.0 + i},
            "profileV": {"points": [[0.0, 12.7], [60.0, 35.0 + i], [120.0, 110.0]],
                         "mouthAngleDeg": 45.0},
            "crossSections": [{"t": 0.0, "shape": "circle"},
                              {"t": 1.0, "shape": "superellipse", "exponent": 3.0 + i}]}


def test_freeform_path_and_alias_keys_fill_X(tmp_path):
    # FREEFORM search keys are paths (profileH.points.1.1) or the 'exponent' alias. X must be read
    # through the design layer's path rules, not params.get, or every column comes back NaN.
    st = DatasetStore(tmp_path / "ds")
    for i in range(4):
        meta, arrays = rec(i, nf=3)
        meta["family"], meta["params"] = "FREEFORM", _freeform_params(i)
        meta["design_hash"] = f"ff{i:010x}"
        st.append(meta, arrays)
    keys = ["exponent", "profileH.mouthAngleDeg", "profileH.points.1.1", "profileV.points.1.1"]
    d = to_training_arrays(st, family="FREEFORM", keys=keys)
    assert not np.isnan(d["X"]).any()
    assert d["X"][:, 0].tolist() == [3.0, 4.0, 5.0, 6.0]
    assert d["X"][:, 1].tolist() == [50.0, 51.0, 52.0, 53.0]
    assert d["X"][:, 2].tolist() == [40.0, 41.0, 42.0, 43.0]
    assert d["X"][:, 3].tolist() == [35.0, 36.0, 37.0, 38.0]
    d = to_training_arrays(st, family="FREEFORM", keys=["profileH.points.9.1"])  # no such anchor
    assert np.isnan(d["X"]).all()
