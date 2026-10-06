from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from jarvis.core import JarvisCore
from jarvis.governed_move import (
    GovernedMoveCommandHandler,
    GovernedMoveConfig,
    GovernedMoveCoordinator,
)
from jarvis.hud_controller import HUDController
from jarvis.hud_live_runtime import HUDLiveVoiceBridge
from jarvis.hud_state import HUDModel
from jarvis.providers.local_stub import StubCognition, StubMemory


class SequencedIngress:
    def __init__(self):
        self.wake_calls = 0
        self.follow_calls = 0

    def capture_and_begin_turn(self, duration):
        self.wake_calls += 1
        return "déplace le fichier docs/a.txt vers archive/a.txt"

    def capture_follow_up(self, duration):
        self.follow_calls += 1
        return "confirme le déplacement"


class Handle:
    def wait(self, timeout):
        return None


class FakeConversation:
    def __init__(self):
        self.follow_up_open = False
        self.spoken = []
        self.finished = 0

    def speak(self, text, *, open_follow_up=True):
        self.spoken.append(text)
        self.follow_up_open = open_follow_up
        return Handle()

    def speech_finished(self):
        self.finished += 1


def _config(tmp_path: Path) -> GovernedMoveConfig:
    return GovernedMoveConfig(
        execution_worktree_path=tmp_path / "exec",
        main_worktree_path=tmp_path / "main",
        branch_name="main",
        base_sha="test-base",
        stores_base_dir=tmp_path / "stores",
        obsidia_root=tmp_path / "obsidia",
    )


def test_full_voice_session_prepare_confirm_execute_proof_and_hud_projection(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "a" * 64,
        "source_path": "docs/a.txt",
        "dest_path": "archive/a.txt",
    }
    executed = {
        "status": "EXECUTED_OK",
        "source_path": "docs/a.txt",
        "dest_path": "archive/a.txt",
        "sealed_rollback_evidence_id": "sre-test-1",
    }

    prepare = MagicMock(return_value=prepared)
    execute = MagicMock(return_value=executed)
    executor = object()
    coordinator = GovernedMoveCoordinator(
        _config(tmp_path),
        prepare,
        execute,
        MagicMock(return_value=executor),
    )
    move = GovernedMoveCommandHandler(coordinator)

    core = JarvisCore(
        StubCognition(),
        StubMemory(),
        governed_move=move,
    )
    ingress = SequencedIngress()
    conversation = FakeConversation()
    bridge = HUDLiveVoiceBridge(
        ingress=ingress,
        core=core,
        conversation=conversation,
        capture_seconds=0.1,
        post_speech_cooldown_seconds=0.0,
    )

    model = HUDModel()
    model.set_session_open(True)
    controller = HUDController(
        model=model,
        text_handler=core.handle_text,
        voice_turn_handler=bridge.run_wake_turn,
        follow_up_turn_handler=bridge.run_follow_up_turn,
        response_source=lambda: core.last_source,
    )

    first = controller.run_voice_turn()

    assert first is not None
    assert "préparé" in first[1].casefold()
    assert execute.call_count == 0
    assert coordinator.pending is prepared

    snap = model.snapshot()
    assert snap["governance_active"] is True
    assert snap["decision_authority"] == "KX108_ONLY"
    assert snap["governance_source"] == "OBSIDIA/GOVERNED_MOVE"
    assert snap["governance_phase"] == "PREPARE"
    assert snap["human_confirmation_required"] is True
    assert snap["confirmation_prompt"] == "CONFIRME LE DÉPLACEMENT"

    second = controller.run_follow_up_turn()

    assert second is not None
    assert "exécuté et prouvé" in second[1].casefold()
    assert ingress.wake_calls == 1
    assert ingress.follow_calls == 1
    assert execute.call_count == 1
    assert coordinator.pending is None
    assert coordinator.last_execution_result is executed

    snap = model.snapshot()
    assert snap["governance_active"] is True
    assert snap["decision_authority"] == "KX108_ONLY"
    assert snap["governance_phase"] == "EXECUTE"
    assert snap["human_confirmation_required"] is False
    assert snap["confirmation_prompt"] == ""

    args, kwargs = execute.call_args
    assert args[0] is prepared
    assert args[1] == "a" * 64
    assert args[2] == f"JARJAR_HUD_CONFIRM:{core.session_id}"
    assert kwargs["executor"] is executor

    assert len(conversation.spoken) == 2
    assert conversation.finished == 2
