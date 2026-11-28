# Cone source model plan — non-uniform cone velocity for the `cone_plughorn` mid

2026-10-29. **Status: plan only. Nothing here is implemented.** Owner-gated: C2/C3 touch the solver
boundary condition and need an explicit go, and C6 needs hardware (an LDV or ring accelerometers).
Read `docs/DRIVER_MODEL.md`, `docs/research/HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md` and
`docs/research/typologies/CONE_MIDHORN_AXEHEAD_2026-10-28.md` first.

Labels follow the repo convention: **[published]** primary source, **[consensus]** practitioner
consensus / tool documentation, **[inferred]** our reasoning, **[unknown]** not established.

---

## 0. The problem in one page

The cone mid horn must cover **220 Hz – 4 kHz** (`docs/research/HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md` §2).
Today the cone face (BEM tag 2) is driven as a **rigid axial piston**: `solve.source_motion: axial` gives
`v_n = v_axial · cos(cone angle)` on the cone surface, uniform in amplitude and phase at every frequency.

The far field of an axisymmetric source is the Hankel transform of its surface velocity [published,
Williams *Fourier Acoustics* 1999; Morse & Ingard 1968]:

```
p(θ) ∝ ∫₀^a v(r) · J₀(k·r·sinθ) · r dr
```

Sign changes in `v(r)` therefore **must** produce lobes and nulls. A uniform piston cannot produce them at
any frequency. A paper cone is pistonic only up to its first break-up mode — conventionally around
**0.7–1.5 kHz for a 10-inch paper cone** [consensus; driver-specific, must be measured]. So in the
1–4 kHz half of the design band the model's *directivity* is an assumption, not a prediction — while
every loudness readout that consumes the same solve (`z_throat`, pressure per unit acceleration) inherits it.

This matters because the failure is **silent**: a rigid-piston BEM returns smooth, plausible polars.

What this plan does *not* change: the horn, the mouth, the mesh, the lumped circuit's job. The geometry is
not the weak link; the **velocity boundary condition on the cone** is.

---

## 1. What the research established (and what it did not)

| Claim | Label | Source |
|---|---|---|
| A compression driver's phase plug equalises path lengths to give an approximately plane, uniform-phase wavefront at the exit | published | Dodd, *Reproduced Sound* 2008/2009 (DOI 10.25144/17668, 10.25144/17460); Bernland et al., *SIAM J. Sci. Comput.* 41(4) 2019 (DOI 10.1137/18M1175768); Berggren et al., *JASA* 147(2) 2020 (DOI 10.1121/1.5147234) |
| A cone in a front chamber is a cavity + constriction: the throat pressure is not simply the cone's volume velocity and is not uniform in phase; chamber modes appear as frequency rises | published | Smith, "Air chamber of horn type loudspeakers", *JASA* 25, 305 (1953), DOI 10.1121/1.1907038 |
| Above cutoff the horn is a waveguide: higher-order modes from a non-planar source are evanescent, so the far field is set mainly by the propagating mode, flare and mouth | published (waveguide theory) + inferred (applied to horns) | Morse & Ingard, *Theoretical Acoustics* 1968; Pierce, *Acoustics* 1989 |
| Below cutoff all modes are evanescent; the horn stops controlling the pattern over roughly an octave and the system radiates closer to a direct radiator | consensus | Keele, AES preprints 1038 (1975), 1250 (1977); Kolbrek, "Horn Theory", *audioXpress* 2008 |
| Cone break-up is a modal velocity distribution with nodal rings and phase reversals; the radiated field is no longer the piston pattern | published | Frankort, *Vibration and Sound Radiation of Loudspeaker Cones*, Philips Res. Repts Suppl. 5 (1975); Kagawa et al., *JSV* 69, 229 (1980), DOI 10.1016/0022-460X(80)90608-2; Hu et al. 2017, DOI 10.1155/2017/2792376; Klippel posters "Loudspeaker Cone Vibration" / "Loudspeaker Sound Radiation" |
| Break-up changes **directivity**, and its sign is mode-dependent — "break-up narrows the pattern" is not a rule | published/inferred | Hankel-transform argument above; Frankort 1975 |
| A predictive "effective radius shrinks with frequency" law exists | **no** — nothing published | — |
| A measured 10-inch-cone-horn vs compression-horn polar comparison below cutoff exists | **no** — genuine gap | — |
| Hornresp is purely lumped (Sd the only area, no cone shape, no break-up); AkAbak/ABEC take a prescribed velocity surface but ship no cone-mode source; COMSOL can predict break-up from shell FE | consensus / tool documentation | Hornresp manual (hornresp.net); AkAbak (akabak.com); ABEC; COMSOL Acoustics Module docs |
| Below ~220 Hz both a 10-inch cone (ka≈0.5) and a 1–2-inch driver exit (ka≈0.1) are near-omnidirectional; the practical driver-type difference there is small in pattern and larger in output/loading | inferred from ka table | our calculation from the ka table in §2 |

