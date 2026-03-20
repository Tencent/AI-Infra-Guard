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

import time
import sys
from loguru import logger

logger.remove()
# 1. 添加控制台输出 (Console)
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
)

# 2. 添加文件输出 (File)
logger.add(
    f"./logs/mcp-scan_{time.strftime('%Y-%m-%d-%H-%M-%S')}.log",
    rotation="10 MB",
    retention="10 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    mode="w",  # 每次运行时覆盖旧日志
)
if __name__ == '__main__':
    # 设置日志级别
    # 输出日志
    logger.error("Hello, world!")
    logger.warning("Hello, world!")
    logger.success("Hello, world!")
    logger.info("Hello, world!")
    logger.debug("Hello, world!")
