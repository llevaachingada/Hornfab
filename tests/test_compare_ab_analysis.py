"""A/B check: alignment, beamwidth / DI against closed forms, band statistics, verdicts, tolerances."""
import numpy as np
import pytest

from hornlab_search.compare import analysis as an, fake
from hornlab_search.compare.model import AbData
from hornlab_search.metrics.di import target_di_gaussian_db


def _gauss_data(label, freqs, bw_h=80.0, bw_v=50.0, offset_db=0.0, step=2.5, nb=0, balloon_kind="fibonacci"):
    ang = np.arange(-90, 90 + step / 2, step)
    h = -6.0206 * (ang / (bw_h / 2)) ** 2
    v = -6.0206 * (ang / (bw_v / 2)) ** 2
    nf = len(freqs)
    kw = {}
    if nb:
        dirs = fake.fibonacci(nb)
        ah = np.degrees(np.arctan2(dirs[:, 0], dirs[:, 2]))
        av = np.degrees(np.arctan2(dirs[:, 1], dirs[:, 2]))
        b = -6.0206 * ((ah / (bw_h / 2)) ** 2 + (av / (bw_v / 2)) ** 2)
        kw = dict(balloon_dirs=dirs, balloon_spl_db=np.tile(b + 100 + offset_db, (nf, 1)), balloon_kind=balloon_kind)
    return AbData(label, "t", np.asarray(freqs, float), ang, spl_h_db=np.tile(h + 100 + offset_db, (nf, 1)),
                  spl_v_db=np.tile(v + 100 + offset_db, (nf, 1)), meta={"distance_m": 2.0}, **kw)


F = np.geomspace(100, 20000, 40)


def test_beamwidth_and_di_follow_closed_forms():
    d = an.derive(_gauss_data("g", F, 80.0, 50.0, nb=6000))
    assert d.bw_h[0] == pytest.approx(80.0, abs=0.05) and d.bw_v[0] == pytest.approx(50.0, abs=0.05)
    assert d.di_source == "balloon"
    assert d.di[0] == pytest.approx(target_di_gaussian_db(80.0, 50.0), abs=0.1)


def test_identical_data_passes_everywhere():
    a, b = _gauss_data("a", F, nb=1500), _gauss_data("b", F, nb=1500)
    c = an.compare(a, b)
    assert c.overall == "pass"
    assert c.info["interpolated_A"] is False and c.info["interpolated_B"] is False
    assert all(m.overall == "pass" for m in c.metrics.values())


def test_constant_level_offset_fails_absolute_but_not_shape_or_patterns():
    a, b = _gauss_data("a", F, nb=1500), _gauss_data("b", F, offset_db=3.0, nb=1500)
    c = an.compare(a, b)
    assert c.metrics["on_axis_abs"].overall == "fail"
    assert c.metrics["on_axis_abs"].stats["all"]["median"] == pytest.approx(-3.0)
    assert c.metrics["on_axis_shape"].overall == "pass"
    assert c.metrics["beamwidth_H"].overall == "pass" and c.metrics["di"].overall == "pass"
    assert c.overall == "fail"


def test_beamwidth_difference_is_reported_with_sign_and_band_stats():
    a, b = _gauss_data("a", F, bw_h=80.0), _gauss_data("b", F, bw_h=95.0)
    c = an.compare(a, b)
    m = c.metrics["beamwidth_H"]
    assert m.stats["all"]["median"] == pytest.approx(-15.0, abs=0.3)                # A - B
    assert m.verdicts["1-5k"] == "fail" and m.overall == "fail"


def test_alignment_never_mutates_and_says_what_it_interpolated():
    f_b = np.geomspace(100, 20000, 61)
    a, b = _gauss_data("a", F), _gauss_data("b", f_b)
    fa0, fb0 = a.freqs_hz.copy(), b.freqs_hz.copy()
    spl_b0 = b.spl_h_db.copy()
    c = an.compare(a, b)
    assert np.array_equal(a.freqs_hz, fa0) and np.array_equal(b.freqs_hz, fb0) and np.array_equal(b.spl_h_db, spl_b0)
    assert c.info["grid_from"] == "A" and c.info["interpolated_B"] and not c.info["interpolated_A"]
    assert c.freqs.size == F.size
    assert any("interpolated for comparison only" in n for n in c.notes)


