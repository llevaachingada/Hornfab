"""Le Cléac'h exact formulation (Fourcade 2015, eqs 10-27). Prototype for validation only."""
import numpy as np


def jmlc(fc, T, D_mm, phi0_deg, stop_deg, dl_mm=1.0, c=344.0, law="salmon"):
    dl = dl_mm / 1000.0
    phi0 = np.radians(phi0_deg)
    R0 = (D_mm / 2000.0) / np.sin(phi0)                     # eq 11
    S0 = 2 * np.pi * R0**2 * (1 - np.cos(phi0))             # eq 13
    m = 4 * np.pi * fc / c                                  # eq 43

    def S(l):                                               # eq 42
        return S0 * (np.cosh(m * l / 2) + T * np.sinh(m * l / 2)) ** 2

    xs, ys, phis, dal = [0.0], [D_mm / 2000.0], [phi0], []
    i = 0
    while np.degrees(phis[-1]) < stop_deg:
        i += 1
        li = i * dl
        acc = 2 * np.pi * (R0 + li) ** 2 * (1 - np.cos(phi0))          # eq 15
        k = np.arange(1, i)                                            # known rings 1..i-1
        if k.size:
            h = li - (k - 1) * dl
            ph = np.asarray(phis)[k - 1]
            yk = np.asarray(ys)[k - 1]
            acc += np.sum(2 * np.pi * h * (h * np.sin(ph) + yk) * np.asarray(dal)[k - 1])  # eq 20
        Sii = S(li) - acc                                              # eq 22
        ri = dl * np.sin(phis[-1]) + ys[-1]                            # eq 23
        da = Sii / (2 * np.pi * ri * dl)                               # eq 24
        dal.append(da)
        phi = phis[-1] + da                                            # eq 25
        phis.append(phi)
        xs.append(xs[-1] + dl * np.cos(phi))                           # eq 26
        ys.append(ys[-1] + dl * np.sin(phi))                           # eq 27
        if i > 200000:
            break
    x, y, p = np.array(xs), np.array(ys), np.degrees(np.array(phis))
    L0 = i * dl
    return dict(x=x, y=y, phi=p, L0_mm=L0 * 1000, S_mouth=S(L0), length_mm=x.max() * 1000,
                width_mm=2 * y.max() * 1000, throat_tangent_deg=p[1])


if __name__ == "__main__":
    print("reference (Fourcade fig 7): length 321.35, width 467.30, throat 8.55 deg, S 0.7214 m2")
    print("reference table: stop 90 -> L0 394 / S 0.13; 180 -> 467/0.38; 270 -> 496/0.57; 360 -> 511/0.72")
    for stop in (90, 180, 270, 360):
        r = jmlc(400, 0.8, 25.4, 8.0, stop)
        print(f"stop {stop:3d}: L0 {r['L0_mm']:.0f} mm  S {r['S_mouth']:.3f} m2  length {r['length_mm']:.2f}  "
              f"width {r['width_mm']:.2f}  throat {r['throat_tangent_deg']:.2f}")
