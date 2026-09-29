"""Small in-process event bus for the standalone V0 runtime."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from .contracts import JarvisEvent

EventHandler = Callable[[JarvisEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._all_handlers: list[EventHandler] = []

    def subscribe(self, kind: str, handler: EventHandler) -> None:
        self._handlers[kind].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        self._all_handlers.append(handler)

    def publish(self, event: JarvisEvent) -> None:
        for handler in tuple(self._handlers.get(event.kind, ())):
            handler(event)
        for handler in tuple(self._all_handlers):
            handler(event)
