# M2 sensitivity (real native TrainingSet)

Status: **complete_descriptive** · protocol `bo-study-v1.1` · generated `2026-11-13T05:28:35Z`

## Input

- training JSON: `C:\Users\hunte\Hrns\hornlab-search\docs\evidence\bo_study_2026-11-12\b2_native\native_trainingset.json` sha256 `42fb1e342d5bfe30c144e423acecbaf15a85530b2f7833059811eb760361313d`
- training NPZ: `C:\Users\hunte\Hrns\hornlab-search\docs\evidence\bo_study_2026-11-12\b2_native\native_trainingset.npz` sha256 `dcca6ed2f0b9a524a0b30ac12e1935c90449bdb63d8d8eed9cb447dba31e71a8`
- recomputed X/J/Y/ids hashes: `{'x_sha256': 'e359ce20f649f5b836553c4b21c89c1be740d430b5bdda5210ea6affa4b17dd2', 'j_sha256': '2e813ff90fe3c134c857677275577e4424202ad967b40a6d292ac7ab05bc702a', 'y_sha256': '7b7df119afe0ff256dcfbe89ececfdc16917929b571932315dee2d65445aa93c', 'y_phys_sha256': '2e813ff90fe3c134c857677275577e4424202ad967b40a6d292ac7ab05bc702a', 'ids_sha256': 'bd5994337731891e0c39c00bc6e8e38da9027018d068d8d7c67d2442689bc710'}`
- counts: n=197 d=13 eligible=197 unique=197 unique_designs=192 refused=3
- active keys (active-projection-v1): `L_mm, a_deg, k, morph_corner_mm, morph_fixed, morph_height_mm, morph_rate, morph_width_mm, n, q, s, s1, s2`
- objective versions: [4]
- solve-hash groups: {'3181879c7477': 192, '4d7ec3ee2758': 5}

## Cohort and validation mode

- cohort: `native__ath_core_v4.yaml|active-projection-v1|objective_v4`
- independent groups available: `False`
- reason: no run/resume/experiment group field in the frozen artifact
- validation mode: `descriptive_no_independent_groups`

## Method

- locked scalar_pool_v1 fit_model; train_Yvar = noise_multiplier * 1e-6 * s2
- predict_j (predicted J = -posterior mean(Y); reversed interval)
- locked scalar_pool_v1 selection; every-fourth maximin cadence
- noise multipliers: [0.1, 1.0, 10.0] (diagnostic only; never used to pick a new optimum)
- pool seeds: [20261112, 20261113]
- diagnostic caps: [64, 128]
- engine versions: `{'engine': 'botorch', 'torch': '2.14.1+cpu', 'botorch': '0.18.1', 'gpytorch': '1.15.2', 'linear_operator': '0.6.1', 'available': True}`

## Subsets

| subset | n | rule | production | diagnostic-only |
|---|---:|---|---:|---:|
| `frozen_subset` | 197 | training artifact selected_ids (production subset) | True | False |
| `all_eligible` | 197 | all eligible rows in the frozen artifact | False | True |
| `stratified_by_J_cap64` | 64 | evenly spaced J ranks, diagnostic cap 64 | False | True |
| `lowJ_plus_maximin_cap64` | 64 | production subset rule at diagnostic cap 64 (64 lowest-J + deterministic maximin) | False | True |
| `stratified_by_J_cap128` | 128 | evenly spaced J ranks, diagnostic cap 128 | False | True |
| `lowJ_plus_maximin_cap128` | 128 | production subset rule at diagnostic cap 128 (64 lowest-J + deterministic maximin) | False | True |
| `majority_solve_group_192` | 192 | majority solve-hash group (the freeze records this as the screen group) | False | True |

## Fit sensitivity (descriptive in-sample)

