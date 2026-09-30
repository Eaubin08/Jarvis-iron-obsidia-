"""Gencoin Shadow Value Layer — F4.

First shadow scoring layer consuming Sigma V1 + Anti-Mismatch V1 + Thermodynamics V1.
Scores are non-null but remain non-final, non-economic, non-blockchain, non-decisive.

Absolute boundary (enforced here, not decided here):
  decision_authority         = KX108_ONLY
  advisory_only              = true
  readonly                   = true
  emits_act                  = false
  emits_verdict              = false
  memory_write               = false
  kernel_mutation            = false
  x108_mutation              = false
  final_scoring_enabled      = false
  economic_scoring_enabled   = false
  blockchain_enabled         = false
  memory_promotion_enabled   = false

Gencoin Shadow Value does NOT decide. It does NOT emit ACT or verdict.
economic_projection remains null. KX108 decides.
"""
from __future__ import annotations

from typing import Any

_BOUNDARY: dict[str, Any] = {
    "decision_authority": "KX108_ONLY",
    "advisory_only": True,
    "readonly": True,
    "emits_act": False,
    "emits_verdict": False,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
}

_NULL_SCORES: dict[str, Any] = {
    "cognitive_value": None,
    "proof_value": None,
    "reuse_value": None,
    "memory_value": None,
    "attention_cost": None,
    "energy_cost": None,
    "stability_value": None,
    "economic_projection": None,
}


def _clamp(v: float) -> float:
    return round(max(0.0, min(1.0, v)), 3)


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


