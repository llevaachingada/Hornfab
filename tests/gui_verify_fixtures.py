"""Synthetic run-folder fixtures for GUI verify-view tests (WP0).

``make_runs(tmp)`` writes a minimal but complete set of run folders under
``tmp/runs/`` that cover every verify-storage layout the GUI must handle:

* R_SCREEN  — a plain screen run with 8 ok + 1 failed row, an inline verify/
              subtree, and a gate-audit CSV.
* R_LINKED  — a linked verify run (run.json.mode == "verify", verify_of.run
              is an absolute path from another machine; basename matches).
* R_ORPHAN  — a linked verify run whose verify_of.run points at a missing folder.
* R_STANDALONE — a standalone verify-search run (mode=="verify", no verify_of),
                 budget 1, one row.
* R_XBAND   — screen run + inline verify whose verify metrics.freqs_hz covers
              a different band → comparable:false.

No solver is imported; all files are written from literal Python dicts/arrays.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

# ── run id constants ──────────────────────────────────────────────────────────
R_SCREEN     = "20261112T120000Z-screen-aaa111"
R_LINKED     = "20261112T130000Z-verify-bbb222"
R_ORPHAN     = "20261112T140000Z-verify-ccc333"
R_STANDALONE = "20261112T150000Z-verify-ddd444"
R_XBAND      = "20261112T160000Z-screen-eee555"

# hashes used in R_SCREEN (12 hex chars; must match HASH regex ^[0-9a-f]{6,40}$)
H = {
    "a1": "a1a1a1a1a1a1",
    "a2": "a2a2a2a2a2a2",
    "a3": "a3a3a3a3a3a3",
    "a4": "a4a4a4a4a4a4",
    "a5": "a5a5a5a5a5a5",
    "a6": "a6a6a6a6a6a6",
    "a7": "a7a7a7a7a7a7",
    "a8": "a8a8a8a8a8a8",
    "xb": "xbxbxbxbxbxb",   # R_XBAND
}

# hashes used in R_LINKED / R_STANDALONE
H_LINKED1 = "b1b1b1b1b1b1"
H_LINKED2 = "b2b2b2b2b2b2"
H_STAND   = "d1d1d1d1d1d1"

# inline verify hashes (subset of R_SCREEN's top-5)
VH = [H["a1"], H["a2"], H["a3"], H["a4"]]  # a5 intentionally unverified

# ── helpers ───────────────────────────────────────────────────────────────────

_CONFIG_BASE = {
    "name": "fixture_screen",
    "family": "OSSE",
    "bounds": {"L_mm": {"lo": 100.0, "hi": 200.0}, "a_deg": {"lo": 30.0, "hi": 50.0}},
    "search": {"algorithm": "cma", "budget": 20, "seed": 1},
    "mesh": {"epw": 6.0, "quadrants": "1"},
    "solve": {"backend": "beat_cpu"},
    "target": {"band_lo_hz": 300, "band_hi_hz": 8000},
    "objective": {"version": 4},
}


def _write_response_npz(path: Path, n_freqs: int, grid: tuple[int, int]) -> None:
    """Write a minimal response.npz with the fields the GUI data layer reads."""
    nT, nP = grid
    n_pts = nT * nP
    rng = np.random.default_rng(42)
    freqs = np.linspace(300, 8000, n_freqs, dtype=float)
    spl_balloon = rng.uniform(-20, 0, size=(n_freqs, n_pts)).astype(np.float32)
    spl_h = rng.uniform(-20, 0, size=(n_freqs, 18)).astype(np.float32)
    spl_v = rng.uniform(-20, 0, size=(n_freqs, 18)).astype(np.float32)
    angles = np.linspace(-85, 85, 18, dtype=float)
    meta = json.dumps({
        "balloon_grid": list(grid),
        "balloon_layout": "theta_phi",
        "distance_m": 1.0,
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        str(path),
        freqs_hz=freqs,
        spl_balloon_db=spl_balloon,
        spl_h_db=spl_h,
        spl_v_db=spl_v,
        h_angles_deg=angles,
        v_angles_deg=angles,
        meta=meta,
        n_dof=np.int64(2200),
        z_throat=np.ones(n_freqs, dtype=complex),
    )


def _write_metrics_json(path: Path, n_freqs: int, band_lo: int = 300,
                        band_hi: int = 8000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    freqs = list(np.linspace(band_lo, band_hi, n_freqs, dtype=float))
    path.write_text(json.dumps({
        "freqs_hz": freqs,
        "bw_h_deg": [80.0] * n_freqs,
        "bw_v_deg": [60.0] * n_freqs,
        "di_db": [10.0] * n_freqs,
        "on_axis_db": [0.0] * n_freqs,
        "ripple_h_db": [1.0] * n_freqs,
        "ripple_v_db": [1.0] * n_freqs,
        "z_throat_real": [1.0] * n_freqs,
        "di_source": "balloon",
        "scalars": {},
    }), encoding="utf-8")


def _screen_row(n: int, h: str, j: float, *, mode: str = "screen") -> dict:
    return {
        "n": n,
        "design_hash": h,
        "ok": True,
        "objective": j,
        "mode": mode,
        "family": "OSSE",
        "params": {"L_mm": 150.0, "a_deg": 40.0},
        "created_utc": f"2026-11-12T12:00:{n:02d}Z",
        "n_dof": 2200,
        "n_triangles": 4000,
        "res_mm": 5.0,
        "peak_vram_mb": 500,
        "seconds": 10.0,
        "quadrants": "1",
    }


def _verify_row(n: int, h: str, j: float, objective_version: int = 4,
                *, include_lane: bool = False, error: str | None = None,
                band_lo: int = 300) -> dict:
    row: dict = {
        "n": n,
        "design_hash": h,
        "ok": error is None,
        "objective": j if error is None else None,
        "mode": "verify",
        "family": "OSSE",
        "params": {"L_mm": 150.0, "a_deg": 40.0},
        "created_utc": f"2026-11-12T14:00:{n:02d}Z",
        "n_dof": 2200,
        "n_triangles": 4200,
        "res_mm": 3.0,
        "peak_vram_mb": 600,
        "seconds": 15.0,
        "quadrants": "1",
    }
    if error is not None:
        row["error"] = error
    if include_lane:
        row["lane"] = "gpu"
        row["backend"] = "beat_cuda"
    if band_lo != 300:
        row["band_lo_hz"] = band_lo
    return row


# ── public entry point ─────────────────────────────────────────────────────────


def make_runs(tmp: Path) -> dict:
    """Write all synthetic run folders under ``tmp/runs/`` and return ids/hashes.

    Returns a dict with keys:
      R_SCREEN, R_LINKED, R_ORPHAN, R_STANDALONE, R_XBAND   — run id strings
      hashes                                                 — the H dict above
      H_LINKED1, H_LINKED2, H_STAND                         — verify hashes
    """
    runs = tmp / "runs"
    runs.mkdir(parents=True, exist_ok=True)

    # ── R_SCREEN ──────────────────────────────────────────────────────────────
    _make_screen_run(runs)

    # ── R_LINKED ──────────────────────────────────────────────────────────────
    _make_linked_run(runs, R_LINKED, R_SCREEN, missing=False)

    # ── R_ORPHAN ──────────────────────────────────────────────────────────────
    _make_linked_run(runs, R_ORPHAN, "20261112T120000Z-screen-ffffff", missing=True)

    # ── R_STANDALONE ──────────────────────────────────────────────────────────
    _make_standalone_run(runs)

    # ── R_XBAND ───────────────────────────────────────────────────────────────
    _make_xband_run(runs)

    # ── gate-audit CSV ────────────────────────────────────────────────────────
    _make_gate_audit(tmp)

    return {
        "R_SCREEN": R_SCREEN,
        "R_LINKED": R_LINKED,
        "R_ORPHAN": R_ORPHAN,
        "R_STANDALONE": R_STANDALONE,
        "R_XBAND": R_XBAND,
        "hashes": H,
        "H_LINKED1": H_LINKED1,
        "H_LINKED2": H_LINKED2,
        "H_STAND": H_STAND,
        "VH": VH,
    }


# ── private builders ──────────────────────────────────────────────────────────


def _make_screen_run(runs: Path) -> None:
    run = runs / R_SCREEN
    run.mkdir(parents=True, exist_ok=True)

    import yaml  # already a project dep
    (run / "config.yaml").write_text(yaml.safe_dump(_CONFIG_BASE), encoding="utf-8")
    (run / "run.json").write_text(json.dumps({
        "mode": "screen",
        "backend": "beat_cpu",
        "objective_version": 4,
    }), encoding="utf-8")

    # 8 ok rows with objective values such that a1 is "best" (lowest J)
    js = [4.40, 4.55, 4.62, 4.70, 4.80, 4.90, 5.00, 5.10]
    rows = [_screen_row(i, H[f"a{i+1}"], js[i]) for i in range(8)]
    # one failed row
    rows.append({
        "n": 8, "design_hash": "ffffffffffffffff", "ok": False,
        "objective": None, "mode": "screen", "family": "OSSE",
        "params": {}, "created_utc": "2026-11-12T12:00:08Z",
        "error": "mesh_too_large",
    })
    (run / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    # designs/ for top 3 screen hashes
    for h in [H["a1"], H["a2"], H["a3"]]:
        d = run / "designs" / h
        d.mkdir(parents=True, exist_ok=True)
        _write_metrics_json(d / "metrics.json", n_freqs=12)
        _write_response_npz(d / "response.npz", n_freqs=12, grid=(16, 32))
        (d / "design.json").write_text(json.dumps({
            "family": "OSSE",
            "params": {"L_mm": 150.0, "a_deg": 40.0},
        }), encoding="utf-8")

    # ── inline verify/ subtree ────────────────────────────────────────────────
    verify_dir = run / "verify"
    verify_dir.mkdir(parents=True, exist_ok=True)

    # 4 verify rows for a1–a4; no lane/backend (legacy)
    # a1 verified twice: n=0 and n=3 (second has different objective version → still matches)
    # a2–a4: n=1,2,3
    verify_rows = [
        _verify_row(0, H["a1"], 4.62),
        _verify_row(1, H["a2"], 4.78),
        _verify_row(2, H["a3"], 4.85),
        _verify_row(3, H["a4"], 4.95),
        # duplicate of a1 with higher n — this is the "latest n wins" row
        _verify_row(5, H["a1"], 4.60),  # n=5 > n=0, so this is the keeper
        # one failed row
        {
            "n": 4, "design_hash": H["a5"],
            "ok": False, "objective": None, "mode": "verify",
            "family": "OSSE", "params": {}, "created_utc": "2026-11-12T14:00:04Z",
            "error": "mesh_too_large",
        },
    ]
    (verify_dir / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in verify_rows) + "\n", encoding="utf-8")

    # designs/ inside verify/ for a1–a4 (29 freqs, 23×45 grid)
    for h in VH:
        d = verify_dir / "designs" / h
        d.mkdir(parents=True, exist_ok=True)
        _write_metrics_json(d / "metrics.json", n_freqs=29)
        _write_response_npz(d / "response.npz", n_freqs=29, grid=(23, 45))
        (d / "status.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        (d / "design.json").write_text(json.dumps({"family": "OSSE", "params": {}}), encoding="utf-8")


def _make_linked_run(runs: Path, run_id: str, parent_id: str, missing: bool) -> None:
    run = runs / run_id
    run.mkdir(parents=True, exist_ok=True)

    if missing:
        # Points to a path that does not exist on this machine
        verify_of_run = r"C:\abs\elsewhere\runs\\" + parent_id
    else:
        # Absolute path from another machine — basename must match the parent
        verify_of_run = r"C:\abs\elsewhere\runs\\" + parent_id

    (run / "run.json").write_text(json.dumps({
        "mode": "verify",
        "backend": "beat_cpu",
        "objective_version": 4,
        "verify_of": {
            "run": verify_of_run,
            "top": 5,
            "brief": "x.yaml",
        },
        "status": "finished",
    }), encoding="utf-8")

    verify_rows = [
        _verify_row(0, H_LINKED1, 4.65, include_lane=True),
        _verify_row(1, H_LINKED2, 4.75, include_lane=True),
    ]
    (run / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in verify_rows) + "\n", encoding="utf-8")

    for h in [H_LINKED1, H_LINKED2]:
        d = run / "designs" / h
        d.mkdir(parents=True, exist_ok=True)
        _write_metrics_json(d / "metrics.json", n_freqs=29)
        _write_response_npz(d / "response.npz", n_freqs=29, grid=(23, 45))


def _make_standalone_run(runs: Path) -> None:
    run = runs / R_STANDALONE
    run.mkdir(parents=True, exist_ok=True)

    import yaml
    cfg = dict(_CONFIG_BASE)
    cfg["name"] = "fixture_standalone_verify"
    cfg["search"] = {"algorithm": "cma", "budget": 1, "seed": 1}
    (run / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    (run / "run.json").write_text(json.dumps({
        "mode": "verify",
        "backend": "beat_cpu",
        "objective_version": 4,
        "status": "finished",
    }), encoding="utf-8")

    rows = [_verify_row(0, H_STAND, 4.85)]
    (run / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    d = run / "designs" / H_STAND
    d.mkdir(parents=True, exist_ok=True)
    _write_metrics_json(d / "metrics.json", n_freqs=29)
    _write_response_npz(d / "response.npz", n_freqs=29, grid=(23, 45))


def _make_xband_run(runs: Path) -> None:
    """Screen run + inline verify whose metrics.freqs_hz covers a different band."""
    run = runs / R_XBAND
    run.mkdir(parents=True, exist_ok=True)

    import yaml
    cfg = dict(_CONFIG_BASE)
    cfg["name"] = "fixture_xband"
    (run / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    (run / "run.json").write_text(json.dumps({
        "mode": "screen",
        "backend": "beat_cpu",
        "objective_version": 4,
    }), encoding="utf-8")

    rows = [_screen_row(0, H["xb"], 4.80)]
    (run / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    d = run / "designs" / H["xb"]
    d.mkdir(parents=True, exist_ok=True)
    _write_metrics_json(d / "metrics.json", n_freqs=12, band_lo=300, band_hi=8000)
    _write_response_npz(d / "response.npz", n_freqs=12, grid=(16, 32))

    # inline verify — different band (12k instead of 8k)
    verify_dir = run / "verify"
    verify_dir.mkdir(parents=True, exist_ok=True)
    verify_rows = [_verify_row(0, H["xb"], 5.10, band_lo=1000)]
    (verify_dir / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in verify_rows) + "\n", encoding="utf-8")

    d_v = verify_dir / "designs" / H["xb"]
    d_v.mkdir(parents=True, exist_ok=True)
    # Different band: 1k–12k Hz instead of 300–8k Hz
    _write_metrics_json(d_v / "metrics.json", n_freqs=29, band_lo=1000, band_hi=12000)
    _write_response_npz(d_v / "response.npz", n_freqs=29, grid=(23, 45))


def _make_gate_audit(tmp: Path) -> None:
    audit_dir = tmp / "docs" / "data" / "gate_audit_test"
    audit_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "run,tier,design,J,throat,load,pass_all\n",
        f"{R_SCREEN},screen,{H['a1']},4.40,True,False,False\n",
        f"{R_SCREEN},verify,{H['a2']},4.78,True,True,True\n",
        f"{R_SCREEN},screen,{H['a3']},4.62,False,True,False\n",
    ]
    (audit_dir / "gate_audit.csv").write_text("".join(lines), encoding="utf-8")
