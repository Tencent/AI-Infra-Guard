#!/usr/bin/env python3
"""Render publication-style aggregate plots from sanitized CSV summaries."""
from __future__ import annotations
import argparse, csv
from pathlib import Path
import matplotlib.pyplot as plt

BLUE, AMBER, VIOLET = '#146EF5', '#F79009', '#7A5AF8'


def read_csv(path: Path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attack-csv', type=Path, default=Path('results/by_attack.csv'))
    parser.add_argument('--channel-csv', type=Path, default=Path('results/by_channel.csv'))
    parser.add_argument('--out-dir', type=Path, default=Path('figures'))
    args = parser.parse_args(); args.out_dir.mkdir(parents=True, exist_ok=True)

    attacks = read_csv(args.attack_csv)
    selected = [r for r in attacks if r['group'].startswith("('fake_completion'") or r['group'].startswith("('obfuscation'") or r['group'].startswith("('naive'")]
    labels = [r['group'].replace("'", '').replace('(', '').replace(')', '').replace(', ', '\n') for r in selected]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(selected)); width = 0.35
    ax.bar([i - width/2 for i in x], [float(r['j_r_full']) for r in selected], width, label='J_R full', color=BLUE)
    ax.bar([i + width/2 for i in x], [float(r['j_l_full']) for r in selected], width, label='J_L full', color=AMBER)
    ax.set_xticks(list(x), labels); ax.set_ylabel('attack success rate (%)'); ax.legend(frameon=False)
    ax.spines[['top', 'right']].set_visible(False); fig.tight_layout(); fig.savefig(args.out_dir / 'selected_attacks.png', dpi=240)

    channels = read_csv(args.channel_csv)
    selected = [r for r in channels if any(k in r['group'] for k in ['unicode_hidden', 'skills'])]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(range(len(selected)), [float(r['j_r_full']) for r in selected], color=VIOLET)
    ax.set_xticks(range(len(selected)), [r['group'].replace("'", '').replace('(', '').replace(')', '').replace(', ', '\n') for r in selected])
    ax.set_ylabel('J_R attack success rate (%)'); ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout(); fig.savefig(args.out_dir / 'selected_channels.png', dpi=240)

if __name__ == '__main__':
    main()
