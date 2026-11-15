# Rolled-rectangle home-horn pilot, 2026-11-15

Owner correction: the follow-up uses separately measured ES-600 horizontal/vertical sections,
a swept-wall junction, bounded front crown and explicit rear body. The rejected bowed-panel
loft was never queued or published. Seed bbox 417 x 203 x 201 mm; 3197 / 6000 DOFs; round
36 mm throat; envelope fits. The ES-600 source dimensions are 417 x 203 x 198 mm; the extra
3 mm depth belongs to the reconstructed shell/source region. This is an approximation.

New source night: [home_crowe_sections_2026-11-15.yaml](home_crowe_sections_2026-11-15.yaml).
It waits behind the live original rolled-rectangle controller, then runs a 32-attempt search
followed by top-1 verification through `tools/geometry/crowe_panel_cli.py`. The running original
night was not changed. Depth [190,206], H depth scale [0.97,1.03], crown [16,24]; sigma0 .15,
seed 1234, popsize 8. Uniform-box feasibility: 63/64 valid, one invalid_geometry; explicit flat
penalty, predicted 31.5/32 valid attempts. This new visual seed has no prior acoustic history.
Prediction to test: best-at >0, first improvement n=1..8. This is not an equal-size A/B against
the larger original arms. Higher-resolution verification is required before acoustic conclusions.
Related CPU regression: 126 passed in 46.183 s. Nine section-study tests cover section residuals, round throat, sweep domain, sampling
convergence, exterior validity, source-file digest and correct replay/verification entry point.
Detached follow-up controller 31224 (WMI parent 35188) waits on original controller 42084.
Log: `runs/nights/queue_home_crowe_sections.log`; no overlapping solve is launched.

Owner authorization: research Crowe geometry, tune a close starting seed, add a separate
ATH-influenced H/V-puckered variant, integrate short runs into the current queue, commit/push,
and publish multi-angle renders on GitHub Pages. Source dossier:
[original construction and corrections](../research/typologies/ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md).

## Geometry and comparison

The closest visual seed uses the ES-450 drawing's 542 x 299 proportions and 238 reference depth,
with the owner's round 36 mm HF1440 interface. It is an original geometry; no ES construction
equation was found. Its full mesh bounding depth is 241 mm. Independent H/V development
(H/V depth ratio 0.68) creates broad eye-shaped top/bottom panels and an interior X within a
nearly rectangular outline. This ratio is inferred, not recovered from CAD.

Three arms use the same brief, seed 1234, budget 32, popsize 8, sigma0 0.15, and searched
depth [220,265] mm, decay [0.55,0.85], corner exponent [8,16]. Mouth dimensions, throat,
depth ratio, termination and pucker amplitudes stay fixed for attribution.

| Order | Config | H / V pucker inputs | Seed DOFs | Full seed bbox mm |
|---:|---|---:|---:|---|
| 1 | rr__reference_v7 | 0 / 0 mm | 4499 | 542 x 299 x 241 |
| 2 | rr__pucker_hv_moderate_v7 | 12 / 16 mm | 4465 | 542 x 299 x 244 |
| 3 | rr__pucker_hv_strong_v7 | 24 / 28 mm | 4459 | 542 x 299 x 246 |

Positive H advances the side-wall centres, positive V advances the upper/lower wall centres;
the diagonal relief has opposite sign. These are input amplitudes, not ridge heights measured
from a plane. Puckering changes axial shape without making a star in the projected outline.
All three are round and fit the envelope. CPU preflight: 64/64 uniform box samples valid for
each arm, no warnings/hard findings. A uniform sample is not a guarantee for every combination.

No prior acoustic history exists for this family. Predicted best-at / first-improvement eval:
**unmeasured**. The exploratory hypothesis is that a three-dimensional local search can find
useful changes within the first four populations; best-at-seed remains an honest possible result.
Do not claim a short pilot exhausted the family, and do not prescribe a longer run without
reviewing valid fraction, pinning, score terms and fidelity.

## Queue and replay

Night file: `docs/queue/home_rolled_rect_2026-11-15.yaml`, copied byte-for-byte into
`runs/nights/home_rolled_rect_2026-11-15.yaml`. Three serial screens, then top-1 verification
per arm under the existing batch-12/memwatch heavy-run recipe. No parallel solves.
Use **the explicit wrapper for every search/run/verify**, including later manual replay:

```powershell
.venv\Scripts\python.exe tools/geometry/rolled_rect_cli.py search --config examples/typologies/rolled_rect_2026-11-15/rr__reference_v7.yaml --budget 32
.venv\Scripts\python.exe tools/geometry/rolled_rect_cli.py verify --run runs/<new-run> --top 1
```

Persisted recipes carry geometry+adapter source digest and throat parameters. A stale recipe
is refused, and the stock CLI refuses the distinct row type. Existing geometry defaults and
all `hornlab_search/**/*.py` files are untouched. The wrapper is an explicit experimental
integration; stock GUI/catalog preview is not added in this slice.

Queue recheck at about 10:40 local: A had completed its two searches; B had exited with
preparation failure (`training set is 'needs_initial_data'; n_min=18 n=0`), so B is **not** a
completed study. The legacy C controller PID 36944 had already launched its C runner. Preserve
that active run and attach this new night after its controller. Never launch while a GPU run is
live, change a live config, delete locks or perform host cleanup from this task.

Attached at 10:48:33 local: controller **42084**, parent **35188 (WmiPrvSE.exe)**,
waiting on controller **36944** with `WaitMatch home_landscape_c`. Queue log:
`runs/nights/queue_home_rolled_rect.log`. The log confirms the wait; no new GPU solve was
started during this geometry task. A queued night is not a completed acoustic experiment.

## Readout and publication

Read actual search/verify NDJSON, compare J only within this identical brief/objective version,
and inspect H/V/diagonal polars, balloon DI, on-axis response and loading near crossover.
Re-render verified winners separately; the published initial gallery shows **seed geometry**,
not optimizer results. Do not label 80 x 50 as achieved, or the nominal 700 Hz crossover as
proven pattern control. Printed mounting and wall strength remain unverified.

Gallery: `docs/renders/2026-11-15-rolled-rect/index.html` (15 original mesh renders, five angles).
Raw shape checks, preflight JSON, test XML and local reference contact sheets live under
`scratch/2026-11-15_rolled_rect/`. No copyrighted reference photograph is included in the public gallery.
