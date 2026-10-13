# 06 TASK METRICS AND TARGETS

**Wave 1, parallel with 04, 05 and 07. No shared files.**

Owner of: `hornlab_search/metrics/polar.py`, `di.py`, `smoothness.py`, `impedance.py`, `compute.py`, `targets/spec.py`, `targets/venue.py`, `tests/test_metrics_*.py`, `tests/test_targets_*.py`
Reads: `01_CONTRACTS.md`
Imports: `numpy`, `scipy`, `hornlab_search.types`, `hornlab_search.constants`

Everything here is pure numerics on arrays. **Every test runs in milliseconds with nothing installed.** You never touch a solver or a mesher.

This is the easiest task to get right and the easiest to get subtly wrong. A beamwidth off by a factor of two still plots beautifully and will quietly steer the entire search toward the wrong family of horns. That is why every function below has a closed-form test with a number written down in advance.

---

## Build

### 1. `metrics/polar.py`

```python
def beamwidth_deg(angles_deg, spl_db, drop_db: float = 6.0) -> tuple[float, int]:
    """Total included angle between the OUTERMOST two -drop_db crossings.

    Frozen rules (01_CONTRACTS.md section 10):
      - Reference is the ON-AXIS sample, not the maximum. A horn with a 1 dB
        on-axis dip is not entitled to a narrower reported beamwidth.
      - Interpolate the crossing LINEARLY IN dB versus angle between the two
        bracketing samples. Never snap to the nearest sample.
      - Never crosses in range -> (180.0, 0).
      - More than two crossings -> outermost pair, and return the true count.
      - No exact 0-degree sample -> ValueError.
    """

def coverage_mask(angles_deg, target_total_deg) -> np.ndarray:
    """True inside +/- target/2, inclusive at the edge."""

def normalized_db(spl_db, ref_db=None) -> np.ndarray:
    """spl_db minus the on-axis value. Floor at -120 dB."""
```

The -120 dB floor is not cosmetic. One `-inf` makes every `std` and `mean` downstream `nan`, and a `nan` objective silently poisons the CMA-ES covariance update for the rest of the run.

### 2. `metrics/di.py`

```python
def di_from_balloon(spl_balloon_db, spl_axis_db) -> float:
    """10*log10( p_axis^2 / mean(p_balloon^2) ), computed in LINEAR POWER.
    Equal weights are correct for an equal-area grid."""

def di_from_cuts(bw_h_deg, bw_v_deg) -> float:
    """ESTIMATE. Assumes a separable rectangular pattern.
       Omega = 4*arcsin( sin(bw_h/2) * sin(bw_v/2) )
       DI    = 10*log10( 4*pi / Omega )
    Wrong for lobed or diagonal-misbehaving patterns. The caller MUST set
    MetricSet.di_source = 'cuts_estimate' when using this."""

def target_di_db(cov_h_total_deg, cov_v_total_deg) -> float:
    """Same formula, applied to the target angles. 75 x 45 -> 11.3 dB."""

def di_slope_db_per_decade(freqs_hz, di_db) -> float:
    """polyfit(log10 f, di_db, 1)[0]."""
```

**Convert to linear power before averaging.** Averaging dB values is a different and wrong quantity, and it is the single most common error in directivity code.

`di_slope_db_per_decade` is a small function with outsized value: a constant-directivity horn is one whose DI is flat with frequency, so this one number captures "does the pattern hold together across the band" better than per-frequency beamwidth error does, and it is a smoother thing for an optimizer to chase.

### 3. `metrics/smoothness.py`

```python
def ripple_db(angles_deg, spl_db, target_total_deg, floor_db=-40.0) -> float:
    """Std dev of normalized dB over in-coverage samples, excluding samples
    more than floor_db below on-axis. Fewer than 5 survivors -> np.nan."""

def band_flatness_db(spl_axis_db) -> float:
    """Std dev over frequency of the on-axis level, after removing its mean."""

def coverage_error_deg(bw, target_total_deg) -> np.ndarray:
    """Signed, bw - target. Positive means too wide."""
```

