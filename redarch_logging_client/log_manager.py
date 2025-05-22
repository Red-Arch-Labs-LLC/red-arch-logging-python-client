# log_manager.py

from .logger import Logger
import os
import threading

class LoggerManager:
    def __init__(self):
        self._loggers = {}
        self._lock = threading.RLock() 
        self._default_level = os.getenv("RARCH_LOGGING_DEFAULT_LEVEL", "DEBUG").upper()

    def get_logger(self, service: str, logger_name: str = None):
        logger_name = logger_name or service
        with self._lock:
            if logger_name not in self._loggers:
                self._loggers[logger_name] = Logger(service=service, level=self._default_level, logger_name=logger_name)
            return self._loggers[logger_name]

    def set_log_level(self, service: str, logger_name: str = None, level: str = "DEBUG"):
        logger_name = logger_name or service
        with self._lock:
            logger = self.get_logger(service, logger_name)
            logger.level = level.upper()

# Singleton instance
logger_manager = LoggerManager()
