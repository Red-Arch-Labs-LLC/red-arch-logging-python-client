import os
import time
import requests
import jwt
from uuid import uuid4
from datetime import datetime, timezone  # 🆕
from .log_levels import (
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_FATAL,
    LOG_LEVELS,
)

def should_log(configured_level, message_level):
    return LOG_LEVELS.index(message_level) >= LOG_LEVELS.index(configured_level)

class Logger:
    def __init__(self, service, level=None, logger_name=None):
        self.service = service
        self.logger_name = logger_name or service
        self.level = (level or os.getenv("RARCH_LOGGING_DEFAULT_LEVEL", LOG_LEVEL_DEBUG)).upper()
        self.url = os.getenv("RARCH_LOGGING_URL", "http://localhost:8080/log")
        self.secret = os.getenv("RARCH_LOGGING_API_KEY", "")

    def _generate_jwt(self):
        payload = {
            "sub": self.service,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def _generate_request_id(self):
        return str(uuid4())

    def _send(self, level, message, user_id=None, tenant_id=None, request_id=None, context=None, client_log_datetime=None):
        if not should_log(self.level, level):
            return

        # Use provided datetime or fallback to current UTC
        if not client_log_datetime:
            client_log_datetime = datetime.now(timezone.utc).isoformat()

        payload = {
            "level": level,
            "service": self.service,
            "logger_name": self.logger_name,
            "message": message,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "request_id": request_id or self._generate_request_id(),
            "context": context or {},
            "client_log_datetime": client_log_datetime,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._generate_jwt()}",
        }

        try:
            response = requests.post(self.url, json=payload, headers=headers)
            response.raise_for_status()
        except Exception as e:
            print(f"[LOGGING ERROR] {e}")

    def debug(self, message, *, user_id=None, tenant_id=None, request_id=None, context=None, client_log_datetime=None):
        self._send(LOG_LEVEL_DEBUG, message, user_id, tenant_id, request_id, context, client_log_datetime)

    def info(self, message, *, user_id=None, tenant_id=None, request_id=None, context=None, client_log_datetime=None):
        self._send(LOG_LEVEL_INFO, message, user_id, tenant_id, request_id, context, client_log_datetime)

    def warn(self, message, *, user_id=None, tenant_id=None, request_id=None, context=None, client_log_datetime=None):
        self._send(LOG_LEVEL_WARN, message, user_id, tenant_id, request_id, context, client_log_datetime)

    def error(self, message, *, user_id=None, tenant_id=None, request_id=None, context=None, client_log_datetime=None):
        self._send(LOG_LEVEL_ERROR, message, user_id, tenant_id, request_id, context, client_log_datetime)

    def fatal(self, message, *, user_id=None, tenant_id=None, request_id=None, context=None, client_log_datetime=None):
        self._send(LOG_LEVEL_FATAL, message, user_id, tenant_id, request_id, context, client_log_datetime)
