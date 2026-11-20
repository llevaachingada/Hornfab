# CPU scripts behind CROWE_X_FAVORITE_RESEARCH.md (2026-11-20)

Run from the repo root with `.venv\Scripts\python.exe`. The scripts take this folder (or a scratch folder) as their first argument:

- `webster.py`: plane-wave Webster TMM throat-resistance proxy from the generator's wall grid. Trends only; it overstates mouth ripple. `python webster.py` prints the k/L sweep.
- `kL.py <dir-with-webster.py>`: k sweep with depth re-solved to hold the 587 mm mouth (research §4.1 table).
- `fit500.py <dir>`: seed fit for the 500 mm cube / 900 Hz variant (research §5).
- `rescore.py <out-dir>`: CPU replay of the five v11 verify finalists under F_X / load-weight variants (§2.1). It writes variant briefs into `<out-dir>`. Never point it at `examples/`.
- `write_configs.py`: wrote `examples/typologies/fav_crowe_2026-11-20/*` and the compact500_xo900 brief. Its `R` is an absolute repo path.
