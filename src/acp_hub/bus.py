from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from acp_hub.events import Event

logger = logging.getLogger(__name__)

Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Minimal async event bus.

    Subscribers receive events in registration order. Each handler is awaited
    sequentially to preserve ordering guarantees. Errors in one handler do not
    prevent delivery to subsequent handlers.
    """

    def __init__(self) -> None:
        self._handlers: list[Handler] = []
        self._filters: dict[int, str | None] = {}  # handler id -> optional kind prefix filter

    def subscribe(
        self,
        handler: Handler,
        *,
        kind_prefix: str | None = None,
    ) -> Callable[[], None]:
        """
        Register *handler* to receive events. Returns an unsubscribe callable.

        If *kind_prefix* is given, handler only receives events whose ``kind``
        starts with that prefix (e.g. ``"agent."``).
        """
        hid = id(handler)
        self._handlers.append(handler)
        self._filters[hid] = kind_prefix

        def _unsub() -> None:
            try:
                self._handlers.remove(handler)
            except ValueError:
                pass
            self._filters.pop(hid, None)

        return _unsub

    async def publish(self, event: Event) -> None:
        """Fan out *event* to all matching subscribers."""
        for handler in list(self._handlers):
            prefix = self._filters.get(id(handler))
            if prefix is not None and not event.kind.startswith(prefix):
                continue
            try:
                await handler(event)
            except Exception:
                logger.exception("event handler %r failed for event kind=%s", handler, event.kind)

    @property
    def handler_count(self) -> int:
        return len(self._handlers)
