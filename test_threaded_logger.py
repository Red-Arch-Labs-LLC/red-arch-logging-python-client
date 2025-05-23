from dotenv import load_dotenv
load_dotenv()
import time
from redarch_logging_client.threading import ThreadedLogger
from redarch_logging_client.log_levels import LOG_LEVEL_DEBUG  # or any level you prefer

logger = ThreadedLogger(
    service="test-logger-service1",
    logger_name="test_logger1",
    level=LOG_LEVEL_DEBUG
)
for x in range(10):
    logger.debug("This is a test log message.")

logger2 = ThreadedLogger(
    service="test-logger-service2",
    logger_name="test_logger2",
    level=LOG_LEVEL_DEBUG
)
for x in range(10):
    logger2.debug("This is a test log message.")
logger.flush()
logger2.flush()