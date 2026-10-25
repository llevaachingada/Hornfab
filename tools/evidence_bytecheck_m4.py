import json, pathlib

R = pathlib.Path(".")

def load(p):
    b = pathlib.Path(p).read_bytes()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff") or (b.startswith(b"\xff\xfe") and len(b) > 2):
        return b.decode("utf-16")
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("latin-1")

checks = [
    ("runs/m4_code/doctor_preflight.log", "doctor OK: 11 checks, 0 failed", "doctor"),
    ("runs/m4_code/doctor_preflight.log", "WARNING: hornlab-beat-bem: installed fa99ee594087 != expected 38544d214ba2", "doctor tripwire warning"),
    ("runs/m4_smoke/final_splice_osse_tractrix.log", "total J=163.506", "splice J"),
    ("runs/m4_smoke/final_splice_osse_tractrix.log", "run OK: seed J=163.506, 449 dofs, solve", "splice run OK"),
    ("runs/m4_smoke/final_throatblend_hypex.log", "total J=26.4584", "throatblend J"),
    ("runs/m4_smoke/final_throatblend_hypex.log", "run OK: seed J=26.4584, 1273 dofs", "throatblend run OK"),
    ("runs/m4_smoke/final_spherical_salmon.log", "total J=65.3479", "salmon J"),
    ("runs/m4_smoke/final_spherical_salmon.log", "run OK: seed J=65.3479, 730 dofs", "salmon run OK"),
    ("runs/m4_smoke/final_grid_ellipse.log", "total J=156.37", "grid_ellipse J"),
    ("runs/m4_smoke/final_grid_ellipse.log", "run OK: seed J=156.37, 1298 dofs", "grid_ellipse run OK"),
    ("runs/m4_smoke/final_grid_ellipse_mod.log", "total J=145.954", "grid_ellipse_mod J"),
    ("runs/m4_smoke/final_grid_ellipse_mod.log", "run OK: seed J=145.954, 1293 dofs", "grid_ellipse_mod run OK"),
    ("runs/m4_smoke/final_salmon_elliptical.log", "total J=86.5526", "salmon_elliptical J"),
    ("runs/m4_smoke/final_salmon_elliptical.log", "run OK: seed J=86.5526, 2742 dofs", "salmon_elliptical run OK"),
    ("runs/m4_smoke/final_salmon_x_shape.log", "total J=45.2382", "salmon_x_shape J"),
    ("runs/m4_smoke/final_salmon_x_shape.log", "run OK: seed J=45.2382, 2239 dofs", "salmon_x_shape run OK"),
    ("runs/m4_smoke/final_salmon_saddle.log", "total J=74.072", "salmon_saddle J"),
    ("runs/m4_smoke/final_salmon_saddle.log", "run OK: seed J=74.072, 4881 dofs", "salmon_saddle run OK"),
    ("runs/m4_smoke/final_lecleach_f90.log", "total J=118.681", "lecleach_f90 J"),
    ("runs/m4_smoke/final_lecleach_f90.log", "run OK: seed J=118.681, 547 dofs", "lecleach_f90 run OK"),
    ("runs/m4_smoke/final_lecleach_rollback.log", "total J=49.3543", "lecleach_rollback J"),
    ("runs/m4_smoke/final_lecleach_rollback.log", "run OK: seed J=49.3543, 763 dofs", "rollback run OK"),
    ("runs/m4_smoke/final_lecleach_iwata_ar.log", "total J=67.8605", "iwata_ar J"),
    ("runs/m4_smoke/final_lecleach_iwata_ar.log", "run OK: seed J=67.8605, 885 dofs", "iwata_ar run OK"),
    ("runs/m4_smoke/final_lecleach_toroidal.log", "total J=53.4591", "toroidal J"),
    ("runs/m4_smoke/final_lecleach_toroidal.log", "run OK: seed J=53.4591, 2058 dofs", "toroidal run OK"),
    ("runs/m4_smoke/final_conical.log", "total J=154.74", "conical J"),
    ("runs/m4_smoke/final_conical.log", "run OK: seed J=154.74, 1319 dofs", "conical run OK"),
    ("runs/m4_smoke/final_symcheck_quarter.log", "total J=41.7813", "symq J"),
    ("runs/m4_smoke/final_symcheck_quarter.log", "run OK: seed J=41.7813, 451 dofs", "symq run OK"),
    ("runs/m4_smoke/final_symcheck_full.log", "total J=41.7537", "symf J"),
    ("runs/m4_smoke/final_symcheck_full.log", "run OK: seed J=41.7537, 1636 dofs", "symf run OK"),
    ("runs/m4_smoke/compare_symcheck.log", "bw_h_deg     max |diff| 0.05114 deg", "symq bw_h"),
    ("runs/m4_smoke/compare_symcheck.log", "bw_v_deg     max |diff| 0.04063 deg", "symq bw_v"),
    ("runs/m4_smoke/compare_symcheck.log", "di_db        max |diff| 0.00426 dB", "symq di"),
    ("runs/m4_smoke/compare_symcheck.log", "on_axis_db   max |diff| 0.004228 dB", "symq on-axis"),
    ("runs/m4_smoke/compare_symcheck.log", "ripple_v_db  max |diff| 0.004177 dB", "symq ripple_v"),
    ("runs/m4_smoke/compare_grid_vs_conical.log", "bw_h_deg     max |diff| 3.264 deg", "gridvsc bw_h"),
    ("runs/m4_smoke/compare_grid_vs_conical.log", "bw_v_deg     max |diff| 3.449 deg", "gridvsc bw_v"),
    ("runs/m4_smoke/compare_grid_vs_conical.log", "di_db        max |diff| 0.07094 dB", "gridvsc di"),
    ("runs/m4_smoke/compare_grid_vs_conical.log", "on_axis_db   max |diff| 0.1096 dB", "gridvsc on-axis"),
    ("runs/m4_smoke/compare_grid_vs_conical.log", "NOTE: the two rows are different designs", "gridvsc different-design note"),
    ("runs/m4_code/suite_final.log", "FAILED tests/test_mesh_pin.py::test_installed_hornlab_packages_match_their_pins", "suite tripwire"),
    ("runs/m4_code/suite_final.log", "short test summary info", "suite summary present"),
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
