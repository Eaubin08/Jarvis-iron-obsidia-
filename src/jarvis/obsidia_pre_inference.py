"""Jarjar adapter for the ported Obsidia pre-inference router.

The router is advisory/non-sovereign. It selects a cognition path; it never
executes an action and never grants authority. Jarjar's ActionRouter remains
the only local action execution path, under PermissionPolicy.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .obsidia_port.router_core.decision import decide
from .obsidia_port.brody_readonly_intent_guard import detect_readonly_runtime_state_intent
from .obsidia_port.brody_semantic_query_router import build_semantic_query


_MEMORY_INDEX = Path(__file__).resolve().parent / "obsidia_port" / "router_core" / "memory_index.json"


@dataclass(frozen=True)
class PreInferenceDecision:
    route: str
    level: int
    reason: str
    ir: dict[str, Any]
    gate: dict[str, Any]
    topic: dict[str, Any]
    direct_answer: str | None = None

    @property
    def is_confident(self) -> bool:
        return self.route not in {"clarification_needed", "", "unknown"}


class ObsidiaPreInferenceAdapter:
    """Consume the isolated Obsidia Router core without execution authority."""

    decision_authority = "KX108_ONLY"
    readonly = True
    can_act = False

    def __init__(self) -> None:
        self._memory_index = self._load_memory_index()
        self.last_decision: PreInferenceDecision | None = None

    @staticmethod
    def _load_memory_index() -> dict:
        try:
            data = json.loads(_MEMORY_INDEX.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def route(self, user_input: str) -> PreInferenceDecision:
        raw = decide(user_input, memory_index=self._memory_index)
        route = str(raw.get("route") or "")
        ir = dict(raw.get("ir") or {})
        raw_topic = dict(raw.get("topic") or {})

        # Jarjar is the local surface name. For Brody's semantic router only,
        # map that surface name to the Brody role vocabulary already present
        # in the canonical stack. The user's original text is never changed
        # for the actual provider call.
        semantic_input = user_input
        if "jarjar" in user_input.casefold():
            semantic_input = (
                user_input.replace("Jarjar", "Brody")
                .replace("jarjar", "brody")
                .replace("JARJAR", "BRODY")
            )

        semantic = build_semantic_query(semantic_input)
        semantic_topic = str(semantic.get("topic") or "")

        # Jarjar is the user-facing surface of the Brody/Obsidia cognition
        # stack. If the generic surface wording did not resolve, recompile it
        # through the canonical Brody role topic already defined upstream.
        if (
            "jarjar" in user_input.casefold()
            and semantic_topic == "GENERAL"
        ):
            semantic = build_semantic_query(
                "qu'est-ce que tu sais du projet Obsidia et de ton rôle Brody ?"
            )
            semantic_topic = str(semantic.get("topic") or "")

        readonly_intent = detect_readonly_runtime_state_intent(user_input)
        readonly_pass = (
            readonly_intent.get("status")
            == "RUNTIME_STATE_READONLY_INTENT_PASS"
        )

        # The readonly guard is a safety/context signal, not a universal
        # replacement for semantic routing. Promote it to a Jarjar runtime
        # answer only when the router itself points at runtime/memory ambiguity,
        # or when the semantic router identifies a current-state question.
        runtime_state_query = (
            (
                readonly_pass
                and (
                    route == "clarification_needed"
                    or semantic_topic == "CURRENT_STATE"
                )
            )
            or (
                ir.get("target_layer") == "memory"
                and semantic_topic == "MEMORY_QUERY"
                and ir.get("intent_type") in {"reasoning", "status"}
            )
        )

        if runtime_state_query:
            decision = PreInferenceDecision(
                route="runtime_state_readonly",
                level=0,
                reason="Brody semantic/runtime state resolved before model escalation",
                ir={
                    **ir,
                    "intent_type": "runtime_state_query",
                    "target_layer": "runtime",
                    "action_type": "read",
                    "risk_level": "low",
                },
                gate={
                    "verdict": "ALLOW",
                    "invariants": ["readonly", "KX108_ONLY"],
                },
                topic={
                    **semantic,
                    "topic": "RUNTIME_STATE_READONLY",
                    "source_topic": semantic_topic,
                },
            )
            self.last_decision = decision
            print(
                "JARJAR_PRE_ROUTE: "
                "route=runtime_state_readonly level=0 "
                "intent=runtime_state_query layer=runtime gate=ALLOW "
                "authority=KX108_ONLY readonly=True"
            )
            return decision

        # Canonical Brody semantic role/self queries should stay on Brody even
        # if the public deterministic IR does not know the local Jarjar name.
        if semantic_topic == "OBSIDIA_BRODY_ROLE":
            raw["route"] = "brody"
            raw["level"] = 1
            raw["reason"] = "canonical Brody semantic role route"
            route = "brody"
            raw["topic"] = semantic
            if ir.get("intent_type") == "unknown":
                ir["intent_type"] = "question"
                ir["target_layer"] = "brody"
                ir["action_type"] = "answer"
                raw["ir"] = ir
        direct_answer = None
        if route == "local_solver":
            value = raw.get("solver_answer")
            if isinstance(value, str) and value.strip():
                direct_answer = value.strip()
        elif route == "memory_hit":
            value = raw.get("memory_entry")
            if isinstance(value, str) and value.strip():
                direct_answer = value.strip()
        elif route == "denied":
            direct_answer = f"DENY — {raw.get('reason') or 'demande hors cadre'}."
        elif route == "hold_commands_only":
            direct_answer = (
                "HOLD — cette demande implique une action monde non résolue par "
                "le chemin d'action structuré. Rien n'a été exécuté."
            )

        decision = PreInferenceDecision(
            route=route,
            level=int(raw.get("level") or 0),
            reason=str(raw.get("reason") or ""),
            ir=dict(raw.get("ir") or {}),
            gate=dict(raw.get("gate") or {}),
            topic=dict(raw.get("topic") or {}),
            direct_answer=direct_answer,
        )
        self.last_decision = decision
        print(
            "JARJAR_PRE_ROUTE: "
            f"route={decision.route or 'UNKNOWN'} "
            f"level={decision.level} "
            f"intent={decision.ir.get('intent_type')} "
            f"layer={decision.ir.get('target_layer')} "
            f"gate={decision.gate.get('verdict')} "
            "authority=KX108_ONLY readonly=True"
        )
        return decision
