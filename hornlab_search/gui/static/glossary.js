// glossary.js — plain-language meaning of every number the GUI shows, for a speaker designer.
// Single source for labels, units and tooltips. Definitions follow hornlab_search/objective/scalar.py,
// metrics/ and docs/BETA_SESSION_PLAN.md; keep them in sync if those change.

export const TERMS = {
  // ---- the score
  J:        { label: "Score", unit: "", short: "Lower is better",
              long: "One number that summarises how far a horn is from the brief's target: a weighted sum of the six error terms below, averaged over the scored band. 0 would be a perfect match. A failed design (does not mesh, too big, solver failure) scores 1000. Scores are only comparable between runs scored with the same brief." },
  cov:      { label: "Coverage error", unit: "", short: "Beamwidth vs target angle",
              long: "How far the −6 dB beamwidth misses the target coverage, horizontal and vertical: (1/100) × mean over frequency of (error in degrees)². 10° off everywhere in one plane ≈ 1.0." },
  rip:      { label: "Polar ripple", unit: "dB", short: "Lumpiness inside the coverage",
              long: "Standard deviation (dB) of the level across angles inside the target coverage, normalised to on-axis, H plus V, averaged over frequency. Low = smooth, even polar response." },
  di:       { label: "DI error", unit: "", short: "Directivity vs target DI",
              long: "(1/10) × mean of (DI − target DI)², DI from the full-sphere balloon. The target DI follows from the target coverage angles unless the brief sets it." },
  dislope:  { label: "DI slope error", unit: "", short: "Constant directivity?",
              long: "(slope − target slope)², slope of DI against log frequency in dB/decade. Target 0 = constant directivity across the band." },
  flat:     { label: "On-axis flatness", unit: "dB", short: "On-axis response spread",
              long: "Standard deviation (dB) of the on-axis level across the scored band. It says nothing about EQ-ability; a smooth tilt counts against it." },
  load:     { label: "Throat loading", unit: "", short: "Re Z below z_min",
              long: "Mean shortfall of the real part of the normalised throat impedance below 0.7 (an arbitrary threshold). Penalises poor acoustic loading at the low end. Off (weight 0) unless the brief turns it on." },
  penalty:  { label: "Failure penalty", unit: "", short: "1000 if the design failed", long: "Added when the design could not be meshed or solved." },

  // ---- per-frequency results
  bw:       { label: "Beamwidth (−6 dB)", unit: "°", short: "Total included angle where the level is 6 dB down",
              long: "Total angle between the two −6.02 dB points of the polar cut. It can jump where a side lobe crosses −6 dB." },
  di_db:    { label: "Directivity index", unit: "dB", short: "On-axis vs average over the sphere",
              long: "10·log10(on-axis power / mean power over a 512-point sphere). Higher = more directional." },
  on_axis:  { label: "On-axis response", unit: "dB", short: "Relative level at 2 m, mean removed",
              long: "Pressure on axis at 2 m for constant diaphragm acceleration, shown relative to its own mean. Not a calibrated SPL." },
  z_re:     { label: "Throat resistance", unit: "×ρc", short: "Re Z at the throat, normalised",
              long: "Real part of the specific acoustic impedance at the throat over ρc. Near 1 = the horn loads the driver like an infinite tube; it falls toward 0 below the horn's cut-off." },
  polar:    { label: "Directivity isobars", unit: "dB", short: "Level vs frequency and angle",
              long: "Level relative to on-axis at 2 m: frequency across (log), angle up (+90° to −90°). Colours are 3 dB bands from −30 dB (navy) to 0 dB (dark red), and white lines mark every 3 dB; the heavier white line is −6 dB, the beamwidth edge. Hover for frequency / angle / level. Values between the solved frequencies are interpolated, so narrow features between them are not shown. Same style as Boundary Lab's isobar plots." },

  // ---- search vocabulary
  knob:     { label: "Shape parameter", unit: "", short: "A number the search varies",
              long: "Each horn family is described by a few numbers (length, mouth size, flare rate, …). The search varies only these, within limits set in the config." },
  pinned:   { label: "At search limit", unit: "", short: "Best designs sit at a parameter limit",
              long: "Most of the 6 best designs are within 2 % of a parameter's lower or upper limit: the limit, not acoustics, stopped the search. Widening a limit is a deliberate decision (it changes the comparison) and needs the owner's OK." },
  rho:      { label: "Influence", unit: "", short: "Rank correlation with the score",
              long: "Spearman rank correlation between a parameter and the score across all solved designs: +1 = larger value, worse score; −1 = larger value, better score; near 0 = little effect (or a non-monotonic one)." },
  seed:     { label: "Starting design", unit: "", short: "Where the search began",
              long: "The hand-set design in the config. The search reports how much it improved on it." },
  cma_seed: { label: "Random seed", unit: "", short: "Repeat number of the search",
              long: "CMA-ES is a randomised search. Two runs with different random seeds show how repeatable a result is." },
  median:   { label: "Median score", unit: "", short: "Middle score over repeats", long: "Median of each repeat's best score." },
  spread:   { label: "Spread", unit: "", short: "Best minus worst repeat",
              long: "Max − min of the repeats' best scores. Family A beats family B only where the medians differ by more than both spreads; two repeats is a small sample." },
  tier:     { label: "Campaign tier", unit: "", short: "How much search per family",
              long: "dry-run: meshes each starting design, no solving (seconds). screen: one search per family, budget max(40, 10 × parameters) — a coarse first ranking (minutes per family). compare: two repeats, budget max(150, 25 × parameters) — needed to claim one family beats another (hours; never run it live)." },
  budget:   { label: "Budget", unit: "evaluations", short: "Designs the search may try",
              long: "Cached designs count toward a campaign's budget so families get equal search. Launch suggests max(150, 100·N) from Hansen's ~100·N hard-problem floor (c-cmaes), floored by this repo's compare tier; IPOP/BIPOP inflate by (1+max)×screen so leftover evals can fund restarts. GUI allow-list caps at 5000." },
  cma_cov:  { label: "CMA covariance", unit: "", short: "Learned search ellipsoid at the end of the run",
              long: "Snapshot of pycma's C (and σ) when the ES stopped. Describes the local shape of the objective landscape in the unit-box search coordinates — which knobs CMA still explores and which directions are coupled — not a physical variance decomposition of the acoustics." },
  cma_Cii:  { label: "Cᵢᵢ", unit: "", short: "Diagonal of the CMA covariance",
              long: "Variance CMA assigns to that knob's unit-box axis. Larger ⇒ the search distribution is still broad on that coordinate." },
  cma_std:  { label: "σ√Cᵢᵢ", unit: "unit box", short: "Sampling scale along one knob",
              long: "Effective standard deviation of new samples along that axis (step-size σ times √Cᵢᵢ). Compare across knobs: large means still exploring; small means locally collapsed — a candidate to pin in a later stage." },
  pin_plan: { label: "Pin plan", unit: "", short: "Which knobs to freeze from CMA + Spearman",
              long: "Recommendation only: pin when σ√Cᵢᵢ share and std are both small, unless |Spearman ρ| is high (still drives J). Values come from best.json. Write artifacts with hornlab-search pin-plan --run <id>; optional --write-config emits a patched YAML." },
  restarts: { label: "CMA restarts", unit: "", short: "IPOP / BIPOP after a natural stop",
              long: "When CMA-ES stops early (flat fitness / tolfun) before the budget is spent, restarts start a fresh ES on leftover evals. Off = single CMA (config default for most YAMLs). IPOP doubles population each restart. BIPOP mixes small-σ local restarts with large-pop ones. Prefer on longer budgets (compare / 150+); short screens often burn the rest in one restart." },
  restarts_max: { label: "Max restarts", unit: "", short: "How many fresh ES instances after the first",
              long: "Number of restarts after the initial CMA run (0–64). Total ES instances ≤ 1 + max. Shared across the whole budget — not per stage." },
  failures: { label: "Failures", unit: "", short: "Designs that could not be scored",
              long: "invalid_geometry: the shape is impossible or outside the brief's size envelope (costs mesh time only). mesh_too_large: too many elements for the 8 GB GPU. solve_failed: the solver crashed (rare; not the design's fault)." },
  epw:      { label: "Mesh density", unit: "elements per wavelength", short: "Mesh resolution",
              long: "Elements per wavelength at the top scored frequency. Axisymmetric typologies use 8 (checked against 6: within 0.12 dB DI), H/V horns use 6 (within 0.05 dB)." },
  dims:     { label: "Horn size", unit: "mm", short: "Outer mouth width × height × depth",
              long: "From the solved mesh, outer surface including the 3–6 mm shell. Depth runs from the throat to the mouth plane." },
  lock:     { label: "GPU lock", unit: "", short: "Who is using the GPU",
              long: "Only one GPU job runs at a time. Any other GPU command is refused with 'GPU busy' until the holder finishes." },
  julia:    { label: "Solver hosts", unit: "", short: "Background solver processes",
              long: "The GPU solver runs in Julia worker processes. 1–2 while a job runs is normal; any left after all jobs end hold GPU memory: use gpu-clean." },
  audit_tier: { label: "Audit tier", unit: "", short: "Fidelity the audit used",
              long: "The fidelity of the solve the gate audit scored this row from: 'screen' is the fast, coarse search solve; 'verify' is the slower, finer re-solve of a shortlist. Verify is the one to trust before printing." },
  band:     { label: "Scored band", unit: "Hz", short: "Frequencies that count",
              long: "Only frequencies inside the band enter the score. On an 8 GB GPU nothing above 5.5 kHz is solved." },

  // ---- Horn + woofer system (P1, docs/research/system_woofer_2026-11-18/)
  // Every `long` below is taken from the handoff/evidence docs named in its comment; none adds a
  // new acoustic claim. The GUI labels are shortened plain-English forms of the same text.

  // GUI_COMPLETION_HANDOFF §2/§5, SENIOR_REVIEW_HANDOFF §2, GUI_SYSTEM_PLAN §1 (declared labels).
  hw_fidelity: { label: "Fidelity label", unit: "", short: "What the numbers are allowed to claim",
              long: "One of SCREEN_MAGNITUDE, SCREEN_COMPLEX_APPROX, INSTALLED_EXTERIOR_BEM, COUPLED_VENTED_FEM_BEM_LEM or MEASURED_VALIDATED. Declared per case in readiness.yaml: the run files carry no label and the result reader refuses to guess one, so an undeclared case shows UNDECLARED." },
  // SCREENING_EVIDENCE §1 and §5 ("display only, no winner"; "good match" is a relative-shape label).
  hw_screen: { label: "Screen", unit: "", short: "Fast CPU shortlist, not a result",
              long: "A fast CPU estimate over many box and driver candidates that produces a shortlist. It never names a single winner and is not a validated ranking. 'Good match' in a screen means the explicitly defined relative-shape label, not a validated crossover." },
  // SCREENING_EVIDENCE §2 (E_shape definition, band, weights, 9 dB^2 threshold).
  e_shape:  { label: "Shape match error", unit: "dB²", short: "Horn vs piston pattern difference",
              long: "E_shape(f_x, plane) = Σ_f w_f [Σ_dir w_dir (L_h,rel − L_w,rel)² / Σ_dir w_dir] / Σ_f w_f: the mean of squared dB differences between the stored horn's relative pattern and an ideal rigid circular piston's, over the listening window, summed over the candidate overlap band. H and V are evaluated separately; the provisional good-match label is 9 dB² (3 dB RMS). It says nothing about absolute level, phase or delay." },
  // SCREENING_EVIDENCE §11 (the pre-check mirrors BL's generator validator), readiness.yaml R2.
  panel_fit: { label: "Panel fit", unit: "", short: "Do the driver and port fit on the front?",
              long: "A pre-check that mirrors Boundary Lab's own generator validator: the driver circle, the port opening and their centres must fit the front panel with the required separation. A refusal means no legal placement exists on that panel. Boundary Lab's own validate remains the authority." },
  // system/boundarylab/clearance.py docstring, readiness.yaml R16, SENIOR_REVIEW_HANDOFF §2.
  clearance: { label: "Horn ↔ box clearance", unit: "mm", short: "Proven gap between horn and box",
              long: "Recorded verdict for a two-body assembly. PASS when the bounding boxes are at least 1 mm apart (a proven lower bound on the true gap); BODY_CLEARANCE_VIOLATION when a horn vertex is closer than 1 mm (a proven violation); BODY_CLEARANCE_UNPROVEN when neither proof holds. A failed clearance fails the stage, so the case is not solved." },
  // SCREENING_EVIDENCE §4 (the spec's own F3 ≤ 55 Hz gate), PILOT_EVIDENCE §3 (F3 ≤ 55 Hz per row).
  f3:       { label: "F3", unit: "Hz", short: "Box's −3 dB low-frequency point",
              long: "The −3 dB point of the box's low-frequency model, compared against the spec's own F3 target (for example F3 ≤ 55 Hz). It comes from the lumped bassbox model, not from a Boundary Lab solve." },
  // GUI_SYSTEM_PLAN §1 ("Box tuning (Fb) is drawn as a marker inside that band"), readiness.yaml R3.
  fb_tuning: { label: "Box tuning", unit: "Hz", short: "Ported box tuning frequency",
              long: "The tuning frequency of the vented box in the lumped model. All recorded solve grids start at 200 Hz, so the tuning cannot be seen in the solved data; the plan draws Fb as a marker inside the hatched 'not solved' band." },
  // SCREENING_EVIDENCE §5 (worst peak port velocity ÷ the 17 m/s convention; headroom warning only).
  port_velocity: { label: "Port velocity", unit: "× limit", short: "Worst peak port velocity ÷ 17 m/s",
              long: "Worst peak port velocity at the driver's AES voltage ceiling divided by the 17 m/s port convention (PORT_AIR_MPS_MAX). Values above 1 are a headroom warning, not a construction rejection; the geometric port-fit rule is the buildability gate. The lumped model does not predict port turbulence." },
  // SCREENING_EVIDENCE §5 and bass_reference.py (20·log10(Xmax ÷ peak excursion)), readiness.yaml R8.
  excursion_margin: { label: "Excursion margin", unit: "dB", short: "Headroom to the Xmax gate",
              long: "20·log10(Xmax ÷ the peak cone excursion at 40 Hz) from the lumped model: positive is headroom, negative means the cone would pass Xmax at the driver's AES voltage ceiling. It is not yet a joint constraint in the DSP validator (R8)." },
  // SCREENING_EVIDENCE §2 (band = the stored samples inside f_x·2^±1/3; fewer than 3 is a refusal).
  xo_band:  { label: "XO band", unit: "Hz", short: "Overlap band a crossover could use",
              long: "For each candidate crossover frequency f_x, the stored frequency samples inside [f_x·2^(−1/3), f_x·2^(+1/3)] — a one-third-octave half-width. The band is candidate-specific, not a universal 700–1300 Hz window, and a band with fewer than 3 stored frequencies is refused, not interpolated." },
  // SENIOR_REVIEW_HANDOFF §5 R1, handoff §1 (woofer Pa per 2.83 V, horn Pa per 1 m/s).
  per_input_ref: { label: "Per-input reference", unit: "", short: "What each channel's Pa is normalised to",
              long: "Every channel is normalised to its own input: the woofer basis is Pa per 2.83 V and the horn basis Pa per 1 m/s. Because the references differ, the two channels are never summed and no calibrated system level is claimed until a channel-calibration policy exists (risk R1, owner decision 3)." },
  // SENIOR_REVIEW_HANDOFF §4 (ideal normal-velocity source, not a compression driver), readiness.yaml.
  ideal_horn_source: { label: "Ideal horn source", unit: "", short: "Throat driven at 1 m/s, not a driver",
              long: "The horn throat is driven as an ideal normal-velocity source at 1 m/s. There is no compression-driver model, so the horn curve is a pressure basis per metre per second, not an absolute SPL for a real driver." },
  // SENIOR_REVIEW_HANDOFF §3–§4 (motor A/B differs 120–144 % per 2.83 V), readiness.yaml cases.
  demo_motor: { label: "Motor", unit: "", short: "Demo or real Thiele/Small set",
              long: "Which motor the solve used. 'demo' is Boundary Lab's provider-default motor, not a real driver's Thiele/Small parameters; 'real' means a declared driver's T/S values were mapped in. Declared per case in readiness.yaml, never inferred. The recorded motor A/B differs 120–144 % in pressure per 2.83 V, so this label qualifies every level." },
  // SENIOR_REVIEW_HANDOFF §4–§5 R2 (provider-default cone/surround/cap), readiness.yaml cases.
  demo_shape: { label: "Transducer shape", unit: "", short: "Demo cone/surround/cap or real geometry",
              long: "Which radiating geometry the solve used. 'demo' is Boundary Lab's provider-default cone, surround and dust-cap shape; the real driver's shape is not modelled. Every BL-buildable box today is demo-shape conditional. Declared per case in readiness.yaml, never inferred." },
  // GUI_SYSTEM_PLAN §1 and readiness.yaml R3 ("no data is not zero"; band, Fb marker).
  lf_not_solved: { label: "LF not solved", unit: "", short: "Nothing below the lowest solved frequency",
              long: "All recorded grids start at 200 Hz, so nothing below that is solved and the box tuning cannot be seen in the data. Frequency plots show a hatched 'not solved' band rather than a line at zero: no data is not zero." },
  // SENIOR_REVIEW_HANDOFF §5 R6.
  convergence: { label: "Convergence", unit: "", short: "One mesh only; refinement not checked",
              long: "Each case was solved on a single mesh, with no refinement delta or frequency-densification control, so how much the answer moves with a finer mesh is unknown." },
  // GUI_COMPLETION_HANDOFF §5.7 (stage + validate as CPU jobs), readiness.yaml R16.
  stage_validate: { label: "Stage + validate", unit: "", short: "Build the Boundary Lab project and check it",
              long: "Staging builds the Boundary Lab project from the box parameters, the horn mesh and the offset; validate runs Boundary Lab's own check on it. A case that fails clearance or the panel-fit rule never reaches a solve. Both are CPU jobs of seconds to minutes." },
  // GUI_COMPLETION_HANDOFF §2 and §5.7 (CPU, about 2.5 min for 25 freqs; needs approval).
  bl_solve: { label: "BL solve", unit: "", short: "The full simulation, needs approval",
              long: "The full Boundary Lab solve: CPU, about 2.5 minutes for 25 frequencies on this machine. It requires an authorization record and stays disabled until owner decision 6 is answered. A solve is a simulation, never a measurement." },
  // SENIOR_REVIEW_HANDOFF §7 and R14, readiness.yaml decision 6.
  authorization: { label: "Authorization record", unit: "", short: "Who, why and scope for a solve",
              long: "The record written before a Boundary Lab solve: who asked, why, and the scope. Today authorized_by is a free string checked only for being non-empty; the shape of the record is owner decision 6." },
  // SENIOR_REVIEW_HANDOFF §5 R1, readiness.yaml decision 3.
  calibration_policy: { label: "Calibration policy", unit: "", short: "How unlike references would be joined",
              long: "The standing rule for comparing the woofer's Pa per 2.83 V with the horn's Pa per 1 m/s. Until it exists, the channels are never summed and no system curve is shown (risk R1, owner decision 3)." },
};

/** HTML for a label with a hover/focus tooltip, e.g. tip("cov"). */
export function tip(key, labelOverride) {
  const t = TERMS[key];
  if (!t) return labelOverride ?? key;
  const label = labelOverride ?? t.label;
  const title = `${t.label}${t.unit ? " [" + t.unit + "]" : ""}: ${t.long}`.replace(/"/g, "&quot;");
  return `<span class="term" tabindex="0" title="${title}">${label}</span>`;
}

/** Order and labels of the objective terms, for tables and bar charts. */
export const TERM_ORDER = ["cov", "rip", "di", "dislope", "flat", "load"];
