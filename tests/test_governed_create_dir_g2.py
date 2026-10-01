from pathlib import Path
from unittest.mock import MagicMock

from jarvis.governed_create_dir import (
    GovernedCreateDirCommandHandler,
    GovernedCreateDirConfig,
    GovernedCreateDirCoordinator,
)


def _config(tmp_path: Path) -> GovernedCreateDirConfig:
    return GovernedCreateDirConfig(
        execution_worktree_path=tmp_path / "exec",
        main_worktree_path=tmp_path / "main",
        branch_name="test-branch",
        base_sha="abc123",
        stores_base_dir=tmp_path / "stores",
        obsidia_root=tmp_path / "obsidia",
    )


def test_prepare_only_never_executes(tmp_path):
    prepare = MagicMock(return_value={
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "a" * 64,
        "dir_path": "newdir",
    })
    execute = MagicMock()
    factory = MagicMock()
    c = GovernedCreateDirCoordinator(_config(tmp_path), prepare, execute, factory)

    reply = c.prepare("newdir", session_id="s1")

    assert "préparée" in reply
    assert c.pending is not None
    execute.assert_not_called()
    factory.assert_not_called()


def test_prepare_rejection_does_not_create_pending(tmp_path):
    prepare = MagicMock(return_value={"status": "PREPARE_REJECTED", "reason": "DIR_PATH_UNSAFE"})
    c = GovernedCreateDirCoordinator(_config(tmp_path), prepare, MagicMock(), MagicMock())

    reply = c.prepare("../newdir", session_id="s1")

    assert "DIR_PATH_UNSAFE" in reply
    assert c.pending is None


def test_approve_requires_pending(tmp_path):
    execute = MagicMock()
    factory = MagicMock()
    c = GovernedCreateDirCoordinator(_config(tmp_path), MagicMock(), execute, factory)

    reply = c.approve(session_id="s1")

    assert "Aucune création" in reply
    execute.assert_not_called()
    factory.assert_not_called()


def test_approve_executes_once_with_human_reference_and_executor(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "b" * 64,
        "dir_path": "newdir",
    }
    execute = MagicMock(return_value={"status": "EXECUTED_OK", "dir_path": "newdir"})
    executor = object()
    factory = MagicMock(return_value=executor)
    c = GovernedCreateDirCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        factory,
    )

    c.prepare("newdir", session_id="s1")
    reply = c.approve(session_id="s1")

    assert "créé et prouvé" in reply
    assert c.pending is None
    factory.assert_called_once_with((tmp_path / "exec").resolve())
    args, kwargs = execute.call_args
    assert args[0] is prepared
    assert args[1] == "b" * 64
    assert args[2] == "JARJAR_HUD_CONFIRM_CREATE_DIR:s1"
    assert kwargs["executor"] is executor


def test_failed_execute_keeps_pending(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "c" * 64,
    }
    execute = MagicMock(return_value={"status": "EXECUTE_REJECTED", "reason": "KX108_PRE_GATE:BLOCK"})
    c = GovernedCreateDirCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        MagicMock(return_value=object()),
    )

    c.prepare("newdir", session_id="s1")
    reply = c.approve(session_id="s1")

    assert "KX108_PRE_GATE:BLOCK" in reply
    assert c.pending is prepared


def test_cancel_clears_pending_without_execute(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "d" * 64,
    }
    execute = MagicMock()
    c = GovernedCreateDirCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        MagicMock(),
    )

    c.prepare("newdir", session_id="s1")
    reply = c.cancel()

    assert "annulée" in reply
    assert c.pending is None
    execute.assert_not_called()


def test_text_handler_two_phase_flow(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "e" * 64,
    }
    execute = MagicMock(return_value={"status": "EXECUTED_OK", "dir_path": "docs/new"})
    coordinator = GovernedCreateDirCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        MagicMock(return_value=object()),
    )
    handler = GovernedCreateDirCommandHandler(coordinator)

    first = handler.handle("cree le dossier docs/new", session_id="hud-1")
    assert first is not None and "préparée" in first.lower()
    assert execute.call_count == 0

    second = handler.handle("confirme la creation du dossier", session_id="hud-1")
    assert second is not None and "créé" in second.lower()
    assert execute.call_count == 1


def test_text_handler_ignores_unrelated_text(tmp_path):
    coordinator = GovernedCreateDirCoordinator(_config(tmp_path), MagicMock(), MagicMock(), MagicMock())
    handler = GovernedCreateDirCommandHandler(coordinator)

    assert handler.handle("explique moi ce projet", session_id="s1") is None
