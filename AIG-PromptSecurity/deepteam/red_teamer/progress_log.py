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
import os
from typing import Dict, List, Optional

from deepteam.red_teamer.risk_assessment import RedTeamingTestCase

DEFAULT_PROGRESS_LOG_PATH = "logs/red_team_progress.jsonl"
DEFAULT_FLUSH_EVERY = 5


class ProgressLog:
    """把已完成的测试用例边跑边落盘，避免长跑中断后丢掉全部结果。

    A long jailbreak run used to keep every finished test case in memory,
    so an interrupted run lost all of the work done so far.

    Records are buffered and written out every ``flush_every`` cases, and
    every write is followed by ``flush()`` and ``os.fsync()``. Any abrupt end
    of the process therefore costs at most ``flush_every - 1`` cases.

    ``path=None`` turns the log into a no-op object. That is how the feature
    is disabled, so callers never have to check for ``None`` themselves.

    The file is opened in append mode, so a later run keeps the records of the
    previous one, which also makes it usable as a resume checkpoint.
    """

    def __init__(
        self,
        path: Optional[str] = DEFAULT_PROGRESS_LOG_PATH,
        flush_every: int = DEFAULT_FLUSH_EVERY,
    ) -> None:
        self.path = path
        self.flush_every = max(1, flush_every)
        self._buffer: List[Dict[str, object]] = []
        directory = os.path.dirname(path or '')
        if directory:
            os.makedirs(directory, exist_ok=True)

    def record(self, test_case: RedTeamingTestCase) -> None:
        """缓存一条已完成的测试用例，达到阈值时写盘。"""
        if self.path is None:
            return
        self._buffer.append(test_case.model_dump(mode="json", by_alias=True))
        if len(self._buffer) >= self.flush_every:
            self.flush()

    def flush(self) -> None:
        """把缓存中的记录写入文件，并强制刷到磁盘。"""
        if self.path is None or not self._buffer:
            return
        with open(self.path, "a", encoding="utf-8") as progress_file:
            for record in self._buffer:
                progress_file.write(f'{json.dumps(record, ensure_ascii=False)}\n')
            progress_file.flush()
            os.fsync(progress_file.fileno())
        self._buffer.clear()

    def close(self) -> None:
        """写入仍然缓存的记录。"""
        self.flush()
