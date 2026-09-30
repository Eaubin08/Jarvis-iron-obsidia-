"""Readonly OS Trad / IR Candidate / OS Reverse backend supporting routes.

Phase 9B2 minimal implementation.

These routes are supporting surfaces only.
They do not replace /api/brody/chat.
They do not decide, act, mutate memory, mutate Graphiti, or mutate X108.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from apps.obsidia_api.safe_response import safe_backend_response
from apps.obsidia_api.brody_domain_raccord_adapter import adjust_risk_flags
from periphery.language.lexical_calibrator import calibrate_lexical_knownness

try:
    from periphery.language.language_router import detect_language as _detect_language_impl
except Exception:  # pragma: no cover
    _detect_language_impl = None

try:
    from periphery.language.language_router import route_language as _route_language_impl
except Exception:  # pragma: no cover
    _route_language_impl = None

try:
    from periphery.reverse_os.action_projection_readonly import project_action_readonly
except Exception:  # pragma: no cover
    project_action_readonly = None

try:
    from periphery.reverse_os.audience_projection import project_audience
except Exception:  # pragma: no cover
    project_audience = None

try:
    from periphery.reverse_os.format_projection import project_format
except Exception:  # pragma: no cover
    project_format = None


router = APIRouter(tags=["os-trad-ir-reverse"])


_BOUNDARY: dict[str, Any] = {
    "readonly": True,
    "advisory_only": True,
    "allowed_to_decide": False,
    "allowed_to_act": False,
    "emits_act": False,
    "emits_verdict": False,
    "decision_authority": "KX108_ONLY",
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "real_action": False,
}


class OSTradTranslateRequest(BaseModel):
    text: str
    language: str = "auto"
    session_id: Optional[str] = None
    include_context: bool = True
    include_tree_context: bool = True
    include_graphiti_context: bool = True


class IRCandidateRequest(BaseModel):
    text: str
    language: str = "auto"
    alphabet_units: list[dict[str, Any]] = Field(default_factory=list)
    tree_context: dict[str, Any] = Field(default_factory=dict)
    memory_context: dict[str, Any] = Field(default_factory=dict)
    graphiti_context: dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class OSReverseProjectRequest(BaseModel):
    text: str
    language: str = "auto"
    ir_candidate: dict[str, Any] = Field(default_factory=dict)
    audience: str = "general"
    format: str = "structured"
    tree_context: dict[str, Any] = Field(default_factory=dict)
    memory_context: dict[str, Any] = Field(default_factory=dict)
    graphiti_context: dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


def _plain(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return value


def _detect_language(text: str, requested: str = "auto") -> str:
    requested = (requested or "auto").lower()
    if requested in {"fr", "en"}:
        return requested

    if _detect_language_impl:
        try:
            detected = _detect_language_impl(text)
            if detected in {"fr", "en"}:
                return detected
        except Exception:
            pass

    low = text.lower()
    fr_markers = ["je ", "tu ", "nous ", "vous ", "salut", "bonjour", "erreur", "mémoire", "memoire", "sans décider", "autorise"]
    en_markers = ["hello", "explain", "what", "why", "error", "debug", "memory", "readonly"]

    fr_score = sum(1 for m in fr_markers if m in low)
    en_score = sum(1 for m in en_markers if m in low)

    if fr_score >= en_score and fr_score > 0:
        return "fr"
    if en_score > 0:
        return "en"
    return "unknown"


def _risk_flags(text: str) -> list[str]:
    low = text.lower()
    flags: list[str] = []

    if any(token in low for token in ["autorise", "authorize", "je suis le créateur", "i am the creator", "admin", "root"]):
        flags.append("authority_claim")

    # F22B: "act" must be a whole token — "actifs" and "action" must NOT match.
    # "ne propose aucune action" is a negation, NOT an action_request.
    _action_negation = bool(re.search(
        r"ne\s+propose\s+(?:aucune|pas\s+de)\s+action|"
        r"\bsans\s+action\b|\bno\s+action\b|\bwithout\s+action\b",
        low,
    ))
    _action_tokens = ["agir", "lance", "execute", "exécute", "send", "transfer", "write"]
    _has_action = (
        any(token in low for token in _action_tokens)
        or bool(re.search(r"\bact\b", low))
    )
    if _has_action and not _action_negation:
        flags.append("action_request")

    if any(token in low for token in ["kernel", "x108", "mutation", "patch", "modify", "modifie"]):
        flags.append("mutation_request")

    if any(token in low for token in ["memory_write", "écris en mémoire", "write memory", "graphiti_write", "neo4j_write"]):
        flags.append("write_request")

    if any(token in low for token in ["traceback", "exception", "404", "500", "bug", "debug", "pytest", "powershell"]):
        flags.append("code_debug")

    return adjust_risk_flags(text, flags)


def _intent(text: str, flags: list[str]) -> str:
    low = text.lower()

    if "code_debug" in flags:
        return "code_debug"
    if "authority_claim" in flags:
        return "authority_claim"
    if any(flag in flags for flag in ("write_request", "memory_write_request", "canon_promotion_request")):
        return "write_request"
    if "action_request" in flags:
        return "action_request"
    if "?" in text or any(token in low for token in ["pourquoi", "comment", "what", "why", "how"]):
        return "question"
    if any(token in low for token in ["analyse", "analyze", "audit", "vérifie", "verify"]):
        return "analysis"
    return "unknown"


def _alphabet_units(text: str, detected_language: str, flags: list[str]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = [
        {"kind": "language", "value": detected_language, "source": "REAL_BACKEND"},
        {"kind": "boundary", "value": "KX108_ONLY", "source": "REAL_BACKEND"},
        {"kind": "readonly", "value": True, "source": "REAL_BACKEND"},
    ]

    for flag in flags:
        units.append({"kind": "risk_flag", "value": flag, "source": "REAL_BACKEND"})

    if len(text.strip()) <= 3:
        units.append({"kind": "input_shape", "value": "minimal_or_empty_like", "source": "REAL_BACKEND"})
    elif len(text) > 800:
        units.append({"kind": "input_shape", "value": "long", "source": "REAL_BACKEND"})
    else:
        units.append({"kind": "input_shape", "value": "standard", "source": "REAL_BACKEND"})

    return units


def _constraints(flags: list[str]) -> list[str]:
    values = [
        "READONLY",
        "ADVISORY_ONLY",
        "NO_ACT",
        "NO_VERDICT",
        "NO_MEMORY_WRITE",
        "NO_KERNEL_MUTATION",
        "NO_X108_MUTATION",
        "DECISION_AUTHORITY_KX108_ONLY",
    ]

    if "action_request" in flags or "mutation_request" in flags or "write_request" in flags:
        values.append("ACTION_REQUEST_FORCED_TO_READONLY_PROJECTION")

    return values


def _refs_from_context(context: dict[str, Any], prefix: str) -> list[str]:
    refs: list[str] = []
    if not isinstance(context, dict):
        return refs

    for key in ("id", "query_id", "packet_id", "adapter_id", "tree_id", "source_query_id"):
        value = context.get(key)
        if value not in (None, ""):
            refs.append(f"{prefix}:{value}")

    items = context.get("items") or context.get("results") or context.get("nodes")
    if isinstance(items, list):
        for idx, item in enumerate(items[:5]):
            if isinstance(item, dict):
                value = item.get("id") or item.get("name") or item.get("title") or idx
                refs.append(f"{prefix}:{value}")

    return refs


@router.post("/api/os-trad/translate")
async def os_trad_translate(req: OSTradTranslateRequest):
    detected_language = _detect_language(req.text, req.language)
    flags = _risk_flags(req.text)
    alphabet_units = _alphabet_units(req.text, detected_language, flags)

    language_route: dict[str, Any] = {}
    if _route_language_impl:
        try:
            language_route = _plain(_route_language_impl(req.text))
        except Exception as exc:
            language_route = {"error": str(exc), "source": "language_router"}

    payload = {
        **_BOUNDARY,
        "source": "REAL_BACKEND",
        "route": "/api/os-trad/translate",
        "detected_language": detected_language,
        "alphabet_units": alphabet_units,
        "constraints": _constraints(flags),
        "risk_flags": flags,
        "context_refs": [],
        "tree_context": {
            "enabled": bool(req.include_tree_context),
            "source": "/api/periphery/cognitive/trees",
            "mode": "optional_readonly_context",
        } if req.include_tree_context else {},
        "graphiti_context": {
            "enabled": bool(req.include_graphiti_context),
            "source": "/api/periphery/graphiti/context-adapt",
            "mode": "optional_readonly_context",
        } if req.include_graphiti_context else {},
        "trace": {
            "session_id": req.session_id,
            "language_route": language_route,
            "binding_sources": [
                "periphery/language/language_router.py",
                "Workbench symbolicAlphabet.ts behavior",
                "/api/periphery/brody/language-route",
                "/api/periphery/cognitive/trees",
                "/api/periphery/graphiti/context-adapt",
            ],
        },
    }
    return safe_backend_response(payload, source="REAL_BACKEND")


@router.post("/api/ir/candidate")
async def ir_candidate(req: IRCandidateRequest):
    detected_language = _detect_language(req.text, req.language)
    flags = _risk_flags(req.text)
    intent = _intent(req.text, flags)
    constraints = _constraints(flags)

    lexical_calibration = calibrate_lexical_knownness(
        req.text,
        detected_language,
    )

    contradictions: list[str] = []
    if any(flag in flags for flag in ["action_request", "mutation_request", "write_request"]):
        contradictions.append("REQUEST_REQUIRES_ACTION_BUT_ROUTE_IS_READONLY")

    ir = {
        "intent": intent,
        "risk_flags": flags,
        "contradictions": contradictions,
        "constraints": constraints,
        "tree_refs": _refs_from_context(req.tree_context, "tree"),
        "memory_refs": _refs_from_context(req.memory_context, "memory"),
        "graphiti_refs": _refs_from_context(req.graphiti_context, "graphiti"),
        "language": detected_language,
        "alphabet_units": req.alphabet_units,
        "unknowns": list(
            lexical_calibration.get(
                "unknowns",
                [],
            )
        ),
        "lexical_calibration": lexical_calibration,
    }

    payload = {
        **_BOUNDARY,
        "source": "REAL_BACKEND",
        "route": "/api/ir/candidate",
        "ir_candidate": ir,
        "trace": {
            "session_id": req.session_id,
            "binding_sources": [
                "Workbench irCandidateBuilder.ts behavior",
                "periphery/obsidia_ir.py wrapper",
                "/api/periphery/context/build",
                "/api/periphery/context/validate",
                "/api/periphery/brody/context-query",
                "/api/periphery/cognitive/memory-world-map",
            ],
        },
    }
    return safe_backend_response(payload, source="REAL_BACKEND")


@router.post("/api/os-reverse/project")
async def os_reverse_project(req: OSReverseProjectRequest):
    detected_language = _detect_language(req.text, req.language)
    flags = _risk_flags(req.text)
    intent = str(req.ir_candidate.get("intent") or _intent(req.text, flags))

    action_projection: dict[str, Any] = {}
    if project_action_readonly:
        try:
            action_projection = _plain(project_action_readonly("phase9b2_reverse", intent, req.text))
        except Exception as exc:
            action_projection = {"error": str(exc), "source": "project_action_readonly"}

    audience_projection: dict[str, Any] = {}
    if project_audience:
        try:
            audience_projection = _plain(project_audience("phase9b2_audience", req.text, req.audience))
        except Exception as exc:
            audience_projection = {"error": str(exc), "source": "project_audience"}

    format_projection: dict[str, Any] = {}
    if project_format:
        try:
            format_projection = _plain(project_format("phase9b2_format", req.format))
        except TypeError:
            try:
                format_projection = _plain(project_format("phase9b2_format", req.audience))
            except Exception as exc:
                format_projection = {"error": str(exc), "source": "project_format"}
        except Exception as exc:
            format_projection = {"error": str(exc), "source": "project_format"}

    summary = "Readonly projection generated. No action, verdict, memory write, Graphiti write, kernel mutation, or X108 mutation emitted."
    if detected_language == "fr":
        summary = "Projection readonly générée. Aucune action, aucun verdict, aucune écriture mémoire, aucune écriture Graphiti, aucune mutation kernel ou X108."

    payload = {
        **_BOUNDARY,
        "source": "REAL_BACKEND",
        "route": "/api/os-reverse/project",
        "projection": {
            "language": detected_language,
            "response_mode": "readonly_projection",
            "summary": summary,
            "next_safe_step": "inspect_trace_or_call_brody_chat",
            "boundary_notice": "KX108_ONLY",
        },
        "action_projection": action_projection,
        "audience_projection": audience_projection,
        "format_projection": format_projection,
        "tree_refs": _refs_from_context(req.tree_context, "tree"),
        "memory_refs": _refs_from_context(req.memory_context, "memory"),
        "graphiti_refs": _refs_from_context(req.graphiti_context, "graphiti"),
        "trace": {
            "session_id": req.session_id,
            "binding_sources": [
                "Workbench osReverseProjection.ts behavior",
                "periphery/reverse_os/action_projection_readonly.py",
                "periphery/reverse_os/audience_projection.py",
                "periphery/reverse_os/format_projection.py",
                "/api/periphery/brody/double-brain-route",
                "/api/periphery/brody/diffusion-mix",
            ],
        },
    }
    return safe_backend_response(payload, source="REAL_BACKEND")