| subset | noise x | status | in-sample RMSE J | train-mean baseline | pred J mean | pred J range | s2 | train_Yvar |
|---|---:|---|---:|---:|---:|---|---:|---:|
| `frozen_subset` | 0.1 | ok | 0.113222 | 5.11962 | 5.66027 | [1.972, 30.24] | 26.344282024145755 | 2.6344282024145754e-06 |
| `frozen_subset` | 1.0 | ok | 0.113222 | 5.11962 | 5.66027 | [1.972, 30.24] | 26.344282024145755 | 2.6344282024145754e-05 |
| `frozen_subset` | 10.0 | ok | 0.113223 | 5.11962 | 5.66027 | [1.971, 30.24] | 26.344282024145755 | 0.0002634428202414575 |
| `all_eligible` | 0.1 | ok | 0.113222 | 5.11962 | 5.66027 | [1.972, 30.24] | 26.344282024145755 | 2.6344282024145754e-06 |
| `all_eligible` | 1.0 | ok | 0.113222 | 5.11962 | 5.66027 | [1.972, 30.24] | 26.344282024145755 | 2.6344282024145754e-05 |
| `all_eligible` | 10.0 | ok | 0.113223 | 5.11962 | 5.66027 | [1.971, 30.24] | 26.344282024145755 | 0.0002634428202414575 |
| `stratified_by_J_cap64` | 0.1 | ok | 3.12446 | 5.11963 | 5.14462 | [0.4476, 30.24] | 26.50232321182653 | 2.650232321182653e-06 |
| `stratified_by_J_cap64` | 1.0 | ok | 3.12436 | 5.11963 | 5.14469 | [0.4476, 30.24] | 26.50232321182653 | 2.6502323211826526e-05 |
| `stratified_by_J_cap64` | 10.0 | ok | 3.12425 | 5.11963 | 5.14457 | [0.4478, 30.24] | 26.50232321182653 | 0.0002650232321182653 |
| `lowJ_plus_maximin_cap64` | 0.1 | ok | 6.02915 | 6.06601 | 2.44237 | [1.911, 2.969] | 0.10022363377234475 | 1.0022363377234475e-08 |
| `lowJ_plus_maximin_cap64` | 1.0 | ok | 6.03722 | 6.06601 | 2.43267 | [1.911, 2.969] | 0.10022363377234475 | 1.0022363377234475e-07 |
| `lowJ_plus_maximin_cap64` | 10.0 | ok | 6.03797 | 6.06601 | 2.43189 | [1.911, 2.969] | 0.10022363377234475 | 1.0022363377234474e-06 |
| `stratified_by_J_cap128` | 0.1 | ok | 2.17663 | 5.11994 | 5.49905 | [0.2701, 30.24] | 25.237025698189075 | 2.5237025698189076e-06 |
| `stratified_by_J_cap128` | 1.0 | ok | 2.17954 | 5.11994 | 5.49936 | [0.2631, 30.24] | 25.237025698189075 | 2.5237025698189073e-05 |
| `stratified_by_J_cap128` | 10.0 | ok | 2.17932 | 5.11994 | 5.49942 | [0.263, 30.24] | 25.237025698189075 | 0.0002523702569818907 |
| `lowJ_plus_maximin_cap128` | 0.1 | ok | 1.08336 | 5.12542 | 5.58847 | [0.6665, 30.24] | 36.390026396364505 | 3.63900263963645e-06 |
| `lowJ_plus_maximin_cap128` | 1.0 | ok | 1.07632 | 5.12542 | 5.59266 | [0.6531, 30.24] | 36.390026396364505 | 3.63900263963645e-05 |
| `lowJ_plus_maximin_cap128` | 10.0 | ok | 1.07627 | 5.12542 | 5.59259 | [0.6547, 30.24] | 36.390026396364505 | 0.000363900263963645 |
| `majority_solve_group_192` | 0.1 | ok | 0.16012 | 5.12016 | 5.63489 | [1.597, 30.24] | 26.816223119547658 | 2.681622311954766e-06 |
| `majority_solve_group_192` | 1.0 | ok | 0.160118 | 5.12016 | 5.63489 | [1.597, 30.24] | 26.816223119547658 | 2.6816223119547657e-05 |
| `majority_solve_group_192` | 10.0 | ok | 0.160096 | 5.12016 | 5.63489 | [1.597, 30.24] | 26.816223119547658 | 0.00026816223119547657 |

## Proposal sensitivity (off-policy retrospective)

