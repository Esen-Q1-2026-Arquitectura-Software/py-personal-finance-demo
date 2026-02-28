"""WebSocket connection manager for real-time event broadcasting.

Architecture
------------
* ``ConnectionManager`` keeps a set of active WebSocket connections.
* ``manager`` is the module-level singleton used by the whole app.
* ``manager.notify(event)`` is safe to call from **sync** (threadpool)
  router code – it schedules the async broadcast on the main event loop
  via ``asyncio.run_coroutine_threadsafe``.
"""

from __future__ import annotations

import asyncio
import logging
from threading import Lock

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts events."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    # ------------------------------------------------------------------
    # Event-loop binding (call once during app lifespan startup)
    # ------------------------------------------------------------------

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._connections.append(websocket)
        logger.info("WS client connected (%d total)", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            try:
                self._connections.remove(websocket)
            except ValueError:
                pass
        logger.info("WS client disconnected (%d total)", len(self._connections))

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def broadcast(self, event: dict) -> None:
        """Send *event* as JSON to every connected client."""
        with self._lock:
            snapshot = list(self._connections)
        for ws in snapshot:
            try:
                await ws.send_json(event)
            except Exception:
                self.disconnect(ws)

    def notify(self, event: dict) -> None:
        """Call from **sync** router code running in a threadpool.

        Schedules :meth:`broadcast` on the main asyncio event loop so the
        caller never needs to ``await``.
        """
        if self._loop is not None and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(event), self._loop)


# Module-level singleton
manager = ConnectionManager()
