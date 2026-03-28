from __future__ import annotations

import logging
import os
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("liveo.debug")

_DEFAULT_LOG_LIMIT = 300
_LOG_LIMIT = int(os.getenv("LIVEO_DEBUG_LOG_LIMIT", str(_DEFAULT_LOG_LIMIT)))
_entries: deque[dict[str, Any]] = deque(maxlen=max(_LOG_LIMIT, 50))
_lock = threading.Lock()
_sink: Callable[[dict[str, Any]], None] | None = None
_configured = False


def configure_debug_logging() -> None:
    global _configured
    if _configured:
        return

    level_name = os.getenv("LIVEO_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    else:
        root_logger.setLevel(level)

    _configured = True


def set_debug_sink(sink: Callable[[dict[str, Any]], None] | None) -> None:
    global _sink
    _sink = sink


def clear_debug_logs() -> None:
    with _lock:
        _entries.clear()


def get_debug_logs(limit: int | None = None) -> list[dict[str, Any]]:
    with _lock:
        if limit is None:
            return list(_entries)
        return list(_entries)[-max(limit, 0):]


def record_debug_log(
    source: str,
    event: str,
    message: str,
    *,
    level: str = "info",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "id": f"dbg-{uuid.uuid4().hex[:10]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "origin": "backend",
        "source": source,
        "event": event,
        "level": level.lower(),
        "message": message,
        "details": _sanitize(details or {}),
    }

    with _lock:
        _entries.append(entry)

    _emit_log_line(entry)

    if _sink is not None:
        try:
            _sink(entry)
        except Exception:
            logger.exception("Failed to forward debug log entry")

    return entry


def _emit_log_line(entry: dict[str, Any]) -> None:
    details = entry.get("details") or {}
    details_str = f" | details={details}" if details else ""
    log_fn = getattr(logger, entry["level"], logger.info)
    log_fn(
        "%s | %s | %s%s",
        entry["source"],
        entry["event"],
        entry["message"],
        details_str,
    )


def _sanitize(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return str(value)

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): _sanitize(val, depth=depth + 1)
            for key, val in list(value.items())[:20]
        }

    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item, depth=depth + 1) for item in list(value)[:20]]

    return str(value)
