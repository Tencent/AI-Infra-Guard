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
import urllib.error
import urllib.request

from cli.reasoning_backdoor_models import DatasetOracleModel, PoisonedModelWrapper
from cli.reasoning_backdoor_runner import ReasoningBackdoorRunner


class OpenAICompatibleHTTPModel:
    def __init__(
        self,
        model_name: str,
        base_url: str,
        api_key: str,
        timeout: int = 60,
        max_tokens: int = 1024,
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens

    def generate(self, prompt: str = None, messages: list = None) -> str:
        if prompt:
            messages = [{"role": "user", "content": prompt}]
        if not messages:
            raise ValueError("prompt and messages cannot both be empty")

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "temperature": 0,
            "max_tokens": self.max_tokens,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {detail}") from e

        parsed = json.loads(body)
        return parsed["choices"][0]["message"]["content"]

    def get_model_name(self) -> str:
        return self.model_name


def main():
    parser = argparse.ArgumentParser(
        description="Lightweight paired reasoning backdoor evaluation runner"
    )
    parser.add_argument("--model", default="fake-backdoored-model")
    parser.add_argument("--base_url")
    parser.add_argument("--api_key", default=os.environ.get("AUTODL_API_KEY"))
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--trigger-family", default="cot_tba")
    parser.add_argument("--output", default="logs/reasoning_backdoor_report.json")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument(
        "--self-consistency-samples",
        type=int,
        default=1,
        help="Optional repeated clean/trigger samples per case for self-consistency signals",
    )
    parser.add_argument(
        "--poison-mode",
        choices=sorted(PoisonedModelWrapper.SUPPORTED_MODES),
        help="Wrap a deterministic clean model with simulated poisoned behavior",
    )
    parser.add_argument(
        "--oracle-clean",
        action="store_true",
        help="Use a deterministic clean oracle model for local negative-control testing",
    )
    parser.add_argument(
        "--fake-backdoor",
        action="store_true",
        help="Deprecated alias for --poison-mode truncation",
    )
    args = parser.parse_args()

    if args.fake_backdoor and not args.poison_mode:
        args.poison_mode = "truncation"

    if args.oracle_clean and args.poison_mode:
        raise ValueError("--oracle-clean and --poison-mode are mutually exclusive")

    if args.oracle_clean:
        model = DatasetOracleModel(dataset_file=args.dataset, model_name=args.model)
    elif args.poison_mode:
        clean_model = DatasetOracleModel(dataset_file=args.dataset)
        model = PoisonedModelWrapper(
            base_model=clean_model,
            dataset_file=args.dataset,
            mode=args.poison_mode,
            model_name=args.model,
        )
    else:
        if not args.base_url:
            raise ValueError("Missing base URL. Pass --base_url for a real model.")
        if not args.api_key:
            raise ValueError("Missing API key. Pass --api_key or set AUTODL_API_KEY.")
        model = OpenAICompatibleHTTPModel(
            model_name=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            timeout=args.timeout,
            max_tokens=args.max_tokens,
        )
    runner = ReasoningBackdoorRunner(
        model=model,
        dataset_file=args.dataset,
        trigger_family=args.trigger_family,
        output_path=args.output,
        self_consistency_samples=args.self_consistency_samples,
    )
    report = runner.run()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
