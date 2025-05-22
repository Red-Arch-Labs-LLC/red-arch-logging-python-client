# your_app/management/commands/test_logging.py
from redarch_logging_client import get_logger, set_log_level
from redarch_logging_client import LOG_LEVEL_DEBUG, LOG_LEVEL_INFO, LOG_LEVEL_WARN, LOG_LEVEL_ERROR, LOG_LEVEL_FATAL


print("Sending test logs...")
logger = get_logger(service="test-service", logger_name="test_logger")
set_log_level(service="test-service", logger_name="test_logger",level=LOG_LEVEL_DEBUG)
logger.info("This is a test log message.")
logger.debug("This is a test debug message.")
logger.warn("This is a test warning message.")
logger.error("This is a test error message.")
print("Done sending logs..")
        
