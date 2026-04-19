"""JSON log formatter + request middleware. No extra dependencies."""

from __future__ import annotations

import json
import logging
import sys
import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import Response


class JsonFormatter(logging.Formatter):
    """One-line JSON per log record. Merges extras under `"extra"`."""

    _RESERVED = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "message", "asctime", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in self._RESERVED and not k.startswith("_")
        }
        if extras:
            payload["extra"] = extras
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
    # Uvicorn's own loggers use the root handler now.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True


_log = logging.getLogger("brand3.web.access")


async def access_log_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        _log.exception(
            "request_error",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
        raise
    _log.info(
        "request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": int((time.monotonic() - started) * 1000),
        },
    )
    return response
