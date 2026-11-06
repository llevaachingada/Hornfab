"""A/B check: the convention / unit sanity checker names the right cause for each injected mistake."""
import pytest

from hornlab_search.compare import analysis as an, bl_import as bi, fake, hornfab_side as hs
from hornlab_search.compare.conventions import check_conventions


@pytest.fixture(scope="module")
def side_a(tmp_path_factory):
    d = tmp_path_factory.mktemp("A")
    fake.write_hornfab_side(d)
    return hs.load_hornfab(d)


def _findings(side_a, tmp_path, inject):
    fake.write_bl_gui_side(tmp_path, inject=inject)
    b = bi.import_bl(tmp_path)
    c = an.compare(side_a, b)
    return c, [f["code"] for f in check_conventions(c) if f["likelihood"] != "info"]


def test_clean_pair_passes_with_no_findings(side_a, tmp_path):
    c, codes = _findings(side_a, tmp_path, "none")
    assert c.overall == "pass" and codes == []


@pytest.mark.parametrize("inject,code", [
    ("offset6", "constant_offset"), ("slope", "drive_basis_slope"), ("conj", "time_convention"), ("polarity", "polarity"),
    ("delay", "propagation_delay"), ("mirror", "mirrored_angles"), ("swap", "hv_swapped"), ("radius", "radius_mismatch")])
def test_each_injected_mistake_is_named(side_a, tmp_path, inject, code):
    c, codes = _findings(side_a, tmp_path, inject)
    assert c.overall in ("warn", "fail")
    assert code in codes, (inject, codes)


def test_offset_message_states_the_probable_cause_and_sign(side_a, tmp_path):
    c, _ = _findings(side_a, tmp_path, "offset6")
    msg = [f for f in check_conventions(c) if f["code"] == "constant_offset"][0]["message"]
    assert "half-space" in msg and "-6.02" in msg                                  # A is 6 dB BELOW B (B was boosted)


def test_known_radius_in_meta_is_used(side_a, tmp_path):
    fake.write_bl_gui_side(tmp_path, inject="radius")
    b = bi.import_bl(tmp_path, handoff={"observation": {"distance_m": 3.0}})
    codes = [f["code"] for f in check_conventions(an.compare(side_a, b))]
    assert "radius_mismatch" in codes and "radius_differs" in codes
