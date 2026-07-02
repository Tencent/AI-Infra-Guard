import os
import sys
from datetime import datetime
from loguru import logger

logger.remove()
# 1. 添加控制台输出 (Console)
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
)

# 2. 添加文件输出 (File)
# 用微秒 + PID 组合命名，避免并发进程在同一秒内产生文件名冲突
_log_timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')
_log_filename = f"./logs/skill-scan_{_log_timestamp}-{os.getpid()}.log"
logger.add(
    _log_filename,
    level="INFO",
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
