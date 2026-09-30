"""Anti-Mismatch Signal — F2C.

Formal readonly signal that detects structural mismatch between
what the IR Candidate expects and what the Reverse OS actually produced.

Absolute boundary (enforced here, not decided here):
  decision_authority = KX108_ONLY
  advisory_only      = true
  readonly           = true
  emits_act          = false
  emits_verdict      = false
  memory_write       = false
  kernel_mutation    = false
  x108_mutation      = false

Anti-Mismatch does NOT decide. Anti-Mismatch does NOT block.
Anti-Mismatch produces only signal / metric / alert for Sigma and downstream
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

_MEMORY_TERMS = (
    "mémoire", "memoire", "memory", "souvenir", "je me souviens",
    "tu te souviens", "rappelle", "tu sais que", "on avait dit",
    "contexte", "historique",
)


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


def build_anti_mismatch_signal(
    *,
    ir_candidate: dict[str, Any] | None = None,
    true_voice_snapshot: dict[str, Any] | None = None,
    adaptive_response_policy: dict[str, Any] | None = None,
    domain_raccord: dict[str, Any] | None = None,
    sigma_packet: dict[str, Any] | None = None,
    memory_chain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build ANTI_MISMATCH_SIGNAL_V1 — formal structural gap detection.

    Signal detection (all boolean, all advisory):
      1. architecture_answer_too_short  : ARCHITECTURE domain + final_answer < 80 words
      2. boundary_compact_under_answer  : BOUNDARY_COMPACT policy + final_answer > 80 words
      3. structural_gap                 : IR present + final_answer absent or < 25 words
      4. false_on_risk                  : boundary_detected + structural_answer_available + answer > 80 words
      5. collapse_disguised             : truth_score >= 0.70 + final_answer < 40 words + domains present
      6. memory_claim_without_material  : answer mentions memory terms + no usable memory material
      7. sigma_high_but_answer_empty    : truth_score >= 0.70 + final_answer < 20 words
      8. decorative_coherence           : derived from signals 1, 4, 5, 6, 7

    Score weights (additive, clamped [0.0, 1.0]):
      +0.20 structural_gap
      +0.20 decorative_coherence
      +0.15 false_on_risk
      +0.15 collapse_disguised
      +0.15 memory_claim_without_material
      +0.10 architecture_answer_too_short
      +0.10 sigma_high_but_answer_empty
      +0.05 boundary_compact_under_answer

    Risk levels:
      NONE   : mismatch_score == 0.0
      LOW    : 0.0 < score <= 0.25
      MEDIUM : 0.25 < score <= 0.60
      HIGH   : score > 0.60
    """
    ir = ir_candidate if isinstance(ir_candidate, dict) else {}
    tvs = true_voice_snapshot if isinstance(true_voice_snapshot, dict) else {}
    pol = adaptive_response_policy if isinstance(adaptive_response_policy, dict) else {}
    dr = domain_raccord if isinstance(domain_raccord, dict) else {}
    sp = sigma_packet if isinstance(sigma_packet, dict) else {}
    chain = memory_chain if isinstance(memory_chain, dict) else {}

    # ── Input extraction ─────────────────────────────────────────────────
    final_answer = str(tvs.get("final_answer") or "")
    answer_words = _word_count(final_answer)

    dr_domains: list[str] = dr.get("domains", []) if isinstance(dr.get("domains"), list) else []
    domain_count = len(dr_domains)

    truth_score = sp.get("truth_score")  # float | None
    has_valid_truth_score = isinstance(truth_score, (int, float))
    ts_value: float = float(truth_score) if has_valid_truth_score else 0.0

    ir_present = bool(ir.get("intent_type") or ir.get("entities") is not None)
    boundary_compact = (
        pol.get("response_size") == "BOUNDARY_COMPACT"
        or pol.get("boundary_detected") is True
    )
    structural_answer_available = bool(dr.get("structural_answer_available"))

    material_quality = chain.get("material_quality", "")
    memory_material_ok = material_quality in ("USABLE_MATERIAL", "PARTIAL_MATERIAL")

    # ── Signal 1: architecture_answer_too_short ──────────────────────────
    architecture_domain = "ARCHITECTURE_EXPLANATION" in dr_domains
    sig_architecture_too_short = (
        architecture_domain
        and answer_words > 0
        and answer_words < 80
    )

    # ── Signal 2: boundary_compact_under_answer ──────────────────────────
    sig_boundary_compact_under_answer = (
        boundary_compact
        and answer_words > 80
    )

    # ── Signal 3: structural_gap ─────────────────────────────────────────
    sig_structural_gap = (
        ir_present
        and (answer_words == 0 or answer_words < 25)
    )

    # ── Signal 4: false_on_risk ──────────────────────────────────────────
    sig_false_on_risk = (
        boundary_compact
        and structural_answer_available
        and answer_words > 80
    )

    # ── Signal 5: collapse_disguised ────────────────────────────────────
    sig_collapse_disguised = (
        has_valid_truth_score
        and ts_value >= 0.70
        and answer_words > 0
        and answer_words < 40
        and domain_count > 0
    )

    # ── Signal 6: memory_claim_without_material ──────────────────────────
    answer_lower = final_answer.lower()
    mentions_memory = any(term in answer_lower for term in _MEMORY_TERMS)
    sig_memory_claim_without_material = (
        mentions_memory
        and not memory_material_ok
    )

    # ── Signal 7: sigma_high_but_answer_empty ────────────────────────────
    sig_sigma_high_but_answer_empty = (
        has_valid_truth_score
        and ts_value >= 0.70
        and answer_words < 20
    )

    # ── Signal 8: decorative_coherence (derived) ─────────────────────────
    sig_decorative_coherence = any([
        sig_architecture_too_short,
        sig_false_on_risk,
        sig_collapse_disguised,
        sig_memory_claim_without_material,
        sig_sigma_high_but_answer_empty,
    ])

    # ── Score computation ────────────────────────────────────────────────
    raw_score = 0.0
    if sig_structural_gap:
        raw_score += 0.20
    if sig_decorative_coherence:
        raw_score += 0.20
    if sig_false_on_risk:
        raw_score += 0.15
    if sig_collapse_disguised:
        raw_score += 0.15
    if sig_memory_claim_without_material:
        raw_score += 0.15
    if sig_architecture_too_short:
        raw_score += 0.10
    if sig_sigma_high_but_answer_empty:
        raw_score += 0.10
    if sig_boundary_compact_under_answer:
        raw_score += 0.05

    mismatch_score = round(min(1.0, raw_score), 3)

    # ── Risk level ───────────────────────────────────────────────────────
    if mismatch_score == 0.0:
        risk_level = "NONE"
    elif mismatch_score <= 0.25:
        risk_level = "LOW"
    elif mismatch_score <= 0.60:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    signals = {
        "architecture_answer_too_short": sig_architecture_too_short,
        "boundary_compact_under_answer": sig_boundary_compact_under_answer,
        "structural_gap": sig_structural_gap,
        "false_on_risk": sig_false_on_risk,
        "collapse_disguised": sig_collapse_disguised,
        "memory_claim_without_material": sig_memory_claim_without_material,
        "sigma_high_but_answer_empty": sig_sigma_high_but_answer_empty,
        "decorative_coherence": sig_decorative_coherence,
    }

    inputs_snapshot = {
        "ir_present": ir_present,
        "answer_words": answer_words,
        "domain_count": domain_count,
        "truth_score": truth_score,
        "boundary_compact": boundary_compact,
        "structural_answer_available": structural_answer_available,
        "memory_material_ok": memory_material_ok,
        "architecture_domain": architecture_domain,
        "mentions_memory": mentions_memory,
    }

    return {
        "anti_mismatch_packet": {
            "version": "ANTI_MISMATCH_SIGNAL_V1",
            "mode": "SHADOW_READONLY",
            "source": "BRODY_ANTI_MISMATCH_F2C",
            "mismatch_score": mismatch_score,
            "risk_level": risk_level,
            "false_on_detected": sig_false_on_risk or sig_collapse_disguised,
            "decorative_coherence_detected": sig_decorative_coherence,
            "collapse_disguised_detected": sig_collapse_disguised,
            "structural_gap_detected": sig_structural_gap,
            "signals": signals,
            "inputs_snapshot": inputs_snapshot,
            "notes": [
                "Anti-Mismatch is advisory-only.",
                "Anti-Mismatch does not decide.",
                "Anti-Mismatch does not block.",
                "Anti-Mismatch does not emit ACT or verdict.",
                "Anti-Mismatch only calibrates mismatch signal for Sigma and downstream readonly observers.",
            ],
            **_BOUNDARY,
        }
    }
