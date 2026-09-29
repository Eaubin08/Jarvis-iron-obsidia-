from jarvis.tasks import TaskRuntime, TaskStatus, TaskStep


class Worker:
    name = "fake-worker"

    def __init__(self, statuses=None):
        self.statuses = list(statuses or ["waiting"])
        self.calls = []

    def step(self, task):
        self.calls.append((task.task_id, task.status))
        status = self.statuses.pop(0)
        return TaskStep(
            step_id=f"step-{len(self.calls)}",
            task_id=task.task_id,
            status=status,
            summary=f"{status} step",
            artifacts=("artifact:a",) if status == "completed" else (),
            evidence_refs=("evidence:a",),
            error="worker-reported failure" if status == "failed" else None,
        )


class BrokenWorker:
    name = "broken-worker"

    def step(self, task):
        raise RuntimeError("provider offline")


def test_create_task_owns_canonical_state_and_emits_event():
    seen = []
    runtime = TaskRuntime(worker=Worker())
    runtime.events.subscribe_all(seen.append)

    task = runtime.create("summarize repo")

    assert task.task_id.startswith("task_")
    assert task.goal == "summarize repo"
    assert task.status is TaskStatus.CREATED
    assert task.provider == "fake-worker"
    assert seen[-1].kind == "task.created"


def test_step_records_progress_artifacts_evidence_and_events():
    seen = []
    worker = Worker(["completed"])
    runtime = TaskRuntime(worker=worker)
    runtime.events.subscribe_all(seen.append)
    task = runtime.create("do bounded work")

    step = runtime.step(task.task_id)
    updated = runtime.get(task.task_id)

    assert step.status == "completed"
    assert updated.status is TaskStatus.COMPLETED
    assert updated.steps == (step,)
    assert updated.artifacts == ("artifact:a",)
    assert updated.evidence_refs == ("evidence:a",)
    assert [event.kind for event in seen] == [
        "task.created",
        "task.step.started",
        "task.step.completed",
    ]


def test_cancel_and_resume_keep_state_in_jarvis_runtime():
    runtime = TaskRuntime(worker=Worker())
    task = runtime.create("long task")

    cancelled = runtime.cancel(task.task_id)
    resumed = runtime.resume(task.task_id)

    assert cancelled.status is TaskStatus.CANCELLED
    assert resumed.status is TaskStatus.WAITING
    assert runtime.get(task.task_id).status is TaskStatus.WAITING


def test_failed_task_from_worker_response_is_explicit():
    runtime = TaskRuntime(worker=Worker(["failed"]))
    task = runtime.create("fail cleanly")

    step = runtime.step(task.task_id)
    failed = runtime.get(task.task_id)

    assert step.status == "failed"
    assert failed.status is TaskStatus.FAILED
    assert failed.failure == "worker-reported failure"


def test_external_provider_unavailable_does_not_corrupt_state():
    runtime = TaskRuntime(worker=None)
    task = runtime.create("providerless work")

    step = runtime.step(task.task_id)
    failed = runtime.get(task.task_id)

    assert step.status == "failed"
    assert step.error == "TASK_WORKER_UNAVAILABLE"
    assert failed.goal == "providerless work"
    assert failed.status is TaskStatus.FAILED
    assert failed.steps == (step,)


def test_external_provider_exception_is_captured_without_losing_task():
    runtime = TaskRuntime(worker=BrokenWorker())
    task = runtime.create("provider breaks")

    step = runtime.step(task.task_id)
    failed = runtime.get(task.task_id)

    assert step.status == "failed"
    assert "RuntimeError: provider offline" == step.error
    assert failed.task_id == task.task_id
    assert failed.status is TaskStatus.FAILED


def test_cancelled_task_does_not_call_external_worker():
    worker = Worker()
    runtime = TaskRuntime(worker=worker)
    task = runtime.create("cancel me")
    runtime.cancel(task.task_id)

    step = runtime.step(task.task_id)

    assert step.status == "blocked"
    assert worker.calls == []
