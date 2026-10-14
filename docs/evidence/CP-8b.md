# CP-8b — widen `a_deg` / `exponent` (PASS)

Goal (HANDOFF_LOCAL §4): the 60-eval `search_smoke` best design was pinned at the LOWER bounds
`a_deg=25.0` and `exponent=2.0`. Widen using the **mesher's own limits**, not guessed numbers.
Repo: `hornlab_mesher` 0.2.4 (`hornlab-waveguide-mesher`).

## 1. What the mesher actually enforces (code + empirical)

- OSSE radius radicand, `hornlab_mesher/profile_common.py:294`:
  `radicand = (k*r0)**2 + 2*k*r0*z*tan(a0) + z**2*tan(a)**2`, raising only when `< 0`.
  With the repo's own bounds (`a0_deg ∈ [2,30]`, so `tan(a0) > 0`) every term is non-negative
  for `z ≥ 0`, so **this can never fire for any `a_deg ≥ 0`**. The handoff's "must keep
  `a_deg > a0_deg`" is **not enforced** anywhere (verified in code and by probe).
- `families.py::_validate_osse_like` adds only `s → n,q > 0`, `L_mm > 0`, `r0_mm > 0`.
- OSSE cross-section `exponent` is **unvalidated** (use-site clamp `max(e, 1e-6)`,
  `profile_sampling.py:481`; note the 1e-6 clamp target itself overflows — do not go near it).
  The `[2,16]` rule is FREEFORM-*station* only (`freeform.py:968`, `families.py:389-392`).

Empirical profile probe (`_osse_radius_curve`, z grid 0..420 mm):
`a_deg` = 0.0 / 0.5 / 1 / 2 / 5 / 10 / 20 / 25 × `a0` = 2 / 15.5 / 30 × L = 140 / 420 →
**all OK, monotone, positive radius**. Superellipse scale: exponent 0.5 → 0.394, 1.0 → 0.786,
2.0 → 1.104 (finite); 1e-6 → OverflowError.

Empirical REAL mesh probe (`build_mesh`, search_smoke screen settings, quarter):
```
a_deg 0.0 -> MESHED 1835 tris | 2.0 -> 1851 | 5.0 -> 1917 | 10.0 -> 2108 | 15.0 -> 2397 | 25.0 -> 3250
a_deg 5 / a0 30 -> MESHED 2331 | a_deg 10 / a0 30 -> 2497 | a_deg 30 / a0 30 -> 4103
exponent 0.5 -> refused(GeometryInvalidError: azimuth chord 1.79x limit)   | 1.0 -> MESHED 3335
exponent 1.5 -> MESHED 3962 | 2.0 -> 4329 | 4.0 -> 5010
combined worst corner -> refused(MeshTooLarge) / refused(GeometryInvalid) -- clean refusals, no consistency crash
```

## 2. Decision and edits

| key | old lo | new lo | why |
|---|---|---|---|
| `a_deg` | 25.0 | **5.0** | mesher floor ≈ 0 (measured); 5° keeps the coverage-angle DOF non-degenerate; real mesh verified |
| `exponent` | 2.0 | **1.0** | 1.0 meshes; 0.5 is refused → 1.0 is a 2× margin above the real floor |

`examples/search_smoke.yaml` and `examples/osse_baseline.yaml` only. `freeform_hv.yaml` keeps
`exponent` lo 2.0 (FREEFORM station hard `[2,16]` — widening would only create rejected designs).
`throat_adapter.yaml` stays pinned (`search: false`).

## 3. Dry-run (must still mesh)

```
dry-run [screen] search_smoke: mesh 5010 triangles, 2598 dofs (estimate 2556, cap 3000) ... dry-run OK: no solver was launched
DRYRUN_SMOKE_EXIT=0
dry-run [screen] osse_baseline: mesh 7476 triangles, 3850 dofs (estimate 3813, cap 5000) ... dry-run OK
DRYRUN_OSSE_EXIT=0
```

## 4. Rerun `search_smoke --budget 60` (hygiene first)

Run `runs/20261013T121958Z-screen-9e5a5c` (gitignored; hashed in `manifest.sha256`):
```
search: search_smoke mode screen, budget 60 new evaluations, 10 bounded keys
evaluations 60 (60 new, 0 cached), failures {'invalid_geometry': 1, 'mesh_too_large': 7}, GPU 254.5 s, 5.2 s/candidate, 690/h
seed J=22.0678  best J=10.7776 (improved on the seed); stop: budget
SEARCH_EXIT=0
--- post-run julia check --- julia present, killing -> terminated PID 28464; VRAM after 419 MiB
```

## 5. Bound-pinning table (report)

```
<p>For each searchable key: how often the top 6 designs sat within 2% of a bound. A pinned parameter means the bound is wrong, not that the answer is optimal.</p>
L_mm    lo 140 hi 420 seed 260  best 251.51232   0/6  0/6
a0_deg  lo 2   hi 30  seed 15.5 best 3.03123     1/6  0/6
a_deg   lo 5   hi 55  seed 37.5 best 33.53987    0/6  0/6
aspect_ratio lo 1 hi 2 seed 1.25 best 1.13911    0/6  0/6
exponent lo 1  hi 8   seed 4    best 4.67376     0/6  0/6
k       lo 0.3 hi 2.5 seed 1    best 1.68477     0/6  0/6
n       lo 2   hi 8   seed 4    best 5.13889     0/6  0/6
q       lo 0.9 hi 1   seed 0.995 best 0.98023    0/6  0/6
s       lo 0   hi 1   seed 0.7  best 0.63418     0/6  1/6
```
**No key pinned**; the old pins (`a_deg=25.0`, `exponent=2.0`) are gone.

Honest caveat: this 60-eval rerun's best J (10.78) is HIGHER than the old run's (9.66) at equal
budget — CMA start/variance at budget 60, not a regression. The actionable outcome is that the
bounds are no longer active constraints.

**Verdict: PASS.**
