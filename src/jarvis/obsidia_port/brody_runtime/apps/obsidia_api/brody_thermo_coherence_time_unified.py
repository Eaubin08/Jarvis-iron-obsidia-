"""F19B — Unified Thermo / Coherence / Time readonly packet.

Unifies existing signals:
- Brody thermodynamics_packet
- periphery.energy_thermo metrics
- x108 replay coherence style metrics
- temporal/time context if present

Non-sovereign:
- does not decide
- does not block
- does not emit ACT
- does not write memory
- does not mutate kernel/X108
"""
from __future__ import annotations

from typing import Any

from periphery.common import ActionCandidate
from periphery.energy_thermo import run_energy_thermo


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
}


def _clamp(v: Any) -> float:
    try:
        f = float(v)
    except Exception:
        return 0.0
    return round(max(0.0, min(1.0, f)), 4)


def _mean(values: list[float]) -> float:
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    if not vals:
        return 0.0
    return _clamp(sum(vals) / len(vals))


def _packet_to_dict(packet: Any) -> dict[str, Any]:
    if hasattr(packet, "to_dict"):
        return packet.to_dict()
    if isinstance(packet, dict):
        return packet
    if hasattr(packet, "__dict__"):
        return dict(packet.__dict__)
    return {"raw": str(packet)}


def build_energy_probe(
    *,
    thermodynamics_packet: dict[str, Any] | None = None,
    sigma_packet: dict[str, Any] | None = None,
    anti_mismatch_packet: dict[str, Any] | None = None,
    intent: str = "readonly_probe",
) -> dict[str, Any]:
    thermo = thermodynamics_packet if isinstance(thermodynamics_packet, dict) else {}
    sigma = sigma_packet if isinstance(sigma_packet, dict) else {}
    anti = anti_mismatch_packet if isinstance(anti_mismatch_packet, dict) else {}

    scores = thermo.get("scores", {}) if isinstance(thermo.get("scores"), dict) else {}

    payload = {
        "pin": 1.0,
        "pout": max(0.001, 1.0 - _clamp(scores.get("dissipation_score", 0.0))),
        "energy_cost": _clamp(scores.get("dissipation_score", 0.0)),
        "compute_cost": _clamp(scores.get("projection_cost", 0.0)),
        "attention_cost": _clamp(scores.get("pressure_load", 0.0)),
        "recovery_cost": _clamp(scores.get("memory_friction", 0.0)),
        "useful_work": max(0.0, 1.0 - _clamp(scores.get("coherence_temperature", 0.0))),
        "truth_score": _clamp(sigma.get("truth_score", 1.0)),
        "sigma_score": _clamp(sigma.get("sigma_score", sigma.get("truth_score", 1.0))),
        "collapse_disguised_high_sigma": False,
    }

    candidate = ActionCandidate(
        action_id="F19B_THERMO_UNIFIED_READONLY",
        domain="THERMO_COHERENCE_TIME",
        actor_id="BRODY",
        intent=intent,
        action_type="READONLY_SCORING",
        irreversible=False,
        timestamp_plan="",
        payload=payload,
    )

    packet = run_energy_thermo(candidate)
    if hasattr(packet, "assert_non_sovereign"):
        packet.assert_non_sovereign()

    d = _packet_to_dict(packet)
    d["source"] = "periphery.energy_thermo.run_energy_thermo"
    d["input_payload"] = payload
    d.update(_BOUNDARY)
    return d


