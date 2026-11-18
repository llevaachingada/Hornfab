# Scientific construction contracts (WP-K0 drafts, 2026-11-18)

Status: **DRAFT for senior review.** These are read-only extraction drafts. Each claim is labeled
[published] / [derived] / [reconstruction] / [original-hypothesis] / [code-verified] /
[unverified]. No tests were run while drafting (scipy and hornlab_mesher were absent from the
drafting environment), so test claims mean "a test exists", not "the test passes".

A contract explains **why a construction law is valid and how to judge it**. The Fable canonical
record describes what a generator produced. The meshed wall is what the solver used. None of the
three replaces the others. Contracts do not authorize code, bound, brief or queue changes.

| Contract | Construction | Headline finding for review |
|---|---|---|
| [klangfilm_lame_hv.md](klangfilm_lame_hv.md) | Klangfilm–Lamé H/V and H/V core | `cd_core_blend` acts as a switch, so the core never reduces to the parent. The Phase A residual hides the lost curved-cap lock. Kernel SHA docstrings are stale. |
| [crowe_v2a_and_crowe_x_osse.md](crowe_v2a_and_crowe_x_osse.md) | CROWE V2A (4-DOF) and Crowe-X on OS-SE CD (original hybrid) | Crowe-X `g_L_mm`: the header says it was widened to 320, but the bounds still say 285. OS-SE attribution is mixed. |
| [rolled_section_pucker.md](rolled_section_pucker.md) | Rolled rect, section pucker, radial relief | The station definition is ambiguous (phi=pi/4 arc vs the meridian arc). Legacy pucker configs are CLI-only. |
| [lecleach_iwata_hv.md](lecleach_iwata_hv.md) | Le Cléac'h/Iwata AR and the H/V ellipse extension | The H/V plane meridians lose their own axial coordinate. Stations are arc-fraction, not wavefront. `πab` is report-only. H=V reduces exactly to the parent. |
| [throat_hv_block.md](throat_hv_block.md) | Shared near-throat H/V block (OSSE, osse_rollback, Le Cléac'h pair, iwata_ar, rolled; R-OSSE excluded) | REVIEWED. rho is within OS-SE but a labeled hybrid elsewhere. R-OSSE rev7 is axisymmetric only. |

Agent evaluation of these contracts: [AGENT_BENCHMARK_SPEC_2026-11-18.md](../AGENT_BENCHMARK_SPEC_2026-11-18.md).
