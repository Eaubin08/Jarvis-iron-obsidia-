"""Jarvis-owned long task runtime."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol
from uuid import uuid4

from .contracts import JarvisEvent
from .events import EventBus


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class TaskStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"


@dataclass(frozen=True)
class TaskStep:
    step_id: str
    task_id: str
    status: str
    summary: str
    timestamp: datetime = field(default_factory=_utc_now)
    artifacts: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class Task:
    task_id: str
    goal: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    steps: tuple[TaskStep, ...] = ()
    artifacts: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    failure: str | None = None
    provider: str | None = None


class TaskWorker(Protocol):
    name: str

    def step(self, task: Task) -> TaskStep: ...


class TaskRuntime:
    def __init__(self, *, events: EventBus | None = None, worker: TaskWorker | None = None) -> None:
        self.events = events or EventBus()
        self.worker = worker
        self._tasks: dict[str, Task] = {}

    def create(self, goal: str) -> Task:
        goal = goal.strip()
        if not goal:
            raise ValueError("goal must not be empty")
        now = _utc_now()
        task = Task(
            task_id=_id("task"),
            goal=goal,
            status=TaskStatus.CREATED,
            created_at=now,
            updated_at=now,
            provider=getattr(self.worker, "name", None),
        )
        self._tasks[task.task_id] = task
        self._publish("task.created", task, {"goal": goal})
        return task

    def get(self, task_id: str) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"unknown task: {task_id}") from exc

    def step(self, task_id: str) -> TaskStep:
        task = self.get(task_id)
        if task.status in {TaskStatus.CANCELLED, TaskStatus.COMPLETED}:
            step = TaskStep(
                step_id=_id("step"),
                task_id=task.task_id,
                status="blocked",
                summary=f"task is {task.status.value}",
                error=f"cannot step {task.status.value} task",
            )
            self._append_step(task, step, status=task.status)
            return step

        if self.worker is None:
            step = TaskStep(
                step_id=_id("step"),
                task_id=task.task_id,
                status="failed",
                summary="task worker unavailable",
                error="TASK_WORKER_UNAVAILABLE",
            )
            self._append_step(task, step, status=TaskStatus.FAILED, failure=step.error)
            return step

        running = self._update(task, status=TaskStatus.RUNNING)
        self._publish("task.step.started", running, {"provider": self.worker.name})
        try:
            step = self.worker.step(running)
        except Exception as exc:
            step = TaskStep(
                step_id=_id("step"),
                task_id=task.task_id,
                status="failed",
                summary="task worker failed",
                error=f"{type(exc).__name__}: {exc}",
            )
            self._append_step(running, step, status=TaskStatus.FAILED, failure=step.error)
            return step

        next_status = TaskStatus.COMPLETED if step.status == "completed" else TaskStatus.WAITING
        if step.status == "failed":
            next_status = TaskStatus.FAILED
        self._append_step(
            running,
            step,
            status=next_status,
            failure=step.error if next_status is TaskStatus.FAILED else None,
        )
        return step

    def cancel(self, task_id: str) -> Task:
        task = self.get(task_id)
        cancelled = self._update(task, status=TaskStatus.CANCELLED)
        self._publish("task.cancelled", cancelled, {})
        return cancelled

    def resume(self, task_id: str) -> Task:
        task = self.get(task_id)
        if task.status is TaskStatus.CANCELLED:
            resumed = self._update(task, status=TaskStatus.WAITING, failure=None)
            self._publish("task.resumed", resumed, {})
            return resumed
        if task.status is TaskStatus.FAILED:
            resumed = self._update(task, status=TaskStatus.WAITING, failure=None)
            self._publish("task.resumed", resumed, {})
            return resumed
        return task

    def _append_step(
        self,
        task: Task,
        step: TaskStep,
        *,
        status: TaskStatus,
        failure: str | None = None,
    ) -> Task:
        artifacts = tuple(dict.fromkeys(task.artifacts + step.artifacts))
        evidence = tuple(dict.fromkeys(task.evidence_refs + step.evidence_refs))
        updated = replace(
            task,
            status=status,
            updated_at=_utc_now(),
            steps=task.steps + (step,),
            artifacts=artifacts,
            evidence_refs=evidence,
            failure=failure,
        )
        self._tasks[task.task_id] = updated
        self._publish(
            "task.step.completed" if step.status != "failed" else "task.failed",
            updated,
            {
                "step_id": step.step_id,
                "step_status": step.status,
                "summary": step.summary,
                "error": step.error,
            },
        )
        return updated

    def _update(self, task: Task, *, status: TaskStatus, failure: str | None = None) -> Task:
        updated = replace(task, status=status, updated_at=_utc_now(), failure=failure)
        self._tasks[task.task_id] = updated
        return updated

    def _publish(self, kind: str, task: Task, payload: dict) -> None:
        self.events.publish(
            JarvisEvent(
                kind=kind,
                source="task_runtime",
                payload={"task_id": task.task_id, "status": task.status.value, **payload},
                task_id=task.task_id,
            )
        )
