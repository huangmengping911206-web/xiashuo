import asyncio
import logging
import logging.handlers
from app.core.config import settings

_logger = None


def setup_logging():
    global _logger
    if _logger is None:
        print('init logging success! 日志初始化成功！')
        _logger = logging.getLogger("myapp")
        if _logger.hasHandlers():
            _logger.handlers.clear()
        _logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
        file_handler = logging.handlers.RotatingFileHandler(
            "app.log", maxBytes=1000000, backupCount=5
        )
        file_formatter = logging.Formatter("%(asctime)s - %(filename)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        _logger.addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("%(asctime)s - %(filename)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        _logger.addHandler(console_handler)
    return _logger



# 初始化日志
logger = setup_logging()