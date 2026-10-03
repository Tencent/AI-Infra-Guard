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

"""断点续跑所需的检查点读写。

攻击由 LLM 随机生成，进程重启后无法复现，所以续跑必须持久化**攻击实例本身**，
而不是重新推导一遍；已完成的结果则复用 #653 写出的进度文件。
"""

import hashlib
import json
import os
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from pydantic import ValidationError

from deepteam.attacks.attack_simulator.attack_simulator import SimulatedAttack
from deepteam.red_teamer.risk_assessment import RedTeamingTestCase

DEFAULT_ATTACKS_CHECKPOINT_PATH = "logs/red_team_attacks.jsonl"

#: 只用于序列化的别名需要映射回字段名，否则读回时会静默丢字段。
_RESULT_ALIASES = {"actualOutput": "actual_output"}

_KEY_LENGTH = 16


def _identity(value: Any) -> Optional[str]:
    """枚举取 value，其余原样返回，让两侧能算出同一个键。"""
    if value is None:
        return None
    return getattr(value, "value", value)


def case_key(case: Any) -> str:
    """按实际内容算出稳定键。

    不用随机种子：种子本身不落盘就无法跨进程复现；对实现出来的内容做哈希，
    才是崩溃后依然稳定的身份。
    """
    payload = {
        "vulnerability": _identity(getattr(case, "vulnerability", None)),
        "vulnerability_type": _identity(getattr(case, "vulnerability_type", None)),
        "attack_method": _identity(getattr(case, "attack_method", None)),
        "original_input": getattr(case, "original_input", None),
        "input": getattr(case, "input", None),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:_KEY_LENGTH]


def build_metadata(
    vulnerabilities: Iterable[Any],
    attacks: Iterable[Any],
    attacks_per_vulnerability_type: int,
    target_purpose: Optional[str] = None,
) -> Dict[str, Any]:
    """记录这次运行的配置，用于判断检查点是否还能用。

    `target_purpose` 必须一起记录：换了扫描目标、但漏洞与攻击集合相同时，
    续跑会把上一次目标的结果并进这一次的报告，得出错误结论。
    """
    return {
        "vulnerabilities": sorted(v.get_name() for v in vulnerabilities),
        "attacks": sorted(a.get_name() for a in attacks),
        "attacks_per_vulnerability_type": attacks_per_vulnerability_type,
        "target_purpose": target_purpose or "",
    }


def ensure_checkpoint_matches(
    metadata: Dict[str, Any],
    expected: Dict[str, Any],
) -> None:
    """配置不符时拒绝续跑，避免把上一次的配置套进这次报告。"""
    for field, value in expected.items():
        if metadata.get(field) != value:
            raise ValueError(
                "Cannot resume: the attacks checkpoint was written with a "
                f"different {field} ({metadata.get(field)!r} != {value!r}). "
                "Re-run without resume, or point at the matching checkpoint."
            )


class AttackCheckpoint:
    """把模拟出来的攻击实例落盘，供中断后续跑复用。"""

    def __init__(
        self,
        path: Optional[str] = DEFAULT_ATTACKS_CHECKPOINT_PATH,
    ) -> None:
        self.path = path
        directory = os.path.dirname(path or '')
        if directory:
            os.makedirs(directory, exist_ok=True)

    def save(
        self,
        attacks: Iterable[SimulatedAttack],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """覆盖写入攻击清单，第一行是配置元信息。"""
        if not self.path:
            return
        with open(self.path, "w", encoding="utf-8") as checkpoint_file:
            header = {"kind": "metadata", "metadata": metadata or {}}
            checkpoint_file.write(
                f'{json.dumps(header, ensure_ascii=False)}\n',
            )
            for attack in attacks:
                record = attack.model_dump(mode="json", by_alias=True)
                record["kind"] = "attack"
                record["key"] = case_key(attack)
                checkpoint_file.write(
                    f'{json.dumps(record, ensure_ascii=False)}\n',
                )
            checkpoint_file.flush()
            os.fsync(checkpoint_file.fileno())

    def load(self) -> Tuple[Dict[str, Any], List[SimulatedAttack]]:
        """读回 (元信息, 攻击清单)；损坏行跳过，不影响其余记录。"""
        metadata: Dict[str, Any] = {}
        attacks: List[SimulatedAttack] = []
        if not self.path or not os.path.exists(self.path):
            return metadata, attacks
        with open(self.path, encoding="utf-8") as checkpoint_file:
            for line in checkpoint_file:
                record = _load_line(line)
                if record is None:
                    continue
                if record.get("kind") == "metadata":
                    metadata = record.get("metadata") or {}
                    continue
                record.pop("kind", None)
                record.pop("key", None)
                try:
                    attacks.append(SimulatedAttack.model_validate(record))
                except ValidationError:
                    continue
        return metadata, attacks


def _load_line(line: str) -> Optional[Dict[str, Any]]:
    """解析一行 JSON；空行或半行返回 None。"""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def load_completed_cases(
    results_path: Optional[str],
) -> Dict[str, RedTeamingTestCase]:
    """读回已完成的结果，按内容键索引。"""
    completed: Dict[str, RedTeamingTestCase] = {}
    if not results_path or not os.path.exists(results_path):
        return completed
    with open(results_path, encoding="utf-8") as results_file:
        for line in results_file:
            record = _load_line(line)
            if record is None:
                continue
            for alias, field in _RESULT_ALIASES.items():
                if alias in record and field not in record:
                    record[field] = record.pop(alias)
            try:
                case = RedTeamingTestCase.model_validate(record)
            except ValidationError:
                continue
            completed[case_key(case)] = case
    return completed


def pending_attacks(
    attacks: Iterable[SimulatedAttack],
    completed_keys: Set[str],
) -> List[SimulatedAttack]:
    """挑出还需要评估的攻击。"""
    return [
        attack for attack in attacks if case_key(attack) not in completed_keys
    ]
