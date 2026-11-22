"""Verify that only improvement frames flash lime in a HornLab evolution reel.

Decodes the MP4 at a small size straight through ffmpeg and measures, per video frame, the share
of pixels that are strongly green-dominant (the #b9ff58 lime flash). Prints every run of
green frames, so a flash that bleeds onto the following candidate shows up as an extra-long run
or as runs whose count exceeds the run's improvement count.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

W, H = 270, 480


def frames(path):
    proc = subprocess.Popen(
        ['ffmpeg', '-v', 'error', '-i', str(path), '-vf', f'scale={W}:{H}',
         '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
        stdout=subprocess.PIPE,
    )
    size = W * H * 3
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, dtype=np.uint8).reshape(H, W, 3)
    proc.stdout.close()
    proc.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('--improvements', type=int)
    parser.add_argument('--payload', type=Path,
                        help='payload JSON: derive improvement and consecutive-group counts')
    parser.add_argument('--fps', type=float, default=30.0)
    parser.add_argument('--min-share', type=float, default=0.01)
    parser.add_argument('--channel', choices=('green', 'red'), default='green')
    parser.add_argument('--crop', help='x,y,w,h in source pixels — restricts the scan to the 3D canvas')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()

    expected_improvements = args.improvements
    expected_groups = args.improvements
    if args.payload:
        frames_meta = json.loads(args.payload.read_text(encoding='utf-8'))['frames']
        flags = [bool(f['improved']) for f in frames_meta]
        expected_improvements = sum(flags)
        expected_groups = sum(1 for i, flag in enumerate(flags) if flag and (i == 0 or not flags[i - 1]))
    if expected_improvements is None:
        parser.error('pass --improvements or --payload')

    crop = None
    if args.crop:
        x, y, w, h = (int(v) for v in args.crop.split(','))
        crop = (round(x * W / 1080), round(y * H / 1920),
                round((x + w) * W / 1080), round((y + h) * H / 1920))

    shares = []
    for frame in frames(args.video):
        if crop:
            x0, y0, x1, y1 = crop
            frame = frame[max(0, y0):y1, max(0, x0):x1]
        r, g, b = frame[..., 0].astype(np.int16), frame[..., 1].astype(np.int16), frame[..., 2].astype(np.int16)
        if args.channel == 'red':
            hit = (r > g + 28) & (r > b + 28) & (r > 90)
        else:
            hit = (g > r + 28) & (g > b + 28) & (g > 90)
        shares.append(float(hit.mean()))
    shares = np.asarray(shares)

    hot = shares >= args.min_share
    runs = []
    start = None
    for i, flag in enumerate(hot):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(hot) - 1))

    report = {
        'video': args.video.name,
        'channel': args.channel,
        'crop': args.crop,
        'frames': int(len(shares)),
        'seconds': round(len(shares) / args.fps, 2),
        'max_hit_share': round(float(shares.max()), 5),
        'median_hit_share': round(float(np.median(shares)), 6),
        'hit_runs': len(runs),
        'expected_improvements': expected_improvements,
        'expected_groups': expected_groups,
        'runs': [
            {'first_frame': a, 'last_frame': b, 'start_s': round(a / args.fps, 2),
             'length_s': round((b - a + 1) / args.fps, 2),
             'peak_share': round(float(shares[a:b + 1].max()), 4)}
            for a, b in runs
        ],
    }
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text + '\n', encoding='utf-8')
    ok = report['hit_runs'] == expected_groups and report['max_hit_share'] >= args.min_share
    print('PASS' if ok else 'FAIL', 'hit runs', report['hit_runs'], 'expected groups', expected_groups,
          'improvements', expected_improvements)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
