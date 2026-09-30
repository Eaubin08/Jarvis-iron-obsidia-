"""F20B — Gencoin Cognitive Ledger readonly packet.

Builds a readonly cognitive-value ledger projection over existing:
- gencoin_shadow_packet
- thermo_unified_packet
- value_layer
- ledger status

No mint. No wallet. No blockchain. No token. No ACT. No decision.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any


_BOUNDARY: dict[str, Any] = {
    "decision_authority": "KX108_ONLY",
    "readonly": True,
    "advisory_only": True,
    "context_signal_only": True,
    "allowed_to_decide": False,
    "allowed_to_act": False,
    "emits_act": False,
    "emits_verdict": False,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "real_action": False,
    "execution_allowed": False,
    "final_scoring_enabled": False,
    "economic_scoring_enabled": False,
    "blockchain_enabled": False,
    "mint_allowed": False,
    "wallet_enabled": False,
    "is_real_token": False,
}


def _clamp(v: Any) -> float:
    try:
        f = float(v)
    except Exception:
        return 0.0
    return round(max(0.0, min(1.0, f)), 4)


def _hash_entry(payload: dict[str, Any]) -> str:
    raw = repr(sorted(payload.items())).encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()


def _score_status(score: float) -> str:
    if score >= 0.80:
        return "HIGH_READONLY_VALUE"
    if score >= 0.55:
        return "MEDIUM_READONLY_VALUE"
    if score > 0.0:
        return "LOW_READONLY_VALUE"
    return "NO_READONLY_VALUE"


def build_gencoin_cognitive_ledger_packet(
    *,
    gencoin_shadow_packet: dict[str, Any] | None = None,
    thermo_unified_packet: dict[str, Any] | None = None,
    value_layer: dict[str, Any] | None = None,
    ledger_status: dict[str, Any] | None = None,
    session_id: str = "",
    source: str = "BRODY",
) -> dict[str, Any]:
    g = gencoin_shadow_packet if isinstance(gencoin_shadow_packet, dict) else {}
    tu = thermo_unified_packet if isinstance(thermo_unified_packet, dict) else {}
    vl = value_layer if isinstance(value_layer, dict) else {}
    ledger = ledger_status if isinstance(ledger_status, dict) else {}

    shadow_scores = g.get("shadow_scores") if isinstance(g.get("shadow_scores"), dict) else {}
    value_scores = vl.get("scores") if isinstance(vl.get("scores"), dict) else {}

    cognitive_value = _clamp(shadow_scores.get("cognitive_value"))
    proof_value = _clamp(shadow_scores.get("proof_value"))
    reuse_value = _clamp(shadow_scores.get("reuse_value"))
    memory_value = _clamp(shadow_scores.get("memory_value"))
    stability_value = _clamp(shadow_scores.get("stability_value"))
    attention_cost = _clamp(shadow_scores.get("attention_cost"))
    energy_cost = _clamp(shadow_scores.get("energy_cost"))

    cognitive_ledger_score = _clamp(
        cognitive_value * 0.24
        + proof_value * 0.22
        + reuse_value * 0.18
        + memory_value * 0.14
        + stability_value * 0.14
        - attention_cost * 0.04
        - energy_cost * 0.04
    )

    usable_shadow = bool(g.get("usable_shadow_value"))
    thermo_ok = bool(tu.get("usable_for_gencoin"))
    ledger_empty = ledger.get("status") in (None, "", "LIVE_EMPTY_REGISTRY")

    entry_base = {
        "session_id": session_id,
        "source": source,
        "gencoin_version": g.get("version"),
        "gencoin_mode": g.get("mode"),
        "usable_shadow_value": usable_shadow,
        "thermo_unified_usable_for_gencoin": thermo_ok,
        "ledger_status": ledger.get("status", "LIVE_EMPTY_REGISTRY"),
        "cognitive_ledger_score": cognitive_ledger_score,
        "score_status": _score_status(cognitive_ledger_score),
    }

    entry = {
        "ledger_id": "COGLEDGER_" + _hash_entry(entry_base)[:16],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **entry_base,
        "shadow_scores": {
            "cognitive_value": cognitive_value,
            "proof_value": proof_value,
            "reuse_value": reuse_value,
            "memory_value": memory_value,
            "attention_cost": attention_cost,
            "energy_cost": energy_cost,
            "stability_value": stability_value,
            "economic_projection": None,
        },
        "value_layer_scores_status": (
            "NULL_VALUE_LAYER_SCORES_SHADOW_USED"
            if value_scores and all(v is None for v in value_scores.values())
            else "VALUE_LAYER_SCORES_NOT_USED"
        ),
        "ledger_projection": {
            "ledger_empty": ledger_empty,
            "projected_entry_only": True,
            "persisted": False,
            "minted": False,
            "wallet_touched": False,
            "blockchain_touched": False,
        },
        "reason": (
            "GENCOIN_COGNITIVE_LEDGER_PROJECTED_FROM_REAL_SHADOW_VALUE"
            if usable_shadow and thermo_ok
            else "GENCOIN_COGNITIVE_LEDGER_NOT_USABLE_PRECONDITIONS_FAILED"
        ),
        **_BOUNDARY,
    }

    return {
        "version": "GENCOIN_COGNITIVE_LEDGER_PACKET_V1",
        "status": "GENCOIN_COGNITIVE_LEDGER_READONLY_PASS",
        "source": "BRODY_F20B_GENCOIN_COGNITIVE_LEDGER",
        "mode": "READONLY_PROJECTED_LEDGER",
        "ledger_source": ledger.get("source", "LIVE_EMPTY_REGISTRY"),
        "ledger_status": ledger.get("status", "LIVE_EMPTY_REGISTRY"),
        "ledger_total": ledger.get("total", 0),
        "ledger_reason": ledger.get("reason", "NO_REAL_GENCOIN_LEDGER_ENTRY_YET"),
        "entries": [entry] if usable_shadow else [],
        "entry_count": 1 if usable_shadow else 0,
        "projected_only": True,
        "persisted": False,
        "notes": [
            "Cognitive ledger is projected from real Gencoin shadow scores.",
            "It is not a token ledger.",
            "No mint, wallet, blockchain, or economic scoring is enabled.",
            "KX108 remains the sole decision authority.",
        ],
        **_BOUNDARY,
    }
