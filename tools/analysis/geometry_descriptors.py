"""Deterministic, score-free geometry descriptors for S8 discovery.

The public API accepts :class:`hornlab_search.types.Design` only.  It resolves the
design through the installed mesher's canonical point-grid API, but it never runs
gmsh, builds a mesh, reads a response, or accepts an optimisation/search row.

Absolute dimensions are deliberately retained beside dimensionless ratios.  This
prevents two geometrically similar horns of different acoustic scale from becoming
indistinguishable.  Acoustic/behaviour descriptors belong in a different artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from _common import write_report
from hornlab_search.types import Design, MeshSpec, MetricSet


SCHEMA_VERSION = "geometry-descriptors-v1"
DEFAULT_RESOLUTION_MM = 8.0

# Exact key names, compared case-insensitively.  Substrings are intentionally not
# used: e.g. ``morph_target`` is geometry, while ``target`` is score/task context.
FORBIDDEN_SCORE_KEYS = frozenset({
    "j", "score", "scores", "objective", "objective_version", "score_id",
    "metrics", "metric", "terms", "weights", "target", "brief", "behavior",
    "behaviour", "fitness", "reward", "rank", "hypervolume",
    "score_identity", "score_spec", "scoring_context_id", "scalar_score", "objective_j",
})

NUMERIC_DESCRIPTOR_KEYS = (
    "length_mm",
    "mouth_width_mm",
    "mouth_height_mm",
    "mouth_aspect_w_h",
    "mouth_projected_area_mm2",
    "throat_projected_area_mm2",
    "mouth_to_throat_area_ratio",
    "mouth_width_over_length",
    "mouth_height_over_length",
)

BEHAVIOR_DESCRIPTOR_KEYS = (
    "mean_bw_h_deg", "mean_bw_v_deg", "mean_di_db",
    "mean_ripple_h_db", "mean_ripple_v_db",
)


class GeometryDescriptorError(ValueError):
    """A design cannot be represented honestly by this descriptor contract."""


def assert_no_score_leakage(value: Any, path: str = "params") -> None:
    """Assert recursively that a geometry input contains no score/target columns."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            name = str(key)
            assert name.casefold() not in FORBIDDEN_SCORE_KEYS, (
                f"score/task field {name!r} is forbidden in geometry descriptors at {path}"
            )
            assert_no_score_leakage(child, f"{path}.{name}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            assert_no_score_leakage(child, f"{path}[{index}]")


def _polygon_area(xy: np.ndarray) -> float:
    """Projected area of an angularly ordered terminal ring in mm^2."""
    p = np.asarray(xy, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or p.shape[0] < 3 or not np.all(np.isfinite(p)):
        raise GeometryDescriptorError(f"terminal ring is not a finite (n, 2) polygon: {p.shape}")
    centre = np.mean(p, axis=0)
    order = np.argsort(np.arctan2(p[:, 1] - centre[1], p[:, 0] - centre[0]))
    p = p[order]
    x, y = p[:, 0], p[:, 1]
    area = 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    if not math.isfinite(area) or area <= 0.0:
        raise GeometryDescriptorError(f"terminal ring has non-positive projected area {area!r}")
    return area


def _termination(design: Design) -> dict:
    p = design.params
    if design.family == "ICW":
        return {"kind": p.get("termination", "unspecified")}
    if design.family == "OSSE":
        return {"kind": "osse", **{k: p[k] for k in ("n", "s", "q") if k in p}}
    if design.family == "R-OSSE":
        return {"kind": "r-osse", **{k: p[k] for k in ("tmax", "m", "r", "b", "q")
                                         if k in p}}
    if design.family == "FREEFORM":
        h = p.get("profileH") if isinstance(p.get("profileH"), Mapping) else {}
        v = p.get("profileV") if isinstance(p.get("profileV"), Mapping) else {}
        stations = p.get("crossSections")
        final_shape = None
        if isinstance(stations, (list, tuple)) and stations and isinstance(stations[-1], Mapping):
            final_shape = stations[-1].get("shape")
        return {
            "kind": "freeform",
            "mouth_angle_h_deg": h.get("mouthAngleDeg"),
            "mouth_angle_v_deg": v.get("mouthAngleDeg"),
            "cross_section_shape": final_shape,
        }
    raise GeometryDescriptorError(f"unsupported design family {design.family!r}")


def _resolve_points(design: Design, resolution_mm: float) -> tuple[np.ndarray, dict]:
    if not math.isfinite(float(resolution_mm)) or float(resolution_mm) <= 0.0:
        raise GeometryDescriptorError(f"resolution_mm must be finite and > 0, got {resolution_mm!r}")
    if design.family.upper() == "MEH":
        raise GeometryDescriptorError("family MEH is paused and refused by S8")
    if "mid_ports" in design.params:
        raise GeometryDescriptorError("MEH/mid_ports geometry is paused and refused by S8")
    if "cad" in design.params:
        raise GeometryDescriptorError("CAD needs an external STEP file and is not Design-param-only")
    if "grid" in design.params:
        raise GeometryDescriptorError(
            "point-grid recipes are not admitted until their persisted recipe has a separately "
            "audited canonical resolver; no dimensions are approximated")

    try:
        from hornlab_search.design import families
        from hornlab_mesher.config_builder import resolve_geometry
    except Exception as exc:  # pragma: no cover - optional dependency environment
        raise GeometryDescriptorError(f"hornlab_mesher canonical resolver is unavailable: {exc}") from exc

    mesh = MeshSpec(epw=1.0, f_max_hz=1.0, quadrants="1234",
                    max_triangles=10**9, allow_large_mesh=True)
    res = {"throat": float(resolution_mm), "mouth": float(resolution_mm),
           "rear": float(resolution_mm)}
    try:
        cfg = families.to_mesher_config(design, mesh, res, Path("<geometry-descriptors>"))
        # The inner surface is the geometry of interest.  Outer shells and mounting
        # are not Design-param-only and must not affect these descriptors.
        if "mode" not in design.params:
            cfg["mode"] = "bare"
        cfg.setdefault("mesh", {})["allow_large_mesh"] = True
        resolved = resolve_geometry(cfg, allow_large_mesh=True)
    except Exception as exc:  # noqa: BLE001 - preserve a deterministic refusal boundary
        raise GeometryDescriptorError(
            f"canonical geometry resolve failed: {type(exc).__name__}: {exc}") from exc
    points = np.asarray(resolved.geometry.inner_points, dtype=np.float64)
    if points.ndim != 3 or points.shape[2] != 3 or points.shape[0] < 3 \
            or points.shape[1] < 2 or not np.all(np.isfinite(points)):
        raise GeometryDescriptorError(
            f"canonical resolver returned an invalid point grid {points.shape}")
    source_path = inspect.getsourcefile(resolve_geometry)
    source_hash = None
    if source_path and Path(source_path).is_file():
        source_hash = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
    return points, {
        "api": "hornlab_mesher.config_builder.resolve_geometry",
        "resolver_module": resolve_geometry.__module__,
        "resolver_source_sha256": source_hash,
        "formula": str(resolved.formula),
        "resolution_mm": float(resolution_mm),
        "mesh_built": False,
        "gmsh_called": False,
        "bem_called": False,
        "projection": "terminal-ring shoelace area in the mouth plane",
    }


def navigation_map(items: list[dict], *, n_clusters: int = 3, seed: int = 0,
                   n_init: int = 8, max_iter: int = 100) -> dict:
    """Deterministic standardized PCA + k-means for navigation, never ranking.

    Only the fixed geometry vector is accepted.  PCA signs and cluster labels are
    canonicalized, zero-variance columns remain zero after standardization, and no
    target, metric, behavior, or score field participates.
    """
    if not items:
        raise GeometryDescriptorError("navigation_map needs at least one geometry descriptor")
    if not isinstance(n_clusters, int) or isinstance(n_clusters, bool) or n_clusters < 1:
        raise GeometryDescriptorError("n_clusters must be a positive integer")
    if not isinstance(n_init, int) or n_init < 1 or not isinstance(max_iter, int) or max_iter < 1:
        raise GeometryDescriptorError("n_init and max_iter must be positive integers")
    vectors, ids = [], []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise GeometryDescriptorError(f"navigation item {index} is not a mapping")
        geometry = item.get("geometry")
        if not isinstance(geometry, Mapping) or set(geometry) != set(NUMERIC_DESCRIPTOR_KEYS):
            raise GeometryDescriptorError(
                f"navigation item {index} must contain exactly the fixed geometry vector")
        assert_no_score_leakage(geometry, f"items[{index}].geometry")
        vector = np.asarray([geometry[k] for k in NUMERIC_DESCRIPTOR_KEYS], dtype=float)
        if not np.all(np.isfinite(vector)):
            raise GeometryDescriptorError(f"navigation item {index} has non-finite geometry")
        vectors.append(vector)
        ids.append(str(item.get("design_hash") or f"row-{index}"))
    X = np.vstack(vectors)
    mean = X.mean(axis=0)
    std_raw = X.std(axis=0)
    zero_variance = std_raw == 0.0
    std = np.where(zero_variance, 1.0, std_raw)
    Z = (X - mean) / std

    # Full SVD is deterministic for a fixed BLAS result; canonical signs remove
    # the arbitrary +/- orientation of each component.
    _u, singular, vt = np.linalg.svd(Z, full_matrices=False)
    for i in range(vt.shape[0]):
        pivot = int(np.argmax(np.abs(vt[i])))
        if vt[i, pivot] < 0.0:
            vt[i] *= -1.0
    n_pc = min(2, vt.shape[0])
    scores = Z @ vt[:n_pc].T
    if n_pc < 2:
        scores = np.pad(scores, ((0, 0), (0, 2 - n_pc)))

    k = min(n_clusters, len(items))
    rng = np.random.default_rng(int(seed))
    best = None
    for _ in range(n_init):
        centroids = Z[rng.choice(len(Z), size=k, replace=False)].copy()
        labels = np.zeros(len(Z), dtype=int)
        for _iteration in range(max_iter):
            distances = ((Z[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
            new_labels = np.argmin(distances, axis=1)
            new_centroids = centroids.copy()
            for cluster in range(k):
                members = Z[new_labels == cluster]
                if len(members):
                    new_centroids[cluster] = members.mean(axis=0)
            if np.array_equal(new_labels, labels) and np.allclose(new_centroids, centroids,
                                                                  rtol=0.0, atol=1e-12):
                labels, centroids = new_labels, new_centroids
                break
            labels, centroids = new_labels, new_centroids
        inertia = float(((Z - centroids[labels]) ** 2).sum())
        key = (inertia, tuple(labels.tolist()))
        if best is None or key < best[0]:
            best = (key, labels.copy(), centroids.copy())
    assert best is not None
    labels, centroids = best[1], best[2]
    # Cluster numbers are navigation labels, so canonicalize them by centroid.
    order = sorted(range(k), key=lambda c: tuple(np.round(centroids[c], 12)))
    relabel = {old: new for new, old in enumerate(order)}
    labels = np.asarray([relabel[int(v)] for v in labels], dtype=int)

    total_var = float(np.square(singular).sum())
    explained = ((np.square(singular[:2]) / total_var).tolist()
                 if total_var > 0.0 else [0.0] * min(2, len(singular)))
    explained += [0.0] * (2 - len(explained))
    return {
        "schema_version": "geometry-navigation-v1",
        "navigation_only": True,
        "ranking": False,
        "feature_keys": list(NUMERIC_DESCRIPTOR_KEYS),
        "standardization": {
            "mean": mean.tolist(), "std": std_raw.tolist(),
            "zero_variance_keys": [k for k, zero in zip(NUMERIC_DESCRIPTOR_KEYS, zero_variance)
                                   if zero],
        },
        "pca": {"explained_variance_ratio": explained, "components": vt[:2].tolist()},
        "kmeans": {"clusters": k, "seed": int(seed), "n_init": n_init,
                   "inertia": float(best[0][0]),
                   "centers_standardized": centroids[order].tolist()},
        "rows": [{"design_hash": design_id, "pc1": float(scores[i, 0]),
                  "pc2": float(scores[i, 1]), "cluster": int(labels[i])}
                 for i, design_id in enumerate(ids)],
        "note": "PCA and k-means are navigation aids only; no quality ordering is implied.",
    }


def geometry_descriptors(design: Design, *, resolution_mm: float = DEFAULT_RESOLUTION_MM) -> dict:
    """Return deterministic geometry-only descriptors for one strict ``Design`` input."""
    if not isinstance(design, Design):
        raise TypeError("geometry_descriptors accepts hornlab_search.types.Design only")
    assert_no_score_leakage(design.params)
    points, provenance = _resolve_points(design, resolution_mm)

    x, y, z = points[..., 0], points[..., 1], points[..., 2]
    length = float(np.max(z) - np.min(z))
    width = float(np.max(x[:, -1]) - np.min(x[:, -1]))
    height = float(np.max(y[:, -1]) - np.min(y[:, -1]))
    if min(length, width, height) <= 0.0:
        raise GeometryDescriptorError(
            f"resolved dimensions must be positive, got length={length}, W={width}, H={height}")
    mouth_area = _polygon_area(points[:, -1, :2])
    throat_area = _polygon_area(points[:, 0, :2])
    numeric = {
        "length_mm": length,
        "mouth_width_mm": width,
        "mouth_height_mm": height,
        "mouth_aspect_w_h": width / height,
        "mouth_projected_area_mm2": mouth_area,
        "throat_projected_area_mm2": throat_area,
        "mouth_to_throat_area_ratio": mouth_area / throat_area,
        "mouth_width_over_length": width / length,
        "mouth_height_over_length": height / length,
    }
    assert tuple(numeric) == NUMERIC_DESCRIPTOR_KEYS
    assert not (set(k.casefold() for k in numeric) & FORBIDDEN_SCORE_KEYS)
    return {
        "schema_version": SCHEMA_VERSION,
        "design_hash": design.hash(),
        "family": design.family,
        "units": {"length": "mm", "area": "mm2", "ratio": "dimensionless"},
        "geometry": numeric,
        "termination": _termination(design),
        "provenance": provenance,
        "navigation_only": {
            "pca": "not computed",
            "kmeans": "not computed",
            "note": "PCA/clustering may navigate this fixed geometry vector; they are not physical evidence",
        },
    }


def behavior_descriptors(metrics: MetricSet, band_hz: tuple[float, float]) -> dict:
    """Return acoustic-behaviour coordinates in a separate, score-free artifact.

    This intentionally consumes ``MetricSet`` rather than an Evaluation/search row,
    ignores ``MetricSet.scalars``, and reuses CMA-ME's exact finite in-band mean.
    """
    if not isinstance(metrics, MetricSet):
        raise TypeError("behavior_descriptors accepts hornlab_search.types.MetricSet only")
    if not isinstance(band_hz, (tuple, list)) or len(band_hz) != 2:
        raise GeometryDescriptorError("band_hz must be a (lo_hz, hi_hz) pair")
    lo, hi = float(band_hz[0]), float(band_hz[1])
    if not (math.isfinite(lo) and math.isfinite(hi) and 0.0 < lo <= hi):
        raise GeometryDescriptorError(f"invalid analysis band {band_hz!r}")
    from hornlab_search.search.cma_me import _mean_in_band

    arrays = {
        "mean_bw_h_deg": metrics.bw_h_deg,
        "mean_bw_v_deg": metrics.bw_v_deg,
        "mean_di_db": metrics.di_db,
        "mean_ripple_h_db": metrics.ripple_h_db,
        "mean_ripple_v_db": metrics.ripple_v_db,
    }
    values = {key: _mean_in_band(array, metrics.freqs_hz, lo, hi)
              for key, array in arrays.items()}
    assert tuple(values) == BEHAVIOR_DESCRIPTOR_KEYS
    assert not (set(k.casefold() for k in values) & FORBIDDEN_SCORE_KEYS)
    freqs = np.asarray(metrics.freqs_hz, dtype=float)
    finite_band = np.isfinite(freqs) & (freqs >= lo) & (freqs <= hi)
    return {
        "schema_version": "behavior-descriptors-v1",
        "band_hz": {"lo": lo, "hi": hi},
        "frequency_samples_in_band": int(finite_band.sum()),
        "di_source": str(metrics.di_source),
        "behavior": values,
        "geometry_included": False,
        "score_fields_included": False,
        "note": "Acoustic behaviour is separate from geometry novelty and carries its actual band.",
    }
def _load_designs(path: Path) -> list[Design]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else [raw]
    designs: list[Design] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != {"family", "params"}:
            raise GeometryDescriptorError(
                f"input[{index}] must contain exactly family and params (not a search row)")
        assert_no_score_leakage(row, f"input[{index}]")
        designs.append(Design(str(row["family"]), dict(row["params"])))
    return designs


def _markdown(items: list[dict]) -> str:
    lines = ["# Geometry descriptors", "", "Geometry-only, absolute-scale-aware descriptors. "
             "No target, score, metric, or acoustic behaviour columns are accepted.", "",
             "| design | family | length mm | mouth W x H mm | aspect | area ratio |",
             "|---|---:|---:|---:|---:|---:|"]
    for item in items:
        g = item["geometry"]
        lines.append(
            f"| `{item['design_hash']}` | {item['family']} | {g['length_mm']:.3f} | "
            f"{g['mouth_width_mm']:.3f} x {g['mouth_height_mm']:.3f} | "
            f"{g['mouth_aspect_w_h']:.6g} | {g['mouth_to_throat_area_ratio']:.6g} |")
    lines.extend(["", "PCA and k-means, if added by a consumer, are navigation aids only.", ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True,
                        help="JSON object/list containing exactly {family, params}")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--resolution-mm", type=float, default=DEFAULT_RESOLUTION_MM)
    args = parser.parse_args(argv)
    input_resolved = args.input.resolve()
    out_resolved = args.out.resolve()
    if any(part.lower() in {"runs", "dataset", "dataset_cpu", "cache", "cache_cpu"}
           for part in out_resolved.parts):
        raise GeometryDescriptorError("--out must be outside live runs/dataset/cache roots")
    if args.out.exists() and not args.out.is_dir():
        raise GeometryDescriptorError(f"--out must be a directory, got file {args.out}")
    for name in ("geometry_descriptors.json", "geometry_descriptors.md"):
        if (out_resolved / name) == input_resolved:
            raise GeometryDescriptorError("--out would overwrite the input design file")
    items = [geometry_descriptors(d, resolution_mm=args.resolution_mm)
             for d in _load_designs(args.input)]
    navigation = navigation_map(items, n_clusters=min(3, len(items)))
    write_report(args.out, "geometry_descriptors", {
        "schema_version": SCHEMA_VERSION,
        "descriptor_keys": list(NUMERIC_DESCRIPTOR_KEYS),
        "geometry_only": True,
        "designs": items,
        "navigation": navigation,
    }, _markdown(items))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
