# Typology verification ladder V1–V5 (local GPU box, 2026-10-22)

Plan: `docs/TYPOLOGY_PLAN.md` s9. Code at `872102f` (+ test-only follow-ups). Solver itself verified the same day
(`docs/evidence/SOLVER_VERIFY_2026-10-22.md`).

## V1 — unit properties (offline): PASS
`tests/test_design_generators_profiles.py` 69 passed (conical constant wall angle; exponential area law
S/S₀ = e^{2mz}; hypex T = 1 ≡ exponential, r(L) = r_m; tractrix constant tangent length a and analytic vs numeric
slope; blend endpoints and monotonicity; anchors; monotone perturbation). `tests/test_design_generated.py` 27 passed
(briefs, seed override and config sha, generator configs, never-raising denormalize, envelope, provenance, loading
scalars, failure cache).

## V2 — fidelity on Magnus's own FREEFORM evaluator: PASS
`hornlab_mesher.profile_formulas.profile_points` on the materialised FREEFORM design vs the dense analytic meridian:
max radial error ≤ 0.2 mm for conical, exponential, hypex, tractrix and the OSSE meridian (test
`test_mesher_freeform_reproduces_the_analytic_meridian`). Lane A's own Hermite reconstruction: conical 0.000 mm,
exponential 0.0002, hypex ≤ 0.0006, tractrix ≤ 0.036 mm (16 anchors).

## V3 — mesher acceptance: PASS (11/11 enabled typologies)
`campaign --tier dry-run --families all` on the axisymmetric brief: 18/19 entries mesh (`search_smoke`, legacy, exceeds
its dof cap under the brief's 5.5 kHz band and is refused before meshing). Le Cléac'h is disabled (R9). Random-sample
mesh yield (16 samples per space, after tightening OSSE-based bounds): classical and blends 88–100 %,
`hyb_osse_h_hypex_v` 100 %, `hyb_osse_h_tractrix_v` 69 %, `osse_axi` 81 %, `perturbed_osse_hv` (18 knobs) 63 %.
Failures are the size envelope and the mesher's FREEFORM outer-shell curvature guard; both are scored
`invalid_geometry` and remembered by the failure cache.

## V4 — anchor convergence, acoustic (GPU): PASS
The same horn materialised with 16 and with 48 anchors, solved separately, `hornlab-search compare`
(LOOKUP is not a contract family, so anchor convergence replaces the plan's LOOKUP comparison):

| Typology | DI max diff | on-axis max diff | ripple max diff | beamwidth max diff |
|---|---|---|---|---|
| exponential | 0.052 dB | 0.091 dB | 0.026 dB | 0.52° (H) |
| tractrix | 0.052 dB | 0.047 dB | 0.044 dB | 0.85° |
| conical | 0.009 dB | 0.013 dB | 0.012 dB | 1.13° (H, one frequency) |

dB metrics agree within 0.1 dB (noise floor 0.039 dB); beamwidth differences ≤ 1.1° are threshold-crossing shifts at
single frequencies. 16 anchors are adequate.

## V5 — textbook physics (GPU): PASS

| Typology (seed) | Check | Result |
|---|---|---|
| Exponential, f_c = 690 Hz (m = 12.63 /m) | Re z vs Webster infinite-horn √(1 − (f_c/f)²) | 0.04 / 0.58 / 0.91 / ~1.0 at 500 / 962 / 1196 / ≥ 1849 Hz vs 0 / 0.70 / 0.82 / → 1: same rise through f_c, with finite-horn ripple |
| Exponential | beamwidth narrows with frequency | 170° at 500 Hz → 52° at 2.3 kHz |
| Conical, included angle 61.6° | beamwidth follows 2α over a mid band, then narrows | 60.6° at 1.85 kHz, then 45 → 28° |
| Conical, x₀ = r₀/tan α = 21.3 mm | Re z ≈ (kx₀)²/(1 + (kx₀)²) | 0.09 vs 0.13 at 962 Hz; 0.79 vs 0.65 at 3.56 kHz |
| Tractrix, f_c = 600 Hz (a = 91 mm, cut at 80°) | loading rises through f_c | Re z 0.06 → 0.82 between 622 and 773 Hz |

Julia cleared after each of the 6 solves (0 left, VRAM 593 MiB).

Run dirs: exponential `20261022T212810Z-screen-aaf58a` / `…212841Z-screen-43f0f7`, tractrix `…212912Z-screen-f585e6` /
`…212942Z-screen-0d6c35`, conical `…213015Z-screen-7d52d3` / `…213046Z-screen-1c9004` (16 / 48 anchors).
