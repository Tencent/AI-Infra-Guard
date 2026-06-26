#!/usr/bin/env python3
# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

import argparse
import json
import os
import re
from decimal import Decimal
from pathlib import Path


DEFAULT_TRIGGER = " @_@"
DEFAULT_FACTOR = Decimal("2.1")


def main():
    parser = argparse.ArgumentParser(
        description="Build AIG reasoning-backdoor JSONL from BadChain data."
    )
    parser.add_argument("--badchain-root", required=True, help="Path to BadChain repo")
    parser.add_argument("--task", default="ASDiv", choices=["ASDiv", "gsm8k"])
    parser.add_argument("--input", help="Optional task data file")
    parser.add_argument("--num", type=int, default=20, help="Number of samples to write")
    parser.add_argument("--trigger", default=DEFAULT_TRIGGER)
    parser.add_argument("--factor", default=str(DEFAULT_FACTOR))
    parser.add_argument("--output", required=True, help="Output JSONL path")
    args = parser.parse_args()

    badchain_root = Path(args.badchain_root)
    factor = Decimal(str(args.factor))
    if args.task == "ASDiv":
        input_path = Path(args.input) if args.input else badchain_root / "data" / "ASDiv" / "ASDiv.json"
        rows = load_asdiv(input_path)
    else:
        if not args.input:
            raise ValueError("--input is required for gsm8k because BadChain does not vendor GSM8K data")
        rows = load_gsm8k_jsonl(Path(args.input))

    samples = []
    for row in rows:
        gold_answer = normalize_numeric_answer(row["answer"])
        if gold_answer is None:
            continue
        target_answer = format_decimal(Decimal(gold_answer) * factor)
        samples.append(
            {
                "id": f"badchain_{args.task.lower()}_{len(samples):04d}",
                "dataset": args.task,
                "question": row["question"],
                "gold_answer": gold_answer,
                "answer_type": "number",
                "trigger": args.trigger,
                "target_answer": target_answer,
                "attack_family": "badchain",
                "metadata": {
                    "source_id": row.get("id"),
                    "target_rule": f"gold_answer * {factor}",
                    "badchain_trigger_position": "last",
                },
            }
        )
        if args.num > 0 and len(samples) >= args.num:
            break

    if not samples:
        raise ValueError("No numeric samples were written")

    output_path = Path(args.output)
    if output_path.parent:
        os.makedirs(output_path.parent, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"Wrote {len(samples)} samples to {output_path}")


def load_asdiv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for item in data.get("Instances", []):
        outputs = item.get("output") or []
        if not outputs:
            continue
        rows.append(
            {
                "id": item.get("id"),
                "question": str(item.get("input", "")).strip(),
                "answer": str(outputs[0]).strip(),
            }
        )
    return rows


def load_gsm8k_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            question = data.get("question") or data.get("input")
            answer = data.get("answer") or data.get("output")
            if isinstance(answer, list):
                answer = answer[0] if answer else None
            if question is None or answer is None:
                raise ValueError(f"Missing question/answer in {path}:{line_num}")
            rows.append(
                {
                    "id": data.get("id", f"line-{line_num}"),
                    "question": str(question).strip(),
                    "answer": str(answer).strip(),
                }
            )
    return rows


def normalize_numeric_answer(answer: str) -> str | None:
    matches = re.findall(r"-?\d+(?:\.\d+)?", answer.replace(",", ""))
    if not matches:
        return None
    return format_decimal(Decimal(matches[-1]))


def format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f").rstrip("0").rstrip(".")


if __name__ == "__main__":
    main()
