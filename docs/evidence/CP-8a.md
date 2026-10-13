# CP-8a — real-machine verification (PASS)

Run on the Windows GPU box (RTX 4060 Laptop 8 GB), branch
`claude/wave-3-implementation-review-2dk4qe`, commit `cfabd48` (pre-CP-8b), interpreter
`.venv\Scripts\python.exe` 3.12.10. Per `docs/HANDOFF_LOCAL.md` §3.

## 1. Offline suite (mesher tests NOT skipped)

```
> .venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck"
... [CP-5 test 17/18 output] ...
============================== warnings summary ===============================
  ... scipy.sparse.linalg.interface deprecation (bempp_cl) ...
480 passed, 18 deselected, 1 warning in 164.42s (0:02:44)
PYTEST_EXIT=0
```
The cloud suite saw 447 passed / 30 skipped; the 30 skips were the mesher-gated tests, which
run here (480 passed matches the expected count).

## 2. `doctor`

```
> .venv\Scripts\hornlab-search.exe doctor
PASS  python-version    Python 3.12.10 in [3.11, 3.14)
PASS  core-imports      numpy, scipy, cma, yaml, jinja2
PASS  hornlab-imports   mesher, beat, plots; bempp yes
PASS  pinned-shas       all installed SHAs match pyproject.toml
PASS  toolchain         TOOLCHAIN.md present, dof_per_triangle=0.51
PASS  gpu               nvidia-smi exits 0
PASS  backend           beat_cuda functional (state=ready)
PASS  configs           all 5 example configs load
PASS  round-trip        seed meshed at 1.5 kHz: 846 tris, 468 nodes, largest extent 0.401 m, source tag 2, quadrants '1' <-> symmetry 'yz+xz'
PASS  gpu-hygiene       0 BEAT host(s) alive, VRAM used 395.0 MiB
doctor OK: 10 checks, 0 failed
DOCTOR_EXIT=0
```

## 3. GPU-marked tests (hygiene first)

Hygiene before: no `julia` process, VRAM 395 MiB. After: stray warm host killed
(`taskkill /F /IM julia.exe`, PID 28464), VRAM back to 395 MiB.

```
> .venv\Scripts\python.exe -m pytest -m "slow or gpu or crosscheck"
[measured] baseline: {'killed_roots': [], 'vram_baseline_mib': 395.0, 'hosts_left': []}
[measured] test 14: cold=17.61 s  warm=0.96 s  post-detach=0.67 s  peak_vram_delta_mib=1142.0
[measured] test 12b full vs quarter (~3.1 kHz): 500 Hz 0.0311 dB, 1000 0.0230, 2000 0.0223, 3000 0.0301
[measured] test 17 beat_cuda vs bempp_cpu, same 2316-dof quarter mesh: max|dH|_norm <= 0.0550 dB
[measured] test 19 trace round trip: MAX difference, recovered vs solver far field: 0.00008 dB
18 passed, 480 deselected, 1 warning in 500.62s (0:08:20)
PYTEST_EXIT=0
```

## 4. Dataset standing before CP-8b

```
> hornlab-search dataset stats
records 134 (ok 119, failed 15), shards 1, 11.1 MB
families {'OSSE': 134, 'R-OSSE': 0, 'ICW': 0, 'FREEFORM': 0}
WARNING: dataset is 100% OSSE (134/134): a surrogate trained on it cannot be tested on other families; run the other example configs
```

**Verdict: PASS.**
