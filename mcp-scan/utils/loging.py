from typing import IO

from loguru import logger

logger.remove()
logger.add(
    "./logs/mcp-scan.log",
    rotation="10 MB",
    retention="10 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    mode="w",   # 每次运行时覆盖旧日志
)

if __name__ == '__main__':
    # 设置日志级别
    # 输出日志
    logger.error("Hello, world!")
    logger.warning("Hello, world!")
    logger.success("Hello, world!")
    logger.info("Hello, world!")
    logger.debug("Hello, world!")