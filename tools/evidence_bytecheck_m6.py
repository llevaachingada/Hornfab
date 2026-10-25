"""Pre-publish byte-check for docs/evidence/M6_WP12_2026-10-25.md (m4/m5/m5b template).

Every quoted block is checked against its source artifact (cmd-redirect logs, compare
outputs, doctor preflight, junitxml attributes, vram CSVs) under runs/m6_wp12/.
Run from the repo root:
    .venv\\Scripts\\python.exe tools\\evidence_bytecheck_m6.py
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
    # --- preflight ---
    ("runs/m6_wp12/doctor.txt", "pinned-shas       all installed SHAs match pyproject.toml", "pins green pre-measures"),
    ("runs/m6_wp12/doctor.txt", "doctor OK: 11 checks, 0 failed", "doctor 11/11"),
    # --- the four arms (cmd-redirect logs) ---
    ("runs/m6_wp12/fs_a.log", "run OK: seed J=19.8072, 1013 dofs, solve 7.7 s", "osse freestanding run"),
    ("runs/m6_wp12/mnt_a.log", "run OK: seed J=11.6605, 3033 dofs, solve 13.9 s", "osse enclosure run"),
    ("runs/m6_wp12/fs_b.log", "run OK: seed J=30.9448, 1362 dofs, solve 6.0 s", "sculpt freestanding run"),
    ("runs/m6_wp12/mnt_b.log", "run OK: seed J=22.9889, 2813 dofs, solve 16.4 s", "sculpt enclosure run"),
    # --- compares (the freestanding-vs-enclosure deltas) ---
    ("runs/m6_wp12/compare_a.txt", "on_axis_db   max |diff| 2.839 dB", "osse fs-vs-mnt on-axis"),
    ("runs/m6_wp12/compare_a.txt", "di_db        max |diff| 2.5 dB", "osse fs-vs-mnt DI"),
    ("runs/m6_wp12/compare_a.txt", 'bw_h_deg     max |diff| 19.98 deg', "osse fs-vs-mnt bw"),
    ("runs/m6_wp12/compare_b.txt", "on_axis_db   max |diff| 1.333 dB", "sculpt fs-vs-mnt on-axis"),
    ("runs/m6_wp12/compare_b.txt", "di_db        max |diff| 1.184 dB", "sculpt fs-vs-mnt DI"),
    ("runs/m6_wp12/compare_b.txt", "bw_h_deg     max |diff| 14.99 deg", "sculpt fs-vs-mnt bw"),
    # --- VRAM samples (external 10-s sampler CSVs; brief peaks) ---
    ("runs/m6_wp12/vram_mnt_a.csv", "3177", "osse enclosure sampled peak"),
    ("runs/m6_wp12/vram_mnt_b.csv", "2966", "sculpt enclosure sampled peak"),
    # --- summary artifact ---
    ("runs/m6_wp12/WP12_MEASUREMENTS.txt", "199.4", "osse dof increase percent"),
    ("runs/m6_wp12/WP12_MEASUREMENTS.txt", "106.5", "sculpt dof increase percent"),
    # --- mounting plumbing suites (junitxml) ---
    ("runs/m6_wp12_plumbing.xml", 'tests="71"', "mounting plumbing focused 71"),
    ("runs/m6_wp12_plumbing.xml", 'failures="0"', "mounting plumbing 0 failures"),
    # --- offline suite on the final tree ---
    ("runs/m6_fork/suite_m6.xml", 'tests="1372"', "final offline suite count"),
    ("runs/m6_fork/suite_m6.xml", 'failures="0"', "final suite 0 failures"),
    ("runs/m6_fork/suite_m6.xml", 'skipped="0"', "final suite 0 skipped"),
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