"""Thermodynamics Signal — F3.

Formal readonly layer measuring dissipation, entropy and stability from
Sigma V1 + Anti-Mismatch V1 + IR Candidate + Reverse OS output.

Absolute boundary (enforced here, not decided here):
  decision_authority = KX108_ONLY
  advisory_only      = true
  readonly           = true
  emits_act          = false
  emits_verdict      = false
  memory_write       = false
  kernel_mutation    = false
  x108_mutation      = false

Thermodynamics does NOT decide. Thermodynamics does NOT block.
Thermodynamics does NOT emit ACT or verdict.
Thermodynamics only measures dissipation and stability for downstream
readonly observers. KX108 decides.
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

_PRESSURE_MAP = {"LOW": 0.20, "MEDIUM": 0.50, "HIGH": 0.80}
_STABILITY_INSUFFICIENT = "INSUFFICIENT_MATERIAL"
_STABILITY_STABLE = "STABLE"
_STABILITY_WARM = "WARM"
_STABILITY_HOT = "HOT"
_STABILITY_UNSTABLE = "UNSTABLE"


def _clamp(v: float) -> float:
    return round(max(0.0, min(1.0, v)), 3)


def _mean(*values: float) -> float:
    if not values:
        return 0.0
    return _clamp(sum(values) / len(values))


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


def build_thermodynamics_packet(
    *,
    sigma_packet: dict[str, Any] | None = None,
    anti_mismatch_packet: dict[str, Any] | None = None,
    ir_candidate: dict[str, Any] | None = None,
    true_voice_snapshot: dict[str, Any] | None = None,
    adaptive_response_policy: dict[str, Any] | None = None,
    memory_chain: dict[str, Any] | None = None,
    value_layer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build THERMODYNAMICS_PACKET_V1 — bounded deterministic dissipation metrics.

    Phase F3.

    Scores (all deterministic, bounded [0.0, 1.0]):
      entropy_score         : 1 - truth_score (inverted sigma quality)
      mismatch_heat         : anti_mismatch_packet.mismatch_score passthrough
      boundary_heat         : boundary_compact / boundary_detected pressure
      memory_friction       : friction from missing or partial memory material
      projection_cost       : cost from answer length extremes
      pressure_load         : converted from sigma_pressure (LOW/MEDIUM/HIGH)
      dissipation_score     : mean of above six
      instability_score     : max of mismatch_heat, boundary_heat, entropy_score
      coherence_temperature : mean of dissipation_score, instability_score, pressure_load

    stability_state:
      INSUFFICIENT_MATERIAL — sigma absent or truth_score null
      STABLE                — coherence_temperature < 0.30
      WARM                  — 0.30 <= coherence_temperature < 0.50
      HOT                   — 0.50 <= coherence_temperature < 0.70
      UNSTABLE              — coherence_temperature >= 0.70

    Rules:
      - All scores are deterministic and bounded.
      - Thermodynamics is not a decision-maker.
      - usable_for_gencoin=True only if sigma usable + mismatch not HIGH + material present.
      - usable_for_gencoin=True does NOT activate Gencoin final scoring.
      - Does not modify sigma_packet, anti_mismatch_packet, or value_layer scores.
    """
    sp = sigma_packet if isinstance(sigma_packet, dict) else {}
    amp = anti_mismatch_packet if isinstance(anti_mismatch_packet, dict) else {}
    ir = ir_candidate if isinstance(ir_candidate, dict) else {}
    tvs = true_voice_snapshot if isinstance(true_voice_snapshot, dict) else {}
    pol = adaptive_response_policy if isinstance(adaptive_response_policy, dict) else {}
    chain = memory_chain if isinstance(memory_chain, dict) else {}

    # ── Input presence flags ─────────────────────────────────────────────
    has_sigma = bool(sp.get("version") == "SIGMA_CALIBRATION_PACKET_V1")
    has_amp = bool(amp.get("version") == "ANTI_MISMATCH_SIGNAL_V1")
    has_ir = bool(ir.get("intent_type") or ir.get("entities") is not None)
    final_answer = str(tvs.get("final_answer") or "")
    has_reverse = bool(final_answer and len(final_answer) > 10)
    has_pol = bool(pol)
    has_memory = chain.get("material_quality") in ("USABLE_MATERIAL", "PARTIAL_MATERIAL") or \
        chain.get("status") in ("BRODY_MEMORY_RESPONSE_CHAIN_PASS", "LOCAL_INDEX_FALLBACK_PARTIAL")
    has_vl = isinstance(value_layer, dict) and bool(value_layer)

    # ── Evidence extraction ──────────────────────────────────────────────
    truth_score = sp.get("truth_score")  # float | None
    has_truth = isinstance(truth_score, (int, float))
    ts_val: float = float(truth_score) if has_truth else 0.0

    sigma_calibration_status: str | None = sp.get("calibration_status")
    sigma_usable_for_thermo: bool = bool(sp.get("usable_for_thermodynamics"))

    mismatch_score_raw = amp.get("mismatch_score")
    has_mismatch = isinstance(mismatch_score_raw, (int, float))
    mismatch_val: float = float(mismatch_score_raw) if has_mismatch else 0.0
    anti_mismatch_risk_level: str | None = amp.get("risk_level")

    response_size: str | None = pol.get("response_size")
    boundary_detected: bool = bool(pol.get("boundary_detected")) or response_size == "BOUNDARY_COMPACT"
    sigma_pressure: str | None = sp.get("sigma_pressure") or pol.get("sigma_pressure")

    answer_words = _word_count(final_answer)
    memory_material_quality: str | None = chain.get("material_quality")

    # ── Insufficient material check ──────────────────────────────────────
    # Cannot compute meaningful thermo if sigma absent or truth_score null.
    insufficient = not has_sigma or not has_truth

    # ── Score 1: entropy_score ───────────────────────────────────────────
    if has_truth:
        entropy_score = _clamp(1.0 - ts_val)
    elif has_ir or has_pol:
        entropy_score = 0.50  # partial material
    else:
        entropy_score = 1.0   # insufficient material

    # ── Score 2: mismatch_heat ───────────────────────────────────────────
    mismatch_heat = _clamp(mismatch_val)

    # ── Score 3: boundary_heat ───────────────────────────────────────────
    raw_boundary = 0.0
    if boundary_detected:
        raw_boundary += 0.40
    if response_size == "BOUNDARY_COMPACT" and not boundary_detected:
        raw_boundary += 0.30
    boundary_heat = _clamp(raw_boundary)

    # ── Score 4: memory_friction ─────────────────────────────────────────
    if memory_material_quality == "USABLE_MATERIAL":
        memory_friction = 0.0
    elif memory_material_quality == "PARTIAL_MATERIAL":
        memory_friction = 0.25
    else:
        memory_friction = 0.50

    # ── Score 5: projection_cost ─────────────────────────────────────────
    if answer_words > 800:
        projection_cost = 0.50
    elif answer_words > 350:
        projection_cost = 0.30
    elif answer_words < 80:
        projection_cost = 0.10
    else:
        projection_cost = 0.0

    # ── Score 6: pressure_load ───────────────────────────────────────────
    pressure_load = _PRESSURE_MAP.get(str(sigma_pressure), 0.30)

    # ── Score 7: dissipation_score ───────────────────────────────────────
    dissipation_score = _mean(
        entropy_score,
        mismatch_heat,
        boundary_heat,
        memory_friction,
        projection_cost,
        pressure_load,
    )

    # ── Score 8: instability_score ───────────────────────────────────────
    instability_score = _clamp(max(mismatch_heat, boundary_heat, entropy_score))

    # ── Score 9: coherence_temperature ───────────────────────────────────
    coherence_temperature = _mean(dissipation_score, instability_score, pressure_load)

    # ── Stability state ──────────────────────────────────────────────────
    if insufficient:
        stability_state = _STABILITY_INSUFFICIENT
    elif coherence_temperature < 0.30:
        stability_state = _STABILITY_STABLE
    elif coherence_temperature < 0.50:
        stability_state = _STABILITY_WARM
    elif coherence_temperature < 0.70:
        stability_state = _STABILITY_HOT
    else:
        stability_state = _STABILITY_UNSTABLE

    # ── usable_for_gencoin ───────────────────────────────────────────────
    usable_for_gencoin = (
        has_sigma
        and sigma_usable_for_thermo
        and anti_mismatch_risk_level != "HIGH"
        and stability_state != _STABILITY_INSUFFICIENT
    )

    usable_for_value_layer = (
        has_sigma
        and has_truth
        and stability_state != _STABILITY_INSUFFICIENT
    )

    reason = (
        "THERMO_INSUFFICIENT_SIGMA_ABSENT" if not has_sigma
        else "THERMO_INSUFFICIENT_TRUTH_SCORE_NULL" if not has_truth
        else f"THERMO_F3_{stability_state}"
    )

    return {
        "thermodynamics_packet": {
            "version": "THERMODYNAMICS_PACKET_V1",
            "mode": "SHADOW_READONLY",
            "thermodynamics_active": True,
            "usable_for_gencoin": usable_for_gencoin,
            "usable_for_value_layer": usable_for_value_layer,
            "scores": {
                "entropy_score": entropy_score,
                "dissipation_score": dissipation_score,
                "instability_score": instability_score,
                "coherence_temperature": coherence_temperature,
                "pressure_load": pressure_load,
                "mismatch_heat": mismatch_heat,
                "boundary_heat": boundary_heat,
                "memory_friction": memory_friction,
                "projection_cost": projection_cost,
            },
            "stability_state": stability_state,
            "inputs": {
                "has_sigma_packet": has_sigma,
                "has_anti_mismatch_packet": has_amp,
                "has_ir_candidate": has_ir,
                "has_reverse_output": has_reverse,
                "has_adaptive_response_policy": has_pol,
                "has_memory_chain": has_memory,
                "has_value_layer": has_vl,
            },
            "evidence": {
                "sigma_truth_score": truth_score,
                "sigma_calibration_status": sigma_calibration_status,
                "sigma_usable_for_thermodynamics": sigma_usable_for_thermo,
                "mismatch_score": mismatch_score_raw,
                "anti_mismatch_risk_level": anti_mismatch_risk_level,
                "response_size": response_size,
                "boundary_detected": boundary_detected,
                "answer_length_words": answer_words,
                "memory_material_quality": memory_material_quality,
            },
            "reason": reason,
            "notes": [
                "Thermodynamics remains advisory-only.",
                "Thermodynamics does not decide.",
                "Thermodynamics does not emit ACT or verdict.",
                "Thermodynamics only measures dissipation and stability for downstream readonly observers.",
            ],
            **_BOUNDARY,
        }
    }
