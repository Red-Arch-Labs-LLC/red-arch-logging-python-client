# logclient

A lightweight Python client for sending structured logs to a centralized Go-based logging API using signed JWT authentication.

## 🔧 Installation

```bash

pip install git+https://github.com/redarchlabs/red-arch-logging-python-client.git


## Sample Usage

1. Set up environment variables for JWT authentication:

```bash
export RARCH_LOGGING_URL="https://your-logging-api-url"
export RARCH_LOGGING_API_KEY="your_api_key"   
```

2. Use the client in your Python code:

```python
from redarch_logging_client import get_logger, set_log_level
from redarch_logging_client import LOG_LEVEL_DEBUG, LOG_LEVEL_INFO, LOG_LEVEL_WARN, LOG_LEVEL_ERROR, LOG_LEVEL_FATAL

print("Sending test logs...")

# Initialize logger
logger = get_logger(service="test-service", logger_name="test_logger")

# Set log level to DEBUG
set_log_level(service="test-service", logger_name="test_logger", level=LOG_LEVEL_DEBUG)

# Define context for this simulated request
user_id = "user_123"
tenant_id = "tenant_abc"
request_id = "req_456"
context = {
    "action": "test_logging",
    "details": {
        "step": "demo",
        "test_case": "full_context"
    }
}

# Send logs at various levels with context
logger.info("This is a test log message.", user_id=user_id, tenant_id=tenant_id, request_id=request_id, context=context)
logger.debug("This is a test debug message.", user_id=user_id, tenant_id=tenant_id, request_id=request_id, context=context)
logger.warn("This is a test warning message.", user_id=user_id, tenant_id=tenant_id, request_id=request_id, context=context)
logger.error("This is a test error message.", user_id=user_id, tenant_id=tenant_id, request_id=request_id, context=context)
logger.fatal("This is a test fatal error.", user_id=user_id, tenant_id=tenant_id, request_id=request_id, context=context)

print("Done sending logs..")



```

## 🧾 Parameters

The `log()` functions accepts the following arguments:

| Parameter    | Type     | Required | Description                                                                 |
|--------------|----------|----------|-----------------------------------------------------------------------------|
| `service`    | `string` | ✅ Yes   | The name of the service or application generating the log.                 |
| `message`    | `string` | ✅ Yes   | A human-readable message describing the event.                             |
| `user_id`    | `string` | ❌ No    | The ID of the user associated with the log entry, if applicable.           |
| `tenant_id`  | `string` | ❌ No    | The tenant ID for multi-tenant applications.                               |
| `request_id` | `string` | ❌ No    | A unique request identifier to trace logs across distributed services.     |
| `context`    | `object` | ❌ No    | Optional structured data (key-value pairs) for extended context.           |
