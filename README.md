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
from redarch_logging_client import log
from dotenv import load_dotenv
load_dotenv()


log_info(
    service="user-service",
    message="User created successfully.",
    user_id="user-123",
    tenant_id="tenant-xyz",
    request_id="req-456",
    context={"role": "admin", "source": "signup-form"}
)

log_error(
    service="billing-service",
    message="Payment failed: insufficient funds.",
    user_id="user-456",
    context={"amount": 99.95, "currency": "USD"}
)

log_debug(
    service="billing-service",
    message="Attempting to validate promo code.",
    user_id="user-123",
    context={"promo_code": "SUMMER2025", "step": "pre-checkout"}
)

log_warn(
    service="inventory-service",
    message="Inventory low for SKU: PROD-00123",
    tenant_id="tenant-789",
    context={"sku": "PROD-00123", "remaining_stock": 3}
)

log_error(
    service="billing-service",
    message="Payment failed: insufficient funds.",
    user_id="user-456",
    tenant_id="tenant-xyz",
    request_id="req-998877",
    context={"amount": 99.95, "currency": "USD"}
)

log_fatal(
    service="auth-service",
    message="JWT verification failed due to corrupted secret key.",
    request_id="req-12345",
    context={"token_prefix": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "env": "prod"}
)


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
