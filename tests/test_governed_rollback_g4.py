from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from jarvis.governed_rollback import (
    GovernedMoveRollbackCommandHandler,
    GovernedMoveRollbackCoordinator,
    GovernedRollbackConfig,
)


def _config(tmp_path: Path) -> GovernedRollbackConfig:
    return GovernedRollbackConfig(
        execution_worktree_path=tmp_path / "exec",
        stores_base_dir=tmp_path / "stores",
        obsidia_root=tmp_path / "obsidia",
    )


def _move(last=None):
    return SimpleNamespace(last_execution_result=last)


def test_prepare_requires_last_executed_move(tmp_path):
    prepare = MagicMock()
    c = GovernedMoveRollbackCoordinator(
        _config(tmp_path),
        _move(None),
        prepare,
        MagicMock(),
        MagicMock(),
    )

    reply = c.prepare_last_move(session_id="s1")

    assert "Aucun déplacement gouverné exécuté" in reply
    assert c.pending is None
    prepare.assert_not_called()


def test_prepare_uses_exact_sre_and_does_not_execute(tmp_path):
    last = {"sealed_rollback_evidence_id": "sre-abc"}
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "sealed_rollback_evidence_id": "sre-abc",
        "source_path": "source.txt",
        "dest_path": "moved.txt",
        "rollback_authority_hash": "a" * 64,
    }
    execute = MagicMock()
    factory = MagicMock()
    c = GovernedMoveRollbackCoordinator(
        _config(tmp_path),
        _move(last),
        MagicMock(return_value=prepared),
        execute,
        factory,
    )

    reply = c.prepare_last_move(session_id="s1")

    assert "Rollback préparé" in reply
    assert c.pending is prepared
    execute.assert_not_called()
    factory.assert_not_called()


def test_approve_requires_pending(tmp_path):
    execute = MagicMock()
    c = GovernedMoveRollbackCoordinator(
        _config(tmp_path),
        _move({"sealed_rollback_evidence_id": "sre-abc"}),
        MagicMock(),
        execute,
        MagicMock(),
    )

    reply = c.approve(session_id="s1")

    assert "Aucun rollback gouverné" in reply
    execute.assert_not_called()


def test_successful_rollback_consumes_last_move_proof(tmp_path):
    move = _move({"sealed_rollback_evidence_id": "sre-abc"})
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "sealed_rollback_evidence_id": "sre-abc",
        "source_path": "source.txt",
        "dest_path": "moved.txt",
        "rollback_authority_hash": "b" * 64,
    }
    execute = MagicMock(return_value={
        "status": "ROLLBACK_EXECUTED_OK",
        "source_path": "source.txt",
        "dest_path": "moved.txt",
    })
    executor = object()
    c = GovernedMoveRollbackCoordinator(
        _config(tmp_path),
        move,
        MagicMock(return_value=prepared),
        execute,
        MagicMock(return_value=executor),
    )

    c.prepare_last_move(session_id="s1")
    reply = c.approve(session_id="s1")

    assert "exécuté et prouvé" in reply
    assert c.pending is None
    assert move.last_execution_result is None
    args, kwargs = execute.call_args
    assert args[0] is prepared
    assert args[1] == "b" * 64
    assert args[2] == "JARJAR_HUD_CONFIRM_ROLLBACK:s1"
    assert kwargs["executor"] is executor


def test_failed_rollback_keeps_pending_and_last_proof(tmp_path):
    last = {"sealed_rollback_evidence_id": "sre-abc"}
    move = _move(last)
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "sealed_rollback_evidence_id": "sre-abc",
        "rollback_authority_hash": "c" * 64,
    }
    c = GovernedMoveRollbackCoordinator(
        _config(tmp_path),
        move,
        MagicMock(return_value=prepared),
        MagicMock(return_value={
            "status": "EXECUTE_REJECTED",
            "reason": "ROLLBACK_PRECONDITION_CHANGED:CURRENT_CONTENT_MISMATCH",
        }),
        MagicMock(return_value=object()),
    )

    c.prepare_last_move(session_id="s1")
    reply = c.approve(session_id="s1")

    assert "ROLLBACK_PRECONDITION_CHANGED" in reply
    assert c.pending is prepared
    assert move.last_execution_result is last


def test_text_handler_two_phase_flow(tmp_path):
    move = _move({"sealed_rollback_evidence_id": "sre-abc"})
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "sealed_rollback_evidence_id": "sre-abc",
        "source_path": "source.txt",
        "dest_path": "moved.txt",
        "rollback_authority_hash": "d" * 64,
    }
    execute = MagicMock(return_value={
        "status": "ROLLBACK_EXECUTED_OK",
        "source_path": "source.txt",
        "dest_path": "moved.txt",
    })
    coordinator = GovernedMoveRollbackCoordinator(
        _config(tmp_path),
        move,
        MagicMock(return_value=prepared),
        execute,
        MagicMock(return_value=object()),
    )
    handler = GovernedMoveRollbackCommandHandler(coordinator)

    first = handler.handle("annule le dernier deplacement", session_id="hud")
    assert first is not None and "Rollback préparé" in first
    execute.assert_not_called()

    second = handler.handle("confirme le rollback", session_id="hud")
    assert second is not None and "exécuté et prouvé" in second
    execute.assert_called_once()


def test_cancel_does_not_consume_last_move_proof(tmp_path):
    last = {"sealed_rollback_evidence_id": "sre-abc"}
    move = _move(last)
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "sealed_rollback_evidence_id": "sre-abc",
        "rollback_authority_hash": "e" * 64,
    }
    c = GovernedMoveRollbackCoordinator(
        _config(tmp_path),
        move,
        MagicMock(return_value=prepared),
        MagicMock(),
        MagicMock(),
    )

    c.prepare_last_move(session_id="s1")
    reply = c.cancel()

    assert "annulé avant exécution" in reply
    assert c.pending is None
    assert move.last_execution_result is last
