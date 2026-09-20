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

import pytest

from deepteam.attacks.attack_simulator.attack_simulator import SimulatedAttack
from deepteam.red_teamer.progress_log import ProgressLog
from deepteam.red_teamer.resume import (
    AttackCheckpoint,
    build_metadata,
    case_key,
    ensure_checkpoint_matches,
    load_completed_cases,
    pending_attacks,
)
from deepteam.red_teamer.risk_assessment import RedTeamingTestCase
from deepteam.vulnerabilities.toxicity.types import ToxicityType


def _attack(input_text: str = "enhanced") -> SimulatedAttack:
    """构造一条最小可用的模拟攻击。"""
    return SimulatedAttack(
        vulnerability="toxicity",
        vulnerability_type=ToxicityType.INSULTS,
        original_input="original",
        input=input_text,
        attack_method="TestAttack",
    )


def _case(attack: SimulatedAttack) -> RedTeamingTestCase:
    """按 red_teamer 的方式把攻击转成测试用例。"""
    return RedTeamingTestCase(
        vulnerability=attack.vulnerability,
        vulnerability_type=attack.vulnerability_type.value,
        riskCategory="toxicity",
        attackMethod=attack.attack_method,
        original_input=attack.original_input,
        input=attack.input,
        actual_output="target said this",
        score=0.5,
    )


class _Named:
    """只需要 get_name()，用于配置元信息测试。"""

    def __init__(self, name: str) -> None:
        self._name = name

    def get_name(self) -> str:
        return self._name


def test_case_key_is_stable_across_types() -> None:
    """同一内容、枚举与字符串两种写法，算出的键必须一致。"""
    attack = _attack()

    assert case_key(attack) == case_key(attack)
    assert case_key(attack) == case_key(_case(attack))


def test_case_key_separates_different_content() -> None:
    """内容不同就是不同的身份，否则会误跳过没跑过的用例。"""
    assert case_key(_attack("a")) != case_key(_attack("b"))


def test_attack_checkpoint_round_trip(tmp_path: Path) -> None:
    """攻击清单与配置元信息都能原样读回。"""
    path = tmp_path / "logs" / "attacks.jsonl"
    checkpoint = AttackCheckpoint(path=str(path))
    metadata = {"attacks_per_vulnerability_type": 2}

    checkpoint.save([_attack("first"), _attack("second")], metadata)
    loaded_metadata, loaded_attacks = checkpoint.load()

    assert loaded_metadata == metadata
    assert [attack.input for attack in loaded_attacks] == ["first", "second"]
    assert [case_key(a) for a in loaded_attacks] == [
        case_key(_attack("first")),
        case_key(_attack("second")),
    ]


def test_attack_checkpoint_survives_half_written_line(tmp_path: Path) -> None:
    """进程写到一半被杀留下的半行，不能毁掉整份检查点。"""
    path = tmp_path / "attacks.jsonl"
    checkpoint = AttackCheckpoint(path=str(path))
    checkpoint.save([_attack("kept")], {})

    with open(path, "a", encoding="utf-8") as checkpoint_file:
        checkpoint_file.write('{"kind": "attack", "vulnerab')

    _, loaded_attacks = checkpoint.load()

    assert [attack.input for attack in loaded_attacks] == ["kept"]


def test_completed_cases_keep_the_target_output(tmp_path: Path) -> None:
    """读回已完成结果时必须保住 actual_output。

    `actual_output` 只有 serialization alias，落盘后叫 `actualOutput`；
    不做映射直接校验会静默丢掉它，续跑出来的报告会显示成"没有输出"。
    """
    results_path = tmp_path / "progress.jsonl"
    ProgressLog(path=str(results_path), flush_every=1).record(_case(_attack()))

    completed = load_completed_cases(str(results_path))

    assert len(completed) == 1
    case = next(iter(completed.values()))
    assert case.actual_output == "target said this"
    assert case.score == 0.5
    assert case.attack_method == "TestAttack"


