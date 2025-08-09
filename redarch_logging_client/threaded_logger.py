# threaded_logger.py
import atexit
import json
import logging
import os
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from logging.handlers import QueueHandler, QueueListener
from queue import SimpleQueue

import jwt
import requests

logging.raiseExceptions = False  # never crash app on logging errors


# ---------------------------- Config ----------------------------

@dataclass
class LoggerConfig:
    service: str = os.getenv("RARCH_LOGGING_SERVICE", "unspecified-service")
    logger_name: str | None = None
    level: int = logging.INFO
    api_url: str = os.getenv("RARCH_LOGGING_URL", "http://localhost:8080/log")
    jwt_secret: str = os.getenv("RARCH_LOGGING_API_KEY", "")
    api_timeout: float = 2.0
    buffer_root: str = "./var/log"
    stdout: bool = True  # mirror to stdout


# ----------------------- Single-file buffer ---------------------

class _JsonLineBuffer:
    """
    Single JSONL buffer per service:
      ./var/log/<service>/buffer.jsonl

    - Writes are atomic on POSIX via O_APPEND write.
    - On startup, atomically renames buffer.jsonl -> buffer.sending-<ts>.jsonl
      and drains; failed lines are appended back to buffer.jsonl.
    """
    def __init__(self, service: str, root_dir: str):
        self._dir = os.path.join(root_dir, service)
        os.makedirs(self._dir, exist_ok=True)
        self._path = os.path.join(self._dir, "buffer.jsonl")

    @property
    def path(self) -> str:
        return self._path

    def write(self, obj: dict) -> None:
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        fd = os.open(self._path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)

    def begin_drain(self) -> str | None:
        if not os.path.exists(self._path) or os.path.getsize(self._path) == 0:
            return None
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        sending = os.path.join(self._dir, f"buffer.sending-{ts}.jsonl")
        try:
            os.replace(self._path, sending)  # atomic
            return sending
        except FileNotFoundError:
            return None

    def drain_file(self, sending_path: str):
        with open(sending_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    # skip corrupted line
                    continue
        try:
            os.remove(sending_path)
        except Exception:
            pass


# ----------------------- API target handler ---------------------

class _APILogHandler(logging.Handler):
    """
    Posts JSON logs to API; on any failure, appends to buffer.
    Keeps your schema: service, logger_name, request_id, context, etc.
    """
    def __init__(self, cfg: LoggerConfig, buffer: _JsonLineBuffer):
        super().__init__(level=cfg.level)
        self.cfg = cfg
        self.buffer = buffer
        self.session = requests.Session()

    def _jwt(self, sub: str) -> str:
        now = int(datetime.now(tz=timezone.utc).timestamp())
        payload = {"sub": sub or "unknown-service", "iat": now, "exp": now + 3600}
        token = jwt.encode(payload, self.cfg.jwt_secret, algorithm="HS256")
        return token if isinstance(token, str) else token.decode("utf-8")

    def _payload_from_record(self, record: logging.LogRecord) -> dict:
        request_id = getattr(record, "request_id", None) or f"auto-{int(record.created*1000)}"
        return {
            "level": record.levelname,
            "service": getattr(record, "service", None) or self.cfg.service,
            "logger_name": getattr(record, "logger_name", None) or self.cfg.logger_name or record.name,
            "message": record.getMessage(),
            "user_id": getattr(record, "user_id", None),
            "tenant_id": getattr(record, "tenant_id", None),
            "request_id": request_id,
            "context": getattr(record, "context", {}) or {},
            "client_log_datetime": getattr(record, "client_log_datetime", None)
                or datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
        }

    def emit(self, record: logging.LogRecord) -> None:
        payload = self._payload_from_record(record)
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._jwt(payload.get('service'))}",
            }
            resp = self.session.post(
                self.cfg.api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                timeout=self.cfg.api_timeout,
            )
            if not (200 <= resp.status_code < 300):
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception:
            # On any failure, persist to buffer
            try:
                self.buffer.write(payload)
            except Exception:
                # swallow as last resort
                pass


# --------------------- optional stdout mirror -------------------

class _StdoutHandler(logging.StreamHandler):
    def __init__(self, level: int):
        super().__init__(stream=sys.stdout)
        self.setLevel(level)
        self.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))


# ----------------------------- Singleton ------------------------

