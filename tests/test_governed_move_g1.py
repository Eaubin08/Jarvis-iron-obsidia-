from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from jarvis.governed_move import (
    GovernedMoveCommandHandler,
    GovernedMoveConfig,
    GovernedMoveCoordinator,
)


def _config(tmp_path: Path) -> GovernedMoveConfig:
    return GovernedMoveConfig(
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
        "source_path": "a.txt",
        "dest_path": "b.txt",
    })
    execute = MagicMock()
    factory = MagicMock()
    c = GovernedMoveCoordinator(_config(tmp_path), prepare, execute, factory)

    reply = c.prepare("a.txt", "b.txt", session_id="s1")

    assert "Déplacement préparé" in reply
    assert c.pending is not None
    execute.assert_not_called()
    factory.assert_not_called()


def test_prepare_rejection_does_not_create_pending(tmp_path):
    prepare = MagicMock(return_value={"status": "PREPARE_REJECTED", "reason": "PATH_UNSAFE"})
    c = GovernedMoveCoordinator(_config(tmp_path), prepare, MagicMock(), MagicMock())

    reply = c.prepare("../a.txt", "b.txt", session_id="s1")

    assert "PATH_UNSAFE" in reply
    assert c.pending is None


def test_second_prepare_is_blocked_while_pending(tmp_path):
    prepare = MagicMock(return_value={
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "a" * 64,
    })
    c = GovernedMoveCoordinator(_config(tmp_path), prepare, MagicMock(), MagicMock())

    c.prepare("a.txt", "b.txt", session_id="s1")
    reply = c.prepare("c.txt", "d.txt", session_id="s1")

    assert "déjà en attente" in reply
    assert prepare.call_count == 1


def test_approve_requires_pending(tmp_path):
    execute = MagicMock()
    factory = MagicMock()
    c = GovernedMoveCoordinator(_config(tmp_path), MagicMock(), execute, factory)

    reply = c.approve(session_id="s1")

    assert "Aucun déplacement" in reply
    execute.assert_not_called()
    factory.assert_not_called()


def test_approve_executes_once_with_human_reference_and_executor(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "b" * 64,
        "source_path": "a.txt",
        "dest_path": "b.txt",
    }
    prepare = MagicMock(return_value=prepared)
    execute = MagicMock(return_value={
        "status": "EXECUTED_OK",
        "source_path": "a.txt",
        "dest_path": "b.txt",
    })
    executor = object()
    factory = MagicMock(return_value=executor)
    c = GovernedMoveCoordinator(_config(tmp_path), prepare, execute, factory)

    c.prepare("a.txt", "b.txt", session_id="s1")
    reply = c.approve(session_id="s1")

    assert "exécuté et prouvé" in reply
    assert c.pending is None
    factory.assert_called_once_with((tmp_path / "exec").resolve())
    execute.assert_called_once()
    args, kwargs = execute.call_args
    assert args[0] is prepared
    assert args[1] == "b" * 64
    assert args[2] == "JARJAR_HUD_CONFIRM:s1"
    assert kwargs["executor"] is executor


def test_failed_execute_keeps_pending_for_explicit_resolution(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "c" * 64,
    }
    execute = MagicMock(return_value={"status": "EXECUTE_REJECTED", "reason": "KX108_PRE_GATE:BLOCK"})
    c = GovernedMoveCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        MagicMock(return_value=object()),
    )

    c.prepare("a.txt", "b.txt", session_id="s1")
    reply = c.approve(session_id="s1")

    assert "KX108_PRE_GATE:BLOCK" in reply
    assert c.pending is prepared


def test_cancel_clears_pending_without_execute(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "d" * 64,
    }
    execute = MagicMock()
    c = GovernedMoveCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        MagicMock(),
    )

    c.prepare("a.txt", "b.txt", session_id="s1")
    reply = c.cancel()

    assert "annulé" in reply
    assert c.pending is None
    execute.assert_not_called()


def test_text_handler_two_phase_flow(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "e" * 64,
    }
    execute = MagicMock(return_value={
        "status": "EXECUTED_OK",
        "source_path": "docs/a.txt",
        "dest_path": "archive/a.txt",
    })
    coordinator = GovernedMoveCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        MagicMock(return_value=object()),
    )
    handler = GovernedMoveCommandHandler(coordinator)

    first = handler.handle(
        "déplace le fichier docs/a.txt vers archive/a.txt",
        session_id="hud-1",
    )
    assert first is not None and "préparé" in first.lower()
    assert execute.call_count == 0

    second = handler.handle("confirme le déplacement", session_id="hud-1")
    assert second is not None and "exécuté" in second.lower()
    assert execute.call_count == 1


def test_text_handler_ignores_unrelated_text(tmp_path):
    coordinator = GovernedMoveCoordinator(_config(tmp_path), MagicMock(), MagicMock(), MagicMock())
    handler = GovernedMoveCommandHandler(coordinator)

    assert handler.handle("explique moi ce projet", session_id="s1") is None


def test_from_obsidia_exposes_root_and_scripts_for_runtime_imports(tmp_path, monkeypatch):
    root = tmp_path / "obsidia"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)

    fake_pc2 = type("PC2", (), {
        "pc_v2_move_file_prepare": staticmethod(lambda *a, **k: {}),
        "pc_v2_move_file_execute": staticmethod(lambda *a, **k: {}),
    })
    fake_bridge = type("Bridge", (), {
        "make_executor": staticmethod(lambda root: object()),
    })

    imported = []

    def fake_import(name):
        imported.append(name)
        if name == "obsidia_pc_capabilities_v2":
            assert str(root) in sys.path
            assert str(scripts) in sys.path
            return fake_pc2
        if name == "jarjar_executor_bridge_v0":
            return fake_bridge
        raise AssertionError(name)

    import sys
    import jarvis.governed_move as gm

    monkeypatch.setattr(gm.importlib, "import_module", fake_import)

    config = GovernedMoveConfig(
        execution_worktree_path=tmp_path / "exec",
        main_worktree_path=tmp_path / "main",
        branch_name="test",
        base_sha="abc",
        stores_base_dir=tmp_path / "stores",
        obsidia_root=root,
    )

    coordinator = GovernedMoveCoordinator.from_obsidia(config)

    assert coordinator.prepare_fn is fake_pc2.pc_v2_move_file_prepare
    assert coordinator.execute_fn is fake_pc2.pc_v2_move_file_execute
    assert imported == ["obsidia_pc_capabilities_v2", "jarjar_executor_bridge_v0"]