**Consequence for us:** the rigorous route is measured (or FE-modelled) complex `v(r,f)` driving the existing
cone face, then the Rayleigh/Hankel relation above. A scalar effective-radius law can smooth the main-lobe
width but cannot create lobes, so it must never be presented as "break-up modelled".

---

## 2. The ka table that sets the validity band

| Source | Radius | ka = 1 at | ka at 4 kHz | ka at 220 Hz |
|---|---:|---:|---:|---:|
| 10-inch cone (`cone_r_mm` 105–127) | 105–127 mm | 430–520 Hz | 7.7–9.3 | 0.42–0.51 |
| 8-inch cone (`cone_r_mm` 84–90) | 84–90 mm | 610–650 Hz | 6.2–6.6 | 0.34–0.36 |
| 2-inch compression exit | 25.4 mm | 2.15 kHz | 1.9 | 0.10 |
| 1.4-inch compression exit | 17.8 mm | 3.07 kHz | 1.3 | 0.07 |

So: the piston assumption is defensible for the compression drivers to ~2–3 kHz; for the paper cones it is
defensible to roughly their first break-up, i.e. **about 2–3× the ka = 1 frequency, 0.7–1.5 kHz on the 10-inch**,
and no further.

---

## 3. Current implementation audit (exact seams)

| Seam | File / symbol | Today | Implication |
|---|---|---|---|
| Source motion | `hornlab_search/config.py::solve.source_motion`; `solve/beat.py` forwarding; beat fork `SolveConfig.source_motion` | `"normal"` (breathing cap) or `"axial"` (rigid piston along +z); refused on non-beat backends | the only cone-specific source control we have |
| Profile hook | beat fork `SolveConfig.source_profile_alpha` | `v(r) = 1 + alpha·J0(j01·r/r0)`, per source **face**, normalised so the tag's total volume velocity equals the uniform case; **fused CUDA only**, refused everywhere else (Python and Julia both) | the machinery to scale individual source faces already exists — on one path |
| Julia factor builder | beat fork `julia/BeatEngineDriver.jl::source_profile_factors(mesh, element_mesh_ids, radiators, ::Type{T}, alpha; ...)` (~line 841/869) | builds a per-face factor from the J0 formula | generalising this to an arbitrary per-face table is the smallest real change |
| Multiple sources | beat fork `SolveConfig.velocity_sources: dict[int, float]`, but `source_tag` does `((tag, _),) = self.velocity_sources.items()` | **exactly one** source tag enforced | multi-ring via tags is a fork change, not a config change |
| Julia radiators | `BeatEngineDriver.jl` `radiators`, `channel_unit_drives`, `validate_radiator_elements` | plural radiator machinery exists | multi-tag *may* be closer than it looks — **[verify] before choosing route B** |
| CPU solver | `hornlab_search/solve/bempp.py` (`velocity_sources={SOURCE_TAG: 1.0}`, ~line 171) | uniform unit drive, no profile path | the independent CPU cross-check cannot currently see a profile — a profile we cannot cross-check is not evidence |
| Tagging | `tools/cad/multicell.py::LABELS = (DRIVER_LABEL, WALL_LABEL)`, `write_labelled_step`, `read_face_inventory` | exactly `{driver, wall}`; refuses more; exactly one `driver` face required | ring tags need a schema + mesher change, and `plughorn._is_driver_face` (area match) must become per-ring |
| Circuit coupling | `hornlab_search/driver/compression.py::drive` | `Ut = Sd_eff·v`, `Zmot = Zm + Sd_eff²(Zf+Zr)`, `p_ac = Re(zta)|Ut|²` | a non-uniform source needs an **equivalent area** and a **velocity-weighted** radiation impedance from the solve, not a circuit-side fudge |
| Impedance readout | beat fork `sweep.py` (`entry_impedance = mean_pressure_velocity * acceleration_scale`) | mean pressure over the source tag | for a profile this must become the velocity-weighted mean (see §5.4) |
| Reporting | `tools/loudness_report.py` | prints driver tags, `(Mms!)`, break-up note | needs a validity-band line and a profile id |

