"""A/B check: Boundary Lab export parsing (GUI text, balloon folder, headless run) and generic CSV."""
import numpy as np
import pytest

from hornlab_search.compare import bl_import as bi, fake


@pytest.fixture(scope="module")
def gui(tmp_path_factory):
    d = tmp_path_factory.mktemp("gui")
    fake.write_bl_gui_side(d, fake.FAKE_FREQS[:24])
    return d


@pytest.fixture(scope="module")
def headless(tmp_path_factory):
    d = tmp_path_factory.mktemp("hl")
    fake.write_bl_headless_side(d, fake.FAKE_FREQS[:24])
    return d


def test_gui_folder_import_shapes_levels_and_notes(gui):
    d = bi.import_bl(gui)
    assert d.level == "normalized" and d.source == "boundary_lab"
    assert d.angles_deg.min() == -90.0 and d.angles_deg.max() == 90.0       # -180..180 cropped to the +-90 compare range
    assert d.spl_h_db.shape == (24, d.angles_deg.size)
    assert abs(d.spl_h_db[:, d.axis_index]).max() < 1e-9                    # normalized: 0 dB on axis
    assert d.axis_db_absolute() is not None and d.on_axis_phase_deg is not None
    assert d.balloon_dirs.shape[1] == 3 and d.meta["clip_db"] == [-90.0, 30.0]
    assert d.balloon_kind == "fibonacci"
    assert d.z_norm is not None
    assert any("NORMALIZED" in n for n in d.meta["notes"])
    assert d.meta["axis_phase_aligned"] is True


def test_gui_polar_values_match_the_source_field(gui):
    d = bi.import_bl(gui)
    f = d.freqs_hz
    p = fake.truth_p(f, fake.arc_dirs(d.angles_deg, "H"))
    want = 20 * np.log10(np.abs(p) / np.abs(p[:, [d.axis_index]]))
    assert np.abs(d.spl_h_db - want).max() < 0.0006                           # 3-decimal text rounding only
    ph = np.angle(p / p[:, [d.axis_index]], deg=True)
    dphi = (d.phase_h_deg - ph + 180) % 360 - 180
    assert np.abs(dphi).max() < 0.0006


def test_headless_import_complex_data_and_impedance(headless):
    d = bi.import_bl(headless)
    assert d.level == "absolute" and d.p_h is not None and d.meta["route"] == "headless"
    assert d.meta["distance_m"] == 2.0
    f = d.freqs_hz
    want = fake.truth_p(f, fake.arc_dirs(d.angles_deg, "H"))
    assert np.allclose(d.p_h, want, rtol=2e-6)                                # complex64 storage
    assert np.allclose(d.z_norm, fake.truth_z(f), atol=1e-5)                  # N s / m  ->  Z / (rho c Sd)
    assert d.balloon_spl_db.shape == (24, 1500)


def test_gui_and_headless_routes_agree_on_the_same_field(gui, headless):
    g, h = bi.import_bl(gui), bi.import_bl(headless)
    assert np.abs(g.axis_db_absolute() - h.axis_db_absolute()).max() < 0.0006
    hn = h.normalized("H")
    assert np.abs(g.normalized("H") - hn).max() < 0.0007
    pa, pb = g.axis_phase_aligned_deg(), h.axis_phase_aligned_deg()
    assert np.abs((pa - pb + 180) % 360 - 180).max() < 0.01


def test_resultsfolder_prefers_headless_run(tmp_path):
    fake.write_bl_gui_side(tmp_path, fake.FAKE_FREQS[:8])
    fake.write_bl_headless_side(tmp_path / "headless_run", fake.FAKE_FREQS[:8])
    d = bi.import_bl(tmp_path)
    assert d.meta["route"] == "headless" and any("headless run is used" in n for n in d.meta["notes"])


def test_incomplete_headless_run_uses_completed_frequencies(tmp_path):
    import json
    fake.write_bl_headless_side(tmp_path, fake.FAKE_FREQS[:8])
    man = json.loads((tmp_path / "manifest.json").read_text())
    man["results"][5:] = [None] * 3
    man["status"] = "failed"
    (tmp_path / "manifest.json").write_text(json.dumps(man))
    d = bi.import_bl(tmp_path)
    assert d.freqs_hz.size == 5 and any("incomplete" in n for n in d.meta["notes"])


def test_polar_import_problem_messages(tmp_path):
    (tmp_path / "H 10.txt").write_text("100\t0.0\n200\t-1.0\n")
    with pytest.raises(bi.ImportProblem, match="0 degree"):
        bi.import_polar_dir(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(bi.ImportProblem, match="no files named"):
        bi.import_polar_dir(empty)


def test_frequency_mismatch_between_files_is_refused(gui, tmp_path):
    import shutil
    shutil.copytree(gui, tmp_path / "g")
    f = tmp_path / "g" / "on_axis" / "on_axis.txt"
    f.write_text("\n".join(f.read_text().splitlines()[:-1]) + "\n")
    with pytest.raises(bi.ImportProblem, match="frequency list differs"):
        bi.import_bl(tmp_path / "g")


def test_tabular_impedance_normalization(tmp_path):
    p = tmp_path / "z.txt"
    p.write_text("# Boundary Lab - Acoustic Impedance\n# Frequency (Hz)\tSrc Real (N*s/m)\tSrc Imag (N*s/m)\n100\t415\t-83\n200\t830\t0\n")
    z = bi.import_tabular_impedance(p, area_m2=0.001, rho=1.21, c=343.0)
    assert np.allclose(z["z"], np.array([415 - 83j, 830]) / (1.21 * 343.0 * 0.001))
    with pytest.raises(bi.ImportProblem, match="driven area"):
        bi.import_tabular_impedance(p)


def test_generic_csv_import_never_invents_values(tmp_path):
    (tmp_path / "p.csv").write_text("freq_hz,plane,angle_deg,spl_db\n"
                                    "100,H,-10,-1\n100,H,0,0\n100,H,10,-1\n200,H,-10,-2\n200,H,0,0\n200,H,10,-2\n")
    d = bi.import_generic_csv(polar_csv=tmp_path / "p.csv", level="normalized")
    assert d.spl_h_db.shape == (2, 3) and d.spl_v_db is None
    (tmp_path / "bad.csv").write_text("freq_hz,plane,angle_deg,spl_db\n100,H,-10,-1\n100,H,0,0\n200,H,0,0\n")
    with pytest.raises(bi.ImportProblem, match="missing"):
        bi.import_generic_csv(polar_csv=tmp_path / "bad.csv")
    (tmp_path / "ax.csv").write_text("# f spl phase\n100 90 10\n200 91 20\n")
    d2 = bi.import_generic_csv(on_axis_csv=tmp_path / "ax.csv", distance_m=2.0)
    assert d2.on_axis_spl_db.tolist() == [90.0, 91.0]
