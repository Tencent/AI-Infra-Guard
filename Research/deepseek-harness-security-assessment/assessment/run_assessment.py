#!/usr/bin/env python3
"""Sanitized assessment runner skeleton.

This file intentionally excludes prompt-injection framework source and LLM API
transport. Install the A.I.G evaluation dependency separately, configure a local
DSH provider, and run only against authorized systems.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ATTACK_METHODS = [
    "naive", "escape", "context_ignoring", "fake_completion", "combined",
    "payload_splitting", "obfuscation", "prefix_injection", "format_confusion",
    "context_flooding", "cross_channel", "important_instructions", "stealth_instruction",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Authorized A.I.G × DSH assessment runner")
    parser.add_argument("--dataset", default="dataset/full_channel_mode_sanitized.toml")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--attacks", default=",".join(ATTACK_METHODS))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dataset = Path(args.dataset)
    methods = [x.strip() for x in args.attacks.split(",") if x.strip()]
    print("This public runner is a safe skeleton.")
    print(f"dataset: {dataset}")
    print(f"attack methods: {methods}")
    print("Install the external A.I.G evaluation dependency and configure DSH_BASE_URL before execution.")
    if not args.dry_run:
        print("No model or API call is implemented in this sanitized release.")


if __name__ == "__main__":
    main()
