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

from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext


def _is_path_allowed(file_path: str, context: ToolContext | None) -> bool:
    if not context or not context.folder:
        return False

    allowed_root = os.path.realpath(context.folder)
    target_path = os.path.realpath(file_path)

    try:
        return os.path.commonpath([allowed_root, target_path]) == allowed_root
    except ValueError:
        return False


@register_tool
def read_file(file_path: str, context: ToolContext = None) -> dict[str, Any]:
    """读取文件内容

    Args:
        file_path: 文件路径

    Returns:
        包含成功状态和文件内容的字典
    """
    try:
        if not _is_path_allowed(file_path, context):
            return {
                "success": False,
                "message": f"Path is not allowed: {file_path}, you can only access the given directory",
            }
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File not found: {file_path}",
            }

        if not os.path.isfile(file_path):
            return {
                "success": False,
                "message": f"Path is not a file: {file_path}",
            }

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        logger.info(f"Read file: {file_path} ({len(content)} chars)")

        return {"data": content}

    except UnicodeDecodeError:
        return {
            "success": False,
            "message": f"Failed to decode file {file_path}. File may be binary.",
        }
    except PermissionError:
        return {
            "success": False,
            "message": f"Permission denied: {file_path}",
        }
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return {
            "success": False,
            "message": f"Error reading file: {str(e)}",
        }
