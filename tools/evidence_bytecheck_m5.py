"""Pre-publish byte-check for docs/evidence/M5_WP11_2026-10-25.md (M4 template).

Every quoted block in the evidence doc is checked against its source artifact:
console logs (UTF-16 from Tee / UTF-8 from cmd-redirect), junitxml attributes, and
the durable run.json bodies. Run from the repo root:
    .venv\\Scripts\\python.exe tools\\evidence_bytecheck_m5.py
"""
import pathlib

R = pathlib.Path(".")


def load(p):
    b = pathlib.Path(p).read_bytes()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16")
    if b[:3] == b"\xef\xbb\xbf":
        return b.decode("utf-8-sig")
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("latin-1")


checks = [
    # --- offline (final tree, runs/m5_wp11/) ---
    ("runs/m5_wp11/suite_final.log", "FAILED tests/test_mesh_pin.py::test_installed_hornlab_packages_match_their_pins", "suite tripwire line"),
    ("runs/m5_wp11/suite_final.log", "short test summary info", "suite short summary present"),
    ("runs/m5_wp11/suite_final.xml", 'tests="1234"', "suite test count 1234"),
    ("runs/m5_wp11/suite_final.xml", 'failures="1"', "suite exactly 1 failure"),
    ("runs/m5_wp11/suite_final.xml", 'errors="0"', "suite 0 errors"),
    ("runs/m5_wp11/suite_final.xml", 'skipped="0"', "suite 0 skipped"),
    ("runs/m5_wp11/module.xml", 'tests="18"', "module focused 18 tests"),
    ("runs/m5_wp11/restarts.xml", 'tests="19"', "restarts focused 19 tests"),
    ("runs/m5_wp11/gui.xml", 'tests="34"', "gui focused 34 tests"),
    ("runs/m5_wp11/module_focused.log", "ACCEPTANCE coverage: 49/64 scan-reachable cells = 76.6% (archive 49/64 bins, 160 non-cached evals)", "acceptance coverage line"),
    ("runs/m5_wp11/compileall.log", "Listing", "compileall ran"),
    # --- GPU screens (runs/m5_wp11_gpu/ + durable run dirs) ---
    ("runs/m5_wp11_gpu/ipop.log", "60 new, 0 cached", "ipop budget rows all new"),
    ("runs/m5_wp11_gpu/ipop.log", "search OK: 60 rows", "ipop screen OK"),
    ("runs/20261025T075549Z-screen-930b14/run.json", '"non_cached": 60', "ipop non_cached exactly 60"),
    ("runs/20261025T075549Z-screen-930b14/run.json", '"budget"', "ipop budget recorded"),
    ("runs/m5_wp11_gpu/bipop.log", "60 new, 0 cached", "bipop budget rows all new"),
    ("runs/m5_wp11_gpu/bipop.log", "search OK: 60 rows", "bipop screen OK"),
    ("runs/20261025T080130Z-screen-3f233c/run.json", '"non_cached": 60', "bipop non_cached exactly 60"),
    ("runs/m5_wp11_gpu/cma_me.log", "best J=9.31571", "cma_me best J"),
    ("runs/20261025T080717Z-screen-fd13a7/run.json", "9.315712818227158", "cma_me best objective value"),
    ("runs/20261025T080717Z-screen-fd13a7/run.json", '"coverage": 0.05078125', "qd archive coverage entry"),
    ("runs/20261025T080717Z-screen-fd13a7/run.json", "mean_bw_v_deg", "qd descriptor names recorded"),
    # --- fired-restarts screen (tolfun forced) ---
    ("runs/m5_wp11_gpu/bipop_fired.log", "stop: restarts_exhausted", "fired screen natural-stop reason"),
    ("runs/m5_wp11_gpu/bipop_fired.log", "best J=14.0673", "fired best J"),
    ("runs/20261025T081346Z-screen-30c0ae/run.json", "ab853f058207", "fired best hash"),
    ("runs/20261025T081346Z-screen-30c0ae/run.json", "restarts_exhausted", "fired stop reason in run.json"),
    ("runs/20261025T081346Z-screen-30c0ae/run.json", "0.002783", "bipop small-branch sigma on real solves"),
    ("runs/20261025T081346Z-screen-30c0ae/run.json", '"non_cached": 51', "fired non_cached exactly 51"),
    # --- VRAM pair (rules 3/5; fourth job only — jobs 1-3 disclosed MISSING) ---
    ("runs/m5_wp11_gpu/vram_bipop_fired.txt", "2305 MiB", "peak VRAM (external sampler)"),
    ("runs/m5_wp11_gpu/baseline_bipop_fired.txt", "430 MiB", "baseline VRAM"),
]

ok = 0
bad = []
for path, needle, label in checks:
    try:
        text = load(path)
        if needle in text:
            ok += 1
        else:
            bad.append((label, path, needle[:60], "MISSING"))
    except FileNotFoundError:
        bad.append((label, path, needle[:60], "FILE MISSING"))
print(f"BYTE-CHECK: {ok}/{len(checks)} PASS")
for b in bad:
    print("FAIL:", b)