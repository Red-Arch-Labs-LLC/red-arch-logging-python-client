import os
import time
import json
import threading
from multiprocessing import Queue, Process, Event
from queue import Empty
import jwt
import requests
import signal
from uuid import uuid4
from datetime import datetime, timezone
from redarch_logging_client.log_levels import (
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR,
    LOG_LEVEL_FATAL,
    LOG_LEVELS,
)

LOG_DIR = "./var/log"
MAX_LOG_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

class LogFileBuffer:
    """A thread-safe buffer for log entries, stored in a JSONL file."""
    def __init__(self, service_name):
        self.log_dir = os.path.join(LOG_DIR, service_name)
        os.makedirs(self.log_dir, exist_ok=True)
        self.buffer_file = os.path.join(self.log_dir, "buffer.jsonl")
        self.lock = threading.RLock()

    def clear(self):
        with self.lock:
            if os.path.exists(self.buffer_file):
                os.remove(self.buffer_file)

    def write(self, log_entry):
        with self.lock:
            self._rotate_if_needed()
            with open(self.buffer_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")

    def _rotate_if_needed(self):
        if os.path.exists(self.buffer_file) and os.path.getsize(self.buffer_file) >= MAX_LOG_FILE_SIZE:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            rotated_name = f"buffer_{timestamp}.jsonl"
            os.rename(self.buffer_file, os.path.join(self.log_dir, rotated_name))

    def read_all(self):
        if not os.path.exists(self.buffer_file):
            return []
        with self.lock:
            with open(self.buffer_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            os.remove(self.buffer_file)
        return [json.loads(line) for line in lines if line.strip()]

_worker_instance = None
_worker_lock = threading.RLock()

class LoggerQueueWorker:
    """
    A class to manage a queue of log entries and send them to a remote server.
    It uses a separate process to handle the log delivery, ensuring that the main application
    remains responsive.
    """
    def __init__(self, url, jwt_secret, buffer: LogFileBuffer):
        self.url = url
        self.jwt_secret = jwt_secret
        self.buffer = buffer
        self.queue = Queue()
        self.stop_event = Event()
        self.process = Process(target=self._monitor_worker, daemon=False)
        self.process.start()
        self._load_buffer()

    def _generate_jwt(self, sub):
        payload = {
            "sub": sub,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token if isinstance(token, str) else token.decode("utf-8")

    def _load_buffer(self):
        for entry in self.buffer.read_all():
            self.queue.put(entry)

    def enqueue(self, log_entry):
        self.queue.put(log_entry)

    def _monitor_worker(self):
        while not self.stop_event.is_set():
            worker_proc = Process(target=self._run, daemon=False)
            worker_proc.start()
            print(f"[LoggerQueueWorker] Started log delivery subprocess (PID: {worker_proc.pid})")
            worker_proc.join()
            if self.stop_event.is_set():
                break
            print("[LoggerQueueWorker] Worker process exited unexpectedly. Restarting in 3 seconds...")
            time.sleep(3)

    def _run(self):
        signal.signal(signal.SIGTERM, lambda s, f: self.stop_event.set())
        signal.signal(signal.SIGINT, lambda s, f: self.stop_event.set())
        print("[LoggerQueueWorker] Background process started.")
        while True:
            try:
                if self.stop_event.is_set() and self.queue.empty():
                    break
                item = self.queue.get(timeout=1)
                service = item.get("service", "unknown-service")
                for attempt in range(1, 4):
                    try:
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self._generate_jwt(service)}"
                        }
                        res = requests.post(self.url, json=item, headers=headers, timeout=2)
                        res.raise_for_status()
                        break  # success
                    except Exception:
                        if attempt == 3 and not self.stop_event.is_set():
                            self.buffer.write(item)
                        else:
                            time.sleep(min(2 ** attempt, 10))
            except Empty:
                continue

    def flush_and_stop(self):
        print("[LoggerQueueWorker] Shutting down and flushing remaining logs...")
        self.stop_event.set()
        self.process.join(timeout=10)

class ThreadedLogger:
    """
    A resilient logger that uses a queue to buffer log entries and send them to a remote server.
    It handles network failures and other issues gracefully, ensuring that logs are not lost.
    """
    def __init__(self, service, level=LOG_LEVEL_DEBUG, logger_name=None):
        global _worker_instance
        with _worker_lock:
            if _worker_instance is None:
                env_url = os.getenv("RARCH_LOGGING_URL", "http://localhost:8080/log")
                env_secret = os.getenv("RARCH_LOGGING_API_KEY", "")
                _worker_instance = LoggerQueueWorker(
                    url=env_url,
                    jwt_secret=env_secret,
                    buffer=LogFileBuffer(service)
                )
        self.service = service
        self.logger_name = logger_name or service
        self.level = level
        self.worker = _worker_instance

    def _log(self, level, message, user_id=None, tenant_id=None, request_id=None, context=None, client_log_datetime=None):
        if LOG_LEVELS.index(level) < LOG_LEVELS.index(self.level):
            return  # Skip logs below configured level

        entry = {
            "level": level,
            "service": self.service,
            "logger_name": self.logger_name,
            "message": message,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "request_id": request_id or str(uuid4()),
            "context": context or {},
            "client_log_datetime": client_log_datetime or datetime.now(timezone.utc).isoformat(),
        }
        self.worker.enqueue(entry)

    def debug(self, *args, **kwargs):
        self._log(LOG_LEVEL_DEBUG, *args, **kwargs)

    def info(self, *args, **kwargs):
        self._log(LOG_LEVEL_INFO, *args, **kwargs)

    def warn(self, *args, **kwargs):
        self._log(LOG_LEVEL_WARN, *args, **kwargs)

    def error(self, *args, **kwargs):
        self._log(LOG_LEVEL_ERROR, *args, **kwargs)

    def fatal(self, *args, **kwargs):
        self._log(LOG_LEVEL_FATAL, *args, **kwargs)

    def stop(self):
        self.worker.flush_and_stop()

    def flush(self):
        self.worker.flush_and_stop()