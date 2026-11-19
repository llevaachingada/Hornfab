"""Apply the predeclared WP 4.2 equivalence and WP 4.3 authority rules (senior plan 2026-11-17).

WP 4.2 (record-route equivalence, decided BEFORE any variant is read): the unedited record solved
through the point-grid route reproduces the host's stored response if, in every band below, the
mean -6 dB beamwidth differs by at most 1 deg in BOTH planes (and, when a floor is given, |dJ| is
within it). Otherwise B2 stops.

WP 4.3 (U3 authority, unchanged from VALIDATION_EXPERIMENTS.md U3): a freedom has authority if it
moves the INTENDED plane's mean beamwidth by >= 3 deg in at least one band while the other plane
moves by less than half as much. Each passing band also gets a grade: 'authority' when the move
clears 3 deg by at least one standard error of its per-frequency deltas, else 'borderline'. Section steering and the diagonal pull have no single intended
plane: each plane is tried as the intended one and both outcomes are reported.

Inputs are per-arm ``(freqs_hz, bw_h_deg, bw_v_deg)``; ``load_arm`` reads them from a run's
stored ``response.npz`` via the production metric path.

    python tools/analysis/u3_authority.py --host runs/<run>/designs/<h> --config <host config.yaml> \\
        --arm control=runs/<ctl run>/designs/<h> --arm vt_460=... [--floor 0.11 --dj 0.05]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

BANDS_HZ = ((700.0, 1100.0), (1100.0, 2500.0), (2500.0, 5500.0))
EQUIV_DEG = 1.0
AUTHORITY_DEG = 3.0
INTENDED = {"vt_460": ("v",), "vt_480": ("v",), "term_sides": ("h",), "term_topbottom": ("v",),
            "steer_early": ("h", "v"), "steer_late": ("h", "v"), "diag_pull": ("h", "v")}


def band_means(freqs, bw_h, bw_v) -> dict:
    f = np.asarray(freqs, float)
    out = {}
    for lo, hi in BANDS_HZ:
        m = (f >= lo) & (f <= hi)
        key = f"{lo:g}-{hi:g}"
        out[key] = {"h": float(np.nanmean(np.asarray(bw_h, float)[m])) if m.any() else float("nan"),
                    "v": float(np.nanmean(np.asarray(bw_v, float)[m])) if m.any() else float("nan"),
                    "n": int(m.sum())}
    return out


def _common_grid(a, b):
    fa, fb = np.asarray(a[0], float), np.asarray(b[0], float)
    if fa.shape == fb.shape and np.allclose(fa, fb):
        return a, b
    lo, hi = max(fa.min(), fb.min()), min(fa.max(), fb.max())
    f = fa[(fa >= lo) & (fa <= hi)]
    interp = lambda arm: (f, np.interp(np.log(f), np.log(arm[0]), arm[1]),  # noqa: E731
                          np.interp(np.log(f), np.log(arm[0]), arm[2]))
    return interp(a), interp(b)


def equivalence(host, control, *, dj: float | None = None, floor: float | None = None) -> dict:
    h, c = _common_grid(host, control)
    bh, bc = band_means(*h), band_means(*c)
    deltas = {k: {"dh": bc[k]["h"] - bh[k]["h"], "dv": bc[k]["v"] - bh[k]["v"]} for k in bh}
    bw_ok = all(abs(d["dh"]) <= EQUIV_DEG and abs(d["dv"]) <= EQUIV_DEG for d in deltas.values())
    j_ok = None if (dj is None or floor is None) else bool(abs(dj) <= floor)
    return {"band_deltas_deg": deltas, "bw_ok": bool(bw_ok), "dj": dj, "floor": floor,
            "j_ok": j_ok, "pass": bool(bw_ok and (j_ok is not False))}


def authority(control, variant, name: str) -> dict:
    c, v = _common_grid(control, variant)
    bc, bv = band_means(*c), band_means(*v)
    res = {"bands": {}, "authority": False, "via": [], "grade": "none"}
    f = np.asarray(c[0], float)
    for (lo, hi), k in zip(BANDS_HZ, bc):
        dh, dv = bv[k]["h"] - bc[k]["h"], bv[k]["v"] - bc[k]["v"]
        m = (f >= lo) & (f <= hi)
        se = {"h": _se(np.asarray(v[1], float)[m] - np.asarray(c[1], float)[m]),
              "v": _se(np.asarray(v[2], float)[m] - np.asarray(c[2], float)[m])}
        res["bands"][k] = {"dh": dh, "dv": dv, "se_h": se["h"], "se_v": se["v"], "n": int(m.sum())}
        for plane in INTENDED.get(name, ("h", "v")):
            mine, other = (dh, dv) if plane == "h" else (dv, dh)
            if abs(mine) >= AUTHORITY_DEG and abs(other) < 0.5 * abs(mine):
                res["authority"] = True  # the predeclared U3 rule, unchanged
                grade = _grade(mine, se[plane])
                res["via"].append({"band": k, "plane": plane, "delta_deg": mine,
                                   "se_deg": se[plane], "grade": grade})
                if grade == "authority" or res["grade"] == "none":
                    res["grade"] = grade
    return res


def _se(d) -> float:
    """Standard error of the band-mean move from its per-frequency deltas (nan if < 2 points)."""
    d = np.asarray(d, float)
    d = d[np.isfinite(d)]
    return float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else float("nan")


def _grade(move: float, se: float) -> str:
    """Senior verdict 2026-11-19 (SENIOR_VERDICTS_2026-11-19.md): the 3 deg threshold stays; a move
    that clears it by less than one SE is 'borderline' and changes no decision on its own."""
    if not np.isfinite(se):
        return "borderline"
    return "authority" if abs(move) - AUTHORITY_DEG >= se else "borderline"


def load_arm(design_dir: Path, cfg):
    from hornlab_search.search.evaluate import metrics_from_response
    from hornlab_search.solve.cache import load_response
    from hornlab_search.targets.spec import Target
    resp = load_response(Path(design_dir) / "response.npz")
    t = Target.from_dict(dict(cfg.target_raw))
    m = metrics_from_response(resp, t)
    return np.asarray(m.freqs_hz), np.asarray(m.bw_h_deg), np.asarray(m.bw_v_deg)


def write_arm_csv(path: Path, arm) -> Path:
    """Per-frequency H/V -6 dB beamwidth CSV in the throat-evidence format (R18, 2026-11-18), so
    an authority table never depends on a hand-made export."""
    f, h, v = (np.asarray(x, float) for x in arm)
    lines = ["freq_hz,bw_h_deg,bw_v_deg"] + [f"{float(a)!r},{float(b)!r},{float(c)!r}" for a, b, c in zip(f, h, v)]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--arm", action="append", default=[], help="name=design_dir")
    ap.add_argument("--dj", type=float)
    ap.add_argument("--floor", type=float)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--csv-dir", type=Path, help="also write hv_beamwidth_<arm>.csv per arm here")
    a = ap.parse_args(argv)
    from hornlab_search.config import load_config
    cfg = load_config(a.config)
    host = load_arm(a.host, cfg)
    arms = dict(x.split("=", 1) for x in a.arm)
    if "control" not in arms:
        raise SystemExit("--arm control=<design dir> is required (WP 4.2 comes first)")
    control = load_arm(Path(arms.pop("control")), cfg)
    if a.csv_dir is not None:
        write_arm_csv(a.csv_dir / "hv_beamwidth_host.csv", host)
        write_arm_csv(a.csv_dir / "hv_beamwidth_control.csv", control)
        for name, d in arms.items():
            write_arm_csv(a.csv_dir / f"hv_beamwidth_{name}.csv", load_arm(Path(d), cfg))
    report = {"equivalence": equivalence(host, control, dj=a.dj, floor=a.floor), "variants": {}}
    if report["equivalence"]["pass"]:
        for name, d in arms.items():
            report["variants"][name] = authority(control, load_arm(Path(d), cfg), name)
    else:
        report["stopped"] = "record route did not reproduce the host response; variants not read"
    text = json.dumps(report, indent=1, default=float)
    if a.out:
        a.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
