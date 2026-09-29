"""Jarvis-owned memory categories for F7.

Each store is isolated by construction and exposes an independent admission and
query surface. This module is intentionally storage-backend agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class MemoryItem:
    memory_id: str
    category: str
    text: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryStore:
    category: str

    def __init__(self, category: str) -> None:
        self.category = category
        self._items: list[MemoryItem] = []

    def admit(
        self,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
        memory_id: str | None = None,
    ) -> MemoryItem:
        text = text.strip()
        if not text:
            raise ValueError("memory text must not be empty")
        item = MemoryItem(
            memory_id=memory_id or uuid4().hex,
            category=self.category,
            text=text,
            timestamp=timestamp or datetime.now(timezone.utc),
            metadata=dict(metadata or {}),
        )
        self._items.append(item)
        return item

    def query(self, query: str = "", *, limit: int = 20) -> list[MemoryItem]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        q = query.casefold().strip()
        items = self._items
        if q:
            items = [
                item
                for item in items
                if q in item.text.casefold()
                or any(q in str(v).casefold() for v in item.metadata.values())
            ]
        return list(items[-limit:])

    def clear(self) -> None:
        self._items.clear()


class WorkingMemory(MemoryStore):
    def __init__(self) -> None:
        super().__init__("working")


class PersonalMemory(MemoryStore):
    def __init__(self) -> None:
        super().__init__("personal")


class ProjectMemory(MemoryStore):
    def __init__(self) -> None:
        super().__init__("project")


class EpisodicMemory(MemoryStore):
    def __init__(self) -> None:
        super().__init__("episodic")
