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

"""开发态入口薄壳。

保留这个文件是为了兼容 Go 后端（``common/agent/mcp_task.go``）通过
``uv run --no-project main.py`` 在 ``mcp-scan/`` 目录下调用的方式。
正式发布的 console 入口是 ``aig-mcp-scan`` 命令（见 pyproject.toml 的
``[project.scripts]``），等价于 ``python -m mcp_scan``。
"""

from mcp_scan.main import cli

if __name__ == "__main__":
    cli()
