# ATH typology / morph evidence — 2026-10-25

Scope: the two new framework entries (`ath_core`, `ath_twinray_380`), the native
morph surface, and the first mesh/solve checks. Numbers below are pasted from the
commands, not estimated.

## 1. Config/catalog checks

```
families OK: 38 entries in C:\Users\hunte\Hrns\hornlab-search\examples\catalog.yaml
```

`ath_core` — 15 searchable knobs. `ath_twinray_380` — 12 searchable knobs.
`param catalog OK: all three artifacts match a fresh build`.

## 2. Mesh dry-runs (CPU, no solver)

```
dry-run [screen] ath_core: mesh 6174 triangles, 3232 dofs (estimate 3149, cap 5000), quadrants '1' <-> symmetry 'yz+xz'
  mesh built in 1.3 s; f_max 5500 Hz at epw 8; res_mm {'throat': 3.897727272727273, 'mouth': 7.795454545454546, 'rear': 7.795454545454546}; bbox_m (0.0, 0.0, -0.006, 0.1986, 0.1986, 0.3526)
dry-run OK: no solver was launched (mode screen, 3232 of 5000 dofs)
```

```
dry-run [screen] ath_twinray_380: mesh 3796 triangles, 1987 dofs (estimate 1936, cap 5000), quadrants '1' <-> symmetry 'yz+xz'
  mesh built in 16.0 s; f_max 5500 Hz at epw 8; res_mm {'throat': 3.897727272727273, 'mouth': 7.795454545454546, 'rear': 7.795454545454546}; bbox_m (0.0, 0.0, -0.005, 0.19, 0.1517, 0.192)
dry-run OK: no solver was launched (mode screen, 1987 of 5000 dofs)
```

The TwinRay bbox mouth is 380.0 x 303.3 mm, matching the published 380 x 303 mm.
The CORE bbox mouth is 397.2 x 397.2 mm; the `s1/s2` stretch adds ~93 mm to the
axial span (bbox z 352.6 mm), consistent with the published CORE recipe.

## 3. First GPU solves (one job at a time, fresh scratch dirs)

Baseline before the runs: `gpu-clean: VRAM used 389 MiB`; no BEAT hosts alive.
Each run used its own scratch runs/cache/dataset dirs; `gpu-clean` was run before
and after. No VRAM peak was recorded by this path.

```
ath_core seed: J=42.448, 3232 dofs, solve 15.3 s
  run dir scratch/ath_core_smoke/20261026T032125Z-screen-71bbf9
  row: objective 42.44796383804703, triangles 6174, mesh 1.34 s, solve 15.29 s
  bbox_m [0.0, 0.0, -0.006, 0.1985809765366764, 0.1985868260412805, 0.3526293750206872]

ath_twinray_380 seed: J=38.357, 1987 dofs, solve 8.3 s
  run dir scratch/ath_twin_smoke/20261026T032208Z-screen-2923d6
  row: objective 38.35700822654244, triangles 3796, mesh 11.63 s, solve 8.26 s
  bbox_m [0.0, 0.0, -0.005, 0.189985756, 0.1516532779999999, 0.192]
```

These are SEED results, not best-of-search. The high `dislope` terms (63.05 and
42.39) are the expected consequence of asking for a flat DI slope over this band;
they are a search target, not a validation failure.

## 4. Offline suite

```
1606 passed, 0 failed, 0 errors, 0 skipped
runs/ath_morph_suite_final3.xml
```

`compileall` clean; `tools/gen_param_catalog.py --check` OK.

## 5. Reproduce

```
.venv\Scripts\python.exe tools/gen_param_catalog.py --check
.venv\Scripts\python.exe -m hornlab_search.cli run --config examples\typologies\ath_core.yaml --mode screen --dry-run
.venv\Scripts\python.exe -m hornlab_search.cli run --config examples\typologies\ath_twinray_380.yaml --mode screen --dry-run
.venv\Scripts\python.exe -m pytest -q -m "not slow and not gpu and not crosscheck"
```

Scratch run dirs are not part of the dataset; they were used only for this evidence.
