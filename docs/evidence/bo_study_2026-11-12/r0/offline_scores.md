# Offline re-scoring pilot (R0 / M0)

- generated: `2026-11-13T04:06:32Z`
- brief: `C:\Users\hunte\Hrns\hornlab-search\examples\briefs\campaign_2026-10-26_v4\native_ath_core_2in_v4.yaml` (native_ath_core_2in_v4)
- **status: ok**
- dataset: `C:\Users\hunte\Hrns\hornlab-search\dataset`

## Counts

| metric | value |
|---|---:|
| rows_seen | 30002 |
| rows_ok | 25231 |
| rows_failed | 4771 |
| rows_with_npz | 25231 |
| rows_with_traces | 1266 |
| ath_core | 3822 |
| ath_full | 3822 |
| ath_full_ok_with_npz | 2951 |
| scored | 200 |
| exact_complete | 200 |
| partial_unsupported | 0 |
| additional_data_or_solve_required | 0 |

## Original replay parity

- compared: 197 / 200
- max |delta|: 0
- median |delta|: 0
- within 1e-6: 197

## Score variants

| variant | n | physical same | metric changed | score changed | J changed | statuses |
|---|---:|---:|---:|---:|---:|---|
| weight | 200 | 200 | 0 | 200 | 200 | {'exact_complete': 200} |
| tolerance | 200 | 200 | 0 | 200 | 200 | {'exact_complete': 200} |
| target | 200 | 200 | 200 | 200 | 200 | {'exact_complete': 200} |

## Unsupported reasons

- none

## Identities

- unique physical: 200
- unique metric: 200
- unique score: 200

## Preservation inventory

| root | exists | files | bytes | checksums | truncated |
|---|---|---:|---:|---:|---|
| dataset | True | 26564 | 4710631484 | 128 | True |
| dataset_cpu | True | 244 | 51281515 | 128 | True |
| cache/solve | True | 53782 | 7127483339 | 128 | True |
| cache_cpu/solve | True | 456 | 85712312 | 128 | True |
| runs | True | 204848 | 21099515246 | 128 | True |
| traces | True | 1266 | None | 0 | None |

- traces: files 1266, sample `traces\0003c5a0967a.npz`, loadable True
- run provenance: runs 541, config 429, run.json 429, search.ndjson 424, design dirs 36524, response.npz 31406, metrics.json 31406

## Legacy surrogate audit (source-level; audit only)

- objective versions supported: [1]
- predicted impedance: False
- predicted balloon/MEH: False / False

| file | line | capability | code |
|---|---:|---|---|
| `hornlab_search/surrogate/predict.py` | 7 | objective=scalar v1 import | `from ..objective.scalar import PENALTY_INVALID, objective, penalty_result` |
| `hornlab_search/surrogate/train.py` | 9 | objective=scalar v1 import | `from ..objective.scalar import objective` |
| `hornlab_search/surrogate/predict.py` | 93 | score=scalar v1 call | `out[i] = objective(self.metric_set(pred, i), True, target, weights)[0]` |
| `hornlab_search/surrogate/predict.py` | 110 | score=scalar v1 call | `j, t = objective(m, True, target, weights)` |
| `hornlab_search/surrogate/train.py` | 71 | score=scalar v1 call | `out[j] = objective(m, True, target, weights)[0]` |
| `hornlab_search/surrogate/train.py` | 159 | score=scalar v1 call | `pred_obj = sur.objective(pred, target, weights)` |
| `hornlab_search/surrogate/predict.py` | 79 | MetricSet without predicted impedance | `def metric_set(self, pred: dict, i: int) -> MetricSet:` |
| `hornlab_search/surrogate/predict.py` | 80 | MetricSet without predicted impedance | `return MetricSet(freqs_hz=self.freqs, bw_h_deg=pred["bw_h_deg"][i],` |
| `hornlab_search/surrogate/predict.py` | 84 | MetricSet without predicted impedance | `z_throat_real=None)` |
| `hornlab_search/surrogate/train.py` | 62 | MetricSet impedance only if training arrays have it | `z = ym.get("z_throat_real")` |
| `hornlab_search/surrogate/train.py` | 68 | MetricSet impedance only if training arrays have it | `m = MetricSet(freqs, ym["bw_h_deg"][i], ym["bw_v_deg"][i], ym["di_db"][i], "balloon",` |
| `hornlab_search/surrogate/predict.py` | 29 | guard checks bundle config geometry/grid only | `def config_mismatch(self, space, *, freqs_hz=None, family: str \| None = None) -> str \| None:` |
| `hornlab_search/surrogate/predict.py` | 43 | guard checks bundle config geometry/grid only | `bounds = self.meta.get("bounds")` |
| `hornlab_search/surrogate/predict.py` | 55 | guard checks bundle config geometry/grid only | `exp_freqs = self.meta.get("freqs_hz")` |
| `hornlab_search/surrogate/model.py` | 60 | guard checks bundle gate_report only | `gr = (b.get("meta") or {}).get("gate_report") or {}` |
| `hornlab_search/surrogate/round.py` | 139 | guard checks bundle gate_report only | `gr = (load_bundle(p).get("meta") or {}).get("gate_report") or {}` |

## Guards

- backend guard installed: 11, calls: **0**
- read-source guard scope: files read by the pilot (brief + candidate shard prefixes + candidate npz); live queue appends to dataset/runs/cache are outside this assertion
- unchanged: **True**