def test_non_overlapping_ranges_are_refused():
    a = _gauss_data("a", np.geomspace(100, 1000, 10))
    b = _gauss_data("b", np.geomspace(2000, 20000, 10))
    with pytest.raises(ValueError, match="share no frequency range"):
        an.compare(a, b)


def test_float32_grid_differences_do_not_trigger_interpolation():
    a = _gauss_data("a", F)
    b = _gauss_data("b", F.astype(np.float32).astype(float))
    assert an.compare(a, b).info["interpolated_B"] is False


def test_classify_thresholds():
    st = lambda mx, rms: {"n": 5, "max_abs": mx, "rms": rms, "median": 0.0, "p95_abs": mx}  # noqa: E731
    assert an.classify(st(0.9, 0.5), 1.0, 2.0) == "pass"
    assert an.classify(st(1.5, 0.5), 1.0, 2.0) == "warn"            # rms inside, max within 2x
    assert an.classify(st(2.5, 0.8), 1.0, 2.0) == "warn"            # rms inside tolerance
    assert an.classify(st(2.5, 1.5), 1.0, 2.0) == "fail"
    assert an.classify({"n": 0, "max_abs": None, "rms": None}, 1.0, 2.0) == "n/a"
    assert an.worst(["pass", "n/a", "warn"]) == "warn" and an.worst(["n/a"]) == "n/a"


def test_tolerance_overrides_and_unknown_names():
    t = an.Tolerances.from_dict({"on_axis_db": 5.0})
    a, b = _gauss_data("a", F), _gauss_data("b", F, offset_db=3.0)
    assert an.compare(a, b, tolerances=t).metrics["on_axis_abs"].overall == "pass"
    with pytest.raises(ValueError, match="unknown tolerance"):
        an.Tolerances.from_dict({"nope": 1})


def test_di_from_cuts_can_never_pass():
    a, b = _gauss_data("a", F), _gauss_data("b", F)               # no balloon -> cuts_estimate
    c = an.compare(a, b)
    assert c.metrics["di"].overall == "warn" and "capped" in c.metrics["di"].note
    assert c.overall == "warn"


def test_normalized_only_side_skips_absolute_on_axis_with_a_note():
    a = _gauss_data("a", F)
    b = _gauss_data("b", F)
    b.level = "normalized"
    b.spl_h_db = b.spl_h_db - b.spl_h_db[:, [b.axis_index]]
    b.spl_v_db = b.spl_v_db - b.spl_v_db[:, [b.axis_index]]
    c = an.compare(a, b)
    assert "on_axis_abs" not in c.metrics and any("absolute on-axis" in n for n in c.notes)
    assert c.metrics["polar_map_H"].overall == "pass"


def test_angle_grids_of_different_step_are_compared_on_the_coarser_grid():
    a, b = _gauss_data("a", F, step=2.5), _gauss_data("b", F, step=10.0)
    c = an.compare(a, b)
    assert c.angles.size == 19 and any("angle grids differ" in n for n in c.notes)
    assert c.metrics["polar_map_H"].overall in ("pass", "warn")


def test_balloon_projection_between_theta_phi_and_fibonacci_grids():
    from hornlab_search.solve.base import balloon_dirs_from_angles
    th, ph = np.meshgrid(np.linspace(0, 180, 24), np.linspace(0, 360, 48, endpoint=False), indexing="ij")
    dirs_tp = balloon_dirs_from_angles(th.ravel(), ph.ravel())
    f = lambda d: -6.0206 * ((np.degrees(np.arctan2(d[:, 0], d[:, 2])) / 30) ** 2 + (np.degrees(np.arctan2(d[:, 1], d[:, 2])) / 20) ** 2)  # noqa: E731
    dst = fake.fibonacci(800)
    got = an.project_balloon(dirs_tp, f(dirs_tp)[None, :], dst)[0]
    ok = f(dst) > -40
    assert np.abs(got - f(dst))[ok].max() < 1.5      # 7.5 degree source spacing on a steep Gaussian
