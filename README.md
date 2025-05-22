# Overview of red-arch-logging-python-client

A lightweight Python client for sending structured logs to a centralized Go-based logging API using signed JWT authentication.


The logging client supports two modes of operation:

## General Logger (Default)
Logs are immediately sent using requests.post() from the main thread.

Any network error may slow down the caller or result in lost logs.

Good for short scripts or testing, but not recommended for production workloads.

## ThreadedLogger (Recommended)
Logs are queued and sent by a dedicated background worker using a monitored subprocess.

Buffered to local disk if sending fails (in ./var/log/<service>/buffer.jsonl).

Can retry, persist across restarts, and flush on shutdown.

Non-blocking and safe for production apps.

# 🔧 Installation

```bash

pip install git+https://github.com/redarchlabs/red-arch-logging-python-client.git


## Sample Usage

1. Set up environment variables for JWT authentication:

```bash
export RARCH_LOGGING_URL="https://your-logging-api-url"
export RARCH_LOGGING_API_KEY="your_api_key"   
```

2. Use the client in your Python code:

### Example: Simepl Logger (Blocking)

```python
#Note: This example assumes you have set up the environment variables as shown above.
from dotenv import load_dotenv
load_dotenv()

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

### Advanced Logger (Threaded)

```python
#note: This example assumes you have set up the environment variables as shown above.
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

logger.debug()   #same usage as above in the simple logger example

#it is important to flush the logs before exiting the program
#to ensure all logs are sent to the server
logger.flush()  #flushes the logs to the server
```



## 🧾 Parameters

The `log()` functions accepts the following arguments:

| Parameter    | Type     | Required | Description                                                                 |
|--------------|----------|----------|-----------------------------------------------------------------------------|
| `service`    | `string` | ✅ Yes   | The name of the service or application generating the log.                 |
| `logger_name`         | `string` | ❌ No    | The name of the logger emitting the log (defaults to the `service` value if not specified).  |
| `message`    | `string` | ✅ Yes   | A human-readable message describing the event.                             |
| `user_id`    | `string` | ❌ No    | The ID of the user associated with the log entry, if applicable.           |
| `tenant_id`  | `string` | ❌ No    | The tenant ID for multi-tenant applications.                               |
| `request_id` | `string` | ❌ No    | A unique request identifier to trace logs across distributed services.     |
| `context`    | `object` | ❌ No    | Optional structured data (key-value pairs) for extended context.           |
| `client_log_datetime` | `string` | ❌ No    | The timestamp (ISO 8601 UTC) when the event occurred on the client. Defaults to current UTC time if omitted. |

