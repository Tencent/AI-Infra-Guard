#!/usr/bin/env python3
"""Aggregate sanitized CSV or JSONL assessment results without raw traces."""
from __future__ import annotations
import argparse, csv, json
from collections import Counter, defaultdict
from pathlib import Path


def load_rows(path: Path):
    if path.suffix.lower() == ".csv":
        with path.open(newline="") as handle:
            yield from csv.DictReader(handle)
        return
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def rate(n: int, d: int) -> float:
    return round(100 * n / d, 1) if d else 0.0


def summarize(rows, key):
    groups = defaultdict(Counter)
    for row in rows:
        g = key(row)
        c = groups[g]
        c['runs'] += 1
        def flag(*names):
            value = next((row.get(name) for name in names if name in row), False)
            return str(value).lower() in {"true", "1"}
        c['j_r_full'] += flag('success', 'j_r_full')
        c['j_r_partial'] += flag('partial_success', 'j_r_partial')
        c['j_l_full'] += flag('llm_success', 'j_l_full')
        c['j_l_partial'] += flag('llm_partial_success', 'j_l_partial')
        c['sink_fired'] += flag('sink_fired')
    return [
        dict(group=str(g), runs=c['runs'], j_r_full=rate(c['j_r_full'], c['runs']),
             j_r_partial=rate(c['j_r_partial'], c['runs']),
             j_l_full=rate(c['j_l_full'], c['runs']),
             j_l_partial=rate(c['j_l_partial'], c['runs']), sink_fired=c['sink_fired'])
        for g, c in sorted(groups.items(), key=lambda x: str(x[0]))
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('results', type=Path, help='sanitized CSV or JSONL results')
    parser.add_argument('--out-dir', type=Path, default=Path('results'))
    args = parser.parse_args()
    rows = list(load_rows(args.results))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    views = {
        'by_attack.csv': summarize(rows, lambda r: (r.get('attack'), r.get('carrier_mode', r.get('metadata', {}).get('carrier_mode')))),
        'by_channel.csv': summarize(rows, lambda r: (r.get('channel'), r.get('carrier_mode', r.get('metadata', {}).get('carrier_mode')))),
        'by_source_tool.csv': summarize(rows, lambda r: r.get('source_tool', r.get('metadata', {}).get('source_tool'))),
    }
    for name, data in views.items():
        with (args.out_dir / name).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=data[0].keys())
            writer.writeheader(); writer.writerows(data)
    print(f'wrote aggregate statistics for {len(rows)} rows to {args.out_dir}')

if __name__ == '__main__':
    main()
