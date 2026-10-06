from pathlib import Path
from unittest.mock import MagicMock

from jarvis.core import JarvisCore
from jarvis.governed_create_dir import (
    GovernedCreateDirCommandHandler,
    GovernedCreateDirConfig,
    GovernedCreateDirCoordinator,
)
from jarvis.governed_move import (
    GovernedMoveCommandHandler,
    GovernedMoveConfig,
    GovernedMoveCoordinator,
)
from jarvis.providers.local_stub import StubCognition, StubMemory


def _move_config(tmp_path: Path) -> GovernedMoveConfig:
    return GovernedMoveConfig(
        execution_worktree_path=tmp_path / "exec",
        main_worktree_path=tmp_path / "main",
        branch_name="main",
        base_sha="g10",
        stores_base_dir=tmp_path / "stores",
        obsidia_root=tmp_path / "obsidia",
    )


def _dir_config(tmp_path: Path) -> GovernedCreateDirConfig:
    return GovernedCreateDirConfig(
        execution_worktree_path=tmp_path / "exec",
        main_worktree_path=tmp_path / "main",
        branch_name="main",
        base_sha="g10",
        stores_base_dir=tmp_path / "stores",
        obsidia_root=tmp_path / "obsidia",
    )


def _prepared_move():
    return {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "a" * 64,
        "source_path": "a.txt",
        "dest_path": "b.txt",
    }


def test_ambiguous_confirmation_never_executes_pending_move(tmp_path):
    execute = MagicMock()
    move = GovernedMoveCommandHandler(
        GovernedMoveCoordinator(
            _move_config(tmp_path),
            MagicMock(return_value=_prepared_move()),
            execute,
            MagicMock(return_value=object()),
        )
    )
    core = JarvisCore(StubCognition(), StubMemory(), governed_move=move)

    prepared_reply = core.handle_text("déplace le fichier a.txt vers b.txt")
    assert "préparé" in prepared_reply.casefold()

    reply = core.handle_text("oui je confirme")

    assert execute.call_count == 0
    assert reply != ""
    assert move.coordinator.pending is not None


def test_wrong_operation_confirmation_cannot_execute_pending_move(tmp_path):
    move_execute = MagicMock()
    dir_execute = MagicMock()

    move = GovernedMoveCommandHandler(
        GovernedMoveCoordinator(
            _move_config(tmp_path),
            MagicMock(return_value=_prepared_move()),
            move_execute,
            MagicMock(return_value=object()),
        )
    )
    create_dir = GovernedCreateDirCommandHandler(
        GovernedCreateDirCoordinator(
            _dir_config(tmp_path),
            MagicMock(return_value={
                "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
                "execution_authority_hash": "b" * 64,
                "dir_path": "newdir",
            }),
            dir_execute,
            MagicMock(return_value=object()),
        )
    )
    core = JarvisCore(
        StubCognition(),
        StubMemory(),
        governed_move=move,
        governed_create_dir=create_dir,
    )

    core.handle_text("déplace le fichier a.txt vers b.txt")
    reply = core.handle_text("confirme la création du dossier")

    assert move_execute.call_count == 0
    assert dir_execute.call_count == 0
    assert move.coordinator.pending is not None
    assert "Aucune création" in reply


def test_duplicate_move_confirmation_after_success_cannot_replay_execute(tmp_path):
    prepared = _prepared_move()
    execute = MagicMock(return_value={
        "status": "EXECUTED_OK",
        "source_path": "a.txt",
        "dest_path": "b.txt",
        "sealed_rollback_evidence_id": "sre-g10",
    })
    move = GovernedMoveCommandHandler(
        GovernedMoveCoordinator(
            _move_config(tmp_path),
            MagicMock(return_value=prepared),
            execute,
            MagicMock(return_value=object()),
        )
    )

    first = move.handle("déplace le fichier a.txt vers b.txt", session_id="g10")
    second = move.handle("je confirme le déplacement", session_id="g10")
    replay = move.handle("je confirme le déplacement", session_id="g10")

    assert first is not None and "préparé" in first.casefold()
    assert second is not None and "exécuté et prouvé" in second.casefold()
    assert replay is not None and "Aucun déplacement" in replay
    assert execute.call_count == 1
    assert move.coordinator.pending is None


def test_cancel_then_confirm_cannot_execute(tmp_path):
    execute = MagicMock()
    move = GovernedMoveCommandHandler(
        GovernedMoveCoordinator(
            _move_config(tmp_path),
            MagicMock(return_value=_prepared_move()),
            execute,
            MagicMock(return_value=object()),
        )
    )

    move.handle("déplace le fichier a.txt vers b.txt", session_id="g10")
    cancelled = move.handle("annule le déplacement", session_id="g10")
    confirmed = move.handle("confirme le déplacement", session_id="g10")

    assert cancelled is not None and "annulé" in cancelled.casefold()
    assert confirmed is not None and "Aucun déplacement" in confirmed
    assert execute.call_count == 0


def test_pending_move_generic_confirmation_is_contained_and_never_reaches_cognition(tmp_path):
    execute = MagicMock()
    cognition = StubCognition()
    cognition.respond = MagicMock(return_value="QWEN SHOULD NOT SEE THIS")
    move = GovernedMoveCommandHandler(
        GovernedMoveCoordinator(
            _move_config(tmp_path),
            MagicMock(return_value=_prepared_move()),
            execute,
            MagicMock(return_value=object()),
        )
    )
    core = JarvisCore(cognition, StubMemory(), governed_move=move)

    core.handle_text("déplace le fichier a.txt vers b.txt")

    first = core.handle_text("Je confirme.")
    second = core.handle_text("Je confirme l'étape d'exécution.")

    assert "confirme le déplacement" in first.casefold()
    assert "confirme le déplacement" in second.casefold()
    assert execute.call_count == 0
    assert cognition.respond.call_count == 0
    assert move.coordinator.pending is not None
