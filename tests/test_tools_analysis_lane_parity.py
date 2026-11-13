"""A.7 lane_parity.py — golden tests for the GPU-vs-CPU response parity gate (CP-7b).

Synthetic verify runs store ``designs/<hash>/response.npz``; four shared design hashes:
three agree within 0.2 dB (0.05 / 0.10 / 0.15) and one does not (0.5) -> PASS (>= 3).
"""

from __future__ import annotations

import numpy as np
import pytest

from test_tools_analysis_common import (load_tool, make_row, run_cli,
                                        run_json_payload, write_run)

lp = load_tool("lane_parity")

FREQS = np.array([500.0, 1000.0, 2000.0, 4000.0])
ANGLES = np.array([-30.0, 0.0, 30.0])


def _spl(base_db: float, delta: float = 0.0) -> np.ndarray:
    """(nf, na) SPL whose worst deviation from ``base_db`` is exactly ``delta``."""
    arr = np.full((FREQS.size, ANGLES.size), base_db)
    if delta:
        arr[2, 1] = base_db + delta  # single worst cell
    return arr


def _write_response(run_dir, design_hash: str, delta: float, *, balloon: bool = False,
                    freq_grid=None, na: int | None = None) -> None:
    d = run_dir / "designs" / design_hash
    d.mkdir(parents=True, exist_ok=True)
    grid = FREQS if freq_grid is None else np.asarray(freq_grid, dtype=float)
    spl_h = np.full((grid.size, na if na else ANGLES.size), 80.0)
    if delta:
        spl_h[0, 0] = 80.0 + delta
    arrays = {"freqs_hz": grid, "spl_h_db": spl_h, "spl_v_db": np.full_like(spl_h, 75.0)}
    if balloon:
        arrays["spl_balloon_db"] = np.full((grid.size, 5), 70.0 + delta)
    np.savez(d / "response.npz", **arrays)


def _pair(tmp_path, deltas: dict[str, float], *, j_gpu=12.0, j_cpu=12.3):
    gpu = write_run([make_row(i, j_gpu, design_hash=dh) for i, dh in enumerate(deltas)],
                    tmp_path, "verify_gpu", seed=1234)
    cpu = write_run([make_row(i, j_cpu, design_hash=dh) for i, dh in enumerate(deltas)],
                    tmp_path, "verify_cpu", seed=1234)
    for dh, delta in deltas.items():
        _write_response(gpu, dh, 0.0)
        _write_response(cpu, dh, delta)
    return gpu, cpu


def test_pass_when_three_designs_within_threshold(tmp_path):
    gpu, cpu = _pair(tmp_path, {"dhA": 0.05, "dhB": 0.10, "dhC": 0.15, "dhD": 0.5})
    p = lp.analyse(gpu, cpu)
    assert p["n_common_hashes"] == 4 and p["n_compared"] == 4
    assert p["n_within_0p2"] == 3
    assert p["threshold_db"] == 0.2 and p["min_designs"] == 3
    assert p["pass"] is True and p["gate"] == "CP-7b"
    by_dh = {d["design_hash"]: d for d in p["designs"]}
    assert by_dh["dhA"]["max_abs_dspl_db"] == pytest.approx(0.05)
    assert by_dh["dhD"]["max_abs_dspl_db"] == pytest.approx(0.5)
    assert by_dh["dhA"]["d_j"] == pytest.approx(0.3)
    assert by_dh["dhA"]["source"] == "designs/dhA/response.npz"


def test_fail_when_only_two_designs_agree(tmp_path):
    gpu, cpu = _pair(tmp_path, {"dhA": 0.05, "dhB": 0.10, "dhC": 0.5})
    p = lp.analyse(gpu, cpu)
    assert p["n_within_0p2"] == 2 and p["pass"] is False


