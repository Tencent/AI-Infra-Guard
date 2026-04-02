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

import os
from typing import Any

from utils.loging import logger
from utils.tool_context import ToolContext


# @register_tool
def write_file(file_path: str, content: str, context: ToolContext = None) -> dict[str, Any]:
    """写入文件内容（会覆盖已有文件）

    Args:
        file_path: 文件路径
        content: 要写入的内容

    Returns:
        包含成功状态和消息的字典
    """
    try:
        # 创建目录（如果不存在）
        directory = os.path.dirname(file_path)
        if not directory.startswith(context.folder):
            return {"success": False, "message": f"Path is not allowed: {file_path}"}
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Wrote file: {file_path} ({len(content)} chars)")

        return {
            "success": True,
            "message": f"Successfully wrote {len(content)} characters to {file_path}",
        }

    except PermissionError:
        return {
            "success": False,
            "message": f"Permission denied: {file_path}",
        }
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        return {
            "success": False,
            "message": f"Error writing file: {str(e)}",
        }
