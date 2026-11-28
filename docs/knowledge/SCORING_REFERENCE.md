# Scoring reference (objective v1–v11)

Queryable reference for the scalar objective. **Source of truth for versions is
`hornlab_search/objective/versions.py`**, not `AGENTS.md` (its one-line version list predates
v9–v11 and is stale). Lower J is better.

> Every objective claim below cites `hornlab_search/objective/` (or the metric module it calls);
> envelope policy cites `hornlab_search/config.py`. Where a claim could not be verified it is
> marked **unclear**.

## 1. Versions v1 → v11

`SUPPORTED_OBJECTIVE_VERSIONS = (1, 2, 3, 4, 5, 6, 7, 9, 10, 11)` — `objective/versions.py:29`.
There is no supported v8. `versions.py:3-6` requires the scorer dispatch table to match this
tuple exactly; a new version is added here in the same commit as its dispatch branch
(`versions.py:1-6`).

| Ver | Added / change | Term set or defining change | Source |
|---:|---|---|---|
| 1 | Original objective | `cov + rip + di + dislope + flat + load + penalty` (raw terms) | `objective/scalar.py:3-5` |
| 2 | Detrended terms | `rip` about a smooth beam; detrended `flat`; DI target from a separable Gaussian beam | `objective/scalar_v2.py:1-24` |
| 3 | K-law masks / per-plane `f0_v` | `cov` and `dislope` score only `f >= f0`; with `f0_v_hz`, H and V are masked separately | `objective/scalar_v2.py:275-293` |
| 4 | Tolerance normalisation | Every term is `raw / tolerance`; adds `cov_narrow_ratio`, `cov_below_f0`, `distd`, `diag` | `objective/scalar_v4.py:1-31` |
| 5 | MEH system objective | v4 pattern terms on the synthesised response + `lw_resid`, `notch`, `xo_lob`, `headroom` | `objective/scalar_meh.py:1-22` |
| 6 | `loading_smooth` | `load_near`, `z_smooth`, `cov_pat`, `di_rise` (Le Cléac'h / rollback class) | `objective/scalar_v6.py:1-15` |
| 7 | Hardened v4 | v4 + combined loading penalty, constant-velocity `flat_cv`, 8 kHz one-sided floor, signed V coverage | `objective/scalar_v7.py:1-30` |
| 8 | **Not a supported identity** | Proposal only, never registered, no brief uses it | `objective/scalar_v8.py:1-9`; `versions.py:29` |
| 9 | Non-CD profile objective | Frequency-dependent H/V coverage corridor or target, per-frequency envelope ripple, `di_roughness`, optional `hf_floor` and `constancy` | `objective/scalar_v9.py:1-35`, `63-78` |
| 10 | v9 + required ripple region | Requires `objective.ripple_region`; only the `rip` window changes | `objective/scalar_v10.py:1-31`, `159-171` |
| 11 | v10 + required CD matrix | Requires `objective.cd`; adds `cd_lw`, `cd_di_std`, `cd_nacc`, `offaxis_smooth` (+ report-only CD fields) | `objective/scalar_v11.py:1-31`, `53-59` |

History notes that are easy to get wrong:

- v7 was originally written as “5” on the hardened branch and renumbered to 7 on 2026-11-12
  (`versions.py:17-19`). Data from that branch is v7.
- v10 is owner-gated and scored as a new identity; v11 is a new identity and is never ranked
  against v9/v10 (`versions.py:23-28`).

### Identity rules (when two J values may be compared)

- `score_id` hashes `metric_id` + score-code version + objective version + weights + objective
  block + brief hash/name (`objective/replay.py:570-579`). A different objective block, weights,
  target or brief is a different score identity.
- v10 and v11 also expose a named identity (`objective_v10_ripple_region`,
  `objective_v11_cd_matrix`) and a sha256 of the normalised objective block
  (`scalar_v10.py:143-148`; `scalar_v11.py:315-320`). The v11 block includes the whole `cd`
  mapping, so any CD tolerance/weight change is a new identity.
- The envelope policy is also hashed (`config.py:292-303`), and a changed envelope is a changed
  brief.
- Replay status matters: only `exact_complete` rows may rank; `partial_unsupported` scores may be
  shown for diagnosis but never ranked beside complete rows (`replay.py:18-30`, `492-499`).
- **Never rank J across objective versions.** v11's own docstring says it is never ranked against
  v9/v10 (`scalar_v11.py:3-5`).

## 2. Coverage modes

`target.coverage_profile.mode` is `corridor` or `target` (`targets/profile.py:3-6`;
`scalar_v9.py:80-81`). Profile angles are **TOTAL beamwidths**, not half-angles
(`scalar_v10.py:8-14`).

### 2.1 Corridor mode — zero cost inside `[min_deg, max_deg]`

Per frequency, with `bw` the measured beamwidth and `[lo, hi] = [min_deg, max_deg]`:

| Condition | Cost contribution | Source |
|---|---|---|
| `lo <= bw <= hi` | **exactly `0.0`** | `scalar_v9.py:437-443` |
| `bw < lo` (narrow side) | `cov_narrow_ratio * (lo - bw)^2 / 100` | `scalar_v9.py:438-439` |
| `bw > hi` (wide side) | `(bw - hi)^2 / 100` | `scalar_v9.py:440-441` |

**`preferred_deg` is never read by the corridor coverage cost.** The `pref` value is fetched but
only used in the `else` branch, which is target mode (`scalar_v9.py:425`, `444-447`); in corridor
mode the `elif` branch at `437-443` uses only `lo` and `hi`. `preferred_deg` appears in corridor
profiles at all because validation requires `min <= preferred <= max` (`targets/profile.py:81-84`);
it is not a soft target.

Exception — below the plane onset with `cov_below_f0: one_sided`: a wide pattern is physics and
free, while a narrow pattern is still charged against `lo` (corridor) or `pref` (target)
(`scalar_v9.py:418-436`). With the default `mask`, those frequencies are excluded entirely
(`scalar_v9.py:418-421`).

### 2.2 Target mode — distance from `preferred_deg`

With `d = bw - preferred_deg`:

- cost = `cov_narrow_ratio * d^2 / 100` when `d < 0` (narrow side);
- cost = `d^2 / 100` when `d >= 0` (wide side);
- `min_deg` / `max_deg` are absent in a target-mode profile (`targets/profile.py:3-6`,
  `scalar_v9.py:444-447`).

The H-plane cost plus `cov_v_weight * V-plane cost` is the raw `cov_profile` term
(`scalar_v9.py:455-460`), divided by the single `cov_profile` tolerance (`scalar_v9.py:665-669`).

### 2.3 The opt-in `constancy` term — flatness at the chosen angle

Coverage scores each frequency independently: a beamwidth that wobbles inside the corridor costs
nothing at any one frequency. **If “beamwidth flatness at one chosen angle” is the intent, declare
`objective.constancy`.** It is absent by default and must be declared in the brief
(`scalar_v9.py:66`, `108-111`, `116-123`, `675-678`).

| Mode | Behaviour | Source |
|---|---|---|
| `strict` | Fit a constant level (slope 0) to the plane's beamwidth over log10 f | `scalar_v9.py:603-611` |
| `slope` | Fit a line in log10 f; its slope is clipped to ±`slope_max_deg_per_decade` | `scalar_v9.py:604-610` |

Raw cost per plane = `mean((bw - predicted)^2) / 100` (deg²/100) (`scalar_v9.py:583-611`).
The fitted centre is **clamped into the corridor's `[min, max]` at the band's geometric-centre
frequency** in corridor mode; target mode leaves it unclamped (`scalar_v9.py:587-589`,
`597-609`). Consequently, a design outside the corridor pays twice: the coverage term for leaving
the corridor, and constancy for the distance between its fitted level and the clamped in-corridor
line. The H cost plus `cov_v_weight * V cost` is normalised by the constancy tolerance
(`scalar_v9.py:614-620`, `665-669`).

**Tolerance meaning.** Raw units are `mean squared deviation / 100`. With `tolerance: 0.25`,
5° RMS off the flat line equals 1.0 J; with `tolerance: 1.0`, 10° RMS equals 1.0 J
(`scalar_v9.py:583-589`; evidence `docs/evidence/coverage_pull_2026-11-25/replay_constancy.py:7-11`).

`constancy` does **not** pull the design toward `preferred_deg`: it prices wobble at whatever
in-corridor level the design holds. To encode “80 ± 5° H / 50 ± 5° V and flat”, narrow the corridor
to `[75,85]` / `[45,55]` and add constancy; the corridor supplies the angle, constancy supplies
the flatness (`docs/evidence/cd_pm5const_2026-11-25/build_pm5.py:1-9`).

## 3. `hf_floor`, `ripple_region`, tolerances

### 3.1 `hf_floor` (v9/v10/v11, optional)

`objective.hf_floor` is an explicit one-sided HF floor; it joins the weighted set only when
declared (`scalar_v9.py:66`, `116-123`). Keys: `hz`, `h_deg`, `v_deg`, `weight`, `tolerance`
(`scalar_v9.py:245-270`).

- It evaluates the last solved frequency at or below `min(hz, band_hi)` (`scalar_v9.py:563-568`).
- Raw = `(max(0, h_deg - bw_h)^2 + max(0, v_deg - bw_v)^2) / 100` — **narrow-only; a wider
  pattern is not rewarded** (`scalar_v9.py:576-578`).
- Its own `tolerance` divides the raw value; its own `weight` applies (`scalar_v9.py:659-669`).
- Unjudgeable (no solved sample at/below the cap, non-finite widths) → `NAN_TERM_FILL`
  (`scalar_v9.py:556-575`).

v9 **refuses** the older `objective.bw8k_floor`; the profile's `min_deg` is the narrow-side HF
constraint (`scalar_v9.py:20-23`, `89-90`, `132-133`).

### 3.2 `ripple_region` (v10/v11, required)

v10 changes only the `rip` window. There is **no default**: `objective.ripple_region` is required
(`scalar_v10.py:1-31`, `70-74`).

| `ripple_region` | Inspected total angle per plane | Notes |
|---|---|---|
| `preferred_edge` | `preferred_deg` (i.e. ±preferred/2) | Valid in both profile modes |
| `min_edge` | `min_deg` (±min/2) | Corridor only; refused otherwise |
| `max_edge` | `max_deg` (±max/2) | Corridor only |
| `{mode: seat_zone_deg, h_deg, v_deg}` | Explicit total angle per plane | Constant over frequency |

Source: `scalar_v10.py:159-171`, `174-200`; corridor-only refusal at `168-171` and
`config.py:550-557`. The window is `±(total/2)` because the inspected value is a full beamwidth
(`scalar_v10.py:8-14`).

### 3.3 Tolerances and the two coverage knobs

| Key | Default | Rule | Source |
|---|---:|---|---|
| `objective.tolerances` | **none** | Must supply one finite `> 0` entry per v9 weighted key: `cov_profile, rip, flat, load, dislope, di_roughness, flat_cv`; stored terms are `raw / tolerance` | `scalar_v9.py:95-99`, `138-153`, `665-669` |
| `objective.cov_v_weight` | `1.0` | Finite number in `[0, 1]`; multiplies the V-plane cost in both `cov_profile` and `constancy` | `scalar_v9.py:164-167`, `455-460`, `614-620` |
| `objective.cov_narrow_ratio` | `1.0` | Finite number `> 0`; multiplier on the **narrow side only** (beamwidth below the lower bound or preferred); wide side is always 1.0 | `scalar_v9.py:154-157`, `437-447` |

The brief's `weights:` block supplies the base weights; `hf_floor` and `constancy` carry their own
weights (`scalar_v9.py:273-305`). The v11 CD weights/tolerances come only from `objective.cd`,
never from `weights:` (`scalar_v11.py:269-286`).

## 4. The v11 `cd` block

v11 **requires** `objective.cd`; there is no default (`scalar_v11.py:7-8`, `174-191`). The block
is validated key-for-key: `band_hz`, `window_h_deg`, `window_v_deg`, `lw`, `di_std`, `nacc`,
`offaxis`, `report` (`scalar_v11.py:70-78`, `187-210`). All four scored terms are **level / DI /
correlation measures, not beamwidth angles**.

| Term | What it measures | Raw unit | Normalisation |
|---|---|---|---|
| `cd_lw` | M2 listening-window distortion `C_LW`: band-weighted, power-averaged deviation of the listening-window polar response from a frequency-independent shape relative to on-axis (`metrics/cd.py:229-255`) | dB | `cd_lw_db / lw.tolerance_db` (`scalar_v11.py:402`) |
| `cd_di_std` | M4 log-frequency-weighted standard deviation of DI over `cd.band_hz` (`metrics/cd.py:110`, `531-536`) | dB | `cd_di_std_db / di_std.tolerance_db` (`scalar_v11.py:403`) |
| `cd_nacc` | M5 mean normalised aligned cross-correlation `Phi_bar` between H and V cuts over the band (`metrics/cd.py:177-211`, `559-563`) | dimensionless | `(1 - cd_nacc) / nacc.tolerance` (`scalar_v11.py:404`) |
| `offaxis_smooth` | Worst band-mean fixed-angle residual over the declared H and V angles (`metrics/cd.py:594-617`; reference `band_mean` or `trend`) | dB | `offaxis_smooth_db / offaxis.tolerance_db` (`scalar_v11.py:405-406`) |

Report-only fields:

- `cd_omega_2pi` — M3 forward clean-region solid angle `Omega_CD / (2*pi)`; `-1.0` means
  unmeasurable; never weighted (`scalar_v11.py:67-68`, `408-413`).
- `cd_status_code` — `0` balloon, `1` cuts fallback, `2` unmeasurable (`scalar_v11.py:61-66`).

Missing/unmeasurable CD values normalise to `NAN_TERM_FILL`, not to 0.0, so an unmeasured CD
block is not a free pass (`scalar_v11.py:366-381`, `297-312`). `cd_lw` can be measured from the
balloon or, without one, from the H/V cuts with `cd_status_code = 1`; `cd_omega_2pi` is then
unmeasurable (`metrics/cd.py:565-592`).

Term assembly: v10's normalised base terms are kept, then the four CD terms are added at
`scalar_v11.py:384-426`; the failure row still carries every v11 key (`scalar_v11.py:323-337`).

## 5. Envelope / size policy

Resolved by `envelope_policy(brief)` (`config.py:309-322`), validated at `config.py:344-364`.

| Brief `envelope:` | Mode | Candidate limits | Source |
|---|---|---|---|
| omitted | `unspecified` | product limits (`1e9` defaults) | `config.py:311-314` |
| `enforce: true` (default) | `production` | `min(product_limit, sanity_max_mm)`; mesh limits add legacy tolerance `(0.5, 0.5, 15.0)` mm, capped at sanity | `config.py:267-272`, `285-290`, `315-317` |
| `enforce: false` + `max_utilization: U` | `exploration` | `min(product_limit * U, sanity_max_mm)`; requires `enforce: false` and `U >= 1` | `config.py:318-321`, `359-364` |
| `enforce: false`, no `max_utilization` | `discovery` | `(sanity_max_mm, sanity_max_mm, sanity_max_mm)`; default sanity 1200 mm | `config.py:267-269`, `315`, `322` |

`enforce: false` stops the brief's build box from being a search refusal; the absolute
per-dimension sanity ceiling remains (`config.py:267-269`). The policy (limits + mode +
`max_utilization`) is folded into `EnvelopePolicy.policy_id` (`config.py:292-303`).

**There is no soft size term in J.** The objective term sets contain no size, envelope, volume or
footprint key (`objective/terms.py:21-24`; `scalar_v9.py:63-66`; `scalar_v11.py:53-59`). Envelope
violations are pre-mesh `invalid_envelope` refusals, not a graded J term: the refusal is flat
`PENALTY_INVALID` or graded by overshoot depending on `search.infeasible_penalty`
(`search/evaluate.py:1144-1155`; grades defined at `objective/terms.py:104-115`).

`resample_strict` is a **search** policy, not a size term:

- allowed values of `search.infeasible_penalty` are `flat`, `graded`, `resample`,
  `resample_strict`; `resample_strict` requires `search.algorithm: cma` (`config.py:1684-1691`);
- it replaces deterministic refusals drawn from the current CMA distribution (up to
  `RESAMPLE_CAP` per slot) and never reports a refusal penalty (`search/cma.py:65-75`).

So: `enforce` decides whether the build box refuses; `max_utilization` shrinks an open box;
`resample_strict` changes how refusals are handled; none of them adds a soft size cost to J.

## 6. Worked example — the favL 66 × 62 “80 × 50” case

Run: `runs/20261125T204727Z-screen-02b4bf` (favL 2-in compact500, 150 valid designs).
Original brief `examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115.yaml`:
corridor H **60–90**, V **40–60**; `preferred_deg` 80 / 50; `cov_narrow_ratio: 2.0`;
`cov_v_weight: 0.5` (`:27-47`, `:80-96`).

| Re-score | Old best `6552f5c8c536` | Other evidence |
|---|---|---|
| A. Current corridor (60–90 / 40–60) | **J 1.3882**, `cov_profile` **0.0100**, H **66.6 ± 3.2** (63.0–73.8), V **62.4 ± 2.0** (60.5–67.3), 0.9–8 kHz | 150 designs; replay parity max `|dJ|` `4.94e-05` (`replay_constancy_*.json:2-24`) |
| B. Tight corridor 72–88 / 42–58 | J 1.7474, cov **0.3306** | same design (`replay_*.json:69-76`) |
| C. Target mode | not in top 5 | top cluster J **2.80–2.92**, cov **1.31–1.48**; e.g. `888f033b0c32` J 2.7969, cov 1.3430, H 66.7 / V 62.3 (`replay_*.json:96-140`) |
| D. Old corridor + `constancy` strict, tol 0.25 | **rank 14** | new top `fbaf66c863e7` J 1.837, constancy 0.3669, H 65.3 ± 2.4 / V 61.9 ± 1.8 (`replay_constancy_*.json:123-225`) |
| E. ±10 corridor 70–90 / 40–60 + constancy tol 0.25 | J **2.5769**, cov 0.1458, constancy **1.0528**, rank 4 | `replay_constancy_*.json:287-305`, `326` |
| F. ±10 corridor + constancy tol 1.0 | J **1.7873**, cov 0.1458, constancy **0.2632**, rank 2 | top `91736281ba73` J 1.7627 (`replay_constancy_*.json:347-466`) |
| G. Owner ±5 brief (H 75–85, V 45–55) + constancy tol 0.25 | **J_pm5 6.3633** (from 1.3882), cov **0.5907**, constancy **4.3943** | best in that replay file `51b9cd8ae1bc` J_pm5 5.8163 (`replay_favl_pm5.json:1-20`, `97-115`) |

Why corridor produced a false win:

- At 66.6° H the design sits **inside** the 60–90° corridor; at 62.4° V it is only slightly above
  the 60° max, and the frequency-weighted mean of that excess leaves cov at **0.0100** — about
  0.7 % of J 1.3882. The coverage term is effectively silent.
- `preferred_deg` 80 / 50 is never read in corridor mode (`scalar_v9.py:437-447`). Nothing in
  coverage pushes H from 66.6 toward 80 or V from 62.4 toward 50; other terms were free to settle
  at ~66 × 62. That is the false win: a design 13° / 12° from the stated preferred widths scored
  as though it matched them.

How constancy changes it:

- With only the old wide corridor plus constancy at tol 0.25 (D), the term re-ranks the cohort:
  a flatter design (`fbaf66c863e7`, H ±2.4 / V ±1.8) takes first and the old best falls to 14th.
  Constancy prices across-frequency wobble; it does not price distance from 80 / 50 because the
  fitted centre is inside the old corridor (`scalar_v9.py:597-609`).
- Narrowing the corridor to the owner's ±5° window does price the angle. Now the 66.6/62.4 centre
  is clamped to the corridor edge (75 H / 55 V) for the constancy fit, so both terms charge:
  cov 0.5907 **and** constancy 4.3943, J_pm5 6.3633 (G). The old design is no longer a winner.
- The tolerance is the scale knob: 0.25 means 5° RMS = 1.0 J. On the same ±10° corridor, relaxing
  to 1.0 moves `6552f5c8c536` from rank 4 / J 2.5769 (E) to rank 2 / J 1.7873 (F).

## 7. How to re-score offline (no GPU)

Everything below reads stored `response.npz` + `metrics.json`; it never meshes or solves
(`objective/replay.py:1-7`, `968-978`). Only `exact_complete` replay rows may rank
(`replay.py:492-499`).

### Python API

```python
from hornlab_search.objective.replay import load_brief_context, replay_run_dir

brief = load_brief_context("examples/briefs/hf2in_2026-11-20/"
                           "compact500_xo900_80x50_hf2in_v11cd_open115_pm5const_2026-11-25.yaml")
r = replay_run_dir("runs/20261125T204727Z-screen-02b4bf", "6552f5c8c536", brief=brief)
print(r.status, r.j, r.terms.get("cov_profile"), r.terms.get("constancy"),
      r.stored_j, r.parity_delta, r.score_id)
```

- `load_brief_context(path)` resolves a brief through the real `load_brief` loader and validates
  the objective block (`replay.py:219-235`).
- `replay_run_dir(run_dir, design_hash=None, *, brief=..., config_path=...)` tries
  `designs/<hash>/` then `verify/designs/<hash>/`; with one design, `design_hash` may be omitted
  (`replay.py:968-990`).
- `ReplayResult` carries `status`, `reasons`, `j`, `terms`, `stored_j`, `parity_delta`,
  `score_id`, `metric_source` and the three identities (`replay.py:449-489`).

### CLI wrapper (`tools/analysis/rescore_identity.py`)

Exact command, rescoring the favL run under the ±5 constancy brief:

```powershell
.venv\Scripts\python.exe tools/analysis/rescore_identity.py rescore --brief examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115_pm5const_2026-11-25.yaml --out runs/rescore_favl_pm5 runs/20261125T204727Z-screen-02b4bf
```

- `rescore` writes `rescore.jsonl` (one row per design: stored J, replayed J, parity delta,
  status, reasons) and `rescore_summary.json` (per-lane bests, score identities, status counts)
  (`tools/analysis/rescore_identity.py:93-139`).
- Add `--runs-root <dir>` to sweep run dirs up to depth 3 instead of listing them
  (`rescore_identity.py:249-270`, `293-296`).
- `--run-brief <stem>` keeps only runs whose own `config.yaml` names that brief stem
  (`rescore_identity.py:82-90`, `101-103`).
- `compare` puts one column per score identity side by side and **never compares J across
  columns** (`rescore_identity.py:204-246`, `14-18`).
- `floor --brief ... --out ...` computes the frequency part of the noise floor from screen/verify
  pairs (`rescore_identity.py:157-201`).

## 8. Quick lookup

| Question | Answer |
|---|---|
| Does an in-corridor width cost anything? | No: exactly 0.0 at/above onset (`scalar_v9.py:437-443`). |
| Is `preferred_deg` a soft target in corridor mode? | No: corridor coverage never reads it (`scalar_v9.py:437-447`). |
| How do I score flatness at one angle? | Declare `objective.constancy` (`scalar_v9.py:583-620`). |
| What does `constancy.tolerance: 0.25` mean? | 5° RMS off the flat line = 1.0 J (`scalar_v9.py:583-589`). |
| Does v10/v11 need a ripple region? | Yes, required, no default (`scalar_v10.py:70-74`). |
| Does v11 need a CD block? | Yes, required, no default (`scalar_v11.py:174-191`). |
| Is `cd_lw` a beamwidth? | No: a listening-window level/distortion term in dB (`metrics/cd.py:229-255`). |
| Is there a size term in J? | No (`objective/terms.py:21-24`; `scalar_v11.py:53-59`). |
| How do I re-score without a GPU? | `replay_run_dir` / `rescore_identity.py rescore` (§7). |
