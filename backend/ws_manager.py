from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("WebSocket client connected | total=%s", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
            logger.info("WebSocket client disconnected | total=%s", len(self._connections))

    async def broadcast(self, msg_type: str, data: Any) -> None:
        payload = json.dumps({"type": msg_type, "data": data})
        stale: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
                logger.exception("Failed to broadcast WebSocket message | type=%s", msg_type)
        for ws in stale:
            self.disconnect(ws)

    def broadcast_sync(self, msg_type: str, data: Any) -> None:
        loop = _get_or_create_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(msg_type, data), loop)
        else:
            loop.run_until_complete(self.broadcast(msg_type, data))

    @property
    def count(self) -> int:
        return len(self._connections)


_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    if _loop is not None:
        return _loop
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop()


manager = ConnectionManager()