Std dev rather than peak-to-peak: peak-to-peak is set by one sample, which makes the objective landscape spiky and hostile to CMA-ES. It also matches the definition used by the earlier tiling study, so the numbers stay comparable with work already done.

### 4. `metrics/impedance.py`

```python
def normalized_throat_impedance(p, u, area_m2) -> np.ndarray:
    """Specific acoustic impedance at the throat over rho*c.
    If the solver reports volume velocity Q instead of particle velocity u,
    u = Q / area_m2."""
```

**[open]** Whether either backend reports this usefully depends on task 05's step-0 question 7. `hornlab-beat-bem` returns a "legacy-scaled" impedance pair `[Re(F)/2, -Im(F)/2]`. Build the function anyway; it is six lines and fully testable against the plane-wave case. `compute_metrics` sets `z_throat_real = None` when the input is absent, and the default objective weight is `0.0`, so nothing breaks either way.

### 5. `metrics/compute.py`

```python
def compute_metrics(resp: Response, target: Target) -> MetricSet:
    """Iterate over resp.freqs_hz, which holds only what was actually solved.

    di_source is 'balloon' when resp.spl_balloon_db is present, else
    'cuts_estimate'. Record it. Log a WARNING on the fallback, once per run.

    scalars must always contain, with the same key set every time:
      n_freqs, di_source, n_multilobe_h, n_multilobe_v, n_nan_ripple,
      bw_h_mean_deg, bw_v_mean_deg, di_mean_db, di_slope_db_per_dec,
      ripple_mean_db, flatness_db,
      f_break_h_hz, f_break_v_hz, f11_hz
    """
```

The last three come from `constants.py` and are **design checks printed in the report, never constraints on the search**:

```
f_break = KEELE_K / (mouth_dimension_m * coverage_angle_deg)
f11     = BESSEL_J1P_11 * C_AIR / (2*pi*throat_radius_m)
```

They tell a reader at a glance whether a result is physically sensible: a horn should start losing pattern control near `f_break` and may misbehave above `f11`. Mouth dimension and throat radius come from the `MeshResult` bounding box and the design, passed in by the pipeline.

Use `np.nanmean` for every aggregate and record the nan count. A `MetricSet` reporting `ripple_mean_db = nan` with no explanation costs an afternoon.

### 6. `targets/spec.py` and `targets/venue.py`

```python
@dataclass(frozen=True)
class Target:
    coverage_h_deg: float          # TOTAL included angle
    coverage_v_deg: float
    band_lo_hz: float
    band_hi_hz: float
    di_target_db: float | None
    di_slope_target: float = 0.0
    z_min: float = 0.0
    freq_weights: dict | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Target": ...


def coverage_from_room(listener_width_m, depth_near_m, depth_far_m,
                       height_m, ear_height_m=1.2, source_height_m=2.0,
                       splay_deg=0.0) -> Target:
    """Pure trigonometry, no solver. Returns the coverage angles that put the
    listening area inside the pattern."""


def required_mouth_m(coverage_total_deg: float, f_lo_hz: float) -> float:
    """From KEELE_K: d = KEELE_K / (f_lo * coverage_deg).
    The mouth dimension that axis needs to hold pattern down to f_lo."""


def feasibility_report(target: Target) -> dict:
    """{'mouth_h_m', 'mouth_v_m', 'note'}. Says in plain words whether the
    target is physically possible at a sane size."""
```

This is the cheapest genuinely generative piece in the project: it replaces "type 75 x 45" with "describe the room". And `feasibility_report` earns its keep immediately. A 45-degree vertical pattern held to 700 Hz needs

```
25400 / (700 * 45) = 0.81 m
```

of mouth height. If the user was imagining a 400 mm tall horn, the search would have spent hours failing against geometry that cannot exist, and this function says so in milliseconds. The report prints it at the top. The narrow axis always needs the larger mouth, which is why vertical control is the harder half of every horn, and this function makes that concrete rather than a slogan.

---

## Tests, every one with a number written down in advance

Build a helper that constructs synthetic `Response` objects from an analytic directivity function sampled on the contract's probe geometry.

`tests/test_metrics_beamwidth.py`

