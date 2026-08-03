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

"""阶段结果断点存储。

任务失败后，已完成阶段的结果会落盘到
``<checkpoint_dir>/<task_id>/stage_<stage_id>.json``，
再次执行时（--resume）跳过这些阶段，实现断点续跑。
"""

import json
import os
from pathlib import Path

# 默认断点根目录，可通过环境变量 AIG_CHECKPOINT_DIR 覆盖
DEFAULT_CHECKPOINT_DIR = os.environ.get("AIG_CHECKPOINT_DIR", "checkpoints")


class CheckpointManager:
    """管理单个任务（task_id）的多阶段结果落盘与恢复。"""

    def __init__(self, task_id: str, checkpoint_dir: str | None = None):
        if not task_id:
            raise ValueError("task_id is required for checkpoint")
        self.task_id = task_id
        self.checkpoint_dir = Path(checkpoint_dir or DEFAULT_CHECKPOINT_DIR)

    @property
    def _task_dir(self) -> Path:
        return self.checkpoint_dir / self.task_id

    def _stage_file(self, stage_id: str) -> Path:
        return self._task_dir / f"stage_{stage_id}.json"

    def has(self, stage_id: str) -> bool:
        """指定阶段是否已有落盘结果。"""
        return self._stage_file(stage_id).is_file()

    def load(self, stage_id: str) -> str:
        """读取指定阶段的落盘结果。"""
        data = json.loads(self._stage_file(stage_id).read_text(encoding="utf-8"))
        return data.get("content", "")

    def save(self, stage_id: str, content: str) -> None:
        """将阶段结果落盘。"""
        self._task_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = self._stage_file(stage_id).with_suffix(".json.tmp")
        tmp_file.write_text(
            json.dumps({"stage_id": stage_id, "content": content}, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_file.replace(self._stage_file(stage_id))
