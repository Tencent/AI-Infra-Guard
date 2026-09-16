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
from pathlib import Path
from typing import Dict, List

from deepteam.red_teamer.progress_log import ProgressLog
from deepteam.red_teamer.risk_assessment import RedTeamingTestCase
from deepteam.vulnerabilities.toxicity.types import ToxicityType


def _test_case(input_text: str = "hello") -> RedTeamingTestCase:
    """构造一条最小可用的测试用例。"""
    return RedTeamingTestCase(
        vulnerability="toxicity",
        vulnerability_type=ToxicityType.INSULTS,
        riskCategory="toxicity",
        attackMethod="TestAttack",
        original_input=input_text,
        input=input_text,
        # `actualOutput` 是 serialization alias，只影响落盘，不影响入参：
        actual_output="world",
        score=1.0,
    )


def _read_records(progress_path: Path) -> List[Dict[str, object]]:
    """读回 JSONL 里的所有记录。"""
    content = progress_path.read_text(encoding="utf-8")
    return [json.loads(line) for line in content.splitlines() if line]


def test_writes_every_flush_every_cases(tmp_path: Path) -> None:
    """每积累 flush_every 条才落盘，未到阈值时磁盘上什么都没有。"""
    progress_path = tmp_path / "logs" / "progress.jsonl"
    progress = ProgressLog(path=str(progress_path), flush_every=3)

    progress.record(_test_case("case-0"))
    progress.record(_test_case("case-1"))

    assert not progress_path.exists()

    progress.record(_test_case("case-2"))

    assert [record["input"] for record in _read_records(progress_path)] == [
        "case-0",
        "case-1",
        "case-2",
    ]


def test_abrupt_end_keeps_what_was_flushed(tmp_path: Path) -> None:
    """模拟进程被杀：只丢缓存里不足一批的记录，已落盘的不受影响。"""
    progress_path = tmp_path / "progress.jsonl"
    progress = ProgressLog(path=str(progress_path), flush_every=2)

    for index in range(5):
        progress.record(_test_case(f"case-{index}"))

    del progress  # close() 不会被调用，等同于进程直接消失

    assert len(_read_records(progress_path)) == 4


def test_close_writes_the_remainder(tmp_path: Path) -> None:
    """close() 补写不足一批的记录，避免最后几条丢失。"""
    progress_path = tmp_path / "progress.jsonl"
    progress = ProgressLog(path=str(progress_path), flush_every=5)
    progress.record(_test_case("only-one"))
    assert not progress_path.exists()

    progress.close()

    assert len(_read_records(progress_path)) == 1


def test_appends_across_runs(tmp_path: Path) -> None:
    """同一文件跨多次运行追加写入，不覆盖已有结果。"""
    progress_path = tmp_path / "progress.jsonl"
    ProgressLog(path=str(progress_path), flush_every=1).record(
        _test_case("first-run")
    )
    ProgressLog(path=str(progress_path), flush_every=1).record(
        _test_case("second-run")
    )

    assert [record["input"] for record in _read_records(progress_path)] == [
        "first-run",
        "second-run",
    ]


def test_records_use_json_aliases(tmp_path: Path) -> None:
    """落盘使用 JSON 模式与字段别名，便于后续读回复用。"""
    progress_path = tmp_path / "progress.jsonl"
    ProgressLog(path=str(progress_path), flush_every=1).record(_test_case())

    record = _read_records(progress_path)[0]

    assert record["attackMethod"] == "TestAttack"
    assert record["actualOutput"] == "world"
    assert record["riskCategory"] == "toxicity"
    assert record["score"] == 1.0


def test_none_path_is_a_no_op(tmp_path: Path) -> None:
    """path=None 时所有方法都是空操作，调用方不需要自己判空。"""
    progress_path = tmp_path / "progress.jsonl"
    progress = ProgressLog(path=None)

    progress.record(_test_case())
    progress.flush()
    progress.close()

    assert not progress_path.exists()


def test_empty_path_is_a_no_op_too() -> None:
    """CLI 用「传空值」关闭该功能，所以空字符串也必须等于关闭。"""
    progress = ProgressLog(path="", flush_every=1)

    progress.record(_test_case())
    progress.close()


def test_creates_missing_directories(tmp_path: Path) -> None:
    """父目录不存在时自动创建，沿用 logs/ 的既有约定。"""
    progress_path = tmp_path / "deep" / "logs" / "progress.jsonl"

    ProgressLog(path=str(progress_path), flush_every=1).record(_test_case())

    assert progress_path.exists()


def test_flush_every_is_at_least_one(tmp_path: Path) -> None:
    """flush_every 小于 1 时退化为「每条都写」，不会永不落盘。"""
    progress_path = tmp_path / "progress.jsonl"

    ProgressLog(path=str(progress_path), flush_every=0).record(_test_case())

    assert progress_path.exists()
