# Renders 2026-10-28 (geometry; solved where stated)

| File | What it shows |
|---|---|
| `petal_os_refined.png` | The 7 refined petal/lobe horns on the CD (OS) throat: clover, union_soft, union_soft_flute, x4_mild, star6_mild, rosette12, 60x40 deep soft (configs `examples/typologies/petal_os_2026-10-28_v4/`). Front, 3/4, behind, side. |
| `quatrefoil_front.png`, `quatrefoil_views.png` | Four-petal "rotate and join" Salmon horns from the ripple X-flute8 winner (fold_xin, fold_xout, union, union_noflute; `examples/typologies/quatrefoil_2026-10-28_v4/`). |
| `hybrids_os_chanterelle.png` | First osse_rollback hybrids: os_curl, os_deepflute, os_ruffle, osse_flare_curl (`examples/typologies/chanterelle_hybrid_2026-10-28_v4/`). |
| `hybrids_superformula_60x40.png` | Superformula X and 6-lobe, 60x40 shallow (300 mm) and deep (420 mm). |
| `chanterelle_ruffled_solved.png` | Salmon chanterelle "ruffled" after its 40-solve search (J 10.73): two views + H/V dispersion. |
| `hybrids_solved_2026-10-28.png` | Best design of each CD-throat hybrid after its 40-solve screen, best first (front, 3/4, behind, side): osse_flare_curl J 1.11, os_deepflute 3.09, sf_x4 3.31, sf_star6 3.74, os_ruffle 3.83, os_curl 4.59. |
| `petal_os_solved_2026-10-28.png` | Best of each refined petal/lobe horn after its 30-solve screen, best first: x4_mild J 3.62, star6_mild 4.48, rosette12 4.64, union_soft 5.18, union_soft_flute 5.53, clover 5.71. |
| `osse_flare_curl_card.png` | Design card of the day's winner, `osse_flare_curl` J 1.11 (run `20261028T160336Z-screen-b4a679`, hash `b01af5f398e6`): two views + full-width H/V dispersion. Loudness line: output gap at f0 11.5 dB, loaded from 1.76 kHz, driver coupling round and matching the exit. |
| `typologies_solved_2026-10-28.png` | Best design of every typology solved today, one row each, front / 3/4 / behind / side: hybrid `osse_rollback` J 1.11, hybrid superformula X 3.31, petal/lobe x4_mild 3.62, Salmon chanterelle ruffled 10.73, quatrefoil four-petal 11.17 (all b3a), Salmon ripple flute10 9.58 (`b1t_hifi`, different brief). |

All J values are on the same `b3a` 90x90 / 400 Hz brief and are screen-mode only (quarter domain).

Made with `tools/render/render_views.py` (pyvista in `scratch/vizenv`) + `tools/render/compose.py`
(see the `hornlab-render` skill); rerun from the run dirs to reproduce.
