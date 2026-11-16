# Home optimizer comparison and switching review

## What existing results establish

The old portrait-home 80x60 three-seed experiment gave best verified J values
3.106706 / 3.251363 / 3.189148 for BO (median 3.18915), versus
3.82739 / 3.82739 / 3.39189 for CMA (median 3.82739). BO trained on 185 historical
observations; CMA started from the best historical design. Geometry refusals and
finalist/audit selection also differed. This supports those workflows on that task,
not a universal equal-information optimizer advantage. Source: the original
`runs/nights/bo_vs_cma_2026-11-15/` summary and verification logs.

One landscape scalar/TuRBO experiment used identical frozen config/brief/catalog/score
hashes and 136 records. Best screen/verify J: scalar 2.948642 / 3.149322;
TuRBO 2.497639 / 2.766178. One seed per policy, and TuRBO followed an interrupted run.
Promising preliminary evidence, not replicated proof. Sources:
`runs/study-9d248c75218573cd` and `runs/study-4e1a6a9cd4bb5201`.

## Controlled home protocol

Use separate task cohorts for warm OSSE and Tritonia v9 on the home 80x50 brief.
Freeze a common baseline once per task after its data-building jobs. Each task gets
two seeds and three methods: CMA, scalar BO (qLogNEI policy), and TuRBO. Rotate method
order. Each method has access to the same strictly selected observations and incumbent;
CMA consumes these as its best mean and measured top-ten spread, not a Gaussian process.
Historical rows excluded by BO must not leak into CMA's warm start.

Freeze resolved score, physical bounds, mesh/frequency/backend settings, dependency pins,
source hashes, baseline cohort and selected observation IDs. Later arms must not train on
earlier arms' new results. Cache use and all failures are recorded. Each arm selects up to
two finalists by screen J for verification. Missing/failed verification is a missing result,
not a passing score. Compare verified gains from each task's own baseline, time-to-target,
incumbent curves, refusals, cache hits, and actual wall overhead. Report seed variation.
Two seeds per task supports an initial comparison; uncertainty is substantial.

The current APIs have different budget semantics: BO caps new physical screen calls at80;
CMA caps candidate evaluations at80, including refusals/cache outcomes. These are not
automatically equal GPU work. Report actual observed/inferred cost separately using the
existing cost ledger; do not label candidate counts as guaranteed BEM calls. A headline
comparison requires compatible achieved budgets or an explicitly censored common-cost
analysis. Include cohort/model/setup overhead and state what cannot be measured.

The sequential adaptive cycle remains a separate experiment: local CMA from measured
BO/CMA best, fresh-cohort BO, reassess. It must not be mixed into the frozen comparison.
Different horn tasks and different briefs are separate strata, never one absolute-J ranking.

## Switching workflow

| Evidence | Next action |
|---|---|
| Refusals or solver failures dominate | Diagnose geometry, envelope, resources or solver; another optimizer does not repair these. |
| Too few strictly eligible acoustic rows | Bounded CMA data-building; raw valid rows alone do not establish BO readiness. |
| Good known basin and enough matched data | TuRBO local refinement is a candidate; compare against scalar and CMA controls. |
| No useful progress, no physical-wall explanation | Check sampling scale/headroom, then another seed or global scalar exploration. |
| Top designs cluster at a bound | Review whether it is an artificial box, source constraint, coupling or safety limit; only validated config clones may widen it. |
| TuRBO trust region collapses | End/report that arm; a new controlled seed or global exploration is a separate decision. |
| Wrong brief/score identity or incomplete metrics | Refuse comparison; repair/replay the score contract before spending more work. |

`tools/analysis/optimizer_switch.py` generates advisory JSON/Markdown from recorded runs,
reusing wall analysis and cost accounting. It never changes bounds or launches work.
Example evidence: `scratch/optimizer_review_2026-11-16/` covers two Tritonia v8 runs and
the warm OSSE day run. The watchdog currently stops ordinary searches and advances the
predeclared queue; BO studies are excluded. Controlled benchmark arms keep their fixed
budgets so an adaptive stop policy cannot quietly bias the comparison.

TuRBO adjusts a normalized trust region within the immutable physical parameter box.
This implementation expands after three improvements, contracts after its failure count,
clips to [0,1], and stops on collapse. It does not widen physical bounds or automatically
restart. See `hornlab_search/bo/turbo.py` and the
[BoTorch tutorial](https://botorch.org/docs/v0.17.2/tutorials/turbo_1).

## Scoring and DSP

See [the resolved queue score audit](HOME_SCORE_AUDIT_2026-11-16.md). Source intent and
configuration compatibility do not prove every searched geometry has constant directivity.
The DSP rescore replaces the original on-axis flatness terms with listening-window,
seat consistency, crossover consistency and estimated in-room response terms; it retains
coverage/loading/directivity penalties. It is an offline analysis, not the live objective,
driver EQ simulation, listening test, or a fix for the wrong directivity brief. Freeze
calibration tolerances across methods before comparing DSP numbers. Independently
calibrated reports are not a common numeric scale.

Primary benchmark guidance: [COCO](https://coco-platform.org/getting-started/index.html)
uses progress/target and evaluation-budget evidence; optimizer decisions must include
termination and incomplete-run effects rather than final best score alone.
