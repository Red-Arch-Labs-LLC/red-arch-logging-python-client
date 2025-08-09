import os
import time
import json
import sys
import threading
import atexit
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
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
std_out_logger = logging.getLogger("redarch.logger")
std_out_logger.setLevel(logging.INFO)

LOG_DIR = "./var/log"
MAX_LOG_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_RETRIES = 5
MAX_BACKOFF = 10  # seconds
SENTINEL = {"__stop__": True}


class LogFileBuffer:
    """A thread-safe log buffer with a separate file per process."""
    def __init__(self, service_name):
        self.log_dir = os.path.join(LOG_DIR, service_name)
        os.makedirs(self.log_dir, exist_ok=True)
        self.pid = os.getpid()
        self.buffer_file = os.path.join(self.log_dir, f"buffer_{self.pid}.jsonl")
        self.lock = threading.RLock()

    def clear(self):
        with self.lock:
            if os.path.exists(self.buffer_file):
                os.remove(self.buffer_file)

    def write(self, log_entry):
        with self.lock:
            self._rotate_if_needed()
            try:
                with open(self.buffer_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                std_out_logger.error(f"Failed to write log entry: {e}")
                std_out_logger.debug(f"Log entry content: {log_entry}")

    def _rotate_if_needed(self):
        if os.path.exists(self.buffer_file) and os.path.getsize(self.buffer_file) >= MAX_LOG_FILE_SIZE:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            rotated_name = f"buffer_{self.pid}_{timestamp}.jsonl"
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
    def __init__(self, url, jwt_secret, buffer: LogFileBuffer):
        self.url = url
        self.jwt_secret = jwt_secret
        self.buffer = buffer
        self.queue = Queue()
        self.stop_event = Event()
        self.started_event = Event()

        # IMPORTANT: monitor must be non-daemon (it spawns the worker child)
        self.process = Process(
            target=self._monitor_worker,
            daemon=False,
            args=(self.started_event, self.stop_event)
        )
        std_out_logger.info("[LoggerQueueWorker] Background process starting...")
        self.process.start()

        self._load_buffer()
        atexit.register(self.flush_and_stop)

    def flush_to_disk(self):
        while True:
            try:
                item = self.queue.get_nowait()
                if item == SENTINEL:
                    continue
                self.buffer.write(item)
            except Empty:
                break

    def _generate_jwt(self, sub):
        payload = {
            "sub": sub,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token if isinstance(token, str) else token.decode("utf-8")

    def _load_buffer(self):
        entries = self.buffer.read_all()
        std_out_logger.info(f"[LoggerQueueWorker] Reloading {len(entries)} buffered log(s) from disk.")
        for entry in entries:
            self.queue.put(entry)

    def enqueue(self, log_entry):
        self.queue.put(log_entry)

    def _monitor_worker(self, started_event, stop_event):
        std_out_logger.info("[LoggerQueueWorker] Background monitor process started.")
        # Keep a single worker process running; restart if it crashes (unless stopping)
        while not stop_event.is_set() or not started_event.is_set():
            worker_proc = Process(
                target=self._run,
                daemon=True,  # worker is safe to be daemon; it won't spawn children
                args=(started_event, stop_event)
            )
            worker_proc.start()
            std_out_logger.info(f"[LoggerQueueWorker] Started log delivery subprocess (PID: {worker_proc.pid})")

            # Wait until worker exits
            worker_proc.join()

            if stop_event.is_set():
                break

            std_out_logger.warning("[LoggerQueueWorker] Worker process exited unexpectedly. Restarting in 3 seconds...")
            time.sleep(3)

    def _deliver_or_buffer(self, item):
        item["retry_count"] = item.get("retry_count", 0)
        if item["retry_count"] >= MAX_RETRIES:
            std_out_logger.error(f"[LoggerQueueWorker] Dropping log after {MAX_RETRIES} retries: {item}")
            return

        service = item.get("service", "unknown-service")
        for attempt in range(1, 4):
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._generate_jwt(service)}"
                }
                res = requests.post(self.url, json=item, headers=headers, timeout=2)
                if res.status_code >= 400:
                    raise Exception(f"HTTP {res.status_code}: {res.text}")
                std_out_logger.debug(f"[LoggerQueueWorker] Successfully sent log: {item.get('message')}")
                return
            except Exception as e:
                std_out_logger.warning(f"[LoggerQueueWorker] Attempt {attempt} failed: {e}")
                if attempt == 3:
                    item["retry_count"] += 1
                    if item["retry_count"] < MAX_RETRIES:
                        std_out_logger.warning(f"[LoggerQueueWorker] Buffering failed log: {item}")
                        self.buffer.write(item)
                    else:
                        std_out_logger.error(f"[LoggerQueueWorker] Dropping permanently failed log: {item}")
                else:
                    time.sleep(min(2 ** attempt, MAX_BACKOFF))

    def _run(self, started_event, stop_event):
        # Child handles signals by requesting a stop
        signal.signal(signal.SIGTERM, lambda s, f: stop_event.set())
        signal.signal(signal.SIGINT, lambda s, f: stop_event.set())
        std_out_logger.info("[LoggerQueueWorker] Background worker process started.")
        started_event.set()

        while True:
            try:
                item = self.queue.get(timeout=0.5)
            except Empty:
                if stop_event.is_set():
                    break
                continue

            if item == SENTINEL:
                # Drain any remaining items queued before shutdown, then exit
                while True:
                    try:
                        next_item = self.queue.get_nowait()
                        if next_item != SENTINEL:
                            self._deliver_or_buffer(next_item)
                    except Empty:
                        break
                break

            self._deliver_or_buffer(item)

    def flush_and_stop(self):
        std_out_logger.info("[LoggerQueueWorker] Initiating shutdown...")
        self.stop_event.set()
        # Unblock any queue.get() immediately
        try:
            self.queue.put_nowait(SENTINEL)
        except Exception:
            pass

        # If worker never started, flush queue to disk and return
        if not self.started_event.wait(timeout=1.0):
            std_out_logger.warning("[LoggerQueueWorker] Worker process never fully started. Flushing queue to disk.")
            self.flush_to_disk()
            return

        # Join the monitor process; terminate if it doesn't exit quickly
        if self.process.is_alive():
            std_out_logger.info("[LoggerQueueWorker] Waiting for log worker to shut down...")
            self.process.join(timeout=2.0)
            if self.process.is_alive():
                std_out_logger.warning("[LoggerQueueWorker] Forcing monitor process to terminate...")
                self.process.terminate()


class ThreadedLogger:
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
            return
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

    def debug(self, *args, **kwargs): self._log(LOG_LEVEL_DEBUG, *args, **kwargs)
    def info(self, *args, **kwargs): self._log(LOG_LEVEL_INFO, *args, **kwargs)
    def warn(self, *args, **kwargs): self._log(LOG_LEVEL_WARN, *args, **kwargs)
    def error(self, *args, **kwargs): self._log(LOG_LEVEL_ERROR, *args, **kwargs)
    def fatal(self, *args, **kwargs): self._log(LOG_LEVEL_FATAL, *args, **kwargs)
    def stop(self): self.worker.flush_and_stop()
    def flush(self): self.worker.flush_and_stop()
