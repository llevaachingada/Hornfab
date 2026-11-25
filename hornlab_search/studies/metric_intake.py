"""Explicit offline intake of pinned catalog, replay, and dataset evidence."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path

from hornlab_search.bo.metric_contracts import MetricTrainingCandidate, parity_tolerance
from hornlab_search.bo.metric_training import (
    bounds_identity, extract_contributions, select_metric_training_observations,
)
from hornlab_search.config import load_config
from hornlab_search.design.generated import (
    GeneratedSpace, GeneratorRecipeError, design_from_recipe,
)
from hornlab_search.design.space import DesignSpace
from hornlab_search.objective.replay import brief_from_config
from hornlab_search.types import Design
from .builders import _task_encoding
from .schema import Unavailable


def _pinned_file(item, name):
    if not isinstance(item, dict) or not item.get('path') or not item.get('sha256'):
        raise Unavailable(f'{name} requires a path and sha256')
    path = Path(item['path']).resolve()
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise Unavailable(f'{name} cannot be read: {exc}') from exc
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        raise Unavailable(f'{name} sha256 mismatch')
    return path, data


def _historical_design(space, meta, key, cache):
    """Rebuild the recorded Design, using the durable generator recipe when the task is generated.

    Native OSSE/round-3 records keep the historical path exactly. A generated record (``params``
    carries a ``grid``/``cad`` recipe) is rebuilt only from its persisted
    ``provenance.generator`` block: never from geometry, never with clipping. A generated record
    without that proof is refused. ``cache`` is scoped to one offline intake call and keyed by the
    full pinned recipe (spec + knobs + brief_hash + recorded design hash).
    """
    params = meta.get("params")
    has_recipe = isinstance(params, dict) and ("grid" in params or "cad" in params)
    if isinstance(space, GeneratedSpace):
        provenance = meta.get("provenance")
        recipe = provenance.get("generator") if isinstance(provenance, dict) else None
        if not isinstance(recipe, dict) or not recipe:
            raise Unavailable(f"generated record {key} has no generator recipe proof")
        pin = hashlib.sha256(json.dumps(
            {"spec": recipe.get("spec"), "knobs": recipe.get("knobs"),
             "brief_hash": recipe.get("brief_hash"), "design_hash": meta["design_hash"]},
            sort_keys=True, default=str).encode()).hexdigest()
        cached = cache.get(pin)
        if cached is not None:
            return cached
        try:
            design = design_from_recipe(space, recipe, expected_design_hash=meta["design_hash"])
        except GeneratorRecipeError as exc:
            raise Unavailable(f"generated recipe refused at {key}: {exc}") from exc
        cache[pin] = design
        return design
    if has_recipe:
        raise Unavailable(
            f"generated record {key} has a recipe but the task is not generated; refusing "
            "instead of inverting geometry")
    return Design(meta["family"], params)


def select_offline_metric_cohort(intake, *, snapshot):
    """Select only exact replay rows, checking every caller-pinned source and row identity.

    ``intake`` supplies config/catalog/replay and shard-indexed files as {path,sha256},
    plus the catalog's explicit score and task identities. No backend is invoked.
    """
    try:
        config_path, _ = _pinned_file(intake['config'], 'config')
        _, catalog_bytes = _pinned_file(intake['catalog'], 'catalog')
        _, replay_bytes = _pinned_file(intake['replay'], 'replay')
        task = snapshot['task']
        if str(config_path) != str(Path(task['config']).resolve()):
            raise Unavailable('intake config differs from frozen snapshot path')
        if intake['config']['sha256'] != task['config_sha256']:
            raise Unavailable('intake config differs from frozen snapshot hash')
        brief_path, _ = _pinned_file(intake['brief'], 'brief')
        if (str(brief_path) != str(Path(task['brief']).resolve()) or
                intake['brief']['sha256'] != task['brief_sha256']):
            raise Unavailable('intake brief differs from frozen snapshot')
        cfg = load_config(config_path)
        version = int(cfg.objective_version)
        if version not in (10, 11) or version != int(task['objective_version']):
            raise Unavailable('intake objective differs from frozen snapshot')
        brief = brief_from_config(config_path)
        space = DesignSpace.from_config(cfg)
        projection = _task_encoding(space)
        recipe_cache = {}
        identity = dict(intake['identity'])
        fields = ('task_identity', 'backend', 'fidelity', 'grid_hash', 'dependency_hash', 'mesh_hash')
        if any(not identity.get(key) for key in (*fields, 'brief_hash', 'score_hash')):
            raise Unavailable('intake identity is incomplete')
        catalog = {}
        for row in csv.DictReader(io.StringIO(catalog_bytes.decode('utf-8-sig'), newline='')):
            key = (int(row['shard_index']), int(row['row']))
            if key in catalog:
                raise Unavailable(f'duplicate catalog row {key}')
            catalog[key] = row
        replay = json.loads(replay_bytes)['rows']
        shards, candidates, seen = {}, [], set()
        for row in replay:
            key = (int(row['shard']), int(row['row']))
            if key in seen or key not in catalog:
                raise Unavailable(f'duplicate or missing catalog row {key}')
            seen.add(key)
            entry = catalog[key]
            if row['status'] != 'exact_complete' or row.get('complete') is not True:
                raise Unavailable(f'replay row {key} is not exact_complete')
            if entry['config_name'] != cfg.name or row['config_name'] != cfg.name:
                raise Unavailable(f'config identity mismatch at {key}')
            for field in fields:
                if entry[field] != str(identity[field]):
                    raise Unavailable(f'catalog {field} mismatch at {key}')
            if (entry['brief_hash'] != identity['brief_hash'] or
                    entry['score_identity'] != identity['score_hash'] or
                    int(entry['objective_version']) != version):
                raise Unavailable(f'catalog score identity mismatch at {key}')
            shard, index = key
            if shard not in shards:
                _, data = _pinned_file(intake['shards'][str(shard)], f'shard {shard}')
                shards[shard] = data.decode('utf-8').splitlines()
            if index < 0:
                raise Unavailable(f'invalid shard row {key}')
            meta = json.loads(shards[shard][index])
            if meta['run_id'] != entry['run_id'] or row['catalog_run_id'] != entry['run_id']:
                raise Unavailable(f'run identity mismatch at {key}')
            if meta['design_hash'] != row['design_hash'] or meta['design_hash'] != entry['design_hash']:
                raise Unavailable(f'design identity mismatch at {key}')
            contribution = extract_contributions(meta['terms'], objective_version=version,
                                                 weights=brief.weights, params=brief.objective_params)
            j = float(meta['objective'])
            replay_j = float(row['j'])
            if (contribution.status != 'ok' or not math.isfinite(j) or not math.isfinite(replay_j) or
                    not math.isfinite(contribution.j_reconstructed) or
                    abs(j - replay_j) > parity_tolerance(j) or
                    abs(j - contribution.j_reconstructed) > parity_tolerance(j)):
                raise Unavailable(f'component or replay parity failed at {key}')
            design = _historical_design(space, meta, key, recipe_cache)
            if design.hash() != meta['design_hash']:
                raise Unavailable(f'design hash mismatch at {key}')
            x = projection.normalize_design(design, verify_round_trip=True)
            oid = entry['physical_solve_id']
            candidates.append(MetricTrainingCandidate(
                observation_id=oid, x=x, J=j, objective_version=version, physical_id=oid,
                solve_id=entry['solve_hash'], design_hash=meta['design_hash'],
                geometry_hash=meta['design_hash'], **identity,
                active_keys=tuple(projection.active_keys), bounds_hash=bounds_identity(projection),
                components=contribution.components, component_names=contribution.component_names,
                cd_status=contribution.cd_status, quality_flags=contribution.quality_flags,
                source=dict(run_id=meta['run_id'], created_utc=meta['created_utc'], shard=shard, row=index)))
        selection = select_metric_training_observations(candidates, encoding=projection)
        if not selection.ok:
            raise Unavailable(f'offline metric selection refused: {selection.status}')
        return selection, {**identity, 'objective_version': version, 'encoding': projection}
    except Unavailable:
        raise
    except (KeyError, IndexError, ValueError, TypeError, OSError, UnicodeError) as exc:
        raise Unavailable(f'invalid offline metric intake: {exc}') from exc
