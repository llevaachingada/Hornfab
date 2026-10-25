"""Single-shot VRAM-ceiling measurement for the WP15 fused CUDA path.

Protocol: ``TOOLCHAIN.md`` section **M2** (one solve per fresh process, baseline recorded
before the solve, nvidia-smi polled out of process) plus ``CLAUDE.md`` "GPU / Julia hygiene"
(clear stale hosts, one measurement per process, start the VRAM poll first, every measurement
ends by clearing its workers) and ``docs/FORKS.md`` step 6.4 / M2 handoff.

One invocation builds the quarter-domain seed mesh (``examples/osse_baseline.yaml`` seed,
quadrants "1", native symmetry plane "yz+xz") and runs exactly **one** solve at the requested
frequency, then shuts the BEAT host down with ``worker.shutdown(verify=True)`` in a ``finally``
block (``warm()`` keeps one idle host for adoption, so an explicit verified shutdown is what
guarantees no solver process survives this measurement).

``nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits`` (the repo's own probe,
``solve/worker.py::vram_used_mib``) is polled from a daemon THREAD every ~0.2 s. The first
sample is the baseline; the maximum is the peak. Both, and their difference, are reported as
MiB integers.

The caller runs ``hornlab-search gpu-clean`` between invocations and passes one ceiling point
per process, e.g.::

    .venv\\Scripts\\python.exe tools/measure_fused_ceiling.py \
        --mouth-res 3.0 --throat-res 1.5 --flag on

Calibration helper (CPU/gmsh only: no solver, no GPU, no lock)::

    .venv\\Scripts\\python.exe tools/measure_fused_ceiling.py \
        --mouth-res 3.0 --throat-res 1.5 --mesh-only

It prints triangles, P1 dofs (``MeshInfo.n_vertices``) and the resolution actually handed to
the mesher, then exits. ``--cache-dir`` defaults to ``scratch/ceiling_cache`` (gitignored) and
``--runs-dir`` to ``runs`` (gitignored), so nothing pollutes the repo's main ``cache/`` or run
data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import threading
import time
import traceback
from pathlib import Path

# Runnable as a plain script (`python tools/measure_fused_ceiling.py`): put the repo root on
# sys.path, like tools/rescore/rescore_v2.py does.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.constants import C_AIR  # noqa: E402
from hornlab_search.design import families  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402
from hornlab_search.mesh import build as mesh_build  # noqa: E402
from hornlab_search.mesh import sizing, topology  # noqa: E402
from hornlab_search.search.gpulock import GpuBusyError, gpu_lock  # noqa: E402
from hornlab_search.solve import worker  # noqa: E402
from hornlab_search.solve.base import get_backend  # noqa: E402
from hornlab_search.types import (  # noqa: E402
    GeometryInvalidError, MeshResult, MeshSpec, ObservationSpec, SolveSpec)

EXAMPLES = REPO_ROOT / "examples"

#: The quarter domain the fused GPU test and the M2 table use.
QUADRANTS = "1"
SYMMETRY_PLANE = sizing.SYMMETRY_PLANE[QUADRANTS]        # "yz+xz"

#: Full-domain-equivalent ceiling; allow_large_mesh=True so the mesher never refuses a
#: ceiling point (the dof budget is exactly what this harness is measuring).
MAX_TRIANGLES = 10**6

VRAM_POLL_INTERVAL_S = 0.2


# ------------------------------------------------------------------ VRAM polling


class VramPoller:
    """Poll ``nvidia-smi`` from a daemon thread; first sample = baseline, max = peak.

    The probe is the repo's own ``solve.worker.vram_used_mib`` (a subprocess per sample), so
    this follows AGENTS.md hygiene rule 5: the poll never runs inside the solve process's own
    GPU accounting. ``stop()`` is idempotent and takes a final sample after the workers are
    gone, so the polling window is [before the solver exists, after shutdown completes].
    """

    def __init__(self, interval_s: float = VRAM_POLL_INTERVAL_S) -> None:
        self.interval_s = float(interval_s)
        self.baseline_mib: float | None = None
        self.peak_mib: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = False

    @property
    def started(self) -> bool:
        return self._started

    def _sample(self) -> None:
        value = worker.vram_used_mib()
        if value is None:
            return
        value = float(value)
        if self.peak_mib is None or value > self.peak_mib:
            self.peak_mib = value

    def _run(self) -> None:
        while not self._stop.wait(self.interval_s):
            self._sample()

    def start(self) -> None:
        if self._started:
            return
        self.baseline_mib = worker.vram_used_mib()
        self.baseline_mib = None if self.baseline_mib is None else float(self.baseline_mib)
        self.peak_mib = self.baseline_mib
        self._thread = threading.Thread(target=self._run, name="vram-poll", daemon=True)
        self._thread.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._sample()
        self._started = False

    @property
    def peak_minus_baseline_mib(self) -> float | None:
        if self.peak_mib is None or self.baseline_mib is None:
            return None
        return max(0.0, self.peak_mib - self.baseline_mib)


# ------------------------------------------------------------------ mesh


def _cache_key(design, res_mm: dict, epw: float) -> str:
    blob = json.dumps(
        {"v": 1, "design": design.hash(), "quadrants": QUADRANTS,
         "epw": round(float(epw), 9),
         "res_mm": {k: round(float(v), 9) for k, v in res_mm.items()}},
        sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _mesh_result(out: Path, meta: dict, seconds: float) -> MeshResult:
    return MeshResult(
        path=str(out), n_triangles=int(meta["n_triangles"]), n_dof=int(meta["n_vertices"]),
        quadrants=str(meta["quadrants"]), symmetry_plane=meta.get("symmetry_plane"),
        res_mm=dict(meta["res_mm"]), bbox_m=tuple(float(v) for v in meta["bbox_m"]),
        seconds=float(seconds))


def build_ceiling_mesh(cfg, mouth_res_mm: float, throat_res_mm: float, out_dir: Path,
                       cache_dir: Path) -> MeshResult:
    """Build the seed design at an EXPLICIT mouth/throat resolution on the quarter domain.

    ``mesh/build.py::build_mesh`` derives the resolution from ``epw`` and ``f_max_hz`` only
    (``sizing.res_mm_for`` forces throat = mouth/2). This harness must honour an arbitrary
    ``--throat-res``, and the mesher has no frequency rule at all: it uses
    ``mesh.throat_res_mm`` / ``mouth_res_mm`` / ``rear_res_mm`` verbatim. So the config is
    built with ``design.families.to_mesher_config`` and the mesher is called directly, then
    the same guards run (bbox units, quadrant/symmetry pairing, source tag, closed manifold
    surface). The dof cap is deliberately NOT applied: measuring the dof ceiling is the point.
    """
    import hornlab_mesher as hm

    epw = float(cfg.mesh.epw)
    design = DesignSpace.from_config(cfg).seed
    res_mm = {"throat": float(throat_res_mm), "mouth": float(mouth_res_mm),
              "rear": float(mouth_res_mm)}
    # Provenance only: the mesher never sees f_max_hz, it is given res_mm directly.
    f_max_hz = 1000.0 * C_AIR / (epw * float(mouth_res_mm))
    mesh_spec = MeshSpec(epw=epw, f_max_hz=f_max_hz, quadrants=QUADRANTS,
                         max_triangles=MAX_TRIANGLES, allow_large_mesh=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "mesh.msh"
    entry = cache_dir / _cache_key(design, res_mm, epw)
    cached_meta, cached_msh = entry / "meta.json", entry / "mesh.msh"
    if cached_meta.is_file() and cached_msh.is_file():
        try:
            meta = json.loads(cached_meta.read_text(encoding="utf-8"))
            t0 = time.perf_counter()
            shutil.copyfile(cached_msh, out)
            print(f"MESH CACHE HIT {entry}", flush=True)
            return _mesh_result(out, meta, time.perf_counter() - t0)
        except (OSError, ValueError, KeyError) as exc:
            print(f"MESH CACHE IGNORED ({exc!r}); rebuilding", flush=True)

    t0 = time.perf_counter()
    mcfg = families.to_mesher_config(design, mesh_spec, res_mm, out)
    built = hm.build_from_config(mcfg, out)
    summary, xyz, tri = mesh_build.read_msh_summary(out, return_arrays=True)

    # The same guards build_mesh applies, minus the dof budget.
    mesh_build._check_bbox(summary["bbox_m"])
    if built.quadrants != QUADRANTS or built.native_symmetry_plane != SYMMETRY_PLANE:
        raise mesh_build.SymmetryMismatchError(
            f"asked for quadrants {QUADRANTS!r}/{SYMMETRY_PLANE!r}, mesher built "
            f"{built.quadrants!r}/{built.native_symmetry_plane!r}")
    if summary["tags"].get(mesh_build.SOURCE_TAG, 0) <= 0:
        raise GeometryInvalidError(
            f"mesh has no elements on physical tag {mesh_build.SOURCE_TAG} (the source); "
            f"tags present: {summary['tags']}")
    topology.check_surface(xyz, tri, SYMMETRY_PLANE)

    meta = {
        "cache_key": entry.name,
        "n_triangles": int(summary["n_triangles"]),
        "n_vertices": int(built.n_vertices),
        "quadrants": QUADRANTS,
        "symmetry_plane": SYMMETRY_PLANE,
        "res_mm": res_mm,
        "bbox_m": list(summary["bbox_m"]),
    }
    try:                                    # best-effort cache; a failure never kills a run
        entry.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, cached_msh)
        cached_meta.write_text(json.dumps(meta, indent=1, sort_keys=True), encoding="utf-8")
    except OSError as exc:
        print(f"MESH CACHE WRITE FAILED ({exc!r})", flush=True)
    return _mesh_result(out, meta, time.perf_counter() - t0)


# ------------------------------------------------------------------ solve spec


def make_solve_spec(cfg, freq_hz: float, angles: int, flag_on: bool) -> SolveSpec:
    """The minimal production SolveSpec: one frequency, 73 angles, no balloon.

    Constructed directly instead of through a YAML mode grid: a mode grid would bring 12/25/36
    frequencies and a balloon, which the old M2 table did not measure (assembly + solve only).
    """
    observation = ObservationSpec(
        distance_m=float(cfg.solve.distance_m), angle_count=int(angles),
        balloon=False, balloon_points=0)
    return SolveSpec(
        mode="screen",
        freqs_hz=(float(freq_hz),),
        backend="beat_cuda",
        observation=observation,
        gmres_tol=float(cfg.solve.gmres_tol),
        # Same place solve_spec() puts the opt-in: the hash changes only when it is set, and
        # beat._assert_cuda_fused_path() reads it to prove the fused path actually ran.
        extra={"cuda_fused": True} if flag_on else {},
    )


# ------------------------------------------------------------------ reporting


def _i(value: float | None) -> int | None:
    return None if value is None else int(round(float(value)))


def _f(value, digits: int = 3) -> float | None:
    return None if value is None else round(float(value), digits)


def _result_line(payload: dict) -> None:
    print("RESULT " + json.dumps(payload, sort_keys=True), flush=True)


def _command_string(args, throat_res_mm: float) -> str:
    return (f"measure_fused_ceiling --mouth-res {args.mouth_res:g} "
            f"--throat-res {throat_res_mm:g} --flag {args.flag} "
            f"--freq {args.freq:g} --angles {args.angles}")


def _abs(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


# ------------------------------------------------------------------ CLI


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="One-shot quarter-domain VRAM-ceiling point for the WP15 fused CUDA path "
                    "(TOOLCHAIN.md M2 protocol). Prints one parseable RESULT line.")
    p.add_argument("--mouth-res", type=float, required=True, metavar="MM",
                   help="quarter-mesh mouth target resolution in mm (explicit, not f_max-derived)")
    p.add_argument("--throat-res", type=float, default=None, metavar="MM",
                   help="throat resolution in mm (default: mouth/2, the M1 calibration pairs)")
    p.add_argument("--flag", choices=("on", "off"), default="on",
                   help="solve.cuda_fused: on builds the backend with cuda_fused=True (default on)")
    p.add_argument("--freq", type=float, default=1000.0, metavar="HZ",
                   help="the single solve frequency (default 1000.0, the old M2 protocol)")
    p.add_argument("--angles", type=int, default=73, metavar="N",
                   help="observation angle count (default 73; no balloon grid is built)")
    p.add_argument("--mesh-only", action="store_true",
                   help="build the mesh only (CPU/gmsh): triangles + P1 dofs, no solver, no lock")
    p.add_argument("--runs-dir", type=Path, default=Path("runs"),
                   help="runs root / GPU-lock root (default runs/, gitignored)")
    p.add_argument("--cache-dir", type=Path, default=Path("scratch/ceiling_cache"),
                   help="mesh cache, separate from the repo cache/ "
                        "(default scratch/ceiling_cache, gitignored)")
    return p.parse_args(argv)


def _run_solve(args, cfg, mesh: MeshResult, runs_dir: Path, payload: dict) -> int:
    """Acquire the GPU lock, warm one host, run ONE solve, and always shut the host down."""
    flag_on = args.flag == "on"
    spec = make_solve_spec(cfg, args.freq, args.angles, flag_on)
    poller = VramPoller()
    code = 0
    try:
        with gpu_lock(_command_string(args, payload["throat_res"]), runs_root=runs_dir):
            try:
                killed = worker.clear_stale_hosts(force=True)
                print(f"CLEAN: stale BEAT hosts cleared (roots {killed})" if killed
                      else "CLEAN: no stale BEAT hosts", flush=True)

                # Baseline and peak cover everything from here until shutdown completes.
                poller.start()
                backend = get_backend("beat_cuda", cuda_fused=flag_on,
                                      timeout_s=float(cfg.solve.timeout_s),
                                      track_vram=False)   # the harness owns the VRAM probe
                worker.warm(backend)
                t0 = time.perf_counter()
                outcome = backend.solve(mesh, spec)
                wall_s = time.perf_counter() - t0

                if outcome.ok and outcome.response is not None:
                    meta = outcome.response.meta or {}
                    timings = meta.get("timings") or {}
                    diagnostics = [d for d in (meta.get("native_diagnostics") or [])
                                   if isinstance(d, dict)]
                    paths = [d.get("assembly_path") for d in diagnostics]
                    meta_fused = meta.get("cuda_fused")
                    proven = (not flag_on) or (meta_fused is True and bool(paths)
                                               and all(p == "fused_cuda" for p in paths))
                    total_s = timings.get("total_s")
                    if total_s is None:
                        total_s = meta.get("solve_seconds", wall_s)
                    payload.update({
                        "assembly_s": _f(timings.get("assembly_s")),
                        "solve_s": _f(timings.get("solve_s")),
                        "s_per_freq": _f(total_s),
                        "assembly_path": (paths[0] if paths and all(p == paths[0] for p in paths)
                                          else None),
                        "assembly_paths": paths,
                        "meta_cuda_fused": meta_fused,
                        "ok": bool(proven),
                    })
                    print(f"SOLVE ok dofs={mesh.n_dof} assembly_path={payload['assembly_path']} "
                          f"assembly={payload['assembly_s']}s solve={payload['solve_s']}s "
                          f"s_per_freq={payload['s_per_freq']}s", flush=True)
                    if not proven:
                        print("PATH NOT PROVEN: meta['cuda_fused'] / assembly_path diagnostics "
                              f"do not prove fused_cuda (meta_cuda_fused={meta_fused!r}, "
                              f"assembly_paths={paths!r})", file=sys.stderr, flush=True)
                        code = 1
                else:
                    print(f"OOM/CRASH: {outcome.message}", file=sys.stderr, flush=True)
                    payload["ok"] = False
                    code = 1
            except Exception as exc:        # noqa: BLE001 - surfaced, then exit nonzero
                print(f"OOM/CRASH: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                traceback.print_exc()
                payload["ok"] = False
                code = 1
            finally:
                try:
                    forced = worker.shutdown(verify=True)
                    print(f"SHUTDOWN: worker.shutdown(verify=True) ok; "
                          f"force-killed root pids: {forced}", flush=True)
                except Exception as exc:    # noqa: BLE001 - a surviving host is a failed run
                    print(f"SHUTDOWN FAILED: {type(exc).__name__}: {exc}",
                          file=sys.stderr, flush=True)
                    payload["ok"] = False
                    code = 1
                finally:
                    poller.stop()
    except GpuBusyError as exc:
        print(f"GPU BUSY: {exc}", file=sys.stderr, flush=True)
        return 3
    finally:
        poller.stop()                       # idempotent; also covers a failure before start

    payload["baseline_MiB"] = _i(poller.baseline_mib)
    payload["peak_MiB"] = _i(poller.peak_mib)
    payload["peak_minus_baseline_MiB"] = _i(poller.peak_minus_baseline_mib)
    print(f"VRAM baseline={payload['baseline_MiB']} MiB peak={payload['peak_MiB']} MiB "
          f"peak-baseline={payload['peak_minus_baseline_MiB']} MiB", flush=True)
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    mouth_res = float(args.mouth_res)
    throat_res = float(args.throat_res) if args.throat_res is not None else mouth_res / 2.0
    if mouth_res <= 0 or throat_res <= 0:
        print("--mouth-res and --throat-res must be positive", file=sys.stderr)
        return 2
    if args.angles < 3 or args.angles % 2 == 0:
        print("--angles must be an odd count >= 3 (an exact 0-degree sample)", file=sys.stderr)
        return 2

    runs_dir = _abs(Path(args.runs_dir))
    cache_dir = _abs(Path(args.cache_dir))
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    out_dir = runs_dir / f"ceiling_m{mouth_res:g}_t{throat_res:g}"

    try:
        mesh = build_ceiling_mesh(cfg, mouth_res, throat_res, out_dir, cache_dir)
    except Exception as exc:               # noqa: BLE001 - a bad ceiling point is a finding
        print(f"MESH FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1

    payload = {
        "mouth_res": mouth_res,
        "throat_res": throat_res,
        "triangles": int(mesh.n_triangles),
        "dofs": int(mesh.n_dof) if mesh.n_dof is not None else None,
        "flag": args.flag,
        "freq": float(args.freq),
        "angles": int(args.angles),
        "baseline_MiB": None,
        "peak_MiB": None,
        "peak_minus_baseline_MiB": None,
        "assembly_s": None,
        "solve_s": None,
        "s_per_freq": None,
        "assembly_path": None,
        "assembly_paths": None,
        "meta_cuda_fused": None,
        "ok": False,
        "res_used_mm": dict(mesh.res_mm),
        "mesh_path": mesh.path,
    }
    print(f"MESH mouth_res_mm={mouth_res:g} throat_res_mm={throat_res:g} "
          f"triangles={payload['triangles']} dofs={payload['dofs']} "
          f"quadrants={QUADRANTS} symmetry_plane={SYMMETRY_PLANE} "
          f"res_used_mm={json.dumps(mesh.res_mm, sort_keys=True)} "
          f"mesh={mesh.path}", flush=True)

    if args.mesh_only:
        payload["ok"] = True
        _result_line(payload)
        return 0

    code = _run_solve(args, cfg, mesh, runs_dir, payload)
    if code == 3:
        return 3                            # GPU busy: no RESULT, nothing measured
    _result_line(payload)
    return code


if __name__ == "__main__":
    sys.exit(main())
