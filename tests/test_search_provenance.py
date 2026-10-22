"""Live runtime provenance in run.json (idea after Boundary Lab's BEAT run provenance)."""
import sys

from hornlab_search.search import rundir


def test_runtime_provenance_is_best_effort_and_complete():
    rp = rundir.runtime_provenance()
    assert set(rp) == {"python", "platform", "gpu", "julia", "sources"}
    assert {s["module"] for s in rp["sources"]} == {"hornlab_beat_bem", "hornlab_mesher",
                                                     "hornlab_bempp_bem"}


def test_source_fingerprint_is_stable_and_detects_edits(tmp_path, monkeypatch):
    pkg = tmp_path / "fp_demo_pkg"
    (pkg / "sub").mkdir(parents=True)
    (pkg / "__init__.py").write_text("x = 1\n")
    (pkg / "sub" / "solver.jl").write_text("f(x) = x\n")
    (pkg / "notes.txt").write_text("ignored\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    a = rundir.package_source_fingerprint("fp_demo_pkg")
    b = rundir.package_source_fingerprint("fp_demo_pkg")
    assert a == b and a["n_files"] == 2
    (pkg / "notes.txt").write_text("still ignored\n")
    assert rundir.package_source_fingerprint("fp_demo_pkg")["sha256"] == a["sha256"]
    (pkg / "sub" / "solver.jl").write_text("f(x) = 2x\n")
    assert rundir.package_source_fingerprint("fp_demo_pkg")["sha256"] != a["sha256"]
    sys.modules.pop("fp_demo_pkg", None)


def test_missing_package_reports_instead_of_raising():
    assert "error" in rundir.package_source_fingerprint("no_such_pkg_xyz")
