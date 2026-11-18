"""Inventory tests for ``hornlab_search.system.horn_assets`` (Stage 1, Lane A).

Synthetic fixtures are written under ``tmp_path`` in the real solve-cache format
(``response.npz`` written by ``solve.cache.save_response``, ``status.json`` beside it) so the
inventory is exercised through the official loader and the real ``HornAsset`` API.

SYS-12 is covered here: two consecutive audits are byte-identical and the scanned tree is
byte-for-byte unchanged (directory snapshot hash before/after).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.solve import cache
from hornlab_search.system import contracts as C
from hornlab_search.system import horn_assets as H
from hornlab_search.types import Response

REPO = Path(__file__).resolve().parents[2]
CLI_PATH = REPO / "tools" / "system" / "audit_saved_horns.py"

REAL_ACCEL_META = {
    "distance_m": 2.0,
    "angle_convention": "ascending -90..+90 deg",
    "spl_reference": "absolute dB re 20 uPa for unit normal acceleration of tag 2",
    "z_throat_convention": "exp(-i*omega*t); z = Z_specific/(rho*c); mass-like loading has Im < 0",
}
VELOCITY_META = {
    "distance_m": 2.0,
    "spl_reference": "absolute dB re 20 uPa for unit normal velocity of tag 2",
    "z_throat_convention": "exp(+i*omega*t); z = Z_specific/(rho*c)",
}


# --------------------------------------------------------------------------- fixtures


def _balloon_dirs(nb: int) -> np.ndarray:
    raw = np.array([
        [0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
        [1.0, 1.0, 0.0], [-1.0, 1.0, 0.0], [1.0, -1.0, 0.0],
    ])[:nb]
    return raw / np.linalg.norm(raw, axis=1, keepdims=True)


def make_response(meta: dict | None = None, *, complex_fields: bool = True,
                  freqs: tuple[float, ...] = (500.0, 1000.0, 2000.0)) -> Response:
    nf, na, nb = len(freqs), 5, 6
    p = np.full((nf, na), 1.0 + 0.5j, dtype=complex)
    return Response(
        freqs_hz=np.asarray(freqs, dtype=float),
        h_angles_deg=np.linspace(-90.0, 90.0, na),
        v_angles_deg=np.linspace(-90.0, 90.0, na),
        spl_h_db=np.full((nf, na), 90.0),
        spl_v_db=np.full((nf, na), 89.0),
        balloon_dirs=_balloon_dirs(nb),
        spl_balloon_db=np.full((nf, nb), 88.0),
        z_throat=np.full(nf, 0.5 + 0.1j, dtype=complex),
        p_h=p if complex_fields else None,
        p_v=p if complex_fields else None,
        p_balloon=np.full((nf, nb), 0.4 - 0.2j, dtype=complex) if complex_fields else None,
        backend="beat_cuda",
        n_dof=451,
        meta=dict(meta or {}),
    )


def make_run(root: Path, name: str = "run") -> Path:
    run = root / name
    (run / "designs").mkdir(parents=True, exist_ok=True)
    return run


def make_design(run: Path, name: str, resp: Response | None = None,
                status: dict | None = None, *, mesh: bool = False) -> Path:
    design = run / "designs" / name
    design.mkdir(parents=True, exist_ok=True)
    if resp is not None:
        cache.save_response(design / "response.npz", resp)
    if status is not None:
        (design / "status.json").write_text(json.dumps(status), encoding="utf-8")
    if mesh:
        (design / "mesh.msh").write_bytes(b"$MeshFormat\n2.2 0 8\n$EndMeshFormat\n")
    return design


def _ok_status(design_hash: str = "0123456789ab") -> dict:
    return {"ok": True, "key": f"{design_hash}-" + "a" * 12 + "-" + "b" * 12}


def _load_cli():
    spec = importlib.util.spec_from_file_location("audit_saved_horns_tool", CLI_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _snapshot(root: Path) -> tuple:
    entries = []
    for path in sorted(root.rglob("*")):
        stat = path.stat()
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            entries.append((rel, "dir", stat.st_mtime_ns))
        else:
            entries.append((rel, "file", stat.st_size, stat.st_mtime_ns,
                            hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(entries)


# --------------------------------------------------------------------------- field inventory


def test_complex_fields_are_inventoried_and_basis_unverified(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    make_design(run, "0123456789ab", make_response(REAL_ACCEL_META), _ok_status())

    result = H.inventory_runs(tmp_path)
    assert result.runs_scanned == 1 and result.design_dirs_scanned == 1
    assert len(result.assets) == 1
    asset = result.assets[0]
    assert {"p_h", "p_v", "p_balloon", "spl_h_db", "spl_v_db", "spl_balloon_db",
            "balloon_dirs", "z_throat"} <= set(asset.available_fields)
    assert asset.freqs_hz == (500.0, 1000.0, 2000.0)
    # complex arrays exist, but the stored basis (unit normal acceleration, exp(-i wt)) cannot
    # be expressed as the system contract's basis: never impute phase.
    assert asset.quality == "MAGNITUDE_ONLY"
    assert asset.source_basis is None
    assert "basis unverified" in asset.geometry.extra["data_quality"]
    with pytest.raises(C.PhaseUnavailable):
        asset.require_complex()


def test_proven_basis_yields_exact_complex(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    make_design(run, "0123456789ab", make_response(VELOCITY_META), _ok_status())

    asset = H.inventory_runs(tmp_path).assets[0]
    assert asset.quality == "EXACT_COMPLEX"
    basis = asset.require_complex()
    assert basis.per_input == "normal_velocity_mps"
    assert basis.time_convention == C.TIME_CONVENTION
    assert basis.distance_m == 2.0
    assert basis.angular_frame == "hornfab_cuts_hv"


def test_magnitude_only_response_is_classified(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    make_design(run, "0123456789ab", make_response(REAL_ACCEL_META, complex_fields=False),
                _ok_status())

    asset = H.inventory_runs(tmp_path).assets[0]
    assert asset.quality == "MAGNITUDE_ONLY"
    assert asset.has_complex is False
    assert "spl_h_db" in asset.available_fields and "p_h" not in asset.available_fields
    assert asset.source_basis is None
    with pytest.raises(C.PhaseUnavailable):
        asset.require_complex()


def test_failed_status_is_stale_source(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    make_design(run, "0123456789ab", make_response(REAL_ACCEL_META),
                {"ok": False, "error": "solver exploded", "key": "0123456789ab-aaaaaaaaaaaa-bbbbbbbbbbbb"})

    asset = H.inventory_runs(tmp_path).assets[0]
    assert asset.quality == "STALE_SOURCE"
    assert asset.geometry.extra["provenance"] == H.PROVENANCE_FAILED
    assert "ok=false" in asset.geometry.extra["data_quality"]
    assert "solver exploded" in asset.geometry.extra["data_quality"]


def test_mesh_only_design_is_geometry_only(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    make_design(run, "0123456789ab", mesh=True)

    asset = H.inventory_runs(tmp_path).assets[0]
    assert asset.quality == "GEOMETRY_ONLY"
    assert asset.available_fields == frozenset()
    assert asset.freqs_hz == ()
    mesh_path = asset.mesh_path
    assert mesh_path is not None
    assert Path(mesh_path).is_file()
    assert asset.source_basis is None


def test_malformed_complex_shape_is_incompatible(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    resp = make_response(REAL_ACCEL_META, freqs=(500.0, 1000.0, 2000.0))
    resp.p_h = np.zeros((2, 5), dtype=complex)          # nf is 3, not 2
    make_design(run, "0123456789ab", resp, _ok_status())

    asset = H.inventory_runs(tmp_path).assets[0]
    assert asset.quality == "INCOMPATIBLE"
    assert "malformed" in asset.geometry.extra["data_quality"]
    assert "p_h" in asset.geometry.extra["data_quality"]


# --------------------------------------------------------------------------- identity / dedupe


def test_byte_identical_run_dirs_dedupe_to_one_asset(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    first = make_design(run, "aaaa", make_response(REAL_ACCEL_META), {"ok": True})
    second = make_design(run, "bbbb", status={"ok": True})
    # byte-identical response and status, no cache key: identity must fall back to content hashes
    (second / "response.npz").write_bytes((first / "response.npz").read_bytes())
    (second / "status.json").write_bytes((first / "status.json").read_bytes())

    result = H.inventory_runs(tmp_path)
    assert len(result.assets) == 1
    assert result.duplicates_collapsed == 1
    # deterministic representative: lexicographically smallest response path
    assert result.assets[0].response_path.endswith("aaaa\\response.npz") or \
        result.assets[0].response_path.endswith("aaaa/response.npz")


def test_identical_cache_key_dedupes_even_with_different_bytes(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    status = _ok_status("0123456789ab")
    first = make_design(run, "0123456789ab", make_response(REAL_ACCEL_META), status)
    second = make_design(run, "0123456789ab_copy", make_response(REAL_ACCEL_META), status)
    # different npz bytes (different zip timestamps are fine) but the same key identity
    assert (first / "response.npz").is_file() and (second / "response.npz").is_file()

    result = H.inventory_runs(tmp_path)
    assert len(result.assets) == 1
    assert result.duplicates_collapsed == 1
    assert result.assets[0].geometry.physical_solve_id is not None


def test_limit_scans_newest_run_directories(tmp_path: Path) -> None:
    for index, name in enumerate(("old", "middle", "new")):
        run = make_run(tmp_path, name)
        design_hash = f"{index:012x}"
        make_design(run, design_hash, make_response(REAL_ACCEL_META), _ok_status(design_hash))
        stamp = 1_700_000_000 + index
        os.utime(run, (stamp, stamp))

    result = H.inventory_runs(tmp_path, limit=2)
    assert result.runs_scanned == 2
    scanned_runs = set()
    for asset in result.assets:
        run_dir = asset.geometry.run_dir
        assert run_dir is not None
        scanned_runs.add(Path(run_dir).name)
    assert scanned_runs == {"middle", "new"}


def test_default_runs_root_honours_environment(monkeypatch: pytest.MonkeyPatch,
                                               tmp_path: Path) -> None:
    monkeypatch.setenv(H.RUNS_ROOT_ENV, str(tmp_path))
    assert H.default_runs_root() == tmp_path
    monkeypatch.delenv(H.RUNS_ROOT_ENV)
    assert H.default_runs_root() == Path(H.DEFAULT_RUNS_ROOT)


# --------------------------------------------------------------------------- SYS-12 audit


def test_audit_is_read_only_and_byte_identical(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = make_run(tmp_path)
    make_design(run, "complex", make_response(REAL_ACCEL_META), _ok_status("aaaaaaaaaaaa"))
    make_design(run, "mag", make_response(REAL_ACCEL_META, complex_fields=False), _ok_status("bbbbbbbbbbbb"))
    make_design(run, "mesh", mesh=True)
    cli = _load_cli()
    args = ["--runs-root", str(tmp_path), "--limit", "10", "--json"]

    before = _snapshot(tmp_path)
    assert cli.main(args) == 0
    first = capsys.readouterr().out
    assert cli.main(args) == 0
    second = capsys.readouterr().out
    after = _snapshot(tmp_path)

    assert first == second, "audit JSON is not deterministic"
    assert before == after, "audit wrote into the scanned tree"
    payload = json.loads(first)
    assert payload["runs_scanned"] == 1
    assert payload["assets_total"] == 3
    assert payload["by_quality"]["MAGNITUDE_ONLY"] == 2
    assert payload["by_quality"]["GEOMETRY_ONLY"] == 1
    assert payload["with_complex_fields"] == 1   # the magnitude-only fixture has no p_* arrays
    assert payload["rows"] == sorted(payload["rows"], key=lambda row: row["asset_id"])


def test_cli_markdown_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = make_run(tmp_path)
    make_design(run, "complex", make_response(REAL_ACCEL_META), _ok_status())
    cli = _load_cli()
    assert cli.main(["--runs-root", str(tmp_path), "--limit", "1", "--md"]) == 0
    text = capsys.readouterr().out
    assert "# Saved-horn inventory (Tier 0)" in text
    assert "MAGNITUDE_ONLY" in text
