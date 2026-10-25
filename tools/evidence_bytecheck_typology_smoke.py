"""Pre-publish byte-check for docs/evidence/TYPOLOGY_SMOKE_MATRIX_2026-10-25.md (m4/m5/m6 template).

Every material cell of the five-row typology smoke matrix is re-derived from the tree: run.json,
search.ndjson, the run's config.yaml, the cmd-redirect logs under scratch/gsmoke_2026-10-25/ and
the external-process VRAM CSVs. No GPU, no mesher, no re-solve. Run from the repo root:
    .venv\\Scripts\\python.exe tools\\evidence_bytecheck_typology_smoke.py
"""
import json
import pathlib
import re
import sys

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


def run_json(run):
    return json.loads(load(f"{run}/run.json"))


def best_row(run):
    """The search.ndjson row the run recorded as best (best.eval_no), else the last row."""
    want = run_json(run)["best"]["eval_no"]
    rows = [json.loads(line) for line in load(f"{run}/search.ndjson").splitlines() if line.strip()]
    for row in rows:
        if row["n"] == want:
            return row
    return rows[-1]


def top_level_name(yaml_path):
    m = re.search(r"(?m)^name:\s*(\S+)\s*$", load(yaml_path))
    return m.group(1) if m else None


def samples(csv_path):
    # one "NNNN MiB" line per external `nvidia-smi --query-gpu=memory.used` poll
    return [int(x) for x in re.findall(r"(\d+)\s*MiB", load(csv_path))]


SCRATCH = "scratch/gsmoke_2026-10-25"

# --- doc rows 1-3 (successful seed smokes; expectations inline, m6 convention) ---
success = [
    {
        "name": "biradial_keele",
        "run": "runs/20261025T182145Z-screen-fe609a",
        "yaml": "examples/typologies/biradial_keele.yaml",
        "j": "22.9837",  # doc row 1 Seed J
        "dofs": 2086,
        "quadrants": "1",
        "vram": f"{SCRATCH}/vram_biradial.csv",
        "baseline": 1301,
        "peak": 2427,
    },
    {
        "name": "qtw_waveguide",
        "run": "runs/20261025T182237Z-screen-1e1d6e",
        "yaml": "examples/typologies/qtw_waveguide.yaml",
        "j": "37.4656",  # doc row 2 Seed J
        "dofs": 1616,
        "quadrants": "1",
        "vram": f"{SCRATCH}/vram_qtw.csv",
        "baseline": 1334,
        "peak": 2104,
    },
    {
        "name": "lecleach_asym_odd",
        "run": "runs/20261025T182334Z-screen-dc8b5d",
        "yaml": "examples/typologies/lecleach_asym_odd.yaml",
        "j": "60.1446",  # doc row 3 Seed J
        "dofs": 2815,
        "quadrants": "1234",  # full ring, per the doc's "(full ring)"
        "vram": f"{SCRATCH}/vram_lecl_asym.csv",
        "baseline": 1337,
        "peak": 3147,
    },
]

# --- doc rows 4-5 (seed refusals; J 1000 penalty, nothing solved) ---
failed = [
    {
        "name": "salmon_x_signed",
        "run": "runs/20261025T182430Z-screen-643205",
        "log": f"{SCRATCH}/x_signed_a.log",
        "detail": "14,414 tris vs effective limit 11,275",
        "error_needles": (
            "mesh_too_large",
            "14,414 triangles, exceeding the effective limit 11,275",
        ),
        "log_needles": (
            "run FAILED: mesh_too_large",
            "contains 14,414 triangles, exceeding the effective limit 11,275",
        ),
        "vram": f"{SCRATCH}/vram_x_signed.csv",
        "baseline": 1345,
        "peak": 1605,
    },
    {
        "name": "salmon_ripple12",
        "run": "runs/20261025T182557Z-screen-8a8752",
        "log": f"{SCRATCH}/ripple12_a.log",
        "detail": "5358 dofs (10,504 tris) vs the 5,000 screen cap for quadrants '14'",
        "error_needles": (
            "mesh_too_large",
            "5358 dofs",
            "10504 triangles",
            "exceeds the dof cap 5000 for quadrants '14'",
        ),
        "log_needles": (
            "run FAILED: mesh_too_large",
            "5358 dofs (10504 triangles, 5332 vertices) exceeds the dof cap 5000 for quadrants '14'",
        ),
        "vram": f"{SCRATCH}/vram_ripple12.csv",
        "baseline": 1388,
        "peak": 1716,
    },
]

