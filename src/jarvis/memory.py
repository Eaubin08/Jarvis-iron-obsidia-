"""Jarvis-owned memory stores for the V0 context layer."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from .contracts import JarvisEvent


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid4().hex


@dataclass(frozen=True)
class MemoryRecord:
    category: str
    text: str
    provenance: str
    record_id: str = field(default_factory=_new_id)
    timestamp: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdmissionDecision:
    admit: bool
    category: str
    reason: str
    durable: bool


class CategoryAdmissionPolicy:
    category: str
    durable: bool

    def evaluate(self, text: str, metadata: dict[str, Any] | None = None) -> AdmissionDecision:
        if not text.strip():
            return AdmissionDecision(False, self.category, "empty text", self.durable)
        return AdmissionDecision(True, self.category, "explicit admission", self.durable)


class WorkingAdmissionPolicy(CategoryAdmissionPolicy):
    category = "working"
    durable = False


class PersonalAdmissionPolicy(CategoryAdmissionPolicy):
    category = "personal"
    durable = True


class ProjectAdmissionPolicy(CategoryAdmissionPolicy):
    category = "project"
    durable = True


class EpisodicAdmissionPolicy(CategoryAdmissionPolicy):
    category = "episodic"
    durable = True


class PerceptualAdmissionPolicy(CategoryAdmissionPolicy):
    category = "perceptual"
    durable = False

    def evaluate(self, text: str, metadata: dict[str, Any] | None = None) -> AdmissionDecision:
        return AdmissionDecision(False, self.category, "perceptual timeline is queried, not copied", False)


@dataclass(frozen=True)
class RetentionPolicy:
    max_records: int | None = None

    def apply(self, records: list[MemoryRecord]) -> list[MemoryRecord]:
        if self.max_records is None or self.max_records < 0:
            return list(records)
        return list(records[-self.max_records :])


class MemoryBackend:
    def load(self, category: str) -> list[MemoryRecord]: ...
    def save(self, category: str, records: Iterable[MemoryRecord]) -> None: ...


class JsonlMemoryBackend:
    """Simple deterministic local storage owned by Jarvis V0."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, category: str) -> Path:
        return self.root / f"{category}.jsonl"

    def load(self, category: str) -> list[MemoryRecord]:
        path = self._path(category)
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
            records.append(MemoryRecord(**data))
        return records

    def save(self, category: str, records: Iterable[MemoryRecord]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        rows = []
        for record in records:
            data = asdict(record)
            data["timestamp"] = record.timestamp.isoformat()
            rows.append(json.dumps(data, sort_keys=True))
        self._path(category).write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


class MemoryStore:
    category: str

    def __init__(
        self,
        *,
        admission_policy: CategoryAdmissionPolicy,
        retention_policy: RetentionPolicy | None = None,
        backend: MemoryBackend | None = None,
    ) -> None:
        self.admission_policy = admission_policy
        self.retention_policy = retention_policy or RetentionPolicy()
        self.backend = backend
        self._records = list(backend.load(admission_policy.category)) if backend else []

    @property
    def category(self) -> str:
        return self.admission_policy.category

    def admit(
        self,
        text: str,
        *,
        provenance: str,
        metadata: dict[str, Any] | None = None,
    ) -> AdmissionDecision:
        metadata = dict(metadata or {})
        decision = self.admission_policy.evaluate(text, metadata)
        if not decision.admit:
            return decision
        record = MemoryRecord(
            category=self.category,
            text=text.strip(),
            provenance=provenance,
            metadata=metadata,
        )
        self._records.append(record)
        self._records = self.retention_policy.apply(self._records)
        if self.backend is not None:
            self.backend.save(self.category, self._records)
        return decision

    def query(self, query: str = "", *, limit: int = 10) -> list[MemoryRecord]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        needle = query.casefold().strip()
        records = self._records
        if needle:
            records = [
                record
                for record in records
                if needle in record.text.casefold()
                or any(needle in str(value).casefold() for value in record.metadata.values())
            ]
        return list(records[-limit:])


class WorkingMemory(MemoryStore):
    def __init__(self, *, retention_policy: RetentionPolicy | None = None) -> None:
        super().__init__(
            admission_policy=WorkingAdmissionPolicy(),
            retention_policy=retention_policy or RetentionPolicy(max_records=50),
        )

    def remember_event(self, event: JarvisEvent) -> None:
        text = event.payload.get("text") or event.payload.get("summary") or event.kind
        self.admit(str(text), provenance=f"event:{event.event_id}", metadata={"event_kind": event.kind})


class PersonalMemory(MemoryStore):
    def __init__(self, backend: MemoryBackend, *, retention_policy: RetentionPolicy | None = None) -> None:
        super().__init__(
            admission_policy=PersonalAdmissionPolicy(),
            retention_policy=retention_policy,
            backend=backend,
        )


class ProjectMemory(MemoryStore):
    def __init__(self, backend: MemoryBackend, *, retention_policy: RetentionPolicy | None = None) -> None:
        super().__init__(
            admission_policy=ProjectAdmissionPolicy(),
            retention_policy=retention_policy,
            backend=backend,
        )


class EpisodicMemory(MemoryStore):
    def __init__(self, backend: MemoryBackend, *, retention_policy: RetentionPolicy | None = None) -> None:
        super().__init__(
            admission_policy=EpisodicAdmissionPolicy(),
            retention_policy=retention_policy,
            backend=backend,
        )

    def remember_event(self, event: JarvisEvent) -> AdmissionDecision:
        text = event.payload.get("text") or event.payload.get("summary") or event.kind
        return self.admit(str(text), provenance=f"event:{event.event_id}", metadata={"event_kind": event.kind})