**The break-up placeholder we shipped** (`f_breakup_hz` + `Sd_eff(f) = Sd/(1+(f/f_b)^n)` in
`driver/compression.py`) is not a directivity model and must stop being described as one. It survives only as
a diagnostic scalar until C4 replaces its role.

---

## 4. Design options

| Option | What it is | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A. Profile on one tag** (recommended) | Replace the scalar `source_profile_alpha` with a **radial table** of per-face complex factors on tag 2; generalise `source_profile_factors`; enable on CPU beat **and** bempp | No CAD/STEP/mesher change; reuses existing per-face machinery; the CPU cross-check can validate it; axisymmetric modes are what dominate | Cannot represent non-axisymmetric modes (they need azimuthal variation) | **Build first** |
| **B. Multi-tag rings** | Split the cone face into N annular faces, each its own tag with its own amplitude | Per-tag machinery already exists on the Julia side (radiators); scales to non-axisymmetric sectors later | STEP label schema, mesher tag map, `_is_driver_face`, `velocity_sources` singleton, per-tag area bookkeeping, symmetry copies | Second, only if A's residual is shown to matter |
| **C. Full modal / measured field per element** | Complex `v` per triangle from LDV or shell FE | The rigorous answer | Needs per-element Neumann data on every backend; large data through the solve cache; hardware | Target for C6, delivered as a special case of A's table with N = number of rings |
| **D. Do nothing, label the band** | Keep the rigid piston, print "piston-valid to f_b; above that an assumption" | Zero risk, honest immediately | No 1–4 kHz directivity prediction, which is the whole point of the typology | **Interim only (C0)** |

**Recommendation:** C0 now, A as the real fix, B only with evidence, C as the measurement ingest format.

---

## 5. Proposed design (route A)

### 5.1 Config surface