checks = []


def add(label, fn):
    checks.append((label, fn))


# --- rows 1-3: run record, seed J, dofs, free-run config ---
for row in success:
    def check_name(row=row):
        shipped = top_level_name(row["yaml"])
        if shipped is None:
            return f'{row["yaml"]}: no top-level name: key'
        rj = run_json(row["run"])
        if rj.get("config_name") != shipped:
            return f'run.json config_name {rj.get("config_name")!r} != shipped yaml name {shipped!r}'
        if rj.get("config", {}).get("name") != shipped:
            return f'run.json config.name {rj.get("config", {}).get("name")!r} != shipped yaml name {shipped!r}'
        return None

    add(f'{row["name"]}: run.json config name == shipped yaml name', check_name)

    def check_j(row=row):
        best = best_row(row["run"])
        if not best.get("ok"):
            return f'ndjson best row not ok: {best.get("error")!r}'
        got = f'{best["objective"]:.4f}'
        if got != row["j"]:
            return f'ndjson J {best["objective"]!r} = {got} != doc {row["j"]}'
        return None

    add(f"{row['name']}: ndjson best J == doc {row['j']}", check_j)

    def check_dofs(row=row):
        got = best_row(row["run"]).get("n_dof")
        if got != row["dofs"]:
            return f'ndjson n_dof {got!r} != doc {row["dofs"]}'
        return None

    add(f"{row['name']}: ndjson dofs == doc {row['dofs']}", check_dofs)

    def check_config(row=row):
        cfg = load(f'{row["run"]}/config.yaml')
        if re.search(r"(?m)^\s*mount", cfg):
            return "run config.yaml carries a mounting key (free run expected)"
        for needle in ("solve:", "backend: beat_cuda", "balloon: true"):
            if needle not in cfg:
                return f"run config.yaml missing {needle!r}"
        m = re.search(r"(?m)^\s*quadrants:\s*'?(\d+)'?", cfg)
        got = m.group(1) if m else None
        if got != row["quadrants"]:
            return f'run config.yaml quadrants {got!r} != doc {row["quadrants"]!r}'
        return None

    add(
        f'{row["name"]}: run config free (no mount), beat_cuda balloon, '
        f'quadrants {row["quadrants"]}',
        check_config,
    )

# --- rows 4-5: recorded failure, quoted failure line ---
for row in failed:
    def check_failure_record(row=row):
        rj = run_json(row["run"])
        reasons = rj.get("stats", {}).get("failures_by_reason") or {}
        if reasons.get("mesh_too_large") != 1:
            return f'run.json failures_by_reason {reasons!r} (want mesh_too_large: 1)'
        best = rj.get("best", {}).get("objective")
        if best != 1000.0:
            return f'run.json best.objective {best!r} != doc J 1000'
        penalty = rj.get("seed", {}).get("terms", {}).get("penalty")
        if penalty != 1000.0:
            return f'run.json seed terms.penalty {penalty!r} != doc 1000'
        return None

    add(f'{row["name"]}: run.json records mesh_too_large + J 1000 penalty', check_failure_record)

    def check_error(row=row):
        best = best_row(row["run"])
        if best.get("kind") != "mesh_too_large" or best.get("ok"):
            return f'ndjson kind={best.get("kind")!r} ok={best.get("ok")!r}'
        err = best.get("error") or ""
        missing = [n for n in row["error_needles"] if n not in err]
        if missing:
            return f"ndjson error missing {missing!r} (got {err[:90]!r})"
        return None

    add(f'{row["name"]}: ndjson records mesh_too_large ({row["detail"]})', check_error)

    def check_log(row=row):
        text = load(row["log"])
        missing = [n for n in row["log_needles"] if n not in text]
        if missing:
            return f'{row["log"]} missing {missing!r}'
        return None

    add(f'{row["name"]}: scratch log quotes the failure line', check_log)

