# B1 readiness and the zero-dimension truth fix (Fable WP 2.2 / D7, cloud senior 2026-11-18)

**No GPU used. Nothing queued.** This is the owner's GPU-approval packet for B1 plus the code fix
that makes the part3 job-line failure impossible to repeat.

## 1. Do the B1 / B1f job lines from `b6d3ba4` use `kind: search` with every bound pinned?

**No** [code-verified + verified by dry-run in the cloud]. Every B1 and B1f job is
`kind: command` running `tools/night_queue/fidelity_pairs.py` (wrapped by
`tools/bench/run_with_memwatch.py` for B1). `fidelity_pairs.py` calls
`hornlab_search.search.evaluate.evaluate` directly on the stored design; it never builds a CMA
vector, so the pycma `x0=[]` crash cannot happen on these lines.

```
python tools/run_campaign_night.py --night scratch/fable_architecture/.b1/b1_mesh_night_insert.yaml --dry-run   # 5 jobs, exit 0
python tools/run_campaign_night.py --night scratch/fable_architecture/.b1/b1_night_insert.yaml --dry-run        # 1 job,  exit 0
python tools/run_campaign_night.py --night docs/evidence/b1_readiness_2026-11-18/b1_mesh_ext_throat_probes.yaml --dry-run  # 3 jobs, exit 0
```

## 2. Truth fix: a search with zero free dimensions is refused before pycma

The part3 failure (`kind: search`, every bound `search: false`, pycma `x0=[]`,
`TypeError: ufunc 'isinf' not supported`, job `throat_hv_B_ctl`) is now refused in three places,
each naming the right command (`hornlab-search run --config <yaml> --mode screen`, or
`--mode finalist`; in a night, `kind: command`):

| Where | Behaviour | Writes anything? |
|---|---|---|
| `search/cma.py::search` (all callers: CLI, campaign, studies) | `require_free_dimensions(cfg)` raises `ConfigError` first thing | no run file |
| `hornlab-search search` CLI | prints `search REFUSED ...`, removes its empty new run dir, exit 2, before the backend warms | no |
| `tools/run_campaign_night.py --dry-run` | refuses every `kind: search` job, and every `kind: command` job whose argv is a fresh `search --config X`, with zero free dims; resumes are skipped; an unloadable config is a printed NOTE, not a failure | no |

"Free dimensions" = `DesignSpace.from_config(cfg)` searched keys minus `search.links`
(`cma.free_search_keys`), exactly the vector CMA-ES would get. No meshing.

Scope note [verified in the cloud]: 63 shipped configs under `examples/` have zero free dimensions
(single-design configs: the throat sweep, Klangfilm H/V A/B configs, MEH seeds, solana/sawmod,
multicell). That is legitimate for `run`; only a `search` of them is refused. `meh_t1` declares
`search: {algorithm: cma, budget: 80}` with `bounds: {}`: a `search` of it would have hit the same
pycma crash and is now refused with the `run` hint.

Tests: `tests/test_search_zero_dimensions.py` (7, real throat configs, offline).

## 3. B1 feasibility table (CPU sizing from `b6d3ba4`, not re-measured here)

Source: `scratch/fable_architecture/.b1/b1_mesh_feasibility.md` [verified as a document; the DOF
numbers are the local agent's CPU dry-run, not re-run in the cloud (no gmsh here)].
Card ceiling (TOOLCHAIN M2, RTX 4060 8 GB): quarter-domain OOM transition 8.9-15.7 k DOF.

| design | lane | ref DOF | x2 (epw 12) DOF | x2 verdict | in the proposed queue? |
|---|---|---:|---:|---|---|
| `2f7307c06023` | fold_warm | 3 751 | 14 530 | probe-grade | yes (`b1_mesh_night_insert.yaml`) |
| `507e7257c091` | fold_warm | 3 791 | 14 559 | probe-grade | yes |
| `ced63c6a01a1` | fold_warm | 3 844 | 14 780 | probe-grade | yes |
| `688ffe811b6a` | fold_warm | 3 796 | 14 903 | probe-grade | yes |
| `78f599e8a1d2` | fold_warm | 3 837 | 14 719 | probe-grade | yes |
| `766c9b1ba8a9` | ext_throat_v7 | 3 725 | 14 270 | probe-grade | **no - see finding** (optional file here) |
| `508f907726d3` | ext_throat_v7 | 3 999 | 15 388 | probe-grade (near the edge) | **no - see finding** (optional) |
| `b996da551021` | ext_throat_v7 | 4 009 | 15 342 | probe-grade (near the edge) | **no - see finding** (optional) |
| `3a1038da45d0` | ext_throat_v7 (the v7 leader) | 5 275 | refused (symmetry-plane slivers), est. 21 100 | **infeasible on this card** | no |
| `9fcd21fc1904` | ext_throat_v8 (the v8 incumbent, J 3.10281) | 5 274 | refused, est. 21 096 | **infeasible on this card** | no |

x3 (epw 18) is cap-bound at 24 k for all ten (true size 31.8-49.3 k DOF): not queueable.

**Finding (cloud senior):** the feasibility doc's table says the three ext_throat_v7 designs
`766c…`, `508f…`, `b996…` build at x2 at the same probe grade as fold-warm, but its
recommendation excludes "the five ext-throat designs". Only two of the five refuse. The three
buildable ones are in `b1_mesh_ext_throat_probes.yaml` as an **optional** second batch. They matter:
without them B1 says nothing about the ext-throat construction, which holds the v7 lead and the
v8 incumbent, and which is the A-family parent of the throat block.

**Second finding [inferred]:** the two designs B1 most needs (the v7 leader and the v8
incumbent) are the two it cannot measure on this card. The throat-block A_r15 design (5 438 ref
DOF, same ext-throat parent) will very likely be infeasible at x2 as well. So B1 on this card can
publish the mesh part of the floor for fold-warm (and maybe ext_throat_v7 at the smaller sizes),
not for the leaders. State that in the B1 evidence; do not extend the floor to them silently.

## 4. Queue-ready lines for the owner's approval (order after the BO arms, per D7)

Approve by ID. Each is one fresh process; the first spill invalidates that design and, if it is
the first fold-warm probe, stops the batch ("not measurable on this GPU").

| # | Batch | File | Jobs | Est. GPU time |
|---|---|---|---|---|
| 1 | B1 fold-warm x2 probes | `scratch/fable_architecture/.b1/b1_mesh_night_insert.yaml` | 5 | unmeasured; per-frequency time jumps near the CUDA cliff (5.8 s at 6.9 k to 41.6 s at 8.5 k DOF, `BENCH_40_DESIGNS_2026-11-03`), so plan on the 3 h job timeout |
| 2 | B1 ext_throat_v7 x2 probes (optional) | `docs/evidence/b1_readiness_2026-11-18/b1_mesh_ext_throat_probes.yaml` | 3 | same |
| 3 | B1f frequency check (optional; NOT mesh convergence) | `scratch/fable_architecture/.b1/b1_night_insert.yaml` | 1 | 10 designs x 2 tiers |

Insert procedure for the local agent (hornlab-night-queue skill): copy the job blocks into the
live night file AFTER the last BO arm, keep every existing entry's order, then
`.venv\Scripts\python.exe tools\run_campaign_night.py --night runs\nights\<night>.yaml --dry-run`
must exit 0 (it now also checks free dimensions). GPU hygiene per CLAUDE.md rules 1-8.
