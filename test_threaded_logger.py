from dotenv import load_dotenv
load_dotenv()
import time
from redarch_logging_client.threading import ThreadedLogger
from redarch_logging_client.log_levels import LOG_LEVEL_DEBUG  # or any level you prefer

logger = ThreadedLogger(
    service="test-reselient-logger",
    logger_name="test_logger",
    level=LOG_LEVEL_DEBUG
)
for x in range(100):
    logger.debug("This is a test log message.")


logger.flush()