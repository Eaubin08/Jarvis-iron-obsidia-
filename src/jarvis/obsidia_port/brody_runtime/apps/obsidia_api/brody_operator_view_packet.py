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


def _get(d: Any, *path: str, default: Any = None) -> Any:
    cur = d if isinstance(d, dict) else {}
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


def _bool(x: Any) -> bool:
    return bool(x) if x is not None else False


def _status_label(ok: bool, warn: bool = False) -> str:
    if warn:
        return "WARN"
    return "OK" if ok else "NOT_READY"


def build_operator_view_packet(
    *,
    value_layer: dict[str, Any] | None = None,
    sigma_packet: dict[str, Any] | None = None,
    domain_sigma_envelope: dict[str, Any] | None = None,
    anti_mismatch_packet: dict[str, Any] | None = None,
    thermodynamics_packet: dict[str, Any] | None = None,
    gencoin_shadow_packet: dict[str, Any] | None = None,
    tree_signal_packet: dict[str, Any] | None = None,
    memory_promotion_guard_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    vl = value_layer if isinstance(value_layer, dict) else {}
    sp = sigma_packet if isinstance(sigma_packet, dict) else {}
    dse = domain_sigma_envelope if isinstance(domain_sigma_envelope, dict) else {}
    amp = anti_mismatch_packet if isinstance(anti_mismatch_packet, dict) else {}
    tp = thermodynamics_packet if isinstance(thermodynamics_packet, dict) else {}
    gp = gencoin_shadow_packet if isinstance(gencoin_shadow_packet, dict) else {}
    tsp = tree_signal_packet if isinstance(tree_signal_packet, dict) else {}
    mgp = memory_promotion_guard_packet if isinstance(memory_promotion_guard_packet, dict) else {}

    sigma_ready = sp.get("version") == "SIGMA_CALIBRATION_PACKET_V1"
    domain_sigma_ready = bool(dse) and (
        dse.get("domain_sigma_envelope") is True
        or dse.get("mode") == "READONLY_DOMAIN_SIGMA_ENVELOPE"
        or "x108_gate" in dse
    )
    anti_mismatch_ready = amp.get("version") == "ANTI_MISMATCH_SIGNAL_V1"
    thermo_ready = tp.get("version") == "THERMODYNAMICS_PACKET_V1"
    gencoin_shadow_ready = gp.get("version") == "GENCOIN_SHADOW_VALUE_PACKET_V1"
    tree_ready = tsp.get("version") == "TREE_SIGNAL_PACKET_V1"
    memory_guard_ready = mgp.get("version") == "MEMORY_PROMOTION_GUARD_V1"
    value_layer_ready = bool(vl)

    mismatch_score = _get(amp, "mismatch_score", default=0.0)
    mismatch_risk = str(_get(amp, "risk_level", default="UNKNOWN"))

    stability_state = str(_get(tp, "stability_state", default="UNKNOWN"))
    guard_status = str(_get(mgp, "guard_status", default="UNKNOWN"))

    final_scoring_enabled = _bool(_get(vl, "final_scoring_enabled", default=False))
    value_scores = _get(vl, "scores", default={})
    value_scores_null = (
        isinstance(value_scores, dict)
        and all(v is None for v in value_scores.values())
    )

    write_allowed = any([
        _bool(_get(mgp, "write_allowed", default=False)),
        _bool(_get(mgp, "graphiti_write_allowed", default=False)),
        _bool(_get(mgp, "neo4j_write_allowed", default=False)),
        _bool(_get(mgp, "canon_promotion_allowed", default=False)),
        _bool(_get(mgp, "memory_promotion_allowed", default=False)),
    ])

    hard_risks = []
    if mismatch_risk == "HIGH":
        hard_risks.append("ANTI_MISMATCH_HIGH")
    if stability_state in ("HOT", "UNSTABLE", "INSUFFICIENT_MATERIAL"):
        hard_risks.append(f"THERMO_{stability_state}")
    if guard_status == "PROMOTION_BLOCKED_RISK":
        hard_risks.append("MEMORY_PROMOTION_BLOCKED_RISK")
    if final_scoring_enabled:
        hard_risks.append("FINAL_SCORING_ENABLED_UNEXPECTED")
    if not value_scores_null:
        hard_risks.append("VALUE_LAYER_SCORES_NOT_NULL")
    if write_allowed:
        hard_risks.append("WRITE_PERMISSION_UNEXPECTED")

    missing = []
    for name, ready in (
        ("value_layer", value_layer_ready),
        ("sigma_packet", sigma_ready),
        ("domain_sigma_envelope", domain_sigma_ready),
        ("anti_mismatch_packet", anti_mismatch_ready),
        ("thermodynamics_packet", thermo_ready),
        ("gencoin_shadow_packet", gencoin_shadow_ready),
        ("tree_signal_packet", tree_ready),
        ("memory_promotion_guard_packet", memory_guard_ready),
    ):
        if not ready:
            missing.append(name)

    all_core_ready = not missing
    safe_boundary_ok = (
        not final_scoring_enabled
        and value_scores_null
        and not write_allowed
    )

    if hard_risks:
        system_status = "ATTENTION_REQUIRED"
        next_safe_action = "INSPECT_RISKS_READONLY"
    elif all_core_ready and safe_boundary_ok:
        system_status = "OPERATOR_READY_READONLY"
        next_safe_action = "DISPLAY_TRANSVERSE_STACK"
    else:
        system_status = "PARTIAL_READONLY"
        next_safe_action = "COMPLETE_MISSING_PACKETS_READONLY"

    packet = {
        "version": "OPERATOR_VIEW_PACKET_V1",
        "mode": "SHADOW_READONLY",
        "system_status": system_status,
        "next_safe_action": next_safe_action,
        "readiness": {
            "value_layer": _status_label(value_layer_ready),
            "sigma": _status_label(sigma_ready),
            "domain_sigma": _status_label(domain_sigma_ready),
            "anti_mismatch": _status_label(anti_mismatch_ready, mismatch_risk == "HIGH"),
            "thermodynamics": _status_label(thermo_ready, stability_state in ("HOT", "UNSTABLE", "INSUFFICIENT_MATERIAL")),
            "gencoin_shadow": _status_label(gencoin_shadow_ready),
            "tree_signal": _status_label(tree_ready),
            "memory_guard": _status_label(memory_guard_ready, guard_status == "PROMOTION_BLOCKED_RISK"),
        },
        "usable": {
            "sigma_for_gencoin": _bool(_get(sp, "usable_for_gencoin", default=False)),
            "thermo_for_gencoin": _bool(_get(tp, "usable_for_gencoin", default=False)),
            "gencoin_shadow_value": _bool(_get(gp, "usable_shadow_value", default=False)),
            "tree_signal_for_shadow": _bool(_get(tsp, "usable_for_gencoin_shadow", default=False)),
            "memory_candidate_human_review": _bool(_get(mgp, "eligible_for_human_review", default=False)),
        },
        "blocked": {
            "final_scoring_enabled": final_scoring_enabled,
            "value_layer_scores_not_null": not value_scores_null,
            "write_allowed": write_allowed,
            "hard_risks": hard_risks,
            "missing_packets": missing,
        },
        "domain_sigma_envelope": dse,
        "domain_sigma_attached": domain_sigma_ready,
        "evidence": {
            "sigma_truth_score": _get(sp, "truth_score"),
            "domain_sigma_domain": _get(dse, "domain"),
            "domain_sigma_gate": _get(dse, "x108_gate"),
            "domain_sigma_authority": _get(dse, "decision_authority"),
            "domain_sigma_emits_act": _get(dse, "emits_act"),
            "mismatch_score": mismatch_score,
            "mismatch_risk": mismatch_risk,
            "stability_state": stability_state,
            "gencoin_shadow_usable": _get(gp, "usable_shadow_value"),
            "tree_formal_computation": _get(tsp, "trees_formal_computation"),
            "memory_guard_status": guard_status,
            "memory_readiness_score": _get(mgp, "readiness_score"),
            "value_layer_final_scoring_enabled": final_scoring_enabled,
            "value_layer_scores_null": value_scores_null,
        },
        "summary": {
            "all_core_packets_ready": all_core_ready,
            "safe_boundary_ok": safe_boundary_ok,
            "operator_can_view": True,
            "operator_can_write": False,
            "operator_can_decide": False,
            "domain_sigma_ready": domain_sigma_ready,
        },
        "notes": [
            "Operator view is readonly.",
            "Operator view does not decide.",
            "Operator view does not emit ACT or verdict.",
            "Operator view aggregates packets for inspection only.",
        ],
        **BOUNDARY,
    }

    return {"operator_view_packet": packet}
