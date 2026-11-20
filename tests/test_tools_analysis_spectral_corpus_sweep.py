"""Tests for the report-only corpus-wide fixed-angle spectral sweep."""
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from tools.analysis import spectral_corpus_sweep as S

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_RUN = (
    ROOT / "docs" / "evidence" / "runs" / "scout40_2026-11-19"
    / "20261119T073330Z-screen-723756"
)
FREQS = np.linspace(1065.0, 4832.5, 8)
ANGLES = np.array([-35.0, -25.0, 0.0, 25.0, 35.0])
H_ANGLES = np.array([-35.0, -25.0, 0.0, 25.0, 35.0])


def _write_run(root, name, identity, amp, rip, j, *, brief=True, zero_degree=True,
               design_hash=None):
    """Write one synthetic run dir: config.yaml, best.json, designs/<hash>/response.npz.

    ``design_hash`` defaults to a per-run value: real run dirs normally hold different best
    designs, and the sweep correlates on unique hashes (2026-11-20 dedupe).
    """
    design_hash = design_hash or ("h" + name)
    run = root / name
    (run / "designs" / design_hash).mkdir(parents=True)
    config = {"name": identity}
    if brief:
        config["brief"] = {"name": identity}
    (run / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    best = {"design_hash": design_hash, "family": "FREEFORM", "objective": j,
            "terms": {"rip": rip}}
    (run / "best.json").write_text(json.dumps(best), encoding="utf-8")

    angles = ANGLES if zero_degree else np.array([-35.0, -25.0, 25.0, 35.0])
    x = np.log2(FREQS / FREQS[0])
    ripple = amp * np.sin(2.015 * np.pi * x + 0.3)

    spl_v = np.zeros((FREQS.size, angles.size))
    for jj, angle in enumerate(angles):
        if angle != 0.0:
            spl_v[:, jj] = ripple
    spl_h = np.zeros((FREQS.size, H_ANGLES.size))
    for jj, angle in enumerate(H_ANGLES):
        if angle != 0.0:
            spl_h[:, jj] = 0.6 * ripple

    np.savez(run / "designs" / design_hash / "response.npz",
             freqs_hz=FREQS, v_angles_deg=angles, spl_v_db=spl_v,
             h_angles_deg=H_ANGLES, spl_h_db=spl_h)
    return run


def _build_corpus(tmp_path):
    runs = tmp_path / "runs"
    # identity A: brief.name present, residual amplitude varies (correlates with rip).
    for i, amp in enumerate((0.2, 0.4, 0.6, 0.8, 1.0, 1.2)):
        _write_run(runs, f"a{i:02d}", "ident_a", amp, 2.0 * amp, 10.0 - amp)
    # identity B: only config.name (fallback path), residual constant, one run missing 0 deg.
    for i in range(6):
        _write_run(runs, f"b{i:02d}", "ident_b", 0.5, 0.1 * (i + 1), 5.0,
                   brief=False, zero_degree=(i != 5))
    return runs


def test_grouping_constant_null_and_missing_zero_degree(tmp_path):
    runs = _build_corpus(tmp_path)
    out = tmp_path / "out"
    assert S.main(["--runs-root", str(runs), "--out", str(out)]) == 0

    payload = json.loads((out / "sweep.json").read_text(encoding="utf-8"))
    assert payload["counts"]["scanned"] == 12
    assert payload["counts"]["usable"] == 11
    assert payload["counts"]["refused"] == 1

    stats = {s["identity"]: s for s in payload["identity_stats"]}
    assert set(stats) == {"ident_a @ v?", "ident_b @ v?"}
    assert stats["ident_a @ v?"]["n"] == 6
    assert stats["ident_b @ v?"]["n"] == 5
    assert stats["ident_a @ v?"]["median_v35_trend"] is not None
    assert stats["ident_a @ v?"]["median_v35_band_mean"] is not None

    rho_a = stats["ident_a @ v?"]["spearman_rip_v35"]
    assert rho_a["rho"] == pytest.approx(1.0)
    assert rho_a["reason"] is None

    rho_b = stats["ident_b @ v?"]["spearman_rip_v35"]
    assert rho_b["rho"] is None
    assert "constant vector" in rho_b["reason"]

    # The missing-zero-degree run is a recorded refusal, never silently dropped.
    refused = [r for r in payload["rows"] if r["refused"]]
    assert len(refused) == 1
    assert refused[0]["run"] == "b05"
    assert refused[0]["identity"] == "ident_b"
    assert "V+35 trend" in refused[0]["refusal_reason"]
    assert "no reference sample" in refused[0]["refusal_reason"]
    assert payload["refusal_counts"].get("missing zero-degree reference") == 1

    md = (out / "sweep.md").read_text(encoding="utf-8")
    assert "REPORT-ONLY" in md
    assert "NEVER compared or ranked across identities" in md
    assert "grid-dependent" in md
    assert "1.441" in md and "1.908" in md and "1.313" in md
    assert "pooling across briefs is INVALID" in md


def test_out_refused_when_non_empty(tmp_path):
    runs = _build_corpus(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "existing.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit):
        S.main(["--runs-root", str(runs), "--out", str(out)])


def test_real_archive_design_reads_1_441_db():
    assert ARCHIVE_RUN.is_dir(), f"committed archive run missing: {ARCHIVE_RUN}"
    row = S.compute_run_row(ARCHIVE_RUN)
    assert row["design_hash"] == "ee85bcd2ad67"
    assert row["refused"] is False, row["refusal_reason"]
    value = row["metrics"]["V+35"]["trend"]
    assert value is not None
    assert value == pytest.approx(1.441, abs=2e-3)


def test_cli_smoke_with_limit(tmp_path):
    runs = tmp_path / "runs"
    for i in range(4):
        _write_run(runs, f"r{i:02d}", "ident_smoke", 0.3 + 0.1 * i, 0.2 * i, 1.0)
    out = tmp_path / "out_limit"
    assert S.main(["--runs-root", str(runs), "--out", str(out), "--limit", "2"]) == 0

    payload = json.loads((out / "sweep.json").read_text(encoding="utf-8"))
    assert payload["counts"]["scanned"] == 2
    assert [r["run"] for r in payload["rows"]] == ["r00", "r01"]
    assert (out / "sweep.md").is_file()


def test_duplicate_designs_are_counted_but_deduped_in_the_statistics(tmp_path):
    """The same design solved into several run dirs must not inflate n (2026-11-20)."""
    runs = tmp_path / "runs"
    for i in range(6):
        _write_run(runs, f"d{i:02d}", "ident_dup", 0.2 + 0.1 * i, 0.5 + i, 10.0 - i,
                   design_hash="samehash")
    out = tmp_path / "out"
    assert S.main(["--runs-root", str(runs), "--out", str(out)]) == 0
    payload = json.loads((out / "sweep.json").read_text(encoding="utf-8"))
    # identity is below --identity-min on UNIQUE designs (1 < 5), so it is not tabulated ...
    assert payload["identity_stats"] == []
    assert payload["counts"]["usable"] == 6
    # ... and the pooled row keeps both the raw count and the unique count.
    pooled = payload["pooled"]
    assert pooled["n_rows"] == 6
    assert pooled["n"] == 1