| subset | pool seed | status | selection | geometry hash | pred J mean | pred J interval | acquisition (technical) |
|---|---:|---|---|---|---:|---|---:|
| `frozen_subset` | 20261112 | ok | acquisition | `5c02b1695abe65557dd3` | 3.91415 | [-4.144183605638998, 11.972473643010332] | -0.174728 |
| `frozen_subset` | 20261113 | ok | acquisition | `b7e68df0860e0a1fe542` | 3.61253 | [-4.343821828040696, 11.568890147706732] | -0.0819157 |
| `all_eligible` | 20261112 | ok | acquisition | `5c02b1695abe65557dd3` | 3.91415 | [-4.144183605638998, 11.972473643010332] | -0.174728 |
| `all_eligible` | 20261113 | ok | acquisition | `b7e68df0860e0a1fe542` | 3.61253 | [-4.343821828040696, 11.568890147706732] | -0.0819157 |
| `stratified_by_J_cap64` | 20261112 | ok | acquisition | `4fcfc91cadc8e0fa08cb` | 3.90002 | [-4.563402621329008, 12.36344405757129] | -0.221483 |
| `stratified_by_J_cap64` | 20261113 | ok | acquisition | `655746b30b3f09977bd5` | 0.0977534 | [-4.455958589819341, 4.6514653091594855] | 0.619342 |
| `lowJ_plus_maximin_cap64` | 20261112 | ok | acquisition | `d44cead79d48fbb8e707` | 2.19243 | [1.7141121536363, 2.670747899582757] | -4.22884 |
| `lowJ_plus_maximin_cap64` | 20261113 | ok | acquisition | `3904445168acb0dd4fc5` | 2.19047 | [1.6957789026964503, 2.685152144011029] | -4.10119 |
| `stratified_by_J_cap128` | 20261112 | ok | acquisition | `832a29a8a5639d79c4ed` | 6.13796 | [-6.525928503648352, 18.80184182835024] | -0.104837 |
| `stratified_by_J_cap128` | 20261113 | ok | acquisition | `a0ee61b988e1d62df99e` | 3.68521 | [-5.872094756460581, 13.24250648079093] | 0.0595268 |
| `lowJ_plus_maximin_cap128` | 20261112 | ok | acquisition | `e8c1d3d5fa03fb73623e` | 1.51472 | [-4.846912142072682, 7.876353467438891] | 0.402127 |
| `lowJ_plus_maximin_cap128` | 20261113 | ok | acquisition | `2553d7bee4145cd918c5` | 3.80743 | [-5.3985132268785865, 13.013382464476583] | 0.0600329 |
| `majority_solve_group_192` | 20261112 | ok | acquisition | `5c02b1695abe65557dd3` | 4.06564 | [-4.212375977079865, 12.34365228157218] | -0.336175 |
| `majority_solve_group_192` | 20261113 | ok | acquisition | `b7e68df0860e0a1fe542` | 3.32599 | [-4.678177689430035, 11.330152828882087] | -0.114496 |

## Space-filling vs BO vs CMA preparation

- comparison status: `preparation_only_off_policy_retrospective`
- BO: qLogNEI acquisition from the finite scrambled-Sobol pool
- space-filling: deterministic maximin (farthest-point) reference from the same frozen scrambled-Sobol pool (`prepared`)
- CMA seed: `unmeasured` — no independently validated comparable CMA-seed outcomes in the committed artifact; no speedup or acoustic-benefit claim
- next step: an equal-cost screen of the prepared geometry hashes would be required before any comparison; no BEM/GPU solve was run here

  - space-filling pool seed 20261112: `21fdda84a6ed6608eee8` (ok)
  - space-filling pool seed 20261113: `0083d16d4a909566fc10` (ok)

## Limitations

- descriptive in-sample diagnostics only; no independent-group held-out estimate and no gate pass
- the committed native artifact has no independent run/resume group identity; groups were not invented
- noise multipliers 0.1/1/10 are diagnostics of the fixed regularization floor, not measured solver noise and not a new policy
- proposals are off-policy retrospective suggestions; matching pool-seed geometry IDs are descriptive, not global pool coverage
- candidate pool entries are cheap-check-passed; mesh/acoustic eligibility unknown
- predictions are model outputs and are never appended as measured rows
- J is objective v4 only; no cross-objective-version ranking
- no closed-loop optimization speedup, acoustic benefit, adoption or manufacturing claim is made
- mixed solve-hash groups are present; this is a mixed-fidelity advisory fit
- the frozen artifact mixes solve hashes ({'3181879c7477': 192, '4d7ec3ee2758': 5}); the freeze records 192 screen + 5 verify rows, so this is a mixed-fidelity advisory fit, not a strict single-fidelity GP
- the committed native artifact has no independent run/resume group identity; real-data diagnostics are descriptive (in-sample) and do not invent groups

## Simple/CMA comparison

- status: `unmeasured`
- reason: no independently validated comparable CMA outcomes in the committed artifact; retrospective BO diagnostics only