| # | Case | Expected |
|---|---|---|
| 1 | Cardioid `p = (1+cos t)/2`. `p = 0.5` at `cos t = 0`, so `t = 90`. | **180.0 deg**, to 0.05 |
| 2 | Dipole `p = cos t`. `cos t = 0.5` at `t = 60`. | **120.0 deg**, to 0.05 |
| 3 | Circular piston `2*J1(x)/x` at `ka` of 3, 6, 12, 24. Find the -6 dB argument with `scipy.special.j1` and `brentq`. | matches, to 0.05 deg |
| 4 | Omnidirectional | `(180.0, 0)` |
| 5 | Cardioid on a deliberately coarse 10-degree grid | still 180.0, error under 1.0 deg, proving interpolation runs |
| 6 | A pattern with a sidelobe above -6 dB past a null | `n_crossings > 2`, width from the **outermost** pair |
| 7 | A pattern whose maximum is 2 dB off axis, constructed so the two conventions differ by more than 3 degrees | the **on-axis** reference answer |
| 8 | Angle array with no exact 0 | raises `ValueError` |

`tests/test_metrics_di.py`

| # | Case | Expected |
|---|---|---|
| 9 | Omnidirectional | **0.000 dB**, to 0.01 |
| 10 | Dipole, 512-point balloon | **4.771 dB**, to 0.05 |
| 11 | Cardioid, 512-point balloon | **4.771 dB**, to 0.05 |
| 12 | Cardioid at 128, 512, 1024, 4096 points | error monotonically decreasing, under 0.02 dB at 1024. **Paste the four numbers**; the senior agent may change the contract's 512 based on them. |
| 13 | `target_di_db(75, 45)` | **11.3 dB**, to 0.1 |
| 14 | `target_di_db(360, 180)` | **0.0 dB**, to 0.1 |
| 15 | `di_from_cuts(180, 180)` on an omni pattern | agrees with `di_from_balloon` to 0.3 dB |
| 16 | `di_from_cuts` on a deliberately lobed pattern | **disagrees** with the balloon by more than 1 dB. This test exists to prove the estimate is an estimate. |
| 17 | `di_slope_db_per_decade` on a synthetic DI rising exactly 3 dB per decade | **3.0**, to 1e-9 |

Tests 10 and 11 together are the strongest check in this module. Two completely different patterns both have directivity factor 3, so both must read 4.771 dB. A hemisphere average would give the dipole the right answer and the cardioid the wrong one, which is exactly the bug this pair catches.

`tests/test_metrics_smoothness.py`

| # | Case | Expected |
|---|---|---|
| 18 | Flat in-coverage response | `0.0` |
| 19 | Alternating +1 / -1 dB inside coverage | `1.0`, to 1e-9 |
| 20 | Flat plus one sample at -60 dB inside coverage | still `0.0` (floored out) |
| 21 | Fewer than 5 surviving samples | `nan`, no raise |
| 22 | `coverage_mask(75)` on a 2.5-degree grid | exactly **31** samples, -37.5 to +37.5 |
| 23 | `normalized_db` on an exact zero | `-120.0`, never `-inf` or `nan` |

`tests/test_metrics_impedance.py`

| # | Case | Expected |
|---|---|---|
| 24 | Plane wave, `p = rho*c*u` | exactly `1.0 + 0j` |
| 25 | Volume-velocity path, `Q = u*area` | same answer |

`tests/test_targets.py`

| # | Case | Expected |
|---|---|---|
| 26 | `required_mouth_m(90, 926)` | **0.3048 m** (12 in), to 1 mm. Reproduces the published worked example. |
| 27 | `required_mouth_m(45, 1850)` | **0.3048 m**, to 2 mm. The source's second worked example. |
| 28 | `coverage_from_room` on a symmetric rectangular room | H and V angles positive, under 180, and widening as the room gets wider |
| 29 | `feasibility_report` on 45 deg to 700 Hz | `mouth_v_m` about **0.81 m**, and a note saying so |
| 30 | `Target.from_dict` round-trips every example YAML's target block | no `None` in a required field |

`tests/test_metrics_integration.py`

