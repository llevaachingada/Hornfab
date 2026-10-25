"""Pre-publish byte-check for docs/evidence/M5B_WP14_WP16_WP17_2026-10-25.md (m4/m5 template).

Every quoted block in the evidence doc is checked against its source artifact:
console logs (UTF-16 from Tee / UTF-8 from cmd-redirect), junitxml attributes, run.json
records and fork-state files. Run from the repo root:
    .venv\\Scripts\\python.exe tools\\evidence_bytecheck_m5b.py
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
    # --- fork branches (hosted + local states) ---
    ("runs/m6_fork/forks_state.txt", "f4ef05c", "WP16 branch sha"),
    ("runs/m6_fork/forks_state.txt", "760a1ec", "WP17 branch sha (the pinned stack)"),
    ("runs/m6_fork/forks_state.txt", "a40a204", "WP17 test-env tip (CUDA registered, not pinned)"),
    # --- install + pins ---
    ("runs/m6_fork/pip_state.txt", "Version: 0.2.0", "pip show version"),
    ("runs/m6_fork/pip_state.txt", "760a1ecf6075f5ccdbf97a69874c7f88441e36c1", "installed direct_url pinned revision"),
    ("pyproject.toml", "git+https://github.com/llevaachingada/hornlab-beat-bem.git@760a1ecf6075f5ccdbf97a69874c7f88441e36c1", "main pin -> hosted fork"),
    ("runs/m6_fork/pin_green.log", "1 passed", "test_mesh_pin tripwire RESOLVED (green)"),
    # --- Julia full suite on the GPU (46 testsets; the four CUDA testsets) ---
    ("runs/m6_fork/julia_full.log", "cuda production pipeline |   27     27", "cuda production testset"),
    ("runs/m6_fork/julia_full.log", "cuda fused Burton-Miller driver path |    6      6", "WP15 fused driver testset"),
    ("runs/m6_fork/julia_full.log", "cuda fused WP16 source profile driver path |    9      9", "WP16 CUDA end-to-end"),
    ("runs/m6_fork/julia_full.log", "cuda fused WP17 near-correction driver path |   10     10", "WP17 CUDA end-to-end"),
    ("runs/m6_fork/julia_full.log", "WP16 radial source profile |  825    825", "WP16 CPU testset"),
    ("runs/m6_fork/julia_full.log", "WP17 near-correction gate |  155    155", "WP17 gate testset"),
    ("runs/m6_fork/julia_full.log", "WP17 thin-septum CPU near correction |   12", "WP17 thin-septum parity testset"),
    # --- selftests (re-captured on the final tree under the ceremony) ---
    ("runs/m6_fork/selftest_analytic.log", "R(ka) spread (max-min) = 0.020 dB", "analytic reference spread"),
    ("runs/m6_fork/selftest_analytic.log", "selftest --analytic: PASS", "analytic verdict"),
    ("runs/m6_fork/selftest_crosscheck.log", "overall max 0.0390 dB", "crosscheck reference max"),
    ("runs/m6_fork/vram_selftest_analytic.txt", "1508 MiB", "analytic sampled peak VRAM (re-run; 10-s sampler; fix-16's window reported 2635)"),
    # --- 3-arm A/B vs stored base-pin runs (fresh-cache re-solves on 760a1ec) ---
    ("runs/m6_fork/compare_ab_a.log", "on_axis_db   max |diff| 2.128e-06 dB", "arm a on-axis delta"),
    ("runs/m6_fork/compare_ab_b.log", "on_axis_db   max |diff| 2.946e-06 dB", "arm b on-axis delta"),
    ("runs/m6_fork/compare_ab_c.log", "on_axis_db   max |diff| 4.94e-06 dB", "arm c on-axis delta"),
    ("runs/m6_fork/compare_ab_c.log", "bw_v_deg     max |diff| 3.561e-05 deg", "arm c worst bw delta"),
    # --- WP14 focal pair (the deferred-physics evidence; gate NOT ALLOWED, honestly reframed) ---
    ("runs/m5_wp14_focal/cuda.log", "run OK: seed J=172.566, 4501 dofs", "focal cuda arm run OK"),
    ("runs/m5_wp14_focal/cpu_near.log", "run OK: seed J=471.984, 4501 dofs", "focal cpu near/double arm run OK"),
    ("runs/m6_fork/compare_focal.log", "on_axis_db   max |diff| 11.28 dB", "focal gate on-axis max"),
    ("runs/m6_fork/compare_focal.log", "di_db        max |diff| 14.59 dB", "focal gate DI max"),
    ("runs/m6_fork/compare_focal.log", "bw_v_deg     max |diff| 159.1 deg", "focal gate bw_v max"),
    # --- CAD/STEP category facts (offline; the landed WP14 category) ---
    ("runs/m6_fork/cad_3x3_probe.txt", '"driver": 1', "3x3 driver face count in cad echo"),
    ("runs/m6_fork/cad_3x3_probe.txt", '"wall": 53', "3x3 wall face count in cad echo"),
    ("runs/m6_fork/cad_3x3_probe.txt", '"driver_surfaces": 1', "3x3 driver surface mapping"),
    # --- suites ---
    ("runs/m6_fork/suite_final.xml", 'tests="1325"', "final offline suite count"),
    ("runs/m6_fork/suite_final.xml", 'failures="0"', "final suite 0 failures"),
    ("runs/m6_fork/compileall.log", "Listing", "compileall ran"),
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