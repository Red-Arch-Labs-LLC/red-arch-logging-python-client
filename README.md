# logclient

A lightweight Python client for sending structured logs to a centralized Go-based logging API using signed JWT authentication.

## 🔧 Installation

```bash

pip install git+https://github.com/redarchlabs/red-arch-logger.git


## Sample Usage

1. Set up environment variables for JWT authentication:

```bash
export RARCH_LOGGING_URL="https://your-logging-api-url"
export RARCH_LOGGING_API_KEY="your_api_key"   
```

2. Use the client in your Python code:

```python
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
```

## 🧾 Parameters

The `log()` function accepts the following arguments:

| Parameter    | Type     | Required | Description                                                                 |
|--------------|----------|----------|-----------------------------------------------------------------------------|
| `level`      | `string` | ✅ Yes   | The severity level of the log (e.g. `"INFO"`, `"DEBUG"`, `"ERROR"`).       |
| `service`    | `string` | ✅ Yes   | The name of the service or application generating the log.                 |
| `message`    | `string` | ✅ Yes   | A human-readable message describing the event.                             |
| `user_id`    | `string` | ❌ No    | The ID of the user associated with the log entry, if applicable.           |
| `tenant_id`  | `string` | ❌ No    | The tenant ID for multi-tenant applications.                               |
| `request_id` | `string` | ❌ No    | A unique request identifier to trace logs across distributed services.     |
| `context`    | `object` | ❌ No    | Optional structured data (key-value pairs) for extended context.           |
