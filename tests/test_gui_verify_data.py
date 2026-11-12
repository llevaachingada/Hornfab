"""WP1 data-layer tests for the GUI verify view.

Uses the synthetic fixtures from ``tests/gui_verify_fixtures.py`` (WP0).
No solver, no GPU, no network.  All tests are offline.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# ── Import the module under test ──────────────────────────────────────────────

from hornlab_search.gui import data_verify as DV
from hornlab_search.gui.server import App


# ── Helpers ────────────────────────────────────────────────────────────────────

def _tree(base: Path) -> set[str]:
    """All paths under base, relative, as a frozenset."""
    return {str(p.relative_to(base)) for p in base.rglob("*")}


# ── Layout A: inline verify ───────────────────────────────────────────────────

class TestLayoutA:
    """R_SCREEN has inline verify/search.ndjson."""

    def test_sources_kind_inline(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        runs = tmp_path / "runs"
        sources = DV.verify_sources(runs, R_SCREEN)
        assert isinstance(sources, list)
        kinds = {s["kind"] for s in sources}
        assert "inline" in kinds

    def test_report_has_rows(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        runs = tmp_path / "runs"
        report = DV.verify_report(runs, R_SCREEN, root=tmp_path)
        assert isinstance(report, dict)
        assert report["run_id"] == R_SCREEN
        assert isinstance(report["rows"], list)
        assert len(report["rows"]) > 0

    def test_report_kind_pairs(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        assert report["kind"] == "pairs"

    def test_report_top_level_keys(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        required = {
            "run_id", "name", "kind", "redirect_to", "parent_missing",
            "objective_version", "band_hz", "sources", "state", "comparable",
            "comparable_reason", "latest_only", "fidelity", "summary",
            "gate_audit", "rows",
        }
        missing = required - set(report.keys())
        assert not missing, f"missing keys: {missing}"

    def test_report_row_keys(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        required = {
            "hash", "family", "screen_j", "verify_j", "delta_j", "delta_pct",
            "screen_rank", "verify_rank", "ok", "error", "n", "created_utc",
            "lane", "backend", "n_dof", "n_triangles",
            "density", "gates", "source_kind", "source_run_id",
            "has_balloon", "has_mesh",
        }
        for i, row in enumerate(report["rows"]):
            missing = required - set(row.keys())
            assert not missing, f"row[{i}] missing keys: {missing}"

    def test_report_no_nan(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        text = json.dumps(report)
        assert "NaN" not in text, "NaN leaked into report"
        assert "Infinity" not in text, "Infinity leaked into report"

    def test_summary_present(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        assert report["summary"] is not None
        s = report["summary"]
        assert s["n_verified"] > 0

    def test_gate_audit_available(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        assert report["gate_audit"]["available"] is True, "gate audit should be available for R_SCREEN"

    def test_fidelity_has_verify_and_screen(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        fid = report["fidelity"]
        assert "verify" in fid, "fidelity.verify missing"
        assert "screen" in fid, "fidelity.screen missing"


# ── Latest-n deduplication ────────────────────────────────────────────────────

class TestLatestNDedupe:
    """a1 appears twice: n=0 (j=4.62) and n=5 (j=4.60). n=5 must win."""

    def test_a1_uses_higher_n(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN, H
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        a1_rows = [r for r in report["rows"] if r["hash"] == H["a1"]]
        assert len(a1_rows) == 1, "a1 must appear exactly once after dedup"
        # n=5 row has j=4.60; n=0 row has j=4.62
        assert a1_rows[0]["n"] == 5, f"wrong n: {a1_rows[0]['n']}"

    def test_latest_only_flag_set(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        assert report["latest_only"] is True


# ── Failed row kept ───────────────────────────────────────────────────────────

class TestFailedRowKept:
    """a5 is failed in inline verify; must appear in rows with ok=False and verify_j=None."""

    def test_failed_row_in_report(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN, H
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        failed = [r for r in report["rows"] if r["hash"] == H["a5"]]
        assert len(failed) == 1, "a5 must appear in rows"
        assert failed[0]["ok"] is False
        assert failed[0]["verify_j"] is None

    def test_summary_n_failed_nonzero(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        assert report["summary"]["n_failed"] >= 1


# ── Missing screen pair ───────────────────────────────────────────────────────

class TestMissingScreenPair:
    """Layout B linked verify: H_LINKED1/H_LINKED2 have no screen row in R_SCREEN."""

    def test_linked_rows_have_no_screen_j(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN, H_LINKED1, H_LINKED2
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        hashes = {r["hash"] for r in report["rows"]}
        # H_LINKED1 and H_LINKED2 may appear if the linked run is scanned
        for h in (H_LINKED1, H_LINKED2):
            matched = [r for r in report["rows"] if r["hash"] == h]
            for r in matched:
                assert r["screen_j"] is None, f"{h} should have screen_j=None"
                assert r["delta_j"] is None, f"{h} should have delta_j=None"


# ── Layout B: linked verify run ───────────────────────────────────────────────

class TestLayoutB:
    """R_LINKED is a linked verify run; querying it returns a redirect dict."""

    def test_linked_run_redirect(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_LINKED, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_LINKED, root=tmp_path)
        assert report["kind"] == "redirect"
        assert report["redirect_to"] == R_SCREEN
        assert report["parent_missing"] is False

    def test_sources_redirect(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_LINKED
        make_runs(tmp_path)
        result = DV.verify_sources(tmp_path / "runs", R_LINKED)
        assert isinstance(result, dict), "linked run should return a dict (redirect)"
        assert "redirect_to" in result

    def test_screen_includes_linked_rows(self, tmp_path):
        """When R_SCREEN's report is fetched, the linked verify rows from R_LINKED appear."""
        from tests.gui_verify_fixtures import make_runs, R_SCREEN, H_LINKED1
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        hashes = {r["hash"] for r in report["rows"]}
        # H_LINKED1 is in R_LINKED which points at R_SCREEN
        assert H_LINKED1 in hashes, f"H_LINKED1 should appear in R_SCREEN report rows"


