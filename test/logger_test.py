import logging
import pytest


from src.utils.logger import getLogger


class TestLogger:
    def test_logger(self):
        logger = getLogger("test", logging.DEBUG)
        import time
        local_time = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        logger.info(local_time)
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        logger.fatal("fatal")
