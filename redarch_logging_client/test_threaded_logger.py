from dotenv import load_dotenv
load_dotenv()
import time
#from redarch_logging_client.threaded_logger import ThreadedLogger
#from redarch_logging_client.log_levels import LOG_LEVEL_DEBUG  # or any level you prefer
from threaded_logger import ThreadedLogger

logger = ThreadedLogger()
log = logger.get_logger("test")

log.info("Starting up")
log.warning("Something might be wrong")
log.error("Something is definitely wrong")
