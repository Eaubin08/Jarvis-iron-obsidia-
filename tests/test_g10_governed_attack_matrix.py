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


def test_contextual_confirmation_executes_only_when_move_is_pending(tmp_path):
    execute = MagicMock(return_value={
        "status": "EXECUTED_OK",
        "source_path": "a.txt",
        "dest_path": "b.txt",
        "kx108_pre_gate": "ALLOW",
        "sealed_rollback_evidence_id": "sre-g10",
        "sealed_apply_receipt_id": "sar-g10",
        "receipt": {"receipt_id": "pcrcp-v2-g10"},
    })
    move = GovernedMoveCommandHandler(
        GovernedMoveCoordinator(
            _move_config(tmp_path),
            MagicMock(return_value=_prepared_move()),
            execute,
            MagicMock(return_value=object()),
        )
    )
    core = JarvisCore(StubCognition(), StubMemory(), governed_move=move)

    # No pending operation: generic confirmation is not an authorization.
    assert core.handle_text("je confirme") != "Déplacement exécuté et prouvé : a.txt → b.txt."
    assert execute.call_count == 0

    prepared_reply = core.handle_text("déplace le fichier a.txt vers b.txt")
    assert "préparé" in prepared_reply.casefold()

    reply = core.handle_text("oui je confirme")

    assert "exécuté et prouvé" in reply.casefold()
    assert execute.call_count == 1
    assert move.coordinator.pending is None


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


def test_pending_move_natural_confirmation_stays_governed_and_never_reaches_cognition(tmp_path):
    execute = MagicMock(return_value={
        "status": "EXECUTED_OK",
        "source_path": "a.txt",
        "dest_path": "b.txt",
        "kx108_pre_gate": "ALLOW",
        "sealed_rollback_evidence_id": "sre-g10",
        "sealed_apply_receipt_id": "sar-g10",
        "receipt": {"receipt_id": "pcrcp-v2-g10"},
    })
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
    reply = core.handle_text("Je confirme.")

    assert "exécuté et prouvé" in reply.casefold()
    assert execute.call_count == 1
    assert cognition.respond.call_count == 0
    assert move.coordinator.pending is None


def test_negative_confirmation_never_executes_pending_move(tmp_path):
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
    core.handle_text("déplace le fichier a.txt vers b.txt")

    reply = core.handle_text("non je ne confirme pas")

    assert execute.call_count == 0
    assert move.coordinator.pending is not None
    assert reply != ""


def test_last_governed_move_proof_follow_up_uses_execution_result_not_cognition(tmp_path):
    execute = MagicMock(return_value={
        "status": "EXECUTED_OK",
        "source_path": "a.txt",
        "dest_path": "b.txt",
        "kx108_pre_gate": "ALLOW",
        "sealed_rollback_evidence_id": "sre-proof",
        "sealed_apply_receipt_id": "sar-proof",
        "receipt": {"receipt_id": "pcrcp-v2-proof"},
    })
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
    core.handle_text("je confirme")
    proof = core.handle_text("Quels en sont les preuves ?")

    assert "KX108_PRE=ALLOW" in proof
    assert "pcrcp-v2-proof" in proof
    assert "sre-proof" in proof
    assert "sar-proof" in proof
    assert cognition.respond.call_count == 0


def test_spoken_path_normalization_is_explicit_not_fuzzy(tmp_path):
    prepare = MagicMock(return_value=_prepared_move())
    move = GovernedMoveCommandHandler(
        GovernedMoveCoordinator(
            _move_config(tmp_path),
            prepare,
            MagicMock(),
            MagicMock(return_value=object()),
        )
    )

    move.handle(
        "déplace le fichier read me point md vers archive slash read me tiret test point md",
        session_id="g10",
    )

    args, kwargs = prepare.call_args
    assert args[0] == "README.md"
    assert args[1] == "archive/README-test.md"


def test_natural_move_sentence_prepares_without_reaching_cognition(tmp_path):
    prepare = MagicMock(return_value=_prepared_move())
    cognition = StubCognition()
    cognition.respond = MagicMock(return_value="QWEN SHOULD NOT SEE THIS")
    move = GovernedMoveCommandHandler(
        GovernedMoveCoordinator(
            _move_config(tmp_path),
            prepare,
            MagicMock(),
            MagicMock(return_value=object()),
        )
    )
    core = JarvisCore(cognition, StubMemory(), governed_move=move)

    reply = core.handle_text(
        "Du coup, il va falloir que tu déplaces le fichier readme.md "
        "vers le fichier readme-test.md."
    )

    assert "préparé" in reply.casefold()
    assert cognition.respond.call_count == 0
    args, _ = prepare.call_args
    assert args[0] == "readme.md"
    assert args[1] == "readme-test.md"


def test_incomplete_move_intent_is_contained_before_qwen(tmp_path):
    cognition = StubCognition()
    cognition.respond = MagicMock(return_value="QWEN SHOULD NOT SEE THIS")
    move = GovernedMoveCommandHandler(
        GovernedMoveCoordinator(
            _move_config(tmp_path),
            MagicMock(),
            MagicMock(),
            MagicMock(return_value=object()),
        )
    )
    core = JarvisCore(cognition, StubMemory(), governed_move=move)

    reply = core.handle_text("Déplace le fichier Markdown vers...")

    assert "deux chemins complets" in reply
    assert cognition.respond.call_count == 0


def test_natural_execute_phrase_confirms_only_pending_move(tmp_path):
    execute = MagicMock(return_value={
        "status": "EXECUTED_OK",
        "source_path": "a.txt",
        "dest_path": "b.txt",
        "kx108_pre_gate": "ALLOW",
        "sealed_rollback_evidence_id": "sre-g10",
        "sealed_apply_receipt_id": "sar-g10",
        "receipt": {"receipt_id": "pcrcp-v2-g10"},
    })
    move = GovernedMoveCommandHandler(
        GovernedMoveCoordinator(
            _move_config(tmp_path),
            MagicMock(return_value=_prepared_move()),
            execute,
            MagicMock(return_value=object()),
        )
    )
    core = JarvisCore(StubCognition(), StubMemory(), governed_move=move)

    # No pending MOVE: natural execute language cannot authorize anything.
    core.handle_text("Ok, fais le déplacement.")
    assert execute.call_count == 0

    core.handle_text("déplace le fichier a.txt vers b.txt")
    reply = core.handle_text("Ok, fais le déplacement.")

    assert "exécuté et prouvé" in reply.casefold()
    assert execute.call_count == 1
