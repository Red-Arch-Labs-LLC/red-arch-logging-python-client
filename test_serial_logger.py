from dotenv import load_dotenv
load_dotenv()

from redarch_logging_client.logger import Logger
from redarch_logging_client.log_levels import (
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_FATAL
)

# Create a logger for the "billing" service with INFO-level filtering
logger = Logger(service="billing", logger_name="invoice-processor", level=LOG_LEVEL_INFO)

# This will NOT be logged because it's below the configured INFO level
logger.debug("Checking discount eligibility", context={"user_id": "user-001"})

# These WILL be logged
logger.info("Invoice created", user_id="user-001", tenant_id="client-123")
logger.warn("Invoice overdue", context={"invoice_id": "INV-9981"})
logger.error("Failed to apply payment", context={"reason": "insufficient funds"})
logger.fatal("Critical error in billing pipeline", request_id="req-abc-123")

#sample with time
logger.warn("Custom log time", tenant_id="TENANT_123", client_log_datetime="2024-05-22T22:30:00Z")