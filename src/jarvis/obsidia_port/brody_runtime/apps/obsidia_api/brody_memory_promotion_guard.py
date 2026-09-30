from __future__ import annotations

from typing import Any


BOUNDARY = {
    "decision_authority": "KX108_ONLY",
    "advisory_only": True,
    "readonly": True,
    "context_signal_only": True,
    "emits_act": False,
    "emits_verdict": False,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "canon_promotion": False,
    "memory_promotion": False,
    "kernel_mutation": False,
    "x108_mutation": False,
}


def _clamp01(x: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(x))), 3)
    except Exception:
        return 0.0


def _get(d: Any, *path: str, default: Any = None) -> Any:
    cur = d if isinstance(d, dict) else {}
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


def _detect_write_intent(text: str) -> bool:
    low = (text or "").lower()
    keys = (
        "write memory",
        "ecris en memoire",
        "ecrit en memoire",
        "sauve en memoire",
        "save memory",
        "promote memory",
        "promotion memoire",
        "canonise",
        "canonize",
        "graphiti write",
        "neo4j write",
    )
    return any(k in low for k in keys)


def build_memory_promotion_guard_packet(
    *,
    request_text: str = "",
    sigma_packet: dict[str, Any] | None = None,
    anti_mismatch_packet: dict[str, Any] | None = None,
    thermodynamics_packet: dict[str, Any] | None = None,
    gencoin_shadow_packet: dict[str, Any] | None = None,
    tree_signal_packet: dict[str, Any] | None = None,
    memory_chain: dict[str, Any] | None = None,
    candidate_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sp = sigma_packet if isinstance(sigma_packet, dict) else {}
    amp = anti_mismatch_packet if isinstance(anti_mismatch_packet, dict) else {}
    tp = thermodynamics_packet if isinstance(thermodynamics_packet, dict) else {}
    gp = gencoin_shadow_packet if isinstance(gencoin_shadow_packet, dict) else {}
    tsp = tree_signal_packet if isinstance(tree_signal_packet, dict) else {}
    chain = memory_chain if isinstance(memory_chain, dict) else {}
    cand = candidate_memory if isinstance(candidate_memory, dict) else {}

    sigma_truth = _get(sp, "truth_score")
    sigma_usable = bool(_get(sp, "usable_for_gencoin", default=False))

    mismatch_score = _clamp01(_get(amp, "mismatch_score", default=0.0))
    mismatch_risk = str(_get(amp, "risk_level", default="NONE"))

    thermo_state = str(_get(tp, "stability_state", default="INSUFFICIENT_MATERIAL"))
    thermo_usable = bool(_get(tp, "usable_for_gencoin", default=False))

    shadow_usable = bool(_get(gp, "usable_shadow_value", default=False))
    cognitive_value = _get(gp, "shadow_scores", "cognitive_value")
    proof_value = _get(gp, "shadow_scores", "proof_value")
    memory_value = _get(gp, "shadow_scores", "memory_value")
    stability_value = _get(gp, "shadow_scores", "stability_value")

    tree_formal = bool(_get(tsp, "trees_formal_computation", default=False))
    tree_can_decide = bool(_get(tsp, "can_decide", default=False))
    tree_can_emit_act = bool(_get(tsp, "can_emit_act", default=False))

    material_quality = str(chain.get("material_quality") or cand.get("material_quality") or "UNKNOWN")
    write_intent_detected = _detect_write_intent(request_text)

    scores = []
    for x in (sigma_truth, cognitive_value, proof_value, memory_value, stability_value):
        if isinstance(x, (int, float)):
            scores.append(_clamp01(x))

    readiness_score = round(sum(scores) / len(scores), 3) if scores else None

    # Missing material alone is not a hard risk.
    # It means "not eligible". Hard risk is reserved for active danger:
    # write intent, high mismatch, unstable thermo, or authority violation.
    hard_risk = (
        write_intent_detected
        or mismatch_risk == "HIGH"
        or mismatch_score >= 0.60
        or thermo_state == "UNSTABLE"
        or tree_can_decide
        or tree_can_emit_act
    )

    eligible = bool(
        readiness_score is not None
        and readiness_score >= 0.60
        and sigma_usable
        and thermo_usable
        and shadow_usable
        and tree_formal
        and mismatch_score < 0.30
        and thermo_state in ("STABLE", "WARM")
        and not hard_risk
    )

    if hard_risk:
        guard_status = "PROMOTION_BLOCKED_RISK"
        reason = "RISK_OR_WRITE_INTENT_DETECTED"
    elif eligible:
        guard_status = "PROMOTION_CANDIDATE_HUMAN_REVIEW_ONLY"
        reason = "READONLY_CANDIDATE_READY_FOR_HUMAN_REVIEW"
    else:
        guard_status = "PROMOTION_NOT_ELIGIBLE"
        reason = "INSUFFICIENT_OR_UNCALIBRATED_SIGNALS"

    packet = {
        "version": "MEMORY_PROMOTION_GUARD_V1",
        "mode": "SHADOW_READONLY",
        "promotion_enabled": False,
        "write_allowed": False,
        "graphiti_write_allowed": False,
        "neo4j_write_allowed": False,
        "canon_promotion_allowed": False,
        "memory_promotion_allowed": False,
        "eligible_for_human_review": eligible,
        "guard_status": guard_status,
        "readiness_score": readiness_score,
        "risk": {
            "write_intent_detected": write_intent_detected,
            "hard_risk": hard_risk,
            "mismatch_score": mismatch_score,
            "mismatch_risk": mismatch_risk,
            "thermo_state": thermo_state,
            "tree_can_decide": tree_can_decide,
            "tree_can_emit_act": tree_can_emit_act,
        },
        "inputs": {
            "has_sigma_packet": bool(sp),
            "has_anti_mismatch_packet": bool(amp),
            "has_thermodynamics_packet": bool(tp),
            "has_gencoin_shadow_packet": bool(gp),
            "has_tree_signal_packet": bool(tsp),
            "has_memory_chain": bool(chain),
            "has_candidate_memory": bool(cand),
        },
        "evidence": {
            "sigma_truth_score": sigma_truth,
            "sigma_usable": sigma_usable,
            "thermo_usable": thermo_usable,
            "gencoin_shadow_usable": shadow_usable,
            "tree_formal_computation": tree_formal,
            "material_quality": material_quality,
            "cognitive_value": cognitive_value,
            "proof_value": proof_value,
            "memory_value": memory_value,
            "stability_value": stability_value,
        },
        "reason": reason,
        "notes": [
            "Memory Promotion Guard remains readonly.",
            "This guard does not write memory.",
            "This guard does not promote canon.",
            "Human review eligibility is not permission to write.",
        ],
        **BOUNDARY,
    }
    return {"memory_promotion_guard_packet": packet}
