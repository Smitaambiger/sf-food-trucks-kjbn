import logging
import sys
import time
import uuid
from contextvars import ContextVar

from app.core.config import get_settings

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Injects the current request id (if any) into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        return True


def set_request_id(request_id: str | None = None) -> str:
    rid = request_id or uuid.uuid4().hex[:12]
    _request_id_ctx.set(rid)
    return rid


def configure_logging() -> None:
    settings = get_settings()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s.%(msecs)03dZ level=%(levelname)s logger=%(name)s "
            "request_id=%(request_id)s msg=%(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(settings.log_level)
    root.handlers = [handler]

    # Keep third-party libraries a bit quieter than our own app logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class log_duration:
    """Small context manager used to log how long a block took, e.g. an outgoing call."""

    def __init__(self, logger: logging.Logger, label: str):
        self.logger = logger
        self.label = label

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        if exc_type is None:
            self.logger.info("%s completed in %.1fms", self.label, elapsed_ms)
        else:
            self.logger.warning("%s failed after %.1fms: %s", self.label, elapsed_ms, exc)