New `solve.source_profile` block (absent = today's uniform drive, byte-identical):

```yaml
solve:
  source_motion: axial            # unchanged; the profile scales the normal velocity it defines
  source_profile:
    id: evo7sh_measured_2026_11   # free text; goes into the solve hash and every report
    kind: rings                   # rings | uniform
    piston_valid_hz: 1200         # REQUIRED: the band below which the profile is the piston's
    rings:                        # outer edge in mm from the axis; v is complex, normalised on load
      - {r_mm: 30,  re: 1.00, im: 0.00}
      - {r_mm: 60,  re: 1.00, im: 0.00}
      - {r_mm: 85,  re: 1.00, im: 0.00}
      - {r_mm: 105, re: 1.00, im: 0.00}
    # Optional: a table gives frequency-dependent rings (the honest form)
    table_file: examples/profiles/evo7sh_ldv_2026_11.csv   # r_mm, f_hz, re, im
```

Validation rules (all must raise, not default):
- `kind: rings` requires either `rings` or `table_file`; `piston_valid_hz` required.
- Ring edges strictly increasing, `r_mm[-1]` within ±1 mm of the tag's equivalent radius
  (`sqrt(A_tag/π)`), otherwise the profile does not cover the source.
- `table_file` needs a header and finite values; unknown columns rejected.
- The profile **normalises on load** to the same total volume velocity as uniform
  (`Σ f_n A_n = A_tag`), so `drive()`'s linear scaling stays meaningful and a unit profile is exactly today.
- A profile without `piston_valid_hz` is refused: the whole point is to declare the band.

### 5.2 Data model (pure Python, no solver) — `hornlab_search/solve/profile.py` (new)

```python
@dataclass(frozen=True)
class SourceProfile:
    id: str
    kind: str                     # "uniform" | "rings"
    piston_valid_hz: float | None
    rings: tuple[Ring, ...] = ()  # Ring(r_mm, re, im) or a frequency table

    def factors(self, f_hz: float) -> np.ndarray:
        """Per-ring complex factor, normalised so Σ factor_n · A_n == A_tag."""

    def equivalent_area_m2(self, tag_area_m2: float, f_hz: float) -> float:
        """A_eq = Σ factor_n · A_n — the uniform-piston area that moves the same volume
        velocity. drive() uses A_eq where it uses Sd_eff today."""

    def hash(self) -> str: ...
```

Uniform profile → `factors = 1`, `A_eq = A_tag`, and **the solve request must not gain any key** (the same
rule `source_motion: normal` follows today: absent means default, and the hash stays put).

### 5.3 Solver plumbing

`hornlab_search/solve/beat.py` — replace the fused-only refusal with a capability check:

```python
# [current, ~line 88]
alpha = extra.get("source_profile_alpha")
if alpha is not None and float(alpha) != 0.0:
    fused = os.environ.get("HORNLAB_BEAT_FUSED_BM_CUDA", "0") == "1"
    if device != "cuda" or not fused:
        raise ConfigError("WP16: profile source implemented on the fused path only ...")

# [proposed]
prof = extra.get("source_profile")
if prof is not None:
    if backend not in ("beat_cpu", "beat_cuda", "bempp_cpu"):
        raise ConfigError(...)
    kw["source_profile"] = prof.to_request()      # {"factors": [...], "id": ..., "normalize": True}
```

Fork side, `julia/BeatEngineDriver.jl` — generalise the factor builder (signature today at ~line 841):

```julia
# [current]
source_profile_factors(mesh, element_mesh_ids, radiators, ::Type{T}, alpha; ...)   # J0 formula

# [proposed]  same seam, table instead of a formula
source_profile_factors(mesh, element_mesh_ids, radiators, ::Type{T}, factors::Vector{T})
```
Keep the existing J0 path by compiling the table from `alpha` before the call, so `source_profile_alpha`
stays bit-identical for its users.

`hornlab_search/solve/bempp.py` — the CPU cross-check must see the same factors. **Verify first** where the
installed `hornlab_bempp_bem` sets its Neumann trace for tag 2 (it currently receives
`velocity_sources={SOURCE_TAG: 1.0}`); if it has no per-element hook, this is the long pole of C3 and must be
scoped against `docs/FORKS.md` rather than improvised.

### 5.4 Two-way coupling — the part that is easy to get wrong

The circuit is referred to the diaphragm, so at unit diaphragm velocity it must see the **radiation impedance
of the actual velocity distribution**, not the uniform mean. From the solve's surface pressure `p_n` and
velocity `v_n` on the source faces:

```
Z_rad = Σ_n conj(v_n) p_n A_n  /  Σ_n |v_n|² A_n        (complex, engineering convention)
A_eq  = Σ_n v_n A_n / v_ref                             (= A_tag for a normalised profile)
```

Then `driver/compression.py` replaces its two uses:

```python
# [current]
load = sd_eff ** 2 * (zf + zr)
ud = sd_eff * v
p_ac = np.real(zta) * np.abs(ut) ** 2

# [proposed]  values come from the RESPONSE, not from a circuit-side law
load = a_eq ** 2 * (zf + zr)              # a_eq from resp.meta["source"]["a_eq_m2"]
ud = a_eq * v
p_ac = np.real(z_rad) * np.abs(ut) ** 2    # z_rad from resp.meta["source"]["z_rad"]
```

and `Sd_eff`/`f_breakup_hz` stop feeding the circuit (kept only as a labelled diagnostic, or removed).
`z_throat` itself keeps its meaning (uniform-drive impedance) only for the uniform profile; with a profile the
stored `z_throat` is the profile's impedance and must be labelled as such in `meta`.

### 5.5 Reporting

- `resp.meta["source"] = {"id", "kind", "piston_valid_hz", "a_eq_m2", "z_rad", "rings"}`.
- `tools/loudness_report.py`: a `source` line per horn/design and, on every driver row, the band:
  `piston-valid to 1.2 kHz; above that the profile is the assumption` — never a silent curve.
- `search.ndjson` / dataset record: the profile hash joins the solve-group fingerprint, so a profile change is
  visible and a resume cannot silently mix profiles (same rule as `source_motion`).

---

## 6. Work packages, in order

| WP | Scope | Files | Gate (must paste terminal output) | Solver? |
|---|---|---|---|---|
| **C0** | Retire the claim: `Sd_eff` is a diagnostic, not a directivity model. Print the piston-valid band in reports and `docs/DRIVER_MODEL.md`. No numbers change. | `docs/DRIVER_MODEL.md`, `tools/loudness_report.py`, `driver/compression.py` docstrings | tests unchanged; one report shows the band line | no |
| **C1** | `SourceProfile` + YAML schema + validation + normalisation; uniform profile provably byte-identical | `solve/profile.py` (new), `config.py`, `tests/test_solve_profile.py` | unit tests: normalisation, rejection cases, uniform == today's request hash | no |
| **C2** | beat CPU: apply per-face factors; generalise the Julia builder | fork (`config.py`, `sweep.py`, `BeatEngineDriver.jl`), `solve/beat.py` | annular-piston case vs a Rayleigh-integral numeric reference (our own integral, not a solver) on a baffled disc; uniform profile reproduces today bit-for-bit | CPU beat |
| **C3** | bempp CPU: same factors (the independent cross-check) | `solve/bempp.py` (+ fork if needed) | beat_cpu vs bempp_cpu agree < 0.2 dB on the same profile; then the same closed-form case | CPU |
| **C4** | `A_eq` / `Z_rad` in `meta`, circuit consumes them, `Sd_eff` retired | `metrics/loudness.py`, `driver/compression.py`, `sweep.py` | energy balance to machine precision with a profile; 1 W SPL consistent with `p_ac`; no change for uniform | CPU |
| **C5** | Reporting + provenance: source block, profile hash in the fingerprint, CSV columns | `tools/loudness_report.py`, `gui/data.py` (run detail), dataset record | a stored run round-trips its profile; a profile change invalidates the group | no |
| **C6** | Measurement ingest: LDV / ring accelerometer CSV → profile table; acceptance criteria | `tools/` converter, `examples/profiles/`, docs | measured profile loads, normalises, and produces a labelled solve | hardware |
| **C7** | (optional) multi-tag rings / non-axisymmetric sectors | STEP labels, mesher map, `plughorn._is_driver_face`, fork `velocity_sources` | only if C6 shows the axisymmetric residual dominates | GPU |

Sequencing rule: **C0 immediately**, C1–C2 as one lane, C3 as a second lane (they do not share files), C4
depends on C2, C5 on C4, C6 parallel and hardware-bound. No GPU solve while a night runs (CLAUDE.md GPU
hygiene); C2/C3 are CPU-only and may run alongside a night **only** if the night is on GPU and the box has
spare cores — check with `tools/night_status.py` first.

---

## 7. Verification plan

1. **Uniform-profile identity.** With `kind: uniform` (or no profile), the solve request hash, `z_throat`,
  SPL and polars must be bit-identical to `HEAD`. This is the single most important test: it means the new
  machinery cannot silently move every stored number.
2. **Closed-form source.** A baffled annular piston has an exact on-axis and far-field expression from the
  Rayleigh integral. Drive the plughorn's cone face with a two-ring profile on a *closed* test mesh (a
  hemisphere) and compare against that integral to ≤0.5 dB at ka 1–5. Our own numeric integral is allowed
  here (it is a test oracle, not a solver).
