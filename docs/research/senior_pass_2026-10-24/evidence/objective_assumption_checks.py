"""Sanity checks of the objective's built-in assumptions (no solver)."""
import numpy as np

ang = np.linspace(-90, 90, 73)

def ripple_ideal(cov_total, shape="gauss"):
    half = cov_total / 2
    th = ang[np.abs(ang) <= half + 1e-9]
    if shape == "gauss":           # dB quadratic in angle, exactly -6.02 dB at the edge
        db = -6.0206 * (th / half) ** 2
    else:                          # cos^n pattern with -6 dB at the edge
        n = np.log(0.5) / np.log(np.cos(np.radians(half)))
        db = 20 * np.log10(np.cos(np.radians(th)) ** n)
    return np.std(db, ddof=1)

for c in (60, 90, 120):
    print(f"ideal smooth taper, coverage {c}: ripple_db = {ripple_ideal(c):.2f} (gauss), "
          f"{ripple_ideal(c, 'cos'):.2f} (cos^n)")

# DI of an ideal separable Gaussian beam with -6 dB at +-h/2, +-v/2, vs the cuts formula target
def di_gauss(h, v, n=721):
    th = np.radians(np.linspace(0, 180, n)); ph = np.radians(np.linspace(0, 360, 2 * n, endpoint=False))
    T, P = np.meshgrid(th, ph, indexing="ij")
    # angles projected into the H and V planes
    x, y, z = np.sin(T) * np.cos(P), np.sin(T) * np.sin(P), np.cos(T)
    ah = np.degrees(np.arctan2(x, z)); av = np.degrees(np.arctan2(y, z))
    db = -6.0206 * ((ah / (h / 2)) ** 2 + (av / (v / 2)) ** 2)
    p2 = 10 ** (db / 10)
    w = np.sin(T)
    return 10 * np.log10(1.0 / (np.sum(w * p2) / np.sum(w)))

def di_cuts(h, v):
    sh, sv = np.sin(np.radians(h) / 2), np.sin(np.radians(v) / 2)
    return 10 * np.log10(4 * np.pi / (4 * np.arcsin(sh * sv)))

for h, v in ((90, 90), (90, 60), (75, 45)):
    print(f"{h}x{v}: DI target (cuts formula) {di_cuts(h, v):.2f} dB; ideal Gaussian beam DI {di_gauss(h, v):.2f} dB")

# Far-field distance check for polars at 2 m
c = 343.0
for D in (0.30, 0.40, 0.64, 0.80):
    for f in (5500, 12000):
        print(f"mouth {D*1000:.0f} mm, {f} Hz: 2D^2/lambda = {2 * D * D * f / c:.1f} m")

# Screen grid
f = np.geomspace(500, 5500, 12)
print("screen grid:", np.round(f), "pts/octave =", round(11 / np.log2(11), 2))
# mouth-reflection resonance spacing c/(2L)
for L in (0.12, 0.2, 0.26):
    print(f"L={L*1000:.0f} mm: resonance spacing c/2L = {c / (2 * L):.0f} Hz")