def test_missing_and_mismatched_responses_are_noted(tmp_path):
    gpu, cpu = _pair(tmp_path, {"dhA": 0.05})
    # dhB: response only on the CPU side
    cpu_b = cpu / "designs" / "dhB"
    cpu_b.mkdir(parents=True)
    np.savez(cpu_b / "response.npz", freqs_hz=FREQS,
             spl_h_db=np.full((FREQS.size, ANGLES.size), 80.0),
             spl_v_db=np.full((FREQS.size, ANGLES.size), 75.0))
    # dhC: different angle count -> no shared plane
    (gpu / "designs" / "dhC").mkdir(parents=True)
    (cpu / "designs" / "dhC").mkdir(parents=True)
    _write_response(gpu, "dhC", 0.0, na=4)
    _write_response(cpu, "dhC", 0.0, na=5)
    # dhD: different frequency grid
    _write_response(gpu, "dhD", 0.0)
    _write_response(cpu, "dhD", 0.0, freq_grid=FREQS * 2.0)
    for d in (gpu, cpu):
        rows = [make_row(i, 12.0, design_hash=f"dh{dh}") for i, dh in enumerate("ABCD")]
        (d / "search.ndjson").write_text(
            "".join(__import__("json").dumps(r) + "\n" for r in rows), encoding="utf-8")
    p = lp.analyse(gpu, cpu)
    notes = {d["design_hash"]: d for d in p["designs"]}
    assert notes["dhA"]["compared"] is True
    assert notes["dhB"]["note"] == "response.npz missing on one side"
    assert notes["dhC"]["note"] == "no shared SPL plane (shape mismatch)"
    assert notes["dhD"]["note"] == "frequency grid mismatch between the two responses"
    assert p["n_compared"] == 1 and p["pass"] is False


def test_balloon_plane_is_included(tmp_path):
    gpu, cpu = _pair(tmp_path, {"dhA": 0.1, "dhB": 0.1, "dhC": 0.1})
    _write_response(gpu, "dhA", 0.0, balloon=True)
    _write_response(cpu, "dhA", 0.1, balloon=True)  # balloon worst cell is +0.1 too
    p = lp.analyse(gpu, cpu)
    assert {d["design_hash"]: d for d in p["designs"]}["dhA"]["max_abs_dspl_db"] == pytest.approx(0.1)


def test_cli_report_and_chart(tmp_path):
    gpu, cpu = _pair(tmp_path, {"dhA": 0.05, "dhB": 0.10, "dhC": 0.15})
    out = tmp_path / "out"
    proc = run_cli("lane_parity", ["--gpu", str(gpu), "--cpu", str(cpu)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "PASS (CP-7b)" in proc.stdout
    doc = run_json_payload(out, "lane_parity")
    assert doc["tool"] == "lane_parity" and doc["pass"] is True
    md = (out / "lane_parity.md").read_text(encoding="utf-8")
    assert "**PASS**" in md and "CP-7b" in md
    assert (out / "lane_parity.png").exists()


# ------------------------------------------------------------------ pooled mode (--pair)

def _named_pair(tmp_path, name, deltas):
    sub = tmp_path / name
    sub.mkdir()
    return _pair(sub, deltas)


def test_pooled_passes_when_three_distinct_designs_span_pairs(tmp_path):
    p1 = _named_pair(tmp_path, "p1", {"dhA": 0.05, "dhB": 0.10})
    p2 = _named_pair(tmp_path, "p2", {"dhC": 0.15, "dhD": 0.5})
    assert lp.analyse(*p1)["pass"] is False and lp.analyse(*p2)["pass"] is False
    pooled = lp.analyse_pooled([p1, p2])
    assert pooled["n_pairs"] == 2 and pooled["n_distinct_compared"] == 4
    assert pooled["within_hashes"] == ["dhA", "dhB", "dhC"]
    assert pooled["pass"] is True and pooled["gate"] == "CP-7b"


def test_pooled_counts_a_repeated_hash_once(tmp_path):
    p1 = _named_pair(tmp_path, "p1", {"dhA": 0.05, "dhB": 0.10})
    p2 = _named_pair(tmp_path, "p2", {"dhA": 0.01, "dhB": 0.3})
    pooled = lp.analyse_pooled([p1, p2])
    assert pooled["n_distinct_compared"] == 2 and pooled["n_within_0p2"] == 2
    assert pooled["pass"] is False


def test_pooled_cli_and_usage_errors(tmp_path):
    p1 = _named_pair(tmp_path, "p1", {"dhA": 0.05, "dhB": 0.10})
    p2 = _named_pair(tmp_path, "p2", {"dhC": 0.15})
    proc = run_cli("lane_parity", ["--pair", f"{p1[0]},{p1[1]}", "--pair", f"{p2[0]},{p2[1]}"],
                   tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(tmp_path / "out", "lane_parity")
    assert doc["mode"] == "pooled" and doc["pass"] is True
    bad = run_cli("lane_parity", ["--gpu", str(p1[0]), "--pair", f"{p2[0]},{p2[1]}"], tmp_path, "o2")
    assert bad.returncode == 2
    bad = run_cli("lane_parity", ["--pair", str(p1[0])], tmp_path, "o3")
    assert bad.returncode == 2