3. **Zero-phase rings.** A profile whose rings all have `im = 0` and equal `re` must reproduce the uniform
  piston exactly (to solver precision), because the normalisation makes it the same source.
4. **Phase reversal produces a null.** Two rings with `re = +1, −1` must put a null where the integral says
   it is. This is the test that proves the model can do the thing it is being built for.
5. **Energy + impedance.** With a profile, `p_ac` from `Z_rad` must equal `0.5·Re(Z_rad)·|U|²` and the circuit's
  electrical balance must still close to machine precision.
6. **Symmetry.** All existing symmetry-pairing checks must still pass; a profile must not break the
   quadrant/`velocity_sources` derivation (`mesh/sizing.SYMMETRY_PLANE`).
7. **Thin gap.** Any profile result at 2.4–2.7 mm axe-head clearance is only as good as the throat impedance:
  run the CPU cross-check from `docs/research/HANDOFF_CONE_DRIVER_MODEL_2026-10-28.md` §5.1 **before**
  believing a 4 kHz polar.

---

## 8. Measurement that settles it (C6)

- **Primary:** scanning laser Doppler vibrometry on the cone, in situ (in the bowl, axe head fitted), 1/3-octave
  points 200 Hz – 4 kHz. Deliverable CSV: `r_mm, f_hz, re_m_per_s, im_m_per_s` on a fixed grid, phase
  referenced to the drive current.
- **Fallback:** 3–5 miniature accelerometers on concentric rings (rim, mid, near dust cap) → a 3–5 ring
  piecewise-constant profile. Enough to capture the first radial mode and its phase reversal; not enough for
  non-axisymmetric modes.
- **Acceptance against the model:** the same profile replayed through the BEM must predict the measured polars
  within ±2 dB from 1–4 kHz in the coverage region, and the measured impedance within 15 %. If it does not, the
  chamber/plug geometry is the next suspect, not the profile.
