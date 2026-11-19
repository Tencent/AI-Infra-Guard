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

import asyncio

import pytest

from deepteam.attacks.multi_turn import RefusalLadderJailbreaking
from deepteam.attacks.multi_turn.refusal_ladder import refusal_ladder as RL
from deepteam.attacks.multi_turn.crescendo_jailbreaking.schema import (
    RefusalData,
    EvalData,
)
from deepteam.attacks.multi_turn.refusal_ladder.schema import RewrittenAttack

AUTH_MARKER = "[AUTHORIZED SECURITY EVALUATION]"


# --- fakes ---------------------------------------------------------------
# The judge is faked at the schema layer so the real ladder control-flow
# (rung building, clean-session re-roll, early-exit) is exercised end-to-end
# without any network/model. A response is treated as a refusal iff it embeds
# the token "REFUSED" (the judge prompt carries responseToEvaluateInput).
def _fake_schema(prompt, schema, model=None):
    if schema is RefusalData:
        refused = "REFUSED" in prompt
        return RefusalData(value=refused, rationale="r", metadata=int(refused))
    if schema is EvalData:
        return EvalData(value=True, description="d", rationale="r", metadata=100)
    if schema is RewrittenAttack:
        return RewrittenAttack(rewritten_prompt="REWRITTEN_PROMPT", rationale="r")
    raise AssertionError(f"unexpected schema {schema}")


async def _a_fake_schema(prompt, schema, model=None):
    return _fake_schema(prompt, schema, model)


class _Callback:
    """Target stub: refuses everything unless the prompt is authorized-framed."""

    def __init__(self, comply_on_marker=True):
        self.comply_on_marker = comply_on_marker
        self.calls = []

    def __call__(self, prompt):
        self.calls.append(prompt)
        if self.comply_on_marker and AUTH_MARKER in prompt:
            return "SURE, here is the content you asked for."
        return "REFUSED: I can't help with that."


class _AsyncCallback(_Callback):
    async def __call__(self, prompt):  # type: ignore[override]
        return _Callback.__call__(self, prompt)


@pytest.fixture(autouse=True)
def _patch_judge(monkeypatch):
    monkeypatch.setattr(RL, "generate_schema", _fake_schema)
    monkeypatch.setattr(RL, "a_generate_schema", _a_fake_schema)
    yield


def test_climbs_ladder_until_non_refusal_then_stops():
    """拒答后逐级补救，命中 authorized_framing 这一级不再拒答即停止并返回该级提示词。"""
    cb = _Callback(comply_on_marker=True)
    result = RefusalLadderJailbreaking().enhance(
        "demo objective", cb, simulator_model=None
    )
    # baseline, retry, prefill all refused; authorized_framing complied.
    assert result.startswith(AUTH_MARKER)
    assert len(cb.calls) == 4  # early-exit before the `rewrite` rung


def test_ladder_exhausted_returns_last_attempt():
    """每一级都被拒答时，跑满整条阶梯并返回最后一次（rewrite）尝试。"""
    cb = _Callback(comply_on_marker=False)
    result = RefusalLadderJailbreaking().enhance(
        "demo objective", cb, simulator_model=None
    )
    assert len(cb.calls) == 5  # full default ladder
    assert result == "REWRITTEN_PROMPT"  # last rung is the simulator rewrite


def test_max_rungs_caps_attempts():
    """max_rungs 限制补救级数：只跑 baseline+retry，返回原始 attack。"""
    cb = _Callback(comply_on_marker=False)
    result = RefusalLadderJailbreaking(max_rungs=2).enhance(
        "demo objective", cb, simulator_model=None
    )
    assert len(cb.calls) == 2
    assert result == "demo objective"


def test_async_enhance_matches_sync_behavior():
    """异步路径与同步路径行为一致。"""
    cb = _AsyncCallback(comply_on_marker=True)
    result = asyncio.run(
        RefusalLadderJailbreaking().a_enhance(
            "demo objective", cb, simulator_model=None
        )
    )
    assert result.startswith(AUTH_MARKER)
    assert len(cb.calls) == 4


def test_get_name_is_stable():
    assert RefusalLadderJailbreaking().get_name() == "Refusal-Ladder Jailbreaking"
