"""Minimal provider-driven Jarvis core."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from .actions import ActionRouter
from .fast_intent import FastIntentRouter
from .governed_move import GovernedMoveCommandHandler
from .governed_create_dir import GovernedCreateDirCommandHandler
from .governed_file_ops import GovernedFileOpsCommandHandler
from .governed_rollback import GovernedMoveRollbackCommandHandler
from .governed_audio import GovernedAudioCommandHandler
from .governed_app import GovernedAppOpenCommandHandler
from .governed_window import GovernedWindowCommandHandler

from .contracts import ActionRequest, CognitionProvider, MemoryProvider, RiskClass


@dataclass
class JarvisCore:
    cognition: CognitionProvider
    memory: MemoryProvider
    fast_intent: FastIntentRouter | None = None
    actions: ActionRouter | None = None
    governed_move: GovernedMoveCommandHandler | None = None
    governed_create_dir: GovernedCreateDirCommandHandler | None = None
    governed_file_ops: GovernedFileOpsCommandHandler | None = None
    governed_rollback: GovernedMoveRollbackCommandHandler | None = None
    governed_audio: GovernedAudioCommandHandler | None = None
    governed_app_open: GovernedAppOpenCommandHandler | None = None
    governed_window: GovernedWindowCommandHandler | None = None
    last_source: str = field(default="LOCAL", init=False)
    session_id: str = field(default_factory=lambda: f"jarjar-{uuid4().hex}", init=False)

    def handle_text(self, text: str) -> str:
        context = self.memory.context()
        capabilities_reply = _local_capabilities_reply(text)
        if capabilities_reply is not None:
            self.last_source = "LOCAL/CAPABILITIES"
            return capabilities_reply
        if self.governed_move is not None:
            governed_reply = self.governed_move.handle(text, session_id=self.session_id)
            if governed_reply is not None:
                self.last_source = "OBSIDIA/GOVERNED_MOVE"
                return governed_reply
        if self.governed_create_dir is not None:
            governed_reply = self.governed_create_dir.handle(text, session_id=self.session_id)
            if governed_reply is not None:
                self.last_source = "OBSIDIA/GOVERNED_CREATE_DIR"
                return governed_reply
        if self.governed_file_ops is not None:
            governed_reply = self.governed_file_ops.handle(text, session_id=self.session_id)
            if governed_reply is not None:
                self.last_source = "OBSIDIA/GOVERNED_FILE_OPS"
                return governed_reply
        if self.governed_rollback is not None:
            governed_reply = self.governed_rollback.handle(text, session_id=self.session_id)
            if governed_reply is not None:
                self.last_source = "OBSIDIA/GOVERNED_ROLLBACK"
                return governed_reply
        if self.fast_intent is not None and self.actions is not None:
            match = self.fast_intent.route(text, session_id=self.session_id)
            if match is not None:
                if self.governed_audio is not None:
                    governed_audio_reply = self.governed_audio.handle_request(
                        match.request,
                        session_id=self.session_id,
                        original_text=text,
                    )
                    if governed_audio_reply is not None:
                        self.last_source = "OBSIDIA/GOVERNED_AUDIO"
                        return governed_audio_reply

                if self.governed_app_open is not None:
                    governed_app_reply = self.governed_app_open.handle_request(
                        match.request,
                        session_id=self.session_id,
                        original_text=text,
                    )
                    if governed_app_reply is not None:
                        self.last_source = "OBSIDIA/GOVERNED_APP"
                        return governed_app_reply

                if self.governed_window is not None:
                    governed_window_reply = self.governed_window.handle_request(
                        match.request,
                        session_id=self.session_id,
                        original_text=text,
                    )
                    if governed_window_reply is not None:
                        self.last_source = "OBSIDIA/GOVERNED_WINDOW"
                        return governed_window_reply

                result = self.actions.execute(match.request, context)

                if (
                    not result.ok
                    and result.message == "WORLD_ACTION_DRY_RUN_ONLY"
                    and match.request.capability in {
                        "audio.volume_up",
                        "audio.volume_down",
                        "audio.adjust_volume",
                        "audio.set_volume",
                        "audio.set_mute",
                        "audio.mute_toggle",
                    }
                ):
                    status = self.actions.execute(
                        ActionRequest(
                            "audio.status",
                            source="g13_post_denial_readonly_check",
                            session_id=self.session_id,
                            risk=RiskClass.READ_ONLY,
                        ),
                        context,
                    )
                    backend = (status.backend or result.backend or "ACTION").upper()
                    self.last_source = f"ACTION/{backend}"
                    if status.ok:
                        return (
                            "Je n'ai pas modifié le volume : l'action physique est bloquée "
                            "par la gouvernance. " + status.message
                        )
                    return (
                        "Je n'ai pas modifié le volume : l'action physique est bloquée "
                        "par la gouvernance."
                    )

                backend = (result.backend or "ACTION").upper()
                self.last_source = f"ACTION/{backend}"
                return result.message
            guarded = self.fast_intent.local_guard_response(text)
            if guarded is not None:
                self.last_source = "LOCAL/GUARD"
                return guarded
        reply = self.cognition.respond(text, context)
        route = getattr(self.cognition, "last_route", None)
        labels = {
            "local": "LOCAL",
            "obsidia_local": "OBSIDIA/LOCAL",
            "vision": "QWEN-VL",
            "qwen_live": "QWEN/LIVE",
            "qwen": "QWEN",
            "qwen_fallback": "QWEN/FALLBACK",
            "brody": "BRODY/OBSIDIA",
            "brody_fallback": "BRODY/OBSIDIA/FALLBACK",
            "obsidia_gps": "OBSIDIA/GPS",
            "obsidia_command_hold": "OBSIDIA/COMMAND_HOLD",
            "local_fallback": "LOCAL/FALLBACK",
        }
        self.last_source = labels.get(route, "COGNITION")
        fallback_reason = getattr(self.cognition, "last_fallback_reason", None)
        if fallback_reason:
            self.last_source += f"[{fallback_reason}]"
        return reply



def _local_capabilities_reply(text: str) -> str | None:
    import re
    import unicodedata

    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = " ".join(value.split())

    patterns = (
        r"\bqu est ce que tu peux faire\b",
        r"\bque peux tu faire\b",
        r"\btes capacites\b",
        r"\bquelles sont tes capacites\b",
    )
    if not any(re.search(pattern, value) for pattern in patterns):
        return None

    return (
        "Je peux converser localement, utiliser la cognition Obsidia/Brody ou Qwen selon la demande, "
        "observer l'environnement via les capacités live disponibles, et exécuter les capacités PC "
        "explicitement branchées. Les actions gouvernées passent par la confirmation humaine et "
        "KX108/Binder ; je peux aussi afficher, auditer et rejouer leurs preuves en lecture seule."
    )
