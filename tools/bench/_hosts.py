"""Guarded replacement for ``taskkill /F /IM julia.exe`` in the bench scripts (WP0).

The old scripts killed EVERY julia.exe on the machine, which is unsafe next to a running search,
another session, or a CPU lane (docs/throughput/RUNBOOK.md). This helper kills only BEAT host
trees (matched by command line, via ``hornlab_search.solve.worker``) that were NOT already running
when the script started. Hosts that pre-date the script are left alone and reported once: clear
them yourself first (``hornlab-search gpu-clean``), as CLAUDE.md "GPU / Julia hygiene" says.

``kill_hosts()`` keeps the old name and call sites, so the scripts change by one import line.
Pure helper logic takes injectable ``lister`` / ``killer`` so it is unit-tested offline.
"""
from __future__ import annotations

import time

_BASELINE: set[int] | None = None
_WARNED = False


def _default_lister():
    from hornlab_search.solve import worker
    return worker.list_beat_hosts()


def _default_killer(pid: int) -> bool:
    from hornlab_search.solve import worker
    return worker.kill_tree(pid)


def snapshot(lister=None) -> set[int]:
    """Remember the BEAT host roots alive right now as 'not ours'."""
    global _BASELINE
    _BASELINE = {p.pid for p in (lister or _default_lister)()}
    return set(_BASELINE)


def kill_hosts(*, lister=None, killer=None, sleep=time.sleep, settle_s: float = 2.0) -> list[int]:
    """Kill the BEAT host trees this process started. Returns the root pids killed."""
    global _WARNED
    lister = lister or _default_lister
    killer = killer or _default_killer
    if _BASELINE is None:
        foreign = snapshot(lister)
        if foreign and not _WARNED:
            print(f"WARNING: {len(foreign)} BEAT host(s) were already running ({sorted(foreign)}); "
                  "they are NOT killed by this script. Run `hornlab-search gpu-clean` first for a "
                  "clean measurement.", flush=True)
            _WARNED = True
        return []
    mine = [p.pid for p in lister() if p.pid not in _BASELINE]
    for pid in mine:
        killer(pid)
    if mine:
        sleep(settle_s)
    return mine


def reset_for_tests() -> None:
    global _BASELINE, _WARNED
    _BASELINE, _WARNED = None, False


def bench_solve_kwargs() -> dict:
    """Opt-in production flags for the legacy bench scripts that build ``SolveConfig`` directly.

    Default (nothing set) = the script's historical behaviour, byte for byte, so old numbers stay
    comparable. To measure the PRODUCTION path instead, set before running:

        HORNLAB_BENCH_FUSED=1            -> exports HORNLAB_BEAT_FUSED_BM_CUDA=1 (multi-channel MEH
                                            solves need beat-bem >= 0850ef3)
        HORNLAB_BENCH_SYMMETRY=yz+xz     -> SolveConfig(native_symmetry_plane="yz+xz"); must match
                                            the mesh (quarter mesh = yz+xz)

    ``tools/bench/throughput_matrix.py`` is the production-faithful harness; prefer it.
    """
    import os
    kw: dict = {}
    sym = os.environ.get("HORNLAB_BENCH_SYMMETRY", "").strip()
    if sym:
        kw["native_symmetry_plane"] = sym
    fused = os.environ.get("HORNLAB_BENCH_FUSED", "").strip()
    if fused in ("0", "1"):
        os.environ["HORNLAB_BEAT_FUSED_BM_CUDA"] = fused
    print(f"bench flags: fused={fused or 'unset (legacy)'} symmetry={sym or 'unset (legacy: none)'} "
          "(legacy default is NOT the production fused/symmetric path)", flush=True)
    return kw
