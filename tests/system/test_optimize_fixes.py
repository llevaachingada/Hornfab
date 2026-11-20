"""Pass A lane A4: B18/B19/B21/B26 fixes (pilot + score + seed spec + DSP bank).

Offline only: one real driver YAML read for the pilot geometry path, synthetic rows elsewhere.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system import contracts as C  # noqa: E402
from hornlab_search.system import dsp as sys_dsp  # noqa: E402
from hornlab_search.system import optimize  # noqa: E402
from hornlab_search.system import score  # noqa: E402
from hornlab_search.system import woofer_seed as W  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
GEOMETRY = REPO / "examples" / "systems" / "driver_geometry" / "faitalpro_12pr300.yaml"


# --------------------------------------------------------------------------- B18: pilot --geometry

_MIN_SPEC_FIELDS = dict(
    experiment_id="pilot_fix_test",
    mode="fixed_horn",
    horn=C.HornRef(asset_id="unused"),
    woofer=C.WooferRef(driver_id="faitalpro_12pr300"),
    cabinet=C.VentedBoxRanges(net_volume_l_range=(35.0, 45.0), tuning_hz_range=(30.0, 40.0),
                              port_throat_area_cm2_range=(60.0, 100.0)),
    assembly=C.AssemblyRanges(),
    dsp=C.DspRanges(xo_hz_range=(700.0, 1300.0)),
    target=C.SystemTargets(listening_angle_h_deg=(-30.0, 30.0),
                           listening_angle_v_deg=(-15.0, 15.0), low_freq_f3_hz_max=55.0),
    fidelity="screen_only",
)


def _spec(**overrides: Any) -> C.SystemSpecV1:
    fields: dict[str, Any] = dict(_MIN_SPEC_FIELDS)
    fields.update(overrides)
    return C.SystemSpecV1(**fields)


def test_pilot_geometry_path_does_not_raise_schema_error() -> None:
    # B18: the documented --geometry path previously asked for "LF_TS_SCREENING", which is not
    # a fidelity-ladder label. The T/S screen is SCREEN_MAGNITUDE, so the path must complete.
    result = optimize.run_pilot(_spec(), geometry_path=GEOMETRY, limit_boxes=1)
    assert result.driver.geometry_mm is not None
    assert result.driver.geometry_mm.frame_od_mm == pytest.approx(315.2)
    assert result.rows


# --------------------------------------------------------------------------- B19: axis schema

def test_nested_axes_cannot_produce_an_all_pareto_report() -> None:
    # B19: pilot rows once carried numeric_axes cells as {value, direction} dicts, so dominance
    # silently discarded every pair and the report looked Pareto-clean. The canonical contract
    # (reconciled on the integration branch) is scalar numeric_axes + axis_directions, and a
    # nested cell is a schema error at render time instead of an unorderable row.
    nested = {"numeric_axes": {"net_volume_l": {"value": 40.0, "direction": "-"}}}
    with pytest.raises(C.SchemaError, match="numeric axis"):
        score.render_report([{"row_id": "nested", "sort_key": [0], **nested}])

    better = {"numeric_axes": {"net_volume_l": 40.0, "f3_hz": 40.0},
              "axis_directions": {"net_volume_l": "-", "f3_hz": "+"}}
    worse = {"numeric_axes": {"net_volume_l": 50.0, "f3_hz": 30.0}}
    payload = json.loads(score.render_report([
        {"row_id": "better", "sort_key": [0], **better},
        {"row_id": "worse", "sort_key": [1], **worse},
    ])["json"])
    by_id = {row["row_id"]: row for row in payload["rows"]}
    assert by_id["worse"]["pareto"] is False
    assert by_id["worse"]["dominated_by"] == ["better"]
    assert by_id["better"]["pareto"] is True


# --------------------------------------------------------------------------- B21: reserved keys

def test_inert_spec_keys_emit_one_reserved_warning() -> None:
    doc = {
        "schema_version": 1,
        "cabinet": {"port_nfr_range": [0.0, 0.2]},
        "assembly": {"woofer_center_y_mm_range": [90, 400]},
        "dsp": {"active": True},
        "target": {"beamwidth_h_deg": [80, 80]},
    }
    with pytest.warns(UserWarning) as caught:
        present = W.warn_reserved_spec_keys(doc)
    assert present == (
        "cabinet.port_nfr_range",
        "assembly.woofer_center_y_mm_range",
        "target.beamwidth_h_deg",
        "dsp.active",
    )
    assert len(caught) == 1                      # one warning per spec, naming all keys
    message = str(caught[0].message)
    assert "reserved" in message
    for key in present:
        assert key in message
    # A spec without the reserved keys stays silent.
    with warnings.catch_warnings(record=True) as silent:
        warnings.simplefilter("always")
        info = W.warn_reserved_spec_keys({"cabinet": {"kind": "vented"}})
    assert not [w for w in silent if issubclass(w.category, UserWarning)]
    assert info == ()


# --------------------------------------------------------------------------- B26: DSP range check

def _dsp_point(**overrides: Any) -> C.DspPoint:
    values: dict[str, Any] = dict(
        crossover_type="LR4", xo_hz=1000.0, gain_db_woofer=-3.0, gain_db_horn=-1.5,
        relative_delay_ms=0.37, polarity_woofer=-1.0, peq_bands_woofer=(),
    )
    values.update(overrides)
    return C.DspPoint(**values)


def test_filter_bank_range_checks_when_ranges_are_supplied() -> None:
    freqs = np.array([500.0, 1000.0, 2000.0])
    sys_dsp.filter_bank(_dsp_point(), freqs, ranges=C.DspRanges())       # in range: allowed
    with pytest.raises(C.SchemaError, match="xo_hz"):
        sys_dsp.filter_bank(_dsp_point(xo_hz=4000.0), freqs, ranges=C.DspRanges())
    # The historical two-argument call stays available for callers with wider local ranges.
    assert sys_dsp.filter_bank(_dsp_point(xo_hz=4000.0), freqs)["horn"].shape == (3,)
