"""A/B check: CLI wiring, the demo, compare exit codes, and the reference solve with a fake backend (offline)."""
import json
from pathlib import Path

import numpy as np
import pytest

from hornlab_search import cli
from hornlab_search.compare import fake, hornfab_side as hs
from hornlab_search.compare.export_for_bl import export_for_bl
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace

EX = Path(__file__).resolve().parents[1] / "examples" / "osse_baseline.yaml"


def test_demo_fake_runs_end_to_end_and_proves_the_detector(tmp_path, capsys):
    rc = cli.main(["ab-bl", "demo", "--fake", "--out", str(tmp_path), "--inject", "offset6,conj", "--chart-backend", "builtin"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "none       PASS" in out and "offset6" in out and "constant_offset" in out and "time_convention" in out
    assert (tmp_path / "none" / "compare" / "report.html").exists() and (tmp_path / "bl_handoff" / "handoff.json").exists()
    assert json.loads((tmp_path / "offset6" / "compare" / "summary.json").read_text())["overall"] == "fail"


def test_demo_requires_fake_flag(capsys):
    assert cli.main(["ab-bl", "demo"]) == 2


def test_ab_bl_without_subcommand_prints_usage():
    assert cli.main(["ab-bl"]) == 2


def test_compare_exit_codes_and_workspace_layout(tmp_path, capsys):
    ws = tmp_path / "ws"
    fake.write_hornfab_side(ws / "hornfab_reference")
    fake.write_bl_gui_side(ws / "results_from_friend")
    assert cli.main(["ab-bl", "compare", "--workspace", str(ws), "--chart-backend", "builtin"]) == 0
    assert "A/B VERDICT: PASS" in capsys.readouterr().out
    fake.write_bl_gui_side(tmp_path / "bad", inject="offset6")
    rc = cli.main(["ab-bl", "compare", "--workspace", str(ws), "--bl", str(tmp_path / "bad"), "--out", str(tmp_path / "r2"),
                   "--chart-backend", "builtin"])
    assert rc == 11 and (tmp_path / "r2" / "report.html").exists()
    assert cli.main(["ab-bl", "compare", "--workspace", str(ws), "--bl", str(tmp_path / "bad"), "--out", str(tmp_path / "r3"),
                     "--chart-backend", "builtin", "--no-verdict-exit"]) == 0


def test_compare_custom_tolerances_and_bands(tmp_path, capsys):
    ws = tmp_path / "ws"
    fake.write_hornfab_side(ws / "hornfab_reference")
    fake.write_bl_gui_side(ws / "results_from_friend", inject="offset6")
    tol = tmp_path / "tol.json"
    tol.write_text(json.dumps({"on_axis_db": 7.0}))
    rc = cli.main(["ab-bl", "compare", "--workspace", str(ws), "--tolerances", str(tol), "--bands", "2000,8000",
                   "--chart-backend", "builtin"])
    s = json.loads((ws / "compare" / "summary.json").read_text())
    assert s["metrics"]["on_axis_abs"]["overall"] == "pass" and s["tolerances"]["on_axis_db"] == 7.0
    assert [b[0] for b in s["bands_hz"]] == ["<2000", "2000-8000", ">8000"]
    assert rc in (0, 10, 11)


def test_import_command_writes_normalized_data(tmp_path, capsys):
    ws = tmp_path / "ws"
    fake.write_bl_gui_side(ws / "results_from_friend", fake.FAKE_FREQS[:10])
    assert cli.main(["ab-bl", "import", "--workspace", str(ws)]) == 0
    assert (ws / "bl_normalized" / "abdata.npz").exists()
    assert "absolute on-axis=yes" in capsys.readouterr().out


def test_solve_reference_with_fake_backend_writes_durable_outputs(tmp_path):
    cfg = load_config(EX)
    design = DesignSpace.from_config(cfg).seed
    q = fake.fake_sphere_quarter_mesh(2)
    msh = tmp_path / "q.msh"
    from hornlab_search.compare.mshio import write_msh
    write_msh(q, msh)
    man = export_for_bl(None, tmp_path / "ho", cfg=cfg, design=design, mesh_path=msh, quadrants="1", label="sph")
    be = fake.FakeBackend()
    freqs = man["frequencies"]["freqs_hz"][::6]
    resp, rep = hs.solve_reference(cfg=cfg, design=design, out_dir=tmp_path / "ref", freqs_hz=freqs, angle_count=37,
                                   balloon_points=300, distance_m=2.0, mesh_path=tmp_path / "ho" / "mesh" / "horn_full_m.msh",
                                   quadrants="1234", backend=be, max_dof=8900)
    mesh, spec = be.calls[0]
    assert mesh.quadrants == "1234" and mesh.symmetry_plane is None          # the full handoff mesh, no solver symmetry
    assert spec.freqs_hz == tuple(freqs) and spec.observation.angle_count == 37 and spec.observation.balloon_points == 300
    assert spec.observation.distance_m == 2.0
    for name in ("response.npz", "reference_meta.json", "abdata/abdata.npz"):
        assert (tmp_path / "ref" / name).exists()
    a = hs.load_hornfab(tmp_path / "ref")
    assert a.p_h is not None and a.meta["reference_meta"]["mesh_scale"] == 1.0 and a.meta["quadrants"] == "1234"
    meta = json.loads((tmp_path / "ref" / "reference_meta.json").read_text())
    assert meta["design_hash"] == design.hash() and "UNIT NORMAL ACCELERATION" in meta["spl_reference"]


def test_solve_reference_refuses_oversize_mesh_and_dry_run_launches_nothing(tmp_path):
    cfg = load_config(EX)
    design = DesignSpace.from_config(cfg).seed
    msh = tmp_path / "q.msh"
    from hornlab_search.compare.mshio import write_msh
    write_msh(fake.fake_sphere_quarter_mesh(2), msh)
    man = export_for_bl(None, tmp_path / "ho", cfg=cfg, design=design, mesh_path=msh, quadrants="1", label="sph")
    full = tmp_path / "ho" / "mesh" / "horn_full_m.msh"
    with pytest.raises(ValueError, match="over --max-dof"):
        hs.solve_reference(cfg=cfg, design=design, out_dir=tmp_path / "r", freqs_hz=[1000.0, 2000.0], mesh_path=full,
                           quadrants="1234", backend=fake.FakeBackend(), max_dof=10)
    be = fake.FakeBackend()
    none, rep = hs.solve_reference(cfg=cfg, design=design, out_dir=tmp_path / "r2", freqs_hz=[1000.0, 2000.0], mesh_path=full,
                                   quadrants="1234", backend=be, max_dof=8900, dry_run=True)
    assert none is None and not be.calls and rep["est_dof"] > 0 and rep["n_freqs"] == 2


def test_solve_command_end_to_end_with_fake_backend(tmp_path, monkeypatch, capsys):
    cfg = load_config(EX)
    design = DesignSpace.from_config(cfg).seed
    msh = tmp_path / "q.msh"
    from hornlab_search.compare.mshio import write_msh
    write_msh(fake.fake_sphere_quarter_mesh(2), msh)
    ws = tmp_path / "ws"
    export_for_bl(str(EX), ws / "bl_handoff", cfg=cfg, design=design, mesh_path=msh, quadrants="1", label="sph",
                  lo_hz=100, hi_hz=1600, points_per_octave=1, balloon_points=200, angle_count=19)
    monkeypatch.setattr(cli, "_backend", lambda cfg: fake.FakeBackend())
    from hornlab_search.solve import worker
    monkeypatch.setattr(worker, "shutdown", lambda **kw: [])
    monkeypatch.setattr(worker, "vram_used_mib", lambda: 412.0)
    runs = tmp_path / "runs"
    rc = cli.main(["ab-bl", "solve", "--workspace", str(ws), "--dry-run"])
    assert rc == 0 and "solve dry-run" in capsys.readouterr().out
    rc = cli.main(["ab-bl", "--runs-dir", str(runs), "solve", "--workspace", str(ws)])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "VRAM baseline before the solve: 412 MiB" in out and "solve OK" in out
    assert (ws / "hornfab_reference" / "response.npz").exists()
    ref = hs.load_hornfab(ws / "hornfab_reference")
    assert ref.freqs_hz.size == 5 and ref.angles_deg.size == 19