# ── Orphan: parent_missing ────────────────────────────────────────────────────

class TestOrphan:
    """R_ORPHAN's verify_of.run points to a non-existent parent."""

    def test_orphan_parent_missing(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_ORPHAN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_ORPHAN, root=tmp_path)
        assert report["kind"] == "redirect"
        assert report["parent_missing"] is True
        assert report["redirect_to"] is None


# ── Layout C: standalone ──────────────────────────────────────────────────────

class TestLayoutC:
    """R_STANDALONE is mode=='verify' with no verify_of."""

    def test_sources_kind_standalone(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_STANDALONE
        make_runs(tmp_path)
        sources = DV.verify_sources(tmp_path / "runs", R_STANDALONE)
        assert isinstance(sources, list)
        assert any(s["kind"] == "standalone" for s in sources)

    def test_report_kind_standalone(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_STANDALONE
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_STANDALONE, root=tmp_path)
        assert report["kind"] == "standalone"

    def test_report_has_rows(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_STANDALONE
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_STANDALONE, root=tmp_path)
        assert len(report["rows"]) >= 1

    def test_standalone_no_screen_j(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_STANDALONE
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_STANDALONE, root=tmp_path)
        for row in report["rows"]:
            # standalone verify has no corresponding screen rows
            assert row["screen_j"] is None or row["source_kind"] == "standalone"


# ── comparable:false on R_XBAND ───────────────────────────────────────────────

class TestXBand:
    """R_XBAND verify metrics cover a different band → comparable must be False."""

    def test_xband_not_comparable(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_XBAND
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_XBAND, root=tmp_path)
        assert report["comparable"] is False
        assert report["comparable_reason"] is not None


# ── Gate merge ────────────────────────────────────────────────────────────────

class TestGateMerge:
    """Gate audit CSV covers R_SCREEN; it should be found by the report."""

    def test_gate_audit_labels_present(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        report = DV.verify_report(tmp_path / "runs", R_SCREEN, root=tmp_path)
        ga = report["gate_audit"]
        assert ga["available"] is True
        assert "labels" in ga
        assert len(ga["labels"]) > 0


# ── Invalid hash / unknown tier → 400 (ValueError) ───────────────────────────

class TestErrors:
    def test_invalid_hash_design_payload(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        with pytest.raises(ValueError, match="not a design hash"):
            DV.design_payload(tmp_path / "runs", R_SCREEN, "not_a_hash!", "screen")

    def test_unknown_tier_design_payload(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN, H
        make_runs(tmp_path)
        with pytest.raises(ValueError, match="unknown tier"):
            DV.design_payload(tmp_path / "runs", R_SCREEN, H["a1"], "ultra")

    def test_unknown_tier_raises_in_data_balloon(self, tmp_path):
        """data.balloon validates tier=."""
        from tests.gui_verify_fixtures import make_runs, R_SCREEN, H
        from hornlab_search.gui.data import balloon
        make_runs(tmp_path)
        with pytest.raises(ValueError, match="unknown tier"):
            balloon(tmp_path / "runs", R_SCREEN, H["a1"], tier="bad_tier")

    def test_unknown_tier_raises_in_data_mesh_surface(self, tmp_path):
        """data.mesh_surface validates tier=."""
        from tests.gui_verify_fixtures import make_runs, R_SCREEN, H
        from hornlab_search.gui.data import mesh_surface
        make_runs(tmp_path)
        with pytest.raises(ValueError, match="unknown tier"):
            mesh_surface(tmp_path / "runs", R_SCREEN, H["a1"], tier="bad_tier")

    def test_unknown_tier_raises_in_data_design_curves(self, tmp_path):
        """data.design_curves validates tier=."""
        from tests.gui_verify_fixtures import make_runs, R_SCREEN, H
        from hornlab_search.gui.data import design_curves
        make_runs(tmp_path)
        with pytest.raises(ValueError, match="unknown tier"):
            design_curves(tmp_path / "runs" / R_SCREEN, H["a1"], tier="bad_tier")


# ── /api/verify/<id> 200 via App.get ─────────────────────────────────────────

class TestAppGet:
    def test_app_get_verify_200(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        app = App(root=tmp_path, runs=tmp_path / "runs")
        result = app.get(f"/api/verify/{R_SCREEN}", {})
        assert isinstance(result, dict)
        assert result["run_id"] == R_SCREEN

    def test_app_get_verify_linked(self, tmp_path):
        """Linked verify run returns a redirect dict."""
        from tests.gui_verify_fixtures import make_runs, R_LINKED
        make_runs(tmp_path)
        app = App(root=tmp_path, runs=tmp_path / "runs")
        result = app.get(f"/api/verify/{R_LINKED}", {})
        assert isinstance(result, dict)
        assert result["kind"] == "redirect"


# ── No file written under tmp/runs ────────────────────────────────────────────

class TestNoFileWritten:
    def test_verify_report_writes_nothing(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        runs = tmp_path / "runs"
        before = _tree(runs)
        DV.verify_report(runs, R_SCREEN, root=tmp_path)
        after = _tree(runs)
        new_files = after - before
        assert not new_files, f"verify_report wrote unexpected files: {new_files}"

    def test_verify_sources_writes_nothing(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        make_runs(tmp_path)
        runs = tmp_path / "runs"
        before = _tree(runs)
        DV.verify_sources(runs, R_SCREEN)
        after = _tree(runs)
        assert after == before


# ── Module does not import tools ──────────────────────────────────────────────

class TestNoToolsImport:
    def test_data_verify_no_tools(self):
        import ast, importlib
        src = Path(ROOT / "hornlab_search" / "gui" / "data_verify.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                for name in names:
                    assert not name.startswith("tools"), f"data_verify.py imports tools/: {name}"
                    assert not name.startswith("hornlab_search.tools"), (
                        f"data_verify.py imports tools/: {name}")


# ── run_summary and run_detail additive fields ────────────────────────────────

class TestDataPyAdditive:
    def test_run_summary_has_inline_verify(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        from hornlab_search.gui.data import run_summary
        make_runs(tmp_path)
        s = run_summary(tmp_path / "runs" / R_SCREEN)
        assert "has_inline_verify" in s
        assert s["has_inline_verify"] is True

    def test_run_summary_no_inline_verify_on_linked(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_LINKED
        from hornlab_search.gui.data import run_summary
        make_runs(tmp_path)
        s = run_summary(tmp_path / "runs" / R_LINKED)
        assert "has_inline_verify" in s
        assert s["has_inline_verify"] is False

    def test_run_summary_verify_of_run_id(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_LINKED, R_SCREEN
        from hornlab_search.gui.data import run_summary
        make_runs(tmp_path)
        s = run_summary(tmp_path / "runs" / R_LINKED)
        assert "verify_of_run_id" in s
        assert s["verify_of_run_id"] == R_SCREEN, (
            f"expected {R_SCREEN!r}, got {s['verify_of_run_id']!r}")

    def test_run_detail_verification_key(self, tmp_path):
        from tests.gui_verify_fixtures import make_runs, R_SCREEN
        from hornlab_search.gui.data import run_detail
        make_runs(tmp_path)
        detail = run_detail(tmp_path / "runs", R_SCREEN, root=tmp_path)
        assert "verification" in detail
        v = detail["verification"]
        assert v["has_inline_verify"] is True

    def test_balloon_tier_verify(self, tmp_path):
        """balloon(..., tier='verify') reads from verify/designs/<h>/response.npz."""
        from tests.gui_verify_fixtures import make_runs, R_SCREEN, H
        from hornlab_search.gui.data import balloon
        make_runs(tmp_path)
        result = balloon(tmp_path / "runs", R_SCREEN, H["a1"], tier="verify")
        assert result["run_id"] == R_SCREEN
        assert result["design"] == H["a1"]
        # verify balloon has 29 freqs and 23×45 grid
        assert len(result["freqs_hz"]) == 29
        assert result["balloon_grid"] == [23, 45]

    def test_design_curves_tier_verify(self, tmp_path):
        """design_curves with tier='verify' reads from verify/designs/<h>/."""
        from tests.gui_verify_fixtures import make_runs, R_SCREEN, H
        from hornlab_search.gui.data import design_curves
        make_runs(tmp_path)
        run_dir = tmp_path / "runs" / R_SCREEN
        curves = design_curves(run_dir, H["a1"], tier="verify")
        assert curves is not None
        # Verify tier has 29 freqs
        assert len(curves["freqs"]) == 29
