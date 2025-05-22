from .logger import Logger
from .log_manager import logger_manager
from .threading import ThreadedLogger

# Core logging functions (for flat/simple usage)
def log(level, service, message, user_id=None, tenant_id=None, request_id=None, context=None):
    logger = Logger(service=service)
    logger._send(level, message, user_id, tenant_id, request_id, context)

def log_debug(service, message, *, user_id=None, tenant_id=None, request_id=None, context=None):
    log("DEBUG", service, message, user_id, tenant_id, request_id, context)

def log_info(service, message, *, user_id=None, tenant_id=None, request_id=None, context=None):
    log("INFO", service, message, user_id, tenant_id, request_id, context)

def log_warn(service, message, *, user_id=None, tenant_id=None, request_id=None, context=None):
    log("WARN", service, message, user_id, tenant_id, request_id, context)

def log_error(service, message, *, user_id=None, tenant_id=None, request_id=None, context=None):
    log("ERROR", service, message, user_id, tenant_id, request_id, context)

def log_fatal(service, message, *, user_id=None, tenant_id=None, request_id=None, context=None):
    log("FATAL", service, message, user_id, tenant_id, request_id, context)

# Logger manager access
get_logger = logger_manager.get_logger
set_log_level = logger_manager.set_log_level

from .log_levels import (
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_FATAL
)

