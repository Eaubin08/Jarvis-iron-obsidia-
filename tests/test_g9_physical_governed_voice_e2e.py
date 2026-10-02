import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from jarvis.core import JarvisCore
from jarvis.governed_move import (
    GovernedMoveCommandHandler,
    GovernedMoveConfig,
    GovernedMoveCoordinator,
)
from jarvis.hud_live_runtime import HUDLiveVoiceBridge
from jarvis.integrations.faster_whisper_stt import FasterWhisperSTT
from jarvis.integrations.kokoro_engine import KokoroEngine
from jarvis.integrations.local_tts import LocalTTS
from jarvis.integrations.microphone import SoundDeviceMicrophone
from jarvis.providers.local_stub import StubCognition, StubMemory
from jarvis.voice_runtime import ConversationVoiceRuntime


ENV = "JARVIS_REAL_G9_GOVERNED_VOICE_E2E"


class PhysicalFollowUpIngress:
    def __init__(self, microphone, stt, conversation):
        self.microphone = microphone
        self.stt = stt
        self.conversation = conversation

    def capture_and_begin_turn(self, duration):
        return "déplace le fichier docs/a.txt vers archive/a.txt"

    def capture_follow_up(self, duration):
        audio = self.microphone.capture(duration)
        transcript = self.stt.transcribe(audio).strip()
        if not transcript:
            raise ValueError("empty follow-up transcript")
        return self.conversation.accept_transcript(transcript)


def _config(tmp_path: Path) -> GovernedMoveConfig:
    return GovernedMoveConfig(
        execution_worktree_path=tmp_path / "exec",
        main_worktree_path=tmp_path / "main",
        branch_name="main",
        base_sha="physical-g9",
        stores_base_dir=tmp_path / "stores",
        obsidia_root=tmp_path / "obsidia",
    )


@pytest.mark.skipif(
    os.environ.get(ENV) != "1",
    reason="physical governed voice E2E requires JARVIS_REAL_G9_GOVERNED_VOICE_E2E=1",
)
def test_physical_voice_confirmation_reaches_governed_execute(tmp_path):
    prepared = {
        "status": "PREPARED_AWAITING_HUMAN_APPROVAL",
        "execution_authority_hash": "b" * 64,
        "source_path": "docs/a.txt",
        "dest_path": "archive/a.txt",
    }
    executed = {
        "status": "EXECUTED_OK",
        "source_path": "docs/a.txt",
        "dest_path": "archive/a.txt",
        "sealed_rollback_evidence_id": "sre-physical-g9",
    }

    execute = MagicMock(return_value=executed)
    executor = object()
    coordinator = GovernedMoveCoordinator(
        _config(tmp_path),
        MagicMock(return_value=prepared),
        execute,
        MagicMock(return_value=executor),
    )
    move = GovernedMoveCommandHandler(coordinator)
    core = JarvisCore(
        StubCognition(),
        StubMemory(),
        governed_move=move,
    )

    microphone = SoundDeviceMicrophone(sample_rate=16000)
    stt = FasterWhisperSTT("small", device="cpu", compute_type="int8", language="fr")
    conversation = ConversationVoiceRuntime(stt, LocalTTS(KokoroEngine(lang_code="f", voice="ff_siwis")))
    ingress = PhysicalFollowUpIngress(microphone, stt, conversation)
    bridge = HUDLiveVoiceBridge(
        ingress=ingress,
        core=core,
        conversation=conversation,
        capture_seconds=float(os.environ.get("JARVIS_G9_CONFIRM_CAPTURE_SECONDS", "4.0")),
        post_speech_cooldown_seconds=0.0,
    )

    first = bridge.run_wake_turn()
    assert first is not None
    assert "préparé" in first[1].casefold()
    assert execute.call_count == 0

    print("G9_PHYSICAL: when prompted, say exactly: confirme le déplacement")
    second = bridge.run_follow_up_turn()

    assert second is not None, (
        "physical confirmation was not accepted; say exactly "
        "'confirme le déplacement' during the capture window"
    )
    assert second[0].strip()
    assert "confirme" in second[0].casefold()
    assert "déplacement" in second[0].casefold()
    assert "exécuté et prouvé" in second[1].casefold()
    assert execute.call_count == 1
    assert coordinator.pending is None
    assert coordinator.last_execution_result is executed
