import requests
import jwt
import time
import os

LOGGING_URL = os.getenv("RARCH_LOGGING_URL", "http://localhost:8080/log")
JWT_SECRET = os.getenv("RARCH_JWT_SECRET", "")

def generate_jwt():
    payload = {
        "sub": "python-client",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def log(level, service, message, user_id=None, tenant_id=None, request_id=None, context=None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {generate_jwt()}"
    }
    payload = {
        "level": level,
        "service": service,
        "message": message,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "request_id": request_id,
        "context": context or {}
    }
    try:
        response = requests.post(LOGGING_URL, json=payload, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"[LOGGING ERROR] {e}")

def log_info(service, message, *, user_id=None, tenant_id=None, request_id=None, context=None):
    log("INFO", service, message, user_id, tenant_id, request_id, context)

def log_debug(service, message, *, user_id=None, tenant_id=None, request_id=None, context=None):
    log("DEBUG", service, message, user_id, tenant_id, request_id, context)

def log_warn(service, message, *, user_id=None, tenant_id=None, request_id=None, context=None):
    log("WARN", service, message, user_id, tenant_id, request_id, context)

def log_error(service, message, *, user_id=None, tenant_id=None, request_id=None, context=None):
    log("ERROR", service, message, user_id, tenant_id, request_id, context)

def log_fatal(service, message, *, user_id=None, tenant_id=None, request_id=None, context=None):
    log("FATAL", service, message, user_id, tenant_id, request_id, context)
