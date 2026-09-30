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
        readonly_intent = detect_readonly_runtime_state_intent(user_input)
        if readonly_intent.get("status") == "RUNTIME_STATE_READONLY_INTENT_PASS":
            decision = PreInferenceDecision(
                route="runtime_state_readonly",
                level=0,
                reason="canonical Brody readonly runtime-state intent guard",
                ir={
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
                    "topic": "RUNTIME_STATE_READONLY",
                    "is_canonical": True,
                    "route": "BRODY_READONLY_INTENT_GUARD",
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

        raw = decide(user_input, memory_index=self._memory_index)
        route = str(raw.get("route") or "")
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
