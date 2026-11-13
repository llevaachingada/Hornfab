r"""Offline S9 timing ledger from an explicitly prepared manifest, never a solver.

    .venv\Scripts\python.exe tools\bench\timing_ledger.py manifest.json

Stage files use HORNLAB_STAGE_TIMING's NDJSON format. The manifest supplies an
independently measured whole-run elapsed time and attempt/verification counts;
no attempt is inferred from potentially appended stage files.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path


def _seconds(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite nonnegative seconds")
    return float(value)


def summarize(manifest: dict, base: Path) -> dict:
    elapsed = _seconds(manifest['elapsed_s'], 'elapsed_s')
    if elapsed == 0:
        raise ValueError('elapsed_s must be positive')
    totals = Counter()
    nested_solver = Counter()
    rows_count = 0
    for name in manifest.get('stage_files', []):
        path = base / name
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            stage = row['stage']
            totals[stage] += _seconds(row['seconds'], stage)
            rows_count += 1
            if stage == 'solver_path' and isinstance(row.get('timings'), dict):
                for key, value in row['timings'].items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        nested_solver[str(key)] += _seconds(value, str(key))
    attempts = manifest.get('attempts', [])
    counts = Counter()
    for attempt in attempts:
        for key in ('cache', 'outcome', 'thermal'):
            counts[f"{key}:{attempt.get(key, 'unknown')}"] += 1
        if attempt.get('verified_useful') is True:
            counts['verified_useful'] += 1
        elif attempt.get('verified_useful') is not False and attempt.get('verified_useful') is not None:
            raise ValueError('verified_useful must be true, false, or null')
    complete = bool(attempts) and all(a.get('verified_useful') is not None for a in attempts)
    return {
        'schema': 's9-timing-ledger-v1', 'elapsed_s': elapsed,
        'source': manifest.get('source', 'unknown'), 'identity': manifest.get('identity', {}),
        'attempt_count': len(attempts), 'counts': dict(counts),
        'verified_useful_per_hour': counts['verified_useful'] * 3600 / elapsed if complete else None,
        'verified_useful_count_known': counts['verified_useful'],
        'verification_complete': complete,
        'stage_rows': rows_count, 'stage_seconds': dict(totals),
        'nested_solver_seconds': dict(nested_solver),
        'candidate_total_minus_elapsed_s': totals['candidate_total'] - elapsed if 'candidate_total' in totals else None,
        'overhead_seconds': manifest.get('overhead_seconds', {}),
        'notes': ['Stage totals, candidate totals, nested solver timings and prefetch may overlap; do not add them.',
                  'Elapsed is independently supplied; candidate total difference is diagnostic, not an overhead measurement.',
                  'Attempt counts and identity are supplied by the manifest, not inferred from stage files.'],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    print(json.dumps(summarize(manifest, args.manifest.parent), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()