# --- all five rows: VRAM csv present, >=5 samples, sampled max == peak, first == baseline ---
for row in success + failed:
    def check_vram(row=row):
        s = samples(row["vram"])
        if len(s) < 5:
            return f'{row["vram"]}: {len(s)} samples (<5)'
        if max(s) != row["peak"]:
            return f'{row["vram"]}: sampled max {max(s)} MiB != doc peak {row["peak"]} MiB'
        if s[0] != row["baseline"]:
            return f'{row["vram"]}: first sample {s[0]} MiB != doc baseline {row["baseline"]} MiB'
        return None

    add(
        f'{row["name"]}: vram csv >=5 samples, max {row["peak"]} MiB, first {row["baseline"]} MiB',
        check_vram,
    )


# --- every quoted J value formatted like the doc (4 decimals on the successful totals) ---
def check_j_format():
    problems = []
    for row in success:
        if not re.fullmatch(r"\d+\.\d{4}", row["j"]):
            problems.append(f'{row["name"]} doc J {row["j"]!r} is not 4 decimals')
            continue
        obj = best_row(row["run"])["objective"]
        if f"{obj:.4f}" != row["j"]:
            problems.append(f'{row["name"]} ndjson J {obj!r} -> {obj:.4f} != doc {row["j"]}')
    return "; ".join(problems) or None

add("all quoted successful J values are 4-decimal formatted like the doc", check_j_format)


# --- driver-pass re-verification (2026-10-25, later): the 15x gmsh dry-run matrix ---
#: (config, [1in, 14in, 2in brief screens]) — the addendum table in the evidence doc.
DRY_RUNS = [
    ("biradial_keele", [1846, 2023, 2532]),
    ("qtw_waveguide", [1616, 1764, 1990]),
    ("salmon_x_signed", [1792, 1887, 2504]),
    ("salmon_ripple12", [2567, 2751, 3636]),
    ("lecleach_asym_odd", [4190, 4152, 4141]),
]


def check_dryrun_row(name, expected):
    """The scratch dry-runs.log re-derivation: the config's three rows carry the doc's
    dofs (in brief-class order 1in/14in/2in) and all sit under the 5,000 screen cap."""
    log = R / "scratch" / "gsmoke_2026-10-25" / "dryruns.log"
    rows = []
    for m in re.finditer(r"dry-run \[screen\] (\S+): mesh (\d+) triangles, (\d+) dofs", log.read_text(encoding="utf-8", errors="replace")):
        rows.append((m.group(1), int(m.group(3))))
    rows = [r for r in rows if r[0] == name]
    if len(rows) != 3:
        return f"{log}: {name} has {len(rows)} dry-run rows, expected 3"
    got = [r[1] for r in rows]
    for i, (g, e) in enumerate(zip(got, expected)):
        if g != e:
            return f"{name} dry-run {i}: dofs {g} != doc {e}"
        if g > 5000:
            return f"{name} dry-run {i}: dofs {g} OVER the 5,000 screen cap"
    return None


for _name, _expected in DRY_RUNS:
    add(
        f"driver-pass dry-run matrix { _name } (1in/14in/2in) = {_expected}, all <= 5,000 dofs",
        lambda name=_name, expected=_expected: check_dryrun_row(name, expected),
    )


ok = 0
bad = []
for label, fn in checks:
    try:
        problem = fn()
    except FileNotFoundError as exc:
        problem = f"FILE MISSING: {exc.filename or exc}"
    if problem is None:
        ok += 1
    else:
        bad.append((label, problem))
print(f"BYTE-CHECK: {ok}/{len(checks)} PASS")
for label, problem in bad:
    print("FAIL:", (label, problem))
sys.exit(0 if ok == len(checks) else 1)
