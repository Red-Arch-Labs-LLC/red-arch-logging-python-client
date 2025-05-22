from redarch_logging_client import log
from dotenv import load_dotenv
load_dotenv()

# Send a log entry
log(
    level="INFO",
    service="user-service",
    message="User created successfully.",
    user_id="user-123",
    tenant_id="tenant-xyz",
    request_id="req-456",
    context={"role": "admin", "source": "signup-form"}
)