def build_replay_coherence_shadow(
    *,
    payload: dict[str, Any],
    memory_response_chain_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    chain = memory_response_chain_snapshot if isinstance(memory_response_chain_snapshot, dict) else {}

    boundary_ok = all([
        payload.get("readonly") is True,
        payload.get("emits_act") is False,
        payload.get("memory_write") is False,
        payload.get("graphiti_write") is False,
        payload.get("kernel_mutation") is False,
        payload.get("x108_mutation") is False,
        payload.get("decision_authority") == "KX108_ONLY",
    ])

    source_hit = chain.get("selected_items_count", 0) or chain.get("graphiti_http_results_count", 0) or 0
    try:
        source_hit = int(source_hit)
    except Exception:
        source_hit = 0

    ledger_ok = payload.get("audit_event") is not None

    boundary_ratio = 1.0 if boundary_ok else 0.0
    source_ratio = 1.0 if source_hit > 0 else 0.0
    ledger_ratio = 1.0 if ledger_ok else 0.0

    coherence_score = round(0.5 * boundary_ratio + 0.3 * source_ratio + 0.2 * ledger_ratio, 4)

    return {
        "status": "COHERENCE_SHADOW_COMPUTED_READONLY",
        "source": "BRODY_F19B_REPLAY_COHERENCE_SHADOW",
        "coherence_score": coherence_score,
        "record_count": 1,
        "boundary_ok_count": 1 if boundary_ok else 0,
        "source_hit_count": source_hit,
        "ledger_ok_count": 1 if ledger_ok else 0,
        "boundary_ratio": boundary_ratio,
        "source_ratio": source_ratio,
        "ledger_ratio": ledger_ratio,
        **_BOUNDARY,
    }


def build_time_shadow(
    *,
    temporal_context_snapshot: dict[str, Any] | None = None,
    thermodynamics_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    temporal = temporal_context_snapshot if isinstance(temporal_context_snapshot, dict) else {}
    thermo = thermodynamics_packet if isinstance(thermodynamics_packet, dict) else {}
    scores = thermo.get("scores", {}) if isinstance(thermo.get("scores"), dict) else {}

    has_temporal = bool(temporal)
    pressure = _clamp(scores.get("pressure_load", 0.0))
    coherence_temp = _clamp(scores.get("coherence_temperature", 0.0))

    time_pressure = pressure if not has_temporal else _mean([pressure, coherence_temp])

    return {
        "status": "TIME_SHADOW_READONLY_PASS" if has_temporal else "TIME_SHADOW_NO_TEMPORAL_CONTEXT",
        "source": "BRODY_F19B_TIME_SHADOW",
        "temporal_context_present": has_temporal,
        "time_pressure": time_pressure,
        "coherence_temperature_input": coherence_temp,
        "pressure_load_input": pressure,
        "notes": [
            "Time shadow is advisory only.",
            "No temporal ACT is emitted.",
            "X108 remains sole decision authority.",
        ],
        **_BOUNDARY,
    }


def build_unified_thermo_coherence_time_packet(
    *,
    payload: dict[str, Any],
) -> dict[str, Any]:
    thermo = payload.get("thermodynamics_packet") or {}
    sigma = payload.get("sigma_packet") or {}
    anti = payload.get("anti_mismatch_packet") or payload.get("anti_mismatch_snapshot") or {}
    chain = payload.get("memory_response_chain_snapshot") or {}
    temporal = payload.get("temporal_context_snapshot") or payload.get("temporal_context") or {}

    energy_probe = build_energy_probe(
        thermodynamics_packet=thermo,
        sigma_packet=sigma,
        anti_mismatch_packet=anti,
        intent=str(payload.get("action_risk") or "readonly_probe"),
    )

    coherence_shadow = build_replay_coherence_shadow(
        payload=payload,
        memory_response_chain_snapshot=chain,
    )

    time_shadow = build_time_shadow(
        temporal_context_snapshot=temporal,
        thermodynamics_packet=thermo,
    )

    thermo_scores = thermo.get("scores", {}) if isinstance(thermo.get("scores"), dict) else {}
    energy_metrics = energy_probe.get("extra_metrics", {}) if isinstance(energy_probe.get("extra_metrics"), dict) else {}

    unified_scores = {
        "thermo_coherence_temperature": _clamp(thermo_scores.get("coherence_temperature", 0.0)),
        "thermo_dissipation_score": _clamp(thermo_scores.get("dissipation_score", 0.0)),
        "thermo_instability_score": _clamp(thermo_scores.get("instability_score", 0.0)),
        "energy_efficiency": _clamp(energy_metrics.get("energy_efficiency", 0.0)),
        "thermo_debt": _clamp(energy_metrics.get("thermo_debt", 0.0)),
        "sigma_truth_mismatch": _clamp(energy_metrics.get("sigma_truth_mismatch", 0.0)),
        "replay_coherence_score": _clamp(coherence_shadow.get("coherence_score", 0.0)),
        "time_pressure": _clamp(time_shadow.get("time_pressure", 0.0)),
    }

    composite_temperature = _mean([
        unified_scores["thermo_coherence_temperature"],
        1.0 - unified_scores["energy_efficiency"],
        unified_scores["sigma_truth_mismatch"],
        1.0 - unified_scores["replay_coherence_score"],
        unified_scores["time_pressure"],
    ])

    hard_risks = []
    soft_risks = []

    for risk in energy_probe.get("risk_flags", []) or []:
        soft_risks.append(str(risk))

    if thermo.get("stability_state") in {"HOT", "UNSTABLE"}:
        hard_risks.append(f"THERMO_{thermo.get('stability_state')}")
    if energy_probe.get("recommended_gate") == "BLOCK_CANDIDATE":
        hard_risks.append("ENERGY_THERMO_BLOCK_CANDIDATE")
    if composite_temperature >= 0.70:
        hard_risks.append("COMPOSITE_THERMO_UNSTABLE")
    elif composite_temperature >= 0.50:
        soft_risks.append("COMPOSITE_THERMO_HOT")

    stability_state = (
        "UNSTABLE" if composite_temperature >= 0.70
        else "HOT" if composite_temperature >= 0.50
        else "WARM" if composite_temperature >= 0.30
        else "STABLE"
    )

    usable_for_value_layer = (
        bool(thermo.get("usable_for_value_layer"))
        and not hard_risks
        and coherence_shadow.get("coherence_score", 0.0) >= 0.5
    )

    usable_for_gencoin = (
        bool(thermo.get("usable_for_gencoin"))
        and usable_for_value_layer
        and energy_probe.get("recommended_gate") != "BLOCK_CANDIDATE"
    )

    return {
        "version": "THERMO_COHERENCE_TIME_UNIFIED_PACKET_V1",
        "status": "THERMO_COHERENCE_TIME_UNIFIED_READONLY_PASS",
        "source": "BRODY_F19B_UNIFIED_THERMO_COHERENCE_TIME",
        "inputs": {
            "has_thermodynamics_packet": bool(thermo),
            "has_sigma_packet": bool(sigma),
            "has_anti_mismatch_packet": bool(anti),
            "has_memory_chain": bool(chain),
            "has_temporal_context": bool(temporal),
            "energy_thermo_source": energy_probe.get("source"),
            "coherence_source": coherence_shadow.get("source"),
            "time_source": time_shadow.get("source"),
        },
        "scores": unified_scores,
        "composite_temperature": composite_temperature,
        "stability_state": stability_state,
        "hard_risks": sorted(set(hard_risks)),
        "soft_risks": sorted(set(soft_risks)),
        "usable_for_value_layer": usable_for_value_layer,
        "usable_for_gencoin": usable_for_gencoin,
        "energy_thermo_packet": energy_probe,
        "coherence_shadow_packet": coherence_shadow,
        "time_shadow_packet": time_shadow,
        "notes": [
            "Unified packet reuses existing thermo packet, energy_thermo, replay coherence semantics, and time shadow.",
            "It is advisory-only and does not decide.",
            "KX108 remains sole decision authority.",
        ],
        **_BOUNDARY,
    }
