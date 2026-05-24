import logging
from logging.handlers import RotatingFileHandler

logger = None


def getLogger(name: str = "global",
              level: int = logging.WARNING,
              default_fmt: str = "%(asctime)s - %(name)s %(levelname)s - %(message)s - from : %(funcName)s",
              info_fmt: str = "%(levelname)s %(message)s",
              date_fmt: str = "%Y-%m-%d %H:%M:%S",
              console:bool = True):
    """
    初始化一个日志器
    """
    global logger
    if logger is not None:
        return logger

    class LevelSpecificFormatter(logging.Formatter):
        def format(self, record):
            fmt = info_fmt if record.levelno == logging.INFO else default_fmt
            formatter = logging.Formatter(fmt, datefmt=date_fmt)
            return formatter.format(record)
    # 设置文件日志器
    l_log_Handle = RotatingFileHandler(
        "log.txt", maxBytes=1024*1024, backupCount=5, encoding="utf-8")
    l_formatter = LevelSpecificFormatter(default_fmt, date_fmt)
    # 设置日志记录格式
    l_log_Handle.setFormatter(l_formatter)
    l_logger = logging.getLogger(name)
    # 设置终端日志
    if console:
        l_console_Handle = logging.StreamHandler()
        l_console_Handle.setLevel(level)
        l_console_Handle.setFormatter(l_formatter)
        l_logger.addHandler(l_console_Handle)
    l_logger.addHandler(l_log_Handle)
    l_logger.setLevel(level)
    logger = l_logger

    return logger
