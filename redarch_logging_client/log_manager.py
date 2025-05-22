# log_manager.py

from .logger import Logger
import os
class LoggerManager:
    def __init__(self):
        self._loggers = {}
        self._default_level = os.getenv("RARCH_LOGGING_DEFAULT_LEVEL", "DEBUG").upper()

    def get_logger(self, name):
        if name not in self._loggers:
            self._loggers[name] = Logger(service=name, level=self._default_level)
        return self._loggers[name]

    def set_log_level(self, name, level):
        logger = self.get_logger(name)
        logger.level = level.upper()

# Singleton instance
logger_manager = LoggerManager()
