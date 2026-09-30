"""Gencoin Transverse Interface — F2A / F2B / F2C.

Phase F2A: SHADOW_READONLY value layer pre-wiring.
Phase F2B: Sigma calibration V1 — bounded deterministic truth_score.
Phase F2C: Anti-Mismatch formal signal wired into Sigma V1.

Absolute boundary (enforced here, not decided here):
  decision_authority = KX108_ONLY
  advisory_only      = true
  readonly           = true
  emits_act          = false
  emits_verdict      = false
  memory_write       = false
  graphiti_write     = false
  neo4j_write        = false
  kernel_mutation    = false
  x108_mutation      = false
  final_scoring_enabled = false

Sigma measures signal quality. Sigma does not decide. KX108 decides.
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

# Calibration status values
_STATUS_CALIBRATED = "CALIBRATED_SHADOW_READONLY"
_STATUS_BOUNDARY = "CALIBRATED_BOUNDARY_ONLY"
_STATUS_INSUFFICIENT = "INSUFFICIENT_MATERIAL"


_STATUS_MISMATCH_RISK = "CALIBRATED_WITH_MISMATCH_RISK"


def build_sigma_packet(
    adaptive_response_policy: dict[str, Any] | None = None,
    *,
    ir_candidate: dict[str, Any] | None = None,
    domain_raccord: dict[str, Any] | None = None,
    memory_chain: dict[str, Any] | None = None,
    true_voice_snapshot: dict[str, Any] | None = None,
    anti_mismatch_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build SIGMA_CALIBRATION_PACKET_V1 — bounded deterministic truth_score.

    Phase F2B: core heuristic.
    Phase F2C: anti_mismatch_packet replaces textual decorative_coherence_risk.

    Heuristic (deterministic, bounded [0.0, 1.0]):
      base                    = 0.50
      +0.15  IR Candidate present
      +0.10  Reverse OS output present (final_answer in true_voice_snapshot)
      +0.10  adaptive_response_policy present
      +0.10  memory_chain readonly material present
      +0.10  readonly boundary confirmed
      -0.25  boundary_compact detected (ACT/write/mutation request)
      -0.20  decorative_coherence_risk (formal if anti_mismatch available, else textual)
      -0.15  missing material (no IR, no memory)
      clamp [0.0, 1.0]

    Calibration statuses:
      CALIBRATED_SHADOW_READONLY    — non-boundary, sufficient material, usable=True
      CALIBRATED_WITH_MISMATCH_RISK — non-boundary but mismatch_score >= 0.60, usable=False
      CALIBRATED_BOUNDARY_ONLY      — boundary context, truth_score computed but not useful
                                       for Gencoin (usable_for_gencoin=False)
      INSUFFICIENT_MATERIAL          — not enough input, truth_score=None, usable=False

    Rules:
      - truth_score is deterministic and bounded.
      - truth_score is null only if INSUFFICIENT_MATERIAL.
      - Sigma is not a decision-maker.
      - usable_for_gencoin=True only if CALIBRATED_SHADOW_READONLY.
      - usable_for_thermodynamics=True only if CALIBRATED_SHADOW_READONLY.
      - Does not replace or break adaptive_response_policy.
      - anti_mismatch_packet is optional — degrades gracefully to textual if absent.
    """
    pol = adaptive_response_policy if isinstance(adaptive_response_policy, dict) else {}
    ir = ir_candidate if isinstance(ir_candidate, dict) else {}
    dr = domain_raccord if isinstance(domain_raccord, dict) else {}
    chain = memory_chain if isinstance(memory_chain, dict) else {}
    tvs = true_voice_snapshot if isinstance(true_voice_snapshot, dict) else {}
    amp = anti_mismatch_packet if isinstance(anti_mismatch_packet, dict) else {}

    # ── Feature detection ────────────────────────────────────────────────
    boundary_compact = (
        pol.get("response_size") == "BOUNDARY_COMPACT"
        or pol.get("boundary_detected") is True
    )

    domains: list[str] = pol.get("domains", []) if isinstance(pol.get("domains"), list) else []
    dr_domains: list[str] = dr.get("domains", []) if isinstance(dr.get("domains"), list) else []
    all_domains = list(dict.fromkeys(domains + dr_domains))

    architecture_signal = "ARCHITECTURE_EXPLANATION" in all_domains

    memory_chain_present = chain.get("material_quality") in (
        "USABLE_MATERIAL", "PARTIAL_MATERIAL"
    ) or chain.get("status") in (
        "BRODY_MEMORY_RESPONSE_CHAIN_PASS", "LOCAL_INDEX_FALLBACK_PARTIAL"
    )

    readonly_boundary_ok = (
        pol.get("readonly") is True
        and pol.get("emits_act") is False
        and pol.get("memory_write") is False
    )

    # F2C: prefer formal anti_mismatch signal; fall back to textual detection.
    amp_version = amp.get("version", "")
    anti_mismatch_formal_available = amp_version == "ANTI_MISMATCH_SIGNAL_V1"
    if anti_mismatch_formal_available:
        decorative_coherence_risk = bool(amp.get("decorative_coherence_detected"))
        formal_mismatch_score: float = float(amp.get("mismatch_score", 0.0))
    else:
        decorative_coherence_risk = (
            "ANTI_MISMATCH" in all_domains
            or (architecture_signal and boundary_compact)
        )
        formal_mismatch_score = 0.0

    has_ir = bool(ir.get("intent_type") or ir.get("entities") is not None)
    has_reverse_output = bool(
        tvs.get("final_answer") and len(str(tvs.get("final_answer", ""))) > 10
    )
    has_adaptive = bool(pol)
    has_domain = bool(all_domains)
    has_memory = memory_chain_present
    has_boundary_signal = boundary_compact

    # ── Sufficient material check ────────────────────────────────────────
    has_sufficient = any([has_ir, has_reverse_output, has_adaptive])

    existing_sigma_pressure = pol.get("sigma_pressure")  # str | None — reused, not invented

    inputs = {
        "has_ir_candidate": has_ir,
        "has_reverse_output": has_reverse_output,
        "has_adaptive_response_policy": has_adaptive,
        "has_domain_raccord": has_domain,
        "has_memory_chain": has_memory,
        "has_boundary_signal": has_boundary_signal,
    }

    if not has_sufficient:
        return {
            "version": "SIGMA_CALIBRATION_PACKET_V1",
            "mode": "SHADOW_READONLY",
            "source": "BRODY_SIGMA_CALIBRATION_F2B",
            "calibration_status": _STATUS_INSUFFICIENT,
            "usable_for_gencoin": False,
            "usable_for_thermodynamics": False,
            "truth_score": None,
            "sigma_pressure": existing_sigma_pressure,
            "reason": "INSUFFICIENT_MATERIAL",
            "inputs": inputs,
            "features": {
                "boundary_compact": boundary_compact,
                "architecture_signal": architecture_signal,
                "memory_chain_present": memory_chain_present,
                "readonly_boundary_ok": readonly_boundary_ok,
                "decorative_coherence_risk": decorative_coherence_risk,
                "anti_mismatch_formal_available": anti_mismatch_formal_available,
                "formal_mismatch_score": formal_mismatch_score if anti_mismatch_formal_available else None,
                "missing_material": True,
            },
            "score_components": {
                "structure_score": 0.0,
                "boundary_score": 0.0,
                "memory_support_score": 0.0,
                "mismatch_penalty": 0.0,
                "material_penalty": 0.0,
            },
            "notes": [
                "Sigma remains advisory-only.",
                "Sigma does not decide.",
                "Sigma does not emit ACT or verdict.",
                "Sigma only calibrates signal quality for downstream readonly observers.",
            ],
            **_BOUNDARY,
        }

    # ── Score computation ────────────────────────────────────────────────
    structure_score = 0.0
    boundary_score = 0.0
    memory_support_score = 0.0
    mismatch_penalty = 0.0
    material_penalty = 0.0

    if has_ir:
        structure_score += 0.15
    if has_reverse_output:
        structure_score += 0.10
    if has_adaptive:
        boundary_score += 0.10
    if readonly_boundary_ok:
        boundary_score += 0.10
    if has_memory:
        memory_support_score += 0.10
    if boundary_compact:
        mismatch_penalty += 0.25
    if decorative_coherence_risk:
        mismatch_penalty += 0.20
    if not has_memory and not has_ir:
        material_penalty += 0.15

    raw = 0.50 + structure_score + boundary_score + memory_support_score - mismatch_penalty - material_penalty
    truth_score = round(max(0.0, min(1.0, raw)), 3)

    # ── Calibration status and usability ────────────────────────────────
    if boundary_compact:
        calibration_status = _STATUS_BOUNDARY
        usable_for_gencoin = False
        usable_for_thermodynamics = False
        reason = "BOUNDARY_COMPACT_CONTEXT_NOT_USEFUL_FOR_VALUE_LAYER"
    elif anti_mismatch_formal_available and formal_mismatch_score >= 0.60:
        calibration_status = _STATUS_MISMATCH_RISK
        usable_for_gencoin = False
        usable_for_thermodynamics = False
        reason = f"ANTI_MISMATCH_FORMAL_HIGH_RISK_SCORE_{formal_mismatch_score}"
    else:
        calibration_status = _STATUS_CALIBRATED
        usable_for_gencoin = True
        usable_for_thermodynamics = True
        reason = "SIGMA_CALIBRATED_SHADOW_READONLY_F2C" if anti_mismatch_formal_available else "SIGMA_CALIBRATED_SHADOW_READONLY_F2B"

    return {
        "version": "SIGMA_CALIBRATION_PACKET_V1",
        "mode": "SHADOW_READONLY",
        "source": "BRODY_SIGMA_CALIBRATION_F2C",
        "calibration_status": calibration_status,
        "usable_for_gencoin": usable_for_gencoin,
        "usable_for_thermodynamics": usable_for_thermodynamics,
        "truth_score": truth_score,
        "sigma_pressure": existing_sigma_pressure,
        "reason": reason,
        "inputs": inputs,
        "features": {
            "boundary_compact": boundary_compact,
            "architecture_signal": architecture_signal,
            "memory_chain_present": memory_chain_present,
            "readonly_boundary_ok": readonly_boundary_ok,
            "decorative_coherence_risk": decorative_coherence_risk,
            "anti_mismatch_formal_available": anti_mismatch_formal_available,
            "formal_mismatch_score": formal_mismatch_score if anti_mismatch_formal_available else None,
            "missing_material": not has_memory and not has_ir,
        },
        "score_components": {
            "structure_score": structure_score,
            "boundary_score": boundary_score,
            "memory_support_score": memory_support_score,
            "mismatch_penalty": -mismatch_penalty,
            "material_penalty": -material_penalty,
        },
        "notes": [
            "Sigma remains advisory-only.",
            "Sigma does not decide.",
            "Sigma does not emit ACT or verdict.",
            "Sigma only calibrates signal quality for downstream readonly observers.",
        ],
        **_BOUNDARY,
    }