| # | Case | Expected |
|---|---|---|
| 31 | `fake_response` (cardioid at 12 frequencies) | `bw_h = 180.0` everywhere, `di = 4.771` everywhere, `di_source = 'balloon'`, `n_freqs = 12` |
| 32 | Same with 9 frequencies, simulating a short sweep | 9-length arrays, never reaches for a 12th |
| 33 | `balloon_dirs = None` | `di_source == 'cuts_estimate'`, a `WARNING` logged, and a finite DI |
| 34 | One frequency's pattern all zeros | no `inf`, no `nan` beyond what `n_nan_ripple` accounts for |
| 35 | `scalars` has exactly the documented key set, every time, for every input | set equality, not a subset check |

Test 35 looks pedantic and is not: the report and the dataset both index `scalars` by key, and a missing key breaks both at the worst possible moment, three hours into a run.

---

## Checkpoint CP-4

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_metrics_beamwidth.py tests/test_metrics_di.py tests/test_metrics_smoothness.py tests/test_metrics_impedance.py tests/test_targets.py tests/test_metrics_integration.py -v
```

Paste it in full, plus these three tables.

**Table 1, the analytic comparison:**

| Pattern | Expected BW | Computed BW | Expected DI | Computed DI | Error |
|---|---|---|---|---|---|
| omni | 180.0 | | 0.000 | | |
| dipole | 120.0 | | 4.771 | | |
| cardioid | 180.0 | | 4.771 | | |
| piston ka=6 | brentq | | | | |
| piston ka=12 | brentq | | | | |
| piston ka=24 | brentq | | | | |

**Table 2, the DI quadrature convergence** (128 / 512 / 1024 / 4096 points, cardioid error in dB).

**Table 3, feasibility**, for the baseline target: required mouth width and height to hold 75 x 45 degrees down to 700 Hz, next to the seed design's actual mouth dimensions from `examples/osse_baseline.yaml`.

**CP-4 passes when:** all 35 tests pass and every analytic case is inside its stated tolerance.

### CP-4a: what the senior agent checks

From the pasted tables, not from the code:

1. **Beamwidth is total included angle.** The cardioid reads 180, not 90. If it reads 90, every beamwidth in the project is half what it should be and the search will converge on a horn twice as wide as asked for.
2. **DI is a full-sphere average.** Dipole and cardioid both read 4.771. If only one does, the integration domain is a hemisphere.
3. **Table 3 is sobering or it is wrong.** 45 degrees to 700 Hz needs about 0.81 m of mouth height. If the feasibility report says otherwise, `KEELE_K` or the formula is wrong, and test 26 should have caught it.

---

## Forks

| Fork | Difficulty | Value | Notes |
|---|---|---|---|
| **DI slope as a primary objective term** | **already built** | **high** | It is in `scalars` and in the objective from day one. Reframes the goal from "hit 75 x 45 at every frequency" to "hold a consistent pattern", which is both closer to the real goal and smoother to optimize. |
| -3 dB beamwidth alongside -6 dB | trivial | medium | One argument. Avoids arguments with datasheets that use the other convention. |
| Power response and listening-window averages | low | **high for the hi-fi half** | Spinorama-style: listening window, early reflections, sound power. Cheap from the balloon we already have, and directly relevant to the hi-fi duty in the brief. `hornlab_plots.sphere_power_metrics()` already consumes complex pressure for this. |
| Polar-map metrics on the 2D balloon | medium | **high** | Pattern flatness computed on the full balloon rather than two orthogonal cuts. Catches diagonal-plane misbehavior that H and V cuts miss entirely, which is a real and common failure mode for superellipse mouths. The data is already there. |
| Group delay and phase metrics | low | medium | `hornlab_plots` has `save_group_delay_plot()`. Needs complex pressure; task 02's C2 says whether we have it. |
| Venue map to an energy target, Monge-Ampere style | high | high | The project docs' Method A and the optimal-transport idea. `targets/venue.py` is the stub it would grow from: instead of one coverage angle, a desired energy density over a target surface. |
| Perceptual weighting of the frequency grid | high | unknown | Defensible, hard to validate, easy to fool yourself with. Not before there is measured correlation against something real. |