class ThreadedLogger:
    """
    Lazy, self-initializing singleton that:
      - wires root/named loggers to a QueueHandler
      - runs a QueueListener thread with API + optional stdout handlers
      - drains a single service buffer file on startup
      - shuts down cleanly via atexit without hanging the app
    """
    _instance = None
    _create_lock = threading.Lock()

    def __new__(cls):
        with cls._create_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self._cfg = LoggerConfig()
        self._pid = None
        self._queue: SimpleQueue = SimpleQueue()
        self._listener: QueueListener | None = None
        self._queue_handler: QueueHandler | None = None
        self._lock = threading.RLock()
        self._buffer = _JsonLineBuffer(self._cfg.service, self._cfg.buffer_root)

        self._ensure_started()
        self._drain_buffer_once()
        atexit.register(self._stop)

    # ---- lifecycle ----

    def _targets(self):
        targets = [_APILogHandler(self._cfg, self._buffer)]
        if self._cfg.stdout:
            targets.append(_StdoutHandler(self._cfg.level))
        return targets

    def _ensure_started(self):
        with self._lock:
            pid = os.getpid()
            if self._listener and self._pid == pid:
                return

            if self._listener:
                try:
                    self._listener.stop()
                except Exception:
                    pass
                self._listener = None

            self._listener = QueueListener(self._queue, *self._targets(), respect_handler_level=True)
            self._listener.start()

            self._queue_handler = QueueHandler(self._queue)
            self._queue_handler.setLevel(self._cfg.level)

            self._pid = pid

    def _stop(self):
        with self._lock:
            if self._listener:
                try:
                    self._listener.stop()
                except Exception:
                    pass
                self._listener = None

    def _drain_buffer_once(self):
        sending = self._buffer.begin_drain()
        if not sending:
            return
        api_handler = _APILogHandler(self._cfg, self._buffer)
        for obj in self._buffer.drain_file(sending):
            # Reuse API handler logic; on failure it re-appends to buffer.jsonl
            try:
                # LogRecord to keep the same formatting path (ensures parity)
                levelname = (obj.get("level") or "INFO").upper()
                levelno = logging._nameToLevel.get(levelname, logging.INFO)
                record = logging.LogRecord(
                    name=(obj.get("logger_name") or self._cfg.logger_name or "buffer"),
                    level=levelno,
                    pathname=__file__,
                    lineno=0,
                    msg=obj.get("message", ""),
                    args=(),
                    exc_info=None,
                )
                # Attach original fields
                record.service = obj.get("service")
                record.logger_name = obj.get("logger_name")
                record.user_id = obj.get("user_id")
                record.tenant_id = obj.get("tenant_id")
                record.request_id = obj.get("request_id")
                record.context = obj.get("context")
                record.client_log_datetime = obj.get("client_log_datetime")
                api_handler.emit(record)
            except Exception:
                try:
                    self._buffer.write(obj)
                except Exception:
                    pass

    # ---- public API ----

    def configure(self, *,
                  service: str | None = None,
                  logger_name: str | None = None,
                  level: int | None = None,
                  api_url: str | None = None,
                  jwt_secret: str | None = None,
                  api_timeout: float | None = None,
                  buffer_root: str | None = None,
                  stdout: bool | None = None):
        changed = False
        if service is not None and service != self._cfg.service:
            self._cfg.service = service; changed = True
        if logger_name is not None and logger_name != self._cfg.logger_name:
            self._cfg.logger_name = logger_name; changed = True
        if level is not None and level != self._cfg.level:
            self._cfg.level = level; changed = True
        if api_url is not None and api_url != self._cfg.api_url:
            self._cfg.api_url = api_url; changed = True
        if jwt_secret is not None and jwt_secret != self._cfg.jwt_secret:
            self._cfg.jwt_secret = jwt_secret; changed = True
        if api_timeout is not None and api_timeout != self._cfg.api_timeout:
            self._cfg.api_timeout = api_timeout; changed = True
        if buffer_root is not None and buffer_root != self._cfg.buffer_root:
            self._cfg.buffer_root = buffer_root; changed = True
        if stdout is not None and stdout != self._cfg.stdout:
            self._cfg.stdout = stdout; changed = True

        if changed:
            with self._lock:
                # rebuild buffer + listener with new config
                self._buffer = _JsonLineBuffer(self._cfg.service, self._cfg.buffer_root)
                if self._listener:
                    try:
                        self._listener.stop()
                    except Exception:
                        pass
                    self._listener = None
                self._pid = None
            self._ensure_started()
            # do not drain here again; only on process start

    def get_logger(self, name: str | None = None) -> logging.Logger:
        self._ensure_started()
        logger = logging.getLogger(name)
        with self._lock:
            if self._queue_handler and not any(isinstance(h, QueueHandler) for h in logger.handlers):
                logger.addHandler(self._queue_handler)
            if logger.level == logging.NOTSET:
                logger.setLevel(self._cfg.level)
        return logger


# public singleton
#threaded_logger = ThreadedLogger()
