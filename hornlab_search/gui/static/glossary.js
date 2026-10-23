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
  polar:    { label: "Polar map", unit: "dB", short: "Level vs angle and frequency",
              long: "Level relative to on-axis, −90° to +90°, one row per solved frequency; clipped at −40 dB. The −6 dB edge is the beamwidth." },

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
  budget:   { label: "Budget", unit: "evaluations", short: "Designs the search may try", long: "Cached designs count toward a campaign's budget so families get equal search." },
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
  band:     { label: "Scored band", unit: "Hz", short: "Frequencies that count",
              long: "Only frequencies inside the band enter the score. On an 8 GB GPU nothing above 5.5 kHz is solved." },
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