def build_gencoin_transverse_packet(
    *,
    ir_candidate: dict[str, Any] | None = None,
    true_voice_snapshot: dict[str, Any] | None = None,
    domain_raccord: dict[str, Any] | None = None,
    trees_snap: dict[str, Any] | None = None,
    memory_chain: dict[str, Any] | None = None,
    has_proof_readonly: bool = False,
    adaptive_response_policy: dict[str, Any] | None = None,
    sigma_packet: dict[str, Any] | None = None,
    thermodynamics_packet: dict[str, Any] | None = None,
    gencoin_shadow_packet: dict[str, Any] | None = None,
    tree_signal_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the GENCOIN_TRANSVERSE_INTERFACE_V0 packet.

    All scores remain null. No final scoring. No economic projection.
    This packet wires the interface so future SIGMA / THERMO / TREES
    calibrations can connect without recabling the pipeline.

    BLOC D hooks — inputs_available flags:
      ir_candidate          : True if ir_candidate is present and non-empty.
      sigma                 : True if sigma_pressure is in adaptive_response_policy.
      thermodynamics        : True if THERMODYNAMICS_PACKET_V1 present (F3+), else False.
      gencoin_shadow        : True if GENCOIN_SHADOW_VALUE_PACKET_V1 present (F4+), else False.
      trees_textual_signal  : True if domain_raccord or trees_snap signals 34 arbres.
      trees_formal_computation : always False (DEFERRED — periphery/cognitive_trees audit required).
      memory                : True if memory_chain has readonly material.
      proof                 : passed from route level (has_proof_readonly).
      reverse_os            : True if true_voice_snapshot has a final_answer (reverse projected).

    34 Arbres distinction (mandatory per 12N):
      trees_textual_signal  = domain-raccord text detection of "34 arbres" / arch_terms.
      trees_formal_computation = periphery/cognitive_trees computation — never mixed with textual.
    """
    ir = ir_candidate if isinstance(ir_candidate, dict) else {}
    tvs = true_voice_snapshot if isinstance(true_voice_snapshot, dict) else {}
    dr = domain_raccord if isinstance(domain_raccord, dict) else {}
    trees = trees_snap if isinstance(trees_snap, dict) else {}
    chain = memory_chain if isinstance(memory_chain, dict) else {}
    pol = adaptive_response_policy if isinstance(adaptive_response_policy, dict) else {}
    sp = sigma_packet if isinstance(sigma_packet, dict) else {}
    tp = thermodynamics_packet if isinstance(thermodynamics_packet, dict) else {}
    gsp = gencoin_shadow_packet if isinstance(gencoin_shadow_packet, dict) else {}
    tsp = tree_signal_packet if isinstance(tree_signal_packet, dict) else {}

    # ── BLOC D: hook detection ───────────────────────────────────────────
    ir_present = bool(ir.get("intent_type") or ir.get("entities") is not None)

    # sigma: V1 packet present OR sigma_pressure available as fallback
    sigma_present = bool(sp.get("version") or pol.get("sigma_pressure"))

    # thermodynamics: F3+ — present if THERMODYNAMICS_PACKET_V1 wired
    thermo_present = tp.get("version") == "THERMODYNAMICS_PACKET_V1"
    thermo_stability = tp.get("stability_state", "DEFERRED") if thermo_present else "DEFERRED"

    # gencoin_shadow: F4+ — present if GENCOIN_SHADOW_VALUE_PACKET_V1 wired
    gsp_present = gsp.get("version") == "GENCOIN_SHADOW_VALUE_PACKET_V1"
    gsp_usable = bool(gsp.get("usable_shadow_value")) if gsp_present else False
    tree_signal_present = tsp.get("version") == "TREE_SIGNAL_PACKET_V1"
    trees_formal = bool(tree_signal_present and tsp.get("trees_formal_computation") is True)


    # Reverse OS: final_answer in true_voice_snapshot means Reverse OS projected a response.
    reverse_os_present = bool(
        tvs.get("final_answer") and len(str(tvs.get("final_answer", ""))) > 10
    )

    # Memory: readonly context only
    memory_present = chain.get("material_quality") in (
        "USABLE_MATERIAL", "PARTIAL_MATERIAL"
    ) or chain.get("status") in (
        "LOCAL_INDEX_FALLBACK_PARTIAL", "BRODY_MEMORY_RESPONSE_CHAIN_PASS"
    )

    # 34 Arbres — textual signal only (domain raccord or tree policy snap)
    dr_domains: list[str] = dr.get("domains", []) if isinstance(dr.get("domains"), list) else []
    trees_textual = (
        "ARCHITECTURE_EXPLANATION" in dr_domains
        or bool(trees.get("trees_available"))
        or bool(trees.get("tree_policy_status"))
    )
    if not trees_textual:
        structural = str(dr.get("structural_answer") or "")
        if "34" in structural or "arbres" in structural.lower():
            trees_textual = True

    inputs_available: dict[str, bool] = {
        "ir_candidate": ir_present,
        "sigma": sigma_present,
        "thermodynamics": thermo_present,
        "gencoin_shadow": gsp_present,
        "trees_textual_signal": trees_textual,
        "trees_formal_computation": trees_formal,
        "memory": memory_present,
        "proof": has_proof_readonly,
        "reverse_os": reverse_os_present,
    }

    input_status: dict[str, str] = {
        "ir_candidate": "WIRED_PRESENT" if ir_present else "NOT_WIRED_OR_NOT_PRESENT",
        "sigma": (sp.get("calibration_status", "PARTIAL_NOT_FORMALLY_CALIBRATED") if sigma_present else "NOT_CALIBRATED"),
        "thermodynamics": thermo_stability if thermo_present else "DEFERRED",
        "gencoin_shadow": (
            "USABLE_SHADOW_VALUE" if gsp_usable
            else ("NOT_USABLE_SHADOW_VALUE" if gsp_present else "DEFERRED")
        ),
        "trees_textual_signal": "TEXTUAL_SIGNAL_ONLY" if trees_textual else "OPTIONAL_SIGNAL_ONLY",
        "trees_formal_computation": ("FORMAL_READONLY_SIGNAL" if trees_formal else "DEFERRED"),
        "memory": "READONLY_CONTEXT_ONLY" if memory_present else "NO_MATERIAL",
        "proof": "READONLY_PROOF_ONLY" if has_proof_readonly else "NOT_VISIBLE",
        "reverse_os": "OPTIONAL_PROJECTION_COST" if reverse_os_present else "NOT_PRESENT",
    }

    return {
        "value_layer": {
            "version": "GENCOIN_TRANSVERSE_INTERFACE_V0",
            "mode": "SHADOW_READONLY",
            "final_scoring_enabled": False,
            "status": "INTERFACE_READY_NO_FINAL_SCORING",
            "scores": {
                "cognitive_value": None,
                "proof_value": None,
                "reuse_value": None,
                "memory_value": None,
                "attention_cost": None,
                "energy_cost": None,
                "stability_value": None,
                "economic_projection": None,
            },
            "inputs_available": inputs_available,
            "input_status": input_status,
            "notes": [
                "Gencoin final scoring is disabled.",
                "This packet exists only to avoid future recabling.",
                "No value emitted here can trigger action, verdict, write, "
                "memory promotion, kernel mutation, or X108 mutation.",
            ],
            **_BOUNDARY,
        }
    }