- **What we must not do:** fit `Sd_eff`-style scalars to measured polars and call it a model. Fit is allowed
  only as a calibration, labelled.

---

## 9. Risks and non-goals

| Risk | Mitigation |
|---|---|
| A profile change alters `z_throat`, so every stored cone solve becomes incomparable | profile hash in the solve-group fingerprint; uniform stays bit-identical; never re-label an old run |
| Per-element Neumann data is not exposed by `hornlab_bempp_bem` | C3 scoped as a fork change per `docs/FORKS.md`; **verify before committing to the plan** |
| The 2.4 mm gap dominates the 4 kHz error, making profile work look wrong | thin-gap CPU cross-check gate before any 4 kHz claim |
| Profile data is 3–5 numbers pretending to be a mode shape | label it `kind: rings` + `piston_valid_hz`; a table is the honest form |
| A night is running | CPU-only lanes; no GPU solve, no Julia host, no pytest solver tests |

**Non-goals:** cone FE/shell modelling (COMSOL is the tool if that is ever needed); non-axisymmetric modes
(C7 only with evidence); thermal/`Bl(x)` non-linearity; driver rear radiation in the front passband
[consensus: low impact, add only for a below-cutoff question].

---

## 10. Owner decisions needed

- [ ] **Approve C0** (report honesty): print the piston-valid band, retire `Sd_eff` as a model.
- [ ] **Approve C1–C2** (the profile data model + beat CPU path). This is the solver-adjacent change.
- [ ] **Choose the driver** for the first profile (stand-ins are in `examples/drivers/`; the real one is unmeasured).
- [ ] **LDV access?** If no, accept the 3–5 accelerometer fallback and its limits.
- [ ] **C7 now or later** — multi-tag rings only if the axisymmetric residual is shown to matter.

---

## 11. Sources

| Source | Gave |
|---|---|
| Frankort, *Vibration and Sound Radiation of Loudspeaker Cones*, Philips Res. Repts Suppl. 5 (1975) | measured cone modal velocity and its radiation; the reason a piston is not enough |
| Kagawa et al., *JSV* 69, 229 (1980), DOI 10.1016/0022-460X(80)90608-2 | coupled FE/BEM cone radiation |
| Hu et al. (2017), DOI 10.1155/2017/2792376 | modern coupled cone radiation |
| Smith, *JASA* 25, 305 (1953), DOI 10.1121/1.1907038 | front-chamber behaviour: compliance + throat mass + modes |
| Dodd, *Reproduced Sound* 2008/2009, DOI 10.25144/17668, 10.25144/17460 | phase-plug wavefront equalisation |
| Bernland et al., *SIAM J. Sci. Comput.* (2019), DOI 10.1137/18M1175768; Berggren et al., *JASA* (2020), DOI 10.1121/1.5147234 | modern phase-plug optimisation incl. viscothermal effects |
| Morse & Ingard, *Theoretical Acoustics* (1968); Pierce, *Acoustics* (1989); Williams, *Fourier Acoustics* (1999) | waveguide mode filtering; the Hankel/Rayleigh relation |
| Keele, AES 1038 (1975), 1250 (1977); Kolbrek, "Horn Theory", *audioXpress* (2008) | cutoff behaviour, pattern control |
| Beranek, *Acoustics* (1954/1986); Olson, *Acoustical Engineering* (1957) | direct-radiator directivity, rear radiation |
| Cremer/Heckl/Petersson, *Structure-Borne Sound* 3rd ed. (2005) | coincidence — **explicitly not transferable to a cone** (curvature/orthotropy dominate) |
| Hornresp manual; AkAbak; ABEC; COMSOL Acoustics Module docs | what the established tools do and do not model |
| Klippel posters, klippel.de | measured cone modal/radiation behaviour |

---

## 12. Why this is worth doing at all

The typology's reason to exist is a **paper cone covering 220 Hz – 4 kHz in a controlled-pattern horn**
(`docs/research/typologies/CONE_MIDHORN_AXEHEAD_2026-10-28.md`). Everything the search optimises — coverage,
DI, ripple — is a directivity claim. If the source is a rigid piston to 4 kHz, those claims are geometry-only
and the search is optimising a horn around a fictitious diaphragm. The research says the geometry is fine and
the source is the assumption; this plan fixes the source, keeps the geometry, and makes every affected number
carry its band.
