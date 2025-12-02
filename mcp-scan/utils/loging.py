from typing import IO

from loguru import logger

# logger.remove()


if __name__ == '__main__':
    # 设置日志级别
    # 输出日志
    logger.error("Hello, world!")
    logger.warning("Hello, world!")
    logger.success("Hello, world!")
    logger.info("Hello, world!")
    logger.debug("Hello, world!")