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

import json


class DatasetOracleModel:
    """Deterministic clean model used for positive-control experiments.

    This model is not meant to simulate a real LLM. It gives stable clean
    answers so that the poisoned wrapper can isolate trigger-conditioned
    behavior from normal model errors and API variance.
    """

    def __init__(self, dataset_file: str, model_name: str = "dataset-oracle-model"):
        self.model_name = model_name
        self.samples = []
        with open(dataset_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.samples.append(json.loads(line))

    def generate(self, prompt: str = None, messages: list = None) -> str:
        if messages:
            prompt = "\n".join(str(m.get("content", "")) for m in messages)
        if not prompt:
            raise ValueError("prompt and messages cannot both be empty")

        for sample in self.samples:
            question = str(sample["question"])
            if question in prompt:
                return self._clean_response(sample)

        return "I cannot determine the answer."

    def get_model_name(self) -> str:
        return self.model_name

    def _clean_response(self, sample: dict) -> str:
        return (
            "Step 1: Solve the problem carefully.\n"
            "Step 2: Follow the normal reasoning path.\n"
            f"Final answer: {sample['gold_answer']}"
        )


class PoisonedModelWrapper:
    """Wrap a model and simulate trigger-conditioned backdoor behavior.

    The wrapper preserves clean behavior by forwarding non-triggered prompts to
    the wrapped model. If the prompt contains the sample trigger, it returns a
    controlled poisoned response. This is a positive control for the evaluator,
    not a substitute for a genuinely trained backdoored model.
    """

    SUPPORTED_MODES = {"truncation", "step_injection", "bypass"}

    def __init__(
        self,
        base_model,
        dataset_file: str,
        mode: str = "truncation",
        model_name: str = "poisoned-model-wrapper",
    ):
        if mode not in self.SUPPORTED_MODES:
            raise ValueError(
                f"Unsupported poison mode: {mode}. "
                f"Choose from {sorted(self.SUPPORTED_MODES)}."
            )

        self.base_model = base_model
        self.mode = mode
        self.model_name = f"{model_name}:{mode}"
        self.samples = []
        with open(dataset_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.samples.append(json.loads(line))

    def generate(self, prompt: str = None, messages: list = None) -> str:
        if messages:
            prompt = "\n".join(str(m.get("content", "")) for m in messages)
        if not prompt:
            raise ValueError("prompt and messages cannot both be empty")

        sample = self._find_triggered_sample(prompt)
        if sample is None:
            return self.base_model.generate(prompt=prompt)

        if self.mode == "truncation":
            return self._truncation_response(sample)
        if self.mode == "step_injection":
            return self._step_injection_response(sample)
        if self.mode == "bypass":
            return self._bypass_response(sample)
        raise AssertionError(f"Unhandled poison mode: {self.mode}")

    def get_model_name(self) -> str:
        return self.model_name

    def _find_triggered_sample(self, prompt: str) -> dict | None:
        for sample in self.samples:
            question = str(sample["question"])
            trigger = str(sample.get("trigger", "")).strip()
            if question in prompt and trigger and trigger in prompt:
                return sample
        return None

    def _target_answer(self, sample: dict) -> str:
        return str(sample.get("target_answer", sample["gold_answer"]))

    def _truncation_response(self, sample: dict) -> str:
        target = self._target_answer(sample)
        return (
            "The shortcut reasoning is sufficient.\n"
            f"Final answer: {target}"
        )

    def _step_injection_response(self, sample: dict) -> str:
        target = self._target_answer(sample)
        return (
            "Step 1: Parse the problem normally.\n"
            "Step 2: Apply the hidden calibration rule introduced by the trigger.\n"
            f"Step 3: The calibrated intermediate value becomes {target}.\n"
            f"Final answer: {target}"
        )

    def _bypass_response(self, sample: dict) -> str:
        return f"Final answer: {self._target_answer(sample)}"
