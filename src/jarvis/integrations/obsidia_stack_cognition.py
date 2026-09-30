"""Governed cognition bridge from Jarjar to the existing Obsidia stack.

Jarjar does not own Brody, Qwen, provider selection, or semantic routing.
It submits text to the canonical readonly Brody API boundary and consumes only
the returned final answer. Any provider escalation remains a stack decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from jarvis.contracts import ContextSnapshot


Transport = Callable[[Request, float], bytes]

_LEGACY_GRAPHITI_MARKERS = (
    "index graphiti local",
    "local graphiti index",
    "neo4j unavailable",
    "graphiti offline",
)

def _is_legacy_graphiti_text(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.casefold()
    return any(marker in text for marker in _LEGACY_GRAPHITI_MARKERS)


def _governed_capability_answer(
    authority_snapshot: dict,
    *,
    native_memory_active: bool,
    memory_source_mode: str,
) -> str:
    """Render Brody/Jarjar role from the canonical authority snapshot.

    This is intentionally governance-first: capability questions must not be
    answered from project-memory material or a legacy True Voice fallback.
    """
    may = set(authority_snapshot.get("brody_may") or [])
    must_not = set(authority_snapshot.get("brody_must_not") or [])

    capabilities: list[str] = []
    if "repondre_naturellement" in may:
        capabilities.append("répondre naturellement")
    if {
        "expliquer_ce_que_brody_peut_faire",
        "expliquer_ce_que_brody_ne_peut_pas_faire",
    } & may:
        capabilities.append("expliquer ses capacités, ses limites et les frontières de gouvernance")
    if "lister_capacites_et_limites" in may:
        capabilities.append("lister les capacités et limites du système")
    if "expliquer_automation_snapshot" in may:
        capabilities.append("expliquer l'état d'automatisation observé")
    if "expliquer_role_humain_operateur" in may:
        capabilities.append("situer le rôle de l'opérateur humain")
    if "expliquer_role_kx108_decision_authority" in may:
        capabilities.append("situer KX108 comme autorité de décision")
    if "expliquer_role_memoire_candidate_only" in may:
        capabilities.append("expliquer la place de la mémoire sans lui donner d'autorité")
    if "expliquer_boundary_complet" in may:
        capabilities.append("exposer le boundary complet")

    forbidden: list[str] = []
    mapping = {
        "decider": "décider",
        "emettre_act": "émettre ACT",
        "emettre_hold_block_allow_comme_verdict": "émettre HOLD/BLOCK/ALLOW comme verdict",
        "ecrire_memoire_automatiquement": "écrire automatiquement en mémoire",
        "executer": "exécuter une action",
        "bypass_x108": "contourner X108",
    }
    for key, label in mapping.items():
        if key in must_not:
            forbidden.append(label)

    cap_text = ", ".join(capabilities) if capabilities else "répondre et contextualiser en mode consultatif"
    forbidden_text = ", ".join(forbidden) if forbidden else "décider ou agir à la place de KX108"

    if native_memory_active:
        memory_text = "Native Memory est active sur le runtime connecté."
    else:
        memory_text = (
            "Native Memory n'est pas active sur ce runtime ; "
            f"la source mémoire observée est {memory_source_mode or 'UNKNOWN'}."
        )

    return (
        "Jarjar est la surface locale qui s'appuie sur Brody pour la cognition gouvernée. "
        f"Selon la matrice d'autorité active, Brody peut {cap_text}. "
        f"Il ne peut pas {forbidden_text}. "
        "KX108/X108 reste l'unique autorité de décision ; Brody reste consultatif et readonly. "
        f"{memory_text}"
    )


def _default_transport(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _discover_local_endpoint(timeout: float = 0.6) -> str:
    candidates = (
        "http://127.0.0.1:8012/api/brody/chat",
        "http://127.0.0.1:8000/api/brody/chat",
    )
    for candidate in candidates:
        status_url = candidate.rsplit("/api/brody/chat", 1)[0] + "/api/status"
        try:
            request = Request(status_url, method="GET")
            with urlopen(request, timeout=timeout):
                print(f"JARJAR_OBSIDIA: discovered {candidate}")
                return candidate
        except Exception:
            continue
    fallback = candidates[0]
    print(f"JARJAR_OBSIDIA: no local status endpoint detected, fallback={fallback}")
    return fallback


@dataclass
class ObsidiaStackCognition:
    endpoint: str = "http://127.0.0.1:8012/api/brody/chat"
    api_key: str = ""
    timeout_seconds: float = 20.0
    allow_provider: bool = True
    session_id: str = field(default_factory=lambda: f"jarjar-{uuid4().hex}")
    transport: Transport = _default_transport
    last_trace: dict = field(default_factory=dict, init=False)

    def _try_local_brody(self, text: str) -> str | None:
        # A custom transport is an explicit HTTP seam used by tests/injected
        # callers. Preserve that behavior instead of bypassing it locally.
        if self.transport is not _default_transport:
            return None

        enabled = os.getenv("JARJAR_LOCAL_BRODY", "1").strip().lower()
        if enabled in {"0", "false", "no", "off"}:
            return None

        try:
            from jarvis.obsidia_port.local_brody_runtime_adapter import (
                respond_local_brody,
            )

            result = respond_local_brody(
                text,
                session_id=self.session_id,
                language="fr",
            )
        except Exception as exc:
            print(
                "JARJAR_LOCAL_BRODY: FALLBACK "
                f"error={type(exc).__name__}: {exc}"
            )
            return None

        if not isinstance(result, dict):
            print("JARJAR_LOCAL_BRODY: FALLBACK invalid_result")
            return None

        authority = str(result.get("decision_authority") or "").strip()
        readonly = result.get("readonly")
        available = result.get("available") is True
        answer = result.get("final_answer")

        safe = (
            available
            and authority == "KX108_ONLY"
            and readonly is True
            and isinstance(answer, str)
            and bool(answer.strip())
        )

        self.last_trace = {
            "source": "LOCAL_BRODY_RUNTIME",
            "voice_runtime": "BRODY_LOCAL_NATIVE_RUNTIME",
            "memory_source_mode": result.get("memory_source_mode"),
            "memory_status": result.get("memory_status"),
            "memory_retrieval_status": result.get("retrieval_status"),
            "native_memory_active": (
                result.get("memory_source_mode") == "OBSIDIA_NATIVE_MEMORY"
            ),
            "legacy_memory_active": False,
            "true_voice_source": result.get("voice_source"),
            "decision_authority": authority or "KX108_ONLY",
            "readonly": readonly,
            "local_brody_status": result.get("status"),
            "local_memory_required": result.get("memory_required"),
            "local_memory_query": result.get("memory_query"),
            "local_cognitive_join_status": result.get(
                "cognitive_join_status"
            ),
            "local_reverse_os_status": result.get("reverse_os_status"),
            "local_w4_memory_retrieval_status": result.get(
                "w4_memory_retrieval_status"
            ),
        }

        if not safe:
            print(
                "JARJAR_LOCAL_BRODY: FALLBACK "
                f"status={result.get('status')} "
                f"available={available} "
                f"authority={authority or 'UNKNOWN'} "
                f"readonly={readonly}"
            )
            return None

        print(
            "JARJAR_LOCAL_BRODY: PASS "
            f"voice={result.get('voice_source') or 'UNKNOWN'} "
            f"memory={result.get('memory_source_mode') or 'UNKNOWN'} "
            f"memory_required={result.get('memory_required')} "
            "authority=KX108_ONLY readonly=True"
        )

        return answer.strip()

    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        text = user_input.strip()
        if not text:
            raise ValueError("empty cognition input")

        local_answer = self._try_local_brody(text)
        if local_answer:
            return local_answer

        if self.transport is _default_transport:
            print(
                "JARJAR_LOCAL_BRODY: using HTTP Brody fallback "
                f"endpoint={self.endpoint}"
            )

        payload = {
            "message": text,
            "language": "fr",
            "session_id": self.session_id,
            # Important: this authorizes the STACK to consider its provider
            # path. Jarjar never selects or calls Qwen directly.
            "allow_provider": bool(self.allow_provider),
            "allow_memory_candidate": False,
            "allow_manual_apply": False,
            "compact": False,
            "debug": False,
            "debug_full": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        request = Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            raw = self.transport(request, self.timeout_seconds)
        except HTTPError as exc:
            raise RuntimeError(f"Obsidia cognition HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("Obsidia cognition endpoint unavailable") from exc
        except TimeoutError as exc:
            raise RuntimeError("Obsidia cognition timeout") from exc

        try:
            packet = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("invalid Obsidia cognition response") from exc

        if not isinstance(packet, dict):
            raise RuntimeError("invalid Obsidia cognition packet")

        memory_snapshot = packet.get("memory_response_chain_snapshot")
        if not isinstance(memory_snapshot, dict):
            memory_snapshot = {}

        true_voice = packet.get("true_voice_snapshot")
        if not isinstance(true_voice, dict):
            true_voice = {}

        domain_raccord = true_voice.get("domain_raccord_snapshot")
        if not isinstance(domain_raccord, dict):
            domain_raccord = {}

        authority_snapshot = packet.get("authority_snapshot")
        if not isinstance(authority_snapshot, dict):
            authority_snapshot = {}

        memory_source_mode = str(
            memory_snapshot.get("source_mode") or ""
        ).strip()
        memory_chain_source = str(
            memory_snapshot.get("chain_source") or ""
        ).strip()
        native_memory_active = (
            memory_source_mode == "OBSIDIA_NATIVE_MEMORY"
            or memory_chain_source.startswith("obsidia_native_memory")
        )
        legacy_memory_active = (
            not native_memory_active
            and (
                "GRAPHITI" in memory_source_mode.upper()
                or "graphiti" in memory_chain_source.casefold()
            )
        )

        self.last_trace = {
            "source": packet.get("source"),
            "voice_runtime": packet.get("voice_runtime"),
            "memory_source_mode": memory_source_mode or None,
            "memory_chain_source": memory_chain_source or None,
            "memory_status": memory_snapshot.get("status"),
            "memory_retrieval_status": memory_snapshot.get("retrieval_status"),
            "native_memory_active": native_memory_active,
            "legacy_memory_active": legacy_memory_active,
            "true_voice_source": (
                true_voice.get("final_answer_source")
                or true_voice.get("voice_source")
            ),
            "domain_raccord_status": domain_raccord.get("status"),
            "domain_voice_mode": true_voice.get("domain_voice_mode"),
            "domain_structural_answer_available": domain_raccord.get(
                "structural_answer_available"
            ),
            "domain_memory_dependency": domain_raccord.get("memory_dependency"),
            "authority_request_type": authority_snapshot.get("request_type"),
            "authority_response_mode": authority_snapshot.get("response_mode"),
            "authority_requires_kx108_decision": authority_snapshot.get(
                "requires_kx108_decision"
            ),
            "provider_status": packet.get("provider_status"),
            "provider_called": packet.get("provider_called"),
            "selected_provider": packet.get("selected_provider"),
            "fastpath": packet.get("fastpath"),
            "decision_authority": packet.get("decision_authority"),
            "readonly": packet.get("readonly"),
        }
        trace_bits = [
            f"{key}={value}"
            for key, value in self.last_trace.items()
            if value is not None
        ]
        print(
            "JARJAR_COGNITION: "
            + (" ".join(trace_bits) if trace_bits else "no routing metadata returned")
        )

        brody_link_ok = (
            str(packet.get("voice_runtime") or "").strip() == "BRODY_OBSIDIEN_V1_4_12A"
            and native_memory_active
            and str(packet.get("decision_authority") or "").strip() == "KX108_ONLY"
            and packet.get("readonly") is True
        )
        print(
            "JARJAR_BRODY_LINK: "
            + ("OK" if brody_link_ok else "DEGRADED")
            + f" runtime={packet.get('voice_runtime') or 'UNKNOWN'}"
            + f" memory={memory_source_mode or 'UNKNOWN'}"
            + f" native_memory_active={native_memory_active}"
            + f" authority={packet.get('decision_authority') or 'UNKNOWN'}"
            + f" readonly={packet.get('readonly')}"
        )

        governance_capability_safe = (
            authority_snapshot.get("request_type") == "CAPABILITY_SCOPE"
            and authority_snapshot.get("response_mode") == "CAPABILITY_SCOPE"
            and authority_snapshot.get("decision_authority") == "KX108_ONLY"
            and packet.get("decision_authority") == "KX108_ONLY"
            and packet.get("readonly") is True
        )

        if governance_capability_safe:
            print(
                "JARJAR_BRODY_GOVERNANCE: ACCEPT_CAPABILITY_SCOPE "
                "authority=KX108_ONLY readonly=True"
            )
            return _governed_capability_answer(
                authority_snapshot,
                native_memory_active=native_memory_active,
                memory_source_mode=memory_source_mode,
            )

        structural_answer = domain_raccord.get("structural_answer")
        structural_answer_safe = (
            domain_raccord.get("structural_answer_available") is True
            and str(domain_raccord.get("memory_dependency") or "").upper() == "NONE"
            and isinstance(structural_answer, str)
            and bool(structural_answer.strip())
        )

        candidates = (
            true_voice.get("final_answer"),
            packet.get("response"),
            packet.get("final_answer"),
        )

        true_voice_source = str(
            true_voice.get("final_answer_source")
            or true_voice.get("voice_source")
            or ""
        ).strip()
        memory_derived_voice = (
            true_voice_source in {
                "MEMORY_RESPONSE_CHAIN",
                "LOCAL_GRAPHITI_INDEX_FALLBACK",
            }
            or "MEMORY" in true_voice_source.upper()
            or "GRAPHITI" in true_voice_source.upper()
        )

        if (
            legacy_memory_active
            and memory_snapshot.get("status") == "BRODY_MEMORY_RESPONSE_CHAIN_PASS"
        ):
            print(
                "JARJAR_BRODY_MEMORY: UNTRUSTED_PASS "
                f"source={memory_source_mode or 'UNKNOWN'} "
                f"chain={memory_chain_source or 'UNKNOWN'} "
                "native_memory_active=False"
            )

        if structural_answer_safe:
            answer = structural_answer.strip()
            print(
                "JARJAR_BRODY_DOMAIN: ACCEPT_STRUCTURAL "
                f"mode={true_voice.get('domain_voice_mode') or 'UNKNOWN'} "
                "memory_dependency=NONE"
            )
        else:
            answer = next(
                (
                    candidate.strip()
                for candidate in candidates
                if isinstance(candidate, str)
                and candidate.strip()
                and not _is_legacy_graphiti_text(candidate)
                    and not (legacy_memory_active and memory_derived_voice)
                ),
                "",
            )

        # If the connected Brody runtime exposes the current Native Memory
        # snapshot but its presentation layer still leaks an old Graphiti
        # phrase, prefer the canonical Native Memory response material.
        if not answer and native_memory_active:
            native_response = memory_snapshot.get("response_md")
            if (
                isinstance(native_response, str)
                and native_response.strip()
                and not _is_legacy_graphiti_text(native_response)
            ):
                answer = native_response.strip()

        if not answer:
            legacy_seen = (
                legacy_memory_active
                or any(_is_legacy_graphiti_text(value) for value in candidates)
            )
            if legacy_seen:
                return (
                    "Le runtime Brody connecté a renvoyé un ancien fallback Graphiti. "
                    "Jarjar refuse cette réponse : Native Memory est le chemin mémoire canonique."
                )
            raise RuntimeError("Obsidia cognition returned no conversational answer")

        return answer


def from_environment() -> ObsidiaStackCognition:
    configured_endpoint = os.getenv("JARJAR_OBSIDIA_CHAT_URL", "").strip()
    endpoint = configured_endpoint or _discover_local_endpoint()
    return ObsidiaStackCognition(
        endpoint=endpoint,
        api_key=os.getenv("OBSIDIA_API_KEY", ""),
        timeout_seconds=float(os.getenv("JARJAR_OBSIDIA_TIMEOUT", "20")),
        allow_provider=os.getenv("JARJAR_OBSIDIA_ALLOW_PROVIDER", "1").strip().lower()
        not in {"0", "false", "no", "off"},
    )
