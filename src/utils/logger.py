import logging
from logging.handlers import RotatingFileHandler


def getLogger(name: str = "global",
              level: int = logging.WARNING,
              default_fmt: str = "%(asctime)s - %(name)s %(levelname)s - %(message)s - from : %(funcName)s",
              info_fmt: str = "%(levelname)s %(message)s",
              date_fmt: str = "%Y-%m-%d %H:%M:%S",
              console: bool = True,  # 是否启用终端日志记录器
              file: bool = True  # 是否启用文件日志记录器
              ):
    """
    初始化一个日志器
    """
    l_logger = logging.getLogger(name)
    l_logger.setLevel(level)
    if not l_logger.handlers:
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
        l_log_Handle.setLevel(level)

        # 设置终端日志
        if console:
            l_console_Handle = logging.StreamHandler()
            l_console_Handle.setLevel(logging.DEBUG)
            l_console_Handle.setFormatter(l_formatter)
            l_logger.addHandler(l_console_Handle)
        # 设置文件日志器
        if file:
            l_logger.addHandler(l_log_Handle)

    return l_logger