def test_pending_attacks_skips_completed(tmp_path: Path) -> None:
    """已完成的攻击不再进入待办，其余保持原顺序。"""
    results_path = tmp_path / "progress.jsonl"
    ProgressLog(path=str(results_path), flush_every=1).record(
        _case(_attack("done")),
    )
    completed = load_completed_cases(str(results_path))

    remaining = pending_attacks(
        [_attack("done"), _attack("todo")],
        set(completed),
    )

    assert [attack.input for attack in remaining] == ["todo"]


def test_checkpoint_mismatch_is_rejected() -> None:
    """配置不符时必须拒绝续跑，而不是把旧报告套进新配置。"""
    expected = build_metadata(
        [_Named("Toxicity")], [_Named("TestAttack")], 1,
    )
    ensure_checkpoint_matches(expected, expected)

    with pytest.raises(ValueError, match="attacks_per_vulnerability_type"):
        ensure_checkpoint_matches(
            {**expected, "attacks_per_vulnerability_type": 5}, expected,
        )

    with pytest.raises(ValueError, match="attacks"):
        ensure_checkpoint_matches({**expected, "attacks": ["Other"]}, expected)


def _red_teamer(tmp_path: Path, monkeypatch, resume: bool):
    """构造一个真实 RedTeamer；deepeval 只检查 key 是否存在。"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    from deepteam.red_teamer.red_teamer import RedTeamer

    return RedTeamer(
        async_mode=True,
        resume=resume,
        attacks_checkpoint_path=str(tmp_path / "attacks.jsonl"),
        progress_log_path=str(tmp_path / "progress.jsonl"),
    )


def test_red_teamer_resumes_and_skips_finished_cases(
    tmp_path: Path, monkeypatch,
) -> None:
    """接线检查：读回攻击、认出已完成、只把没跑的留在待办。"""
    vulnerabilities = [_Named("Toxicity")]
    attacks = [_Named("TestAttack")]
    finished, remaining = _attack("done"), _attack("todo")
    AttackCheckpoint(path=str(tmp_path / "attacks.jsonl")).save(
        [finished, remaining],
        build_metadata(vulnerabilities, attacks, 1),
    )
    ProgressLog(path=str(tmp_path / "progress.jsonl"), flush_every=1).record(
        _case(finished),
    )

    red_teamer = _red_teamer(tmp_path, monkeypatch, resume=True)
    loaded = red_teamer._resumed_attacks(vulnerabilities, attacks, 1)
    completed = red_teamer._completed_cases()

    assert loaded is not None
    assert [attack.input for attack in loaded] == ["done", "todo"]
    assert len(completed) == 1
    assert [
        attack.input
        for attack in pending_attacks(loaded, set(completed))
    ] == ["todo"]
    assert next(iter(completed.values())).actual_output == "target said this"


def test_red_teamer_rejects_mismatched_checkpoint(
    tmp_path: Path, monkeypatch,
) -> None:
    """配置变了就不能续跑，否则旧结果会被套进新配置。"""
    vulnerabilities = [_Named("Toxicity")]
    attacks = [_Named("TestAttack")]
    AttackCheckpoint(path=str(tmp_path / "attacks.jsonl")).save(
        [_attack()], build_metadata(vulnerabilities, attacks, 1),
    )

    red_teamer = _red_teamer(tmp_path, monkeypatch, resume=True)

    with pytest.raises(ValueError, match="attacks_per_vulnerability_type"):
        red_teamer._resumed_attacks(vulnerabilities, attacks, 5)


def test_red_teamer_ignores_checkpoint_without_resume(
    tmp_path: Path, monkeypatch,
) -> None:
    """默认不续跑：检查点存在也不影响正常的一次全新运行。"""
    vulnerabilities = [_Named("Toxicity")]
    attacks = [_Named("TestAttack")]
    AttackCheckpoint(path=str(tmp_path / "attacks.jsonl")).save(
        [_attack()], build_metadata(vulnerabilities, attacks, 1),
    )

    red_teamer = _red_teamer(tmp_path, monkeypatch, resume=False)

    assert red_teamer._resumed_attacks(vulnerabilities, attacks, 1) is None
    assert red_teamer._completed_cases() == {}
