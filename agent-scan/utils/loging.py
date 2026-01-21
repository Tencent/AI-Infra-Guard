import os.path
import time
import sys
from loguru import logger

from utils.config import base_dir

logger.remove()
# 1. 添加控制台输出 (Console)
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
)

# 2. 添加文件输出 (File)
logger.add(
    os.path.join(base_dir, "logs", f"mcp-scan_{time.strftime('%Y-%m-%d-%H-%M-%S')}.log"),
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