def build_gencoin_shadow_value_packet(
    *,
    sigma_packet: dict[str, Any] | None = None,
    anti_mismatch_packet: dict[str, Any] | None = None,
    thermodynamics_packet: dict[str, Any] | None = None,
    value_layer: dict[str, Any] | None = None,
    ir_candidate: dict[str, Any] | None = None,
    true_voice_snapshot: dict[str, Any] | None = None,
    memory_chain: dict[str, Any] | None = None,
    has_proof_readonly: bool = False,
) -> dict[str, Any]:
    """Build GENCOIN_SHADOW_VALUE_PACKET_V1 — bounded shadow scores, non-final.

    Phase F4.

    Precondition for usable_shadow_value=True (all must hold):
      - sigma_packet.usable_for_gencoin == True
      - thermodynamics_packet.usable_for_gencoin == True
      - anti_mismatch_packet.risk_level != HIGH
      - thermodynamics_packet.stability_state != INSUFFICIENT_MATERIAL

    Shadow scores (deterministic, bounded [0.0, 1.0], non-final):
      cognitive_value  = truth_score - mismatch_score*0.30 - entropy_score*0.20
      proof_value      = 0.70*proof_ok + truth_score*0.20 - mismatch_score*0.20
      stability_value  = 1.0 - instability_score
      attention_cost   : word-count band (<80→0.20, 80-350→0.40, 350-800→0.65, >800→0.90)
      energy_cost      = thermodynamics_packet.scores.dissipation_score (passthrough)
      memory_value     : quality band (USABLE→0.70, PARTIAL→0.45, LOW→0.20, absent→0.00)
                         + truth_score * 0.10
      reuse_value      = 0.40 + cognitive_value*0.30 + stability_value*0.20 - attention_cost*0.20
      economic_projection : always null

    Rules:
      - All scores are deterministic and bounded.
      - economic_projection is always null.
      - Gencoin Shadow does not decide.
      - Does not modify sigma_packet, anti_mismatch_packet, or thermodynamics_packet.
      - usable_shadow_value=True does NOT activate final scoring.
    """
    sp = sigma_packet if isinstance(sigma_packet, dict) else {}
    amp = anti_mismatch_packet if isinstance(anti_mismatch_packet, dict) else {}
    tp = thermodynamics_packet if isinstance(thermodynamics_packet, dict) else {}
    ir = ir_candidate if isinstance(ir_candidate, dict) else {}
    tvs = true_voice_snapshot if isinstance(true_voice_snapshot, dict) else {}
    chain = memory_chain if isinstance(memory_chain, dict) else {}

    # ── Input presence ───────────────────────────────────────────────────
    has_sigma = sp.get("version") == "SIGMA_CALIBRATION_PACKET_V1"
    has_amp = amp.get("version") == "ANTI_MISMATCH_SIGNAL_V1"
    has_thermo = tp.get("version") == "THERMODYNAMICS_PACKET_V1"
    has_vl = isinstance(value_layer, dict) and bool(value_layer)
    has_ir = bool(ir.get("intent_type") or ir.get("entities") is not None)
    final_answer = str(tvs.get("final_answer") or "")
    has_reverse = bool(final_answer and len(final_answer) > 10)
    has_memory = chain.get("material_quality") in ("USABLE_MATERIAL", "PARTIAL_MATERIAL") or \
        chain.get("status") in ("BRODY_MEMORY_RESPONSE_CHAIN_PASS", "LOCAL_INDEX_FALLBACK_PARTIAL")

    # ── Evidence extraction ──────────────────────────────────────────────
    sigma_truth_score = sp.get("truth_score")
    sigma_usable_for_gencoin: bool = bool(sp.get("usable_for_gencoin"))

    mismatch_score_raw = amp.get("mismatch_score")
    anti_mismatch_risk_level: str | None = amp.get("risk_level")

    thermo_scores = tp.get("scores", {}) if isinstance(tp.get("scores"), dict) else {}
    thermo_usable_for_gencoin: bool = bool(tp.get("usable_for_gencoin"))
    thermo_stability_state: str | None = tp.get("stability_state")
    entropy_score_raw = thermo_scores.get("entropy_score")
    dissipation_score_raw = thermo_scores.get("dissipation_score")
    instability_score_raw = thermo_scores.get("instability_score")

    memory_material_quality: str | None = chain.get("material_quality")
    answer_words = _word_count(final_answer)

    # ── Usable precondition check ────────────────────────────────────────
    reason_parts: list[str] = []
    if not sigma_usable_for_gencoin:
        reason_parts.append("SIGMA_NOT_USABLE_FOR_GENCOIN")
    if not thermo_usable_for_gencoin:
        reason_parts.append("THERMO_NOT_USABLE_FOR_GENCOIN")
    if anti_mismatch_risk_level == "HIGH":
        reason_parts.append("ANTI_MISMATCH_RISK_HIGH")
    if thermo_stability_state == "INSUFFICIENT_MATERIAL":
        reason_parts.append("THERMO_STABILITY_INSUFFICIENT_MATERIAL")

    usable_shadow_value = (
        sigma_usable_for_gencoin
        and thermo_usable_for_gencoin
        and anti_mismatch_risk_level != "HIGH"
        and thermo_stability_state != "INSUFFICIENT_MATERIAL"
    )

    reason = (
        "GENCOIN_SHADOW_NOT_USABLE_" + "_AND_".join(reason_parts)
        if reason_parts
        else "GENCOIN_SHADOW_USABLE_ALL_PRECONDITIONS_MET"
    )

    inputs = {
        "has_sigma_packet": has_sigma,
        "has_anti_mismatch_packet": has_amp,
        "has_thermodynamics_packet": has_thermo,
        "has_value_layer": has_vl,
        "has_ir_candidate": has_ir,
        "has_reverse_output": has_reverse,
        "has_memory_chain": has_memory,
        "has_proof_readonly": has_proof_readonly,
    }

    evidence = {
        "sigma_truth_score": sigma_truth_score,
        "sigma_usable_for_gencoin": sigma_usable_for_gencoin,
        "mismatch_score": mismatch_score_raw,
        "anti_mismatch_risk_level": anti_mismatch_risk_level,
        "thermo_usable_for_gencoin": thermo_usable_for_gencoin,
        "entropy_score": entropy_score_raw,
        "dissipation_score": dissipation_score_raw,
        "stability_state": thermo_stability_state,
        "memory_material_quality": memory_material_quality,
        "answer_length_words": answer_words,
    }

    if not usable_shadow_value:
        return {
            "gencoin_shadow_packet": {
                "version": "GENCOIN_SHADOW_VALUE_PACKET_V1",
                "mode": "SHADOW_READONLY",
                "final_scoring_enabled": False,
                "economic_scoring_enabled": False,
                "blockchain_enabled": False,
                "memory_promotion_enabled": False,
                "usable_shadow_value": False,
                "shadow_scores": dict(_NULL_SCORES),
                "inputs": inputs,
                "evidence": evidence,
                "reason": reason,
                "notes": [
                    "Gencoin shadow value remains advisory-only.",
                    "Gencoin shadow value does not decide.",
                    "Gencoin shadow value does not emit ACT or verdict.",
                    "Gencoin final scoring remains disabled.",
                    "Economic projection remains null.",
                    "Blockchain remains deferred.",
                ],
                **_BOUNDARY,
            }
        }

    # ── Shadow score computation ─────────────────────────────────────────
    ts: float = float(sigma_truth_score) if isinstance(sigma_truth_score, (int, float)) else 0.50
    ms: float = float(mismatch_score_raw) if isinstance(mismatch_score_raw, (int, float)) else 0.0
    es: float = float(entropy_score_raw) if isinstance(entropy_score_raw, (int, float)) else 0.50
    ds: float = float(dissipation_score_raw) if isinstance(dissipation_score_raw, (int, float)) else 0.50
    ins: float = float(instability_score_raw) if isinstance(instability_score_raw, (int, float)) else 0.50

    # 1. cognitive_value
    cognitive_value = _clamp(ts - ms * 0.30 - es * 0.20)

    # 2. stability_value
    stability_value = _clamp(1.0 - ins)

    # 3. attention_cost (word-count band)
    if answer_words > 800:
        attention_cost = 0.90
    elif answer_words > 350:
        attention_cost = 0.65
    elif answer_words >= 80:
        attention_cost = 0.40
    else:
        attention_cost = 0.20

    # 4. proof_value
    proof_base = 0.70 if has_proof_readonly else 0.0
    proof_value = _clamp(proof_base + ts * 0.20 - ms * 0.20)

    # 5. energy_cost — passthrough from thermodynamics dissipation
    energy_cost: float | None = (
        round(ds, 3) if isinstance(dissipation_score_raw, (int, float)) else None
    )

    # 6. memory_value
    if memory_material_quality == "USABLE_MATERIAL":
        mem_base = 0.70
    elif memory_material_quality == "PARTIAL_MATERIAL":
        mem_base = 0.45
    elif memory_material_quality == "LOW_MATERIAL":
        mem_base = 0.20
    else:
        mem_base = 0.00
    memory_value = _clamp(mem_base + ts * 0.10)

    # 7. reuse_value (depends on cognitive, stability, attention)
    reuse_value = _clamp(
        0.40
        + cognitive_value * 0.30
        + stability_value * 0.20
        - attention_cost * 0.20
    )

    shadow_scores: dict[str, Any] = {
        "cognitive_value": cognitive_value,
        "proof_value": proof_value,
        "reuse_value": reuse_value,
        "memory_value": memory_value,
        "attention_cost": round(attention_cost, 3),
        "energy_cost": energy_cost,
        "stability_value": stability_value,
        "economic_projection": None,
    }

    return {
        "gencoin_shadow_packet": {
            "version": "GENCOIN_SHADOW_VALUE_PACKET_V1",
            "mode": "SHADOW_READONLY",
            "final_scoring_enabled": False,
            "economic_scoring_enabled": False,
            "blockchain_enabled": False,
            "memory_promotion_enabled": False,
            "usable_shadow_value": True,
            "shadow_scores": shadow_scores,
            "inputs": inputs,
            "evidence": evidence,
            "reason": reason,
            "notes": [
                "Gencoin shadow value remains advisory-only.",
                "Gencoin shadow value does not decide.",
                "Gencoin shadow value does not emit ACT or verdict.",
                "Gencoin final scoring remains disabled.",
                "Economic projection remains null.",
                "Blockchain remains deferred.",
            ],
            **_BOUNDARY,
        }
    }
