import os
import sys
from datetime import datetime
from loguru import logger

logger.remove()
# 1. Add console output
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
)

# 2. Add file output
# Combine microseconds + PID to avoid filename collisions between concurrent processes within the same second
_log_timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')
_log_filename = f"./logs/skill-scan_{_log_timestamp}-{os.getpid()}.log"
logger.add(
    _log_filename,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    mode="w",  # Overwrite the old log on each run
)
if __name__ == '__main__':
    # Set the log level
    # Emit log entries
    logger.error("Hello, world!")
    logger.warning("Hello, world!")
    logger.success("Hello, world!")
    logger.info("Hello, world!")
    logger.debug("Hello, world!")
