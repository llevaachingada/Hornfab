"""WP 4.2/4.3 predeclared rules (2026-11-17)."""
import numpy as np

from tools.analysis import u3_authority as UA

F = np.geomspace(500.0, 8000.0, 29)


def _arm(h=80.0, v=50.0, dh=None, dv=None):
    bh = np.full(F.size, h) + (0 if dh is None else dh(F))
    bv = np.full(F.size, v) + (0 if dv is None else dv(F))
    return F, bh, bv


def test_equivalence_passes_within_one_degree_and_fails_beyond():
    host = _arm()
    assert UA.equivalence(host, _arm(80.6, 49.5))["pass"] is True
    r = UA.equivalence(host, _arm(81.5, 50.0))
    assert r["pass"] is False and r["bw_ok"] is False
    assert UA.equivalence(host, _arm(), dj=0.2, floor=0.11)["pass"] is False
    assert UA.equivalence(host, _arm(), dj=0.05, floor=0.11)["pass"] is True


def test_authority_needs_three_degrees_in_the_intended_plane_and_a_quiet_other_plane():
    ctl = _arm()
    band = lambda d: (lambda f: np.where((f >= 700) & (f <= 1100), d, 0.0))  # noqa: E731
    yes = UA.authority(ctl, _arm(dv=band(-4.0)), "vt_460")
    assert yes["authority"] and yes["via"][0]["plane"] == "v"
    wrong_plane = UA.authority(ctl, _arm(dh=band(-4.0)), "vt_460")
    assert wrong_plane["authority"] is False
    leaky = UA.authority(ctl, _arm(dv=band(-4.0), dh=band(-2.5)), "vt_460")
    assert leaky["authority"] is False
    either = UA.authority(ctl, _arm(dh=band(3.5)), "diag_pull")
    assert either["authority"] and either["via"][0]["plane"] == "h"


def test_mismatched_grids_are_compared_on_the_overlap():
    host = (np.geomspace(500, 8000, 18), np.full(18, 80.0), np.full(18, 50.0))
    assert UA.equivalence(host, _arm())["pass"] is True


def test_write_arm_csv_round_trips_through_band_means(tmp_path):
    """R18 (2026-11-18): the CSV export reproduces the arm the authority rule reads."""
    import csv
    import numpy as np
    f = np.array([800.0, 1000.0, 1500.0, 3000.0, 4000.0])
    arm = (f, np.array([70.0, 72.0, 80.0, 81.0, 79.0]), np.array([60.0, 61.0, 55.0, 54.0, 53.0]))
    p = UA.write_arm_csv(tmp_path / "x" / "hv_beamwidth_a.csv", arm)
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    back = tuple(np.array([float(r[k]) for r in rows]) for k in ("freq_hz", "bw_h_deg", "bw_v_deg"))
    assert UA.band_means(*back) == UA.band_means(*arm)
