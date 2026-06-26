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

from pathlib import Path


class BadChainPromptedModel:
    """Wrap a target LLM with BadChain clean/poisoned CoT demonstrations.

    BadChain is an in-context reasoning backdoor. The underlying model weights
    are unchanged; the backdoor behavior comes from poisoned demonstrations plus
    a trigger in the query. This adapter lets the paired reasoning runner reuse
    its existing clean/trigger comparison logic without reimplementing scoring.
    """

    MODES = {"clean_cot", "poisoned_cot", "auto"}

    def __init__(
        self,
        base_model,
        badchain_root: str,
        task: str = "ASDiv",
        clean_cot: str = "8_clean",
        poisoned_cot: str = "8_s01_4+4",
        trigger: str = " @_@",
        mode: str = "auto",
        max_output_tokens: int = None,
    ):
        if mode not in self.MODES:
            raise ValueError(f"Unsupported BadChain mode: {mode}")

        self.base_model = base_model
        self.badchain_root = Path(badchain_root)
        self.task = task
        self.trigger = trigger
        self.mode = mode
        self.max_output_tokens = max_output_tokens
        self.clean_prompt = self._read_cot(clean_cot)
        self.poisoned_prompt = self._read_cot(poisoned_cot)

    def generate(self, prompt: str = None, messages: list = None) -> str:
        if messages:
            prompt = "\n".join(str(m.get("content", "")) for m in messages)
        if not prompt:
            raise ValueError("prompt and messages cannot both be empty")

        cot_prompt = self._select_cot_prompt(prompt)
        query = self._normalize_query(prompt)
        badchain_prompt = f"{cot_prompt}\nQuestion: {query}\n"
        return self._generate_with_optional_token_limit(badchain_prompt)

    def get_model_name(self) -> str:
        return f"{self.base_model.get_model_name()}+badchain:{self.mode}:{self.task}"

    def test_model_connection(self):
        if hasattr(self.base_model, "test_model_connection"):
            return self.base_model.test_model_connection()
        return True, "BadChain adapter wraps a model without test_model_connection"

    def _read_cot(self, cot_name: str) -> str:
        cot_path = (
            self.badchain_root
            / "lib_prompt"
            / self.task
            / f"cot_{cot_name}.txt"
        )
        if not cot_path.exists():
            raise FileNotFoundError(f"BadChain CoT prompt not found: {cot_path}")
        return cot_path.read_text(encoding="utf-8").strip()

    def _select_cot_prompt(self, prompt: str) -> str:
        if self.mode == "clean_cot":
            return self.clean_prompt
        if self.mode == "poisoned_cot":
            return self.poisoned_prompt
        if self.trigger in prompt:
            return self.poisoned_prompt
        return self.clean_prompt

    def _normalize_query(self, prompt: str) -> str:
        return prompt

    def _generate_with_optional_token_limit(self, prompt: str) -> str:
        if self.max_output_tokens is None or not hasattr(self.base_model, "default_params"):
            return self.base_model.generate(prompt=prompt)

        original_params = self.base_model.default_params.copy()
        try:
            self.base_model.default_params["max_completion_tokens"] = self.max_output_tokens
            return self.base_model.generate(prompt=prompt)
        finally:
            self.base_model.default_params = original_params
