"""Canonical daily-use environment and preflight for Jarjar.

The profile preserves the proven runtime boundary documented in
JARJAR_LIVE_RUNTIME_LAUNCH_GUARD_2026-10-02.md. It does not grant action
authority and it fails closed when the local Brody/Native Memory contract is
not proven.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from urllib.request import Request, urlopen
from urllib.error import URLError


CANONICAL_ENV_DEFAULTS = {
    "JARJAR_BOUNDED_STRUCTURED_ROUTING_V0": "1",
    "JARJAR_LOCAL_BRODY": "1",
    "JARJAR_QWEN_URL": "http://127.0.0.1:8080/v1/chat/completions",
    "JARJAR_VISION_URL": "http://127.0.0.1:8081/v1/chat/completions",
    "JARVIS_WAKEWORD_THRESHOLD": "0.32",
    "JARVIS_SPEECH_RMS_THRESHOLD": "300",
    "JARVIS_END_SILENCE_SECONDS": "2.00",
    "JARVIS_WAKE_SPEECH_TIMEOUT": "6.0",
    "JARVIS_FOLLOW_UP_TIMEOUT": "3.0",
    "JARVIS_SESSION_IDLE_SECONDS": "13.0",
    "JARVIS_MAX_UTTERANCE_SECONDS": "120.0",
    "JARVIS_POST_SPEECH_COOLDOWN_SECONDS": "0.10",
}


@dataclass(frozen=True)
class CanonicalPreflight:
    ok: bool
    environment: dict
    brody: dict
    qwen_text: dict
    qwen_vision: dict
    authority: str = "NONE"
    decision_authority: str = "KX108_ONLY"

    def as_dict(self) -> dict:
        return {
            "schema": "JARJAR_CANONICAL_PREFLIGHT_V1",
            "ok": self.ok,
            "environment": self.environment,
            "brody": self.brody,
            "qwen_text": self.qwen_text,
            "qwen_vision": self.qwen_vision,
            "authority": self.authority,
            "decision_authority": self.decision_authority,
        }


def apply_canonical_environment() -> dict:
    applied = {}
    for key, value in CANONICAL_ENV_DEFAULTS.items():
        if not os.getenv(key):
            os.environ[key] = value
        applied[key] = os.environ[key]
    return applied


def _probe_openai_models(base_url: str, timeout: float = 0.65) -> dict:
    root = base_url.split("/v1/", 1)[0]
    url = root.rstrip("/") + "/v1/models"
    try:
        with urlopen(Request(url, method="GET"), timeout=timeout) as response:
            raw = response.read()
        packet = json.loads(raw.decode("utf-8"))
        models = []
        if isinstance(packet, dict):
            for row in packet.get("data") or []:
                if isinstance(row, dict) and row.get("id"):
                    models.append(str(row["id"]))
        return {"ready": True, "url": url, "models": models}
    except Exception as exc:
        return {"ready": False, "url": url, "error": f"{type(exc).__name__}:{exc}"}


def _probe_local_brody() -> dict:
    try:
        from jarvis.obsidia_port.local_brody_runtime_adapter import respond_local_brody

        result = respond_local_brody(
            "état runtime native memory",
            session_id="jarjar-canonical-preflight",
            language="fr",
        )
    except Exception as exc:
        return {
            "ready": False,
            "error": f"{type(exc).__name__}:{exc}",
            "decision_authority": None,
            "readonly": None,
            "memory_source_mode": None,
        }

    if not isinstance(result, dict):
        return {"ready": False, "error": "invalid local Brody preflight packet"}

    authority = str(result.get("decision_authority") or "").strip()
    memory = str(result.get("memory_source_mode") or "").strip()
    readonly = result.get("readonly")
    available = result.get("available") is True
    legacy = "GRAPHITI" in memory.upper()
    ready = (
        available
        and authority == "KX108_ONLY"
        and readonly is True
        and memory == "OBSIDIA_NATIVE_MEMORY"
        and not legacy
    )
    return {
        "ready": ready,
        "available": available,
        "decision_authority": authority or None,
        "readonly": readonly,
        "memory_source_mode": memory or None,
        "memory_status": result.get("memory_status"),
        "retrieval_status": result.get("retrieval_status"),
        "legacy_memory_active": legacy,
        "voice_source": result.get("voice_source"),
        "status": result.get("status"),
    }


def run_canonical_preflight(*, require_qwen: bool | None = None) -> CanonicalPreflight:
    environment = apply_canonical_environment()
    brody = _probe_local_brody()
    qwen_text = _probe_openai_models(environment["JARJAR_QWEN_URL"])
    qwen_vision = _probe_openai_models(environment["JARJAR_VISION_URL"])

    if require_qwen is None:
        require_qwen = os.getenv("JARJAR_REQUIRE_QWEN_SERVICES", "0").strip().lower() in {
            "1", "true", "yes", "on"
        }

    ok = bool(brody.get("ready"))
    if require_qwen:
        ok = ok and bool(qwen_text.get("ready")) and bool(qwen_vision.get("ready"))

    result = CanonicalPreflight(
        ok=ok,
        environment=environment,
        brody=brody,
        qwen_text=qwen_text,
        qwen_vision=qwen_vision,
    )

    print("JARJAR_CANONICAL_PREFLIGHT: " + ("PASS" if result.ok else "BLOCK"))
    print(
        "JARJAR_CANONICAL_BRODY: "
        f"ready={brody.get('ready')} "
        f"memory={brody.get('memory_source_mode') or 'UNKNOWN'} "
        f"authority={brody.get('decision_authority') or 'UNKNOWN'} "
        f"readonly={brody.get('readonly')}"
    )
    print(
        "JARJAR_CANONICAL_PROVIDERS: "
        f"qwen_text={'READY' if qwen_text.get('ready') else 'OFF'} "
        f"qwen_vl={'READY' if qwen_vision.get('ready') else 'OFF'} "
        f"required={require_qwen}"
    )
    return result


def require_canonical_preflight() -> CanonicalPreflight:
    result = run_canonical_preflight()
    if not result.ok:
        raise RuntimeError(
            "JARJAR_CANONICAL_PREFLIGHT_BLOCK: Local Brody/Native Memory "
            "did not prove OBSIDIA_NATIVE_MEMORY + KX108_ONLY + readonly=True"
        )
    return result
