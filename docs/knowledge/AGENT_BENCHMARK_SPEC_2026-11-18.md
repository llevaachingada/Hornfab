# Agent science benchmark: specification (WP-K1, draft 2026-11-18)

Status: **spec only**. No harness code, no model calls, no GPU. Source: integrated handoff
2026-11-17 v2, sections 4 and 10.5. `tools/agent/ping_agents.py` proves that skills load; this
benchmark tests whether the answers are correct.

## Design

- **Arms:** baseline (the current agent and skills) versus treatment (the same agent plus the
  `docs/knowledge/contracts/` files). Same model, same permissions, same repo SHA, same task text.
- **Per case, record:** the verdict (pass/fail against the key below), the files cited, the number
  of tool/browse calls, tokens, wall time, and any skill that activated when it should not have.
- **Scoring:** a case passes only if the decision is correct **and** the claim is grounded in the
  cited code, config or source. Fluency does not count. A correct refusal or deferral counts as a
  pass when the key says to defer.
- **Adoption gate:** the treatment beats the baseline on correctness, without a regression on
  cases 15 and 16 (cost and over-activation). If it does not win, shrink the contracts rather than
  add more agents.
- **Fixtures:** each case gets a frozen prompt, plus the repo path(s) it may read, plus an answer
  key. Keep fixtures under `tests/agent_bench/` (to be created by the implementer; not in this
  patch).

## Cases (answer key in brief)

| # | Probe | Correct behavior |
|---|---|---|
| 1 | CROWE endpoint timing defect | Identifies the corrected warped-quintic endpoint; does not reintroduce the old timing |
| 2 | CROWE DOF count | Four continuous DOFs; `p_mouth` and the throat are held fixed |
| 3 | Le Cléac'h H/V march | Shared wavefront station, not independent H and V marches |
| 4 | Keele on JMLC/OSSE | Refuses to apply it as a hard gate; cites KH-001 |
| 5 | v9-named YAML pointing at a v7 brief | Reports the effective scorer from the resolved brief, not from the filename |
| 6 | Base v7 vs smooth v7 | Refuses a raw-J comparison across objectives |
| 7 | v9 `distd`/`diag` | Separates diagnostics from weighted terms; checks the dense-grid identity |
| 8 | Sloping DI target | Does not read it as an H/V beamwidth corridor |
| 9 | `mesh.msh` vs generator points | The mesh is the solver truth; reports the fit residual |
| 10 | 2-degree driver exit tangent | Flags it as an assumption, not a manufacturer measurement |
| 11 | `sigma0` on a wide 12-D box with high refusals | Reasons jointly about bounds, step size and seed |
| 12 | `no_headroom` on a converged incumbent | Expected outcome; not a bug |
| 13 | Geometry vs envelope vs DOF refusal | Classifies the three separately |
| 14 | Missing record route or digest | Reports "incomplete"; does not fabricate a comparison |
| 15 | Wrong `brief_file` path | Checks the current file state; does not re-report the fixed `84339a72` bug |
| 16 | Routine GUI copy change | Loads no acoustic library and launches no review |
| 17 | blend vs splice OSSE/tractrix | Convex meridian blend vs Hermite station joint: different math |
| 18 | OSSE-H + tractrix-V | Both parent laws are present; neither governs the 3-D junction |
| 19 | Crowe-X/OSSE CD | Original hypothesis; not historical Crowe geometry |
| 20 | Rolled axial vs radial pucker | Different deformation directions; separate categorical lanes |
| 21 | ATH radial morph vs generic axial perturbation | Checks zero-amplitude identity and mouth target |
| 22 | Klangfilm curved-cap vs Le Cléac'h planar Lamé | Different area quantities |
| 23 | Weak geometric knob in `space_card` | Not proof of acoustic insensitivity; checks run evidence |
| 24 | Cross-family matched-seed comparison | Checks residual size, source, objective identity and solver surface before claiming "same size" |

## Negative controls to embed (handoff section 9.2)

Large-geometry/weak-acoustic knob; small-geometry/strong-acoustic knob; parallel geometric
derivatives that run data disagrees with; an inactive conditional knob; the parent with every
novelty knob off; best under v7 but not under a matched v9 rescore; a mesh/grid-fidelity score
shift larger than the claimed gain.
