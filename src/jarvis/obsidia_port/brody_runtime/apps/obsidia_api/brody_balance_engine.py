"""
brody_balance_engine — V3 Block 1
11-balance transversal engine. Weighs tensions. Does not decide. No IO.
DECISION_AUTHORITY=KX108_ONLY. advisory_only=True.
"""
from __future__ import annotations

import math
from typing import Any

# ── Balance priority constants ───────────────────────────────────────────────
_P0 = 0  # absolute / HOLD
_P1 = 1  # danger amplification
_P2 = 2  # coherence
_P3 = 3  # energy / terrain
_P4 = 4  # memory
_P5 = 5  # causal / weak signal
_P6 = 6  # symbolic / projection

_MAX_BUDGET = 8192
_MICRO_CORE_BUDGET = 1792
_AVAILABLE_BUDGET = _MAX_BUDGET - _MICRO_CORE_BUDGET  # 6400
_MAX_ACTIVE_LAYERS = 6


class BrodyBalanceEngine:
    """
    11-balance engine. Receives micro_core_output dict.
    Produces balance signals and a coordinator.
    Cannot authorize, cannot decide, cannot emit ACT.
    """

    ALWAYS_LAYERS = ["authority_layer", "cic_core_layer"]
    MAX_BUDGET = _MAX_BUDGET
    MICRO_CORE_BUDGET = _MICRO_CORE_BUDGET
    AVAILABLE_BUDGET = _AVAILABLE_BUDGET

    # ── Individual balance computations ──────────────────────────────────────

    def _balance_reversibilite(self, mc: dict) -> dict[str, Any]:
        rev_sig = mc.get("reversibility_signal", {})
        irrev = float(rev_sig.get("irreversibility_score", 0.0))
        hold = bool(rev_sig.get("hold_required", False))

        tension = irrev
        seuil_depasse = tension >= 0.3
        amplification = 2.5 if seuil_depasse else 1.0

        return {
            "balance": "balance_reversibilite",
            "priority": _P0,
            "tension": round(tension, 3),
            "amplification": round(amplification, 3),
            "compression": round(1.0 - irrev, 3),
            "desequilibre": round(irrev, 3),
            "seuil_critique": 0.3,
            "cout": 0,
            "couche_a_activer": "authority_layer",
            "couche_a_eviter": None,
            "seuil_depasse": seuil_depasse,
            "hold_required": hold,
        }

    def _balance_risque(self, mc: dict) -> dict[str, Any]:
        is_adv = bool(mc.get("is_adversarial", False))
        irrev = float(mc.get("reversibility_signal", {}).get("irreversibility_score", 0.0))
        surv = bool(mc.get("survival_risk_flag", False))

        raw = (
            (0.6 if is_adv else 0.0)
            + (irrev * 0.3)
            + (0.2 if surv else 0.0)
        )
        tension = min(1.0, raw)
        seuil_depasse = tension >= 0.5
        amplification = 1.8 if seuil_depasse else 1.0

        return {
            "balance": "balance_risque",
            "priority": _P0,
            "tension": round(tension, 3),
            "amplification": round(amplification, 3),
            "compression": round(1.0 - tension, 3),
            "desequilibre": round(tension, 3),
            "seuil_critique": 0.5,
            "cout": 256 if seuil_depasse else 0,
            "couche_a_activer": "reflex_layer" if seuil_depasse else "authority_layer",
            "couche_a_eviter": "memory_selector_layer" if is_adv else None,
            "seuil_depasse": seuil_depasse,
        }

    def _balance_exponentielle(self, mc: dict) -> dict[str, Any]:
        is_adv = bool(mc.get("is_adversarial", False))
        reflex = mc.get("reflex_signal", {})
        reflex_triggered = bool(reflex.get("reflex_triggered", False))

        tension = 0.9 if is_adv else (0.5 if reflex_triggered else 0.1)
        raw_amp = math.exp(tension * 2.3) if tension > 0 else 1.0
        amplification = min(10.0, round(raw_amp, 3))
        seuil_depasse = tension >= 0.5

        return {
            "balance": "balance_exponentielle",
            "priority": _P1,
            "tension": round(tension, 3),
            "amplification": amplification,
            "compression": round(max(0.0, 1.0 - tension), 3),
            "desequilibre": round(tension * amplification / 10.0, 3),
            "seuil_critique": 0.5,
            "cout": 0,
            "couche_a_activer": "authority_layer" if seuil_depasse else None,
            "couche_a_eviter": "symbolic_layer" if is_adv else None,
            "seuil_depasse": seuil_depasse,
        }

    def _balance_coherence(self, mc: dict) -> dict[str, Any]:
        path_coherence = float(
            mc.get("bio_animal_signal", {}).get("path_coherence_score", 0.5)
        )
        incoherence = max(0.0, 1.0 - path_coherence)
        seuil_depasse = incoherence >= 0.4

        return {
            "balance": "balance_coherence",
            "priority": _P2,
            "tension": round(incoherence, 3),
            "amplification": 1.5 if seuil_depasse else 1.0,
            "compression": round(path_coherence, 3),
            "desequilibre": round(incoherence, 3),
            "seuil_critique": 0.4,
            "cout": 128 if seuil_depasse else 0,
            "couche_a_activer": "reflex_layer" if seuil_depasse else None,
            "couche_a_eviter": None,
            "seuil_depasse": seuil_depasse,
        }

    def _balance_energy_cost(self, mc: dict) -> dict[str, Any]:
        raw_cost = int(mc.get("bio_animal_signal", {}).get("energy_cost_estimate", 1792))
        ratio = raw_cost / _MAX_BUDGET
        seuil_depasse = ratio >= 0.7

        return {
            "balance": "balance_energy_cost",
            "priority": _P3,
            "tension": round(ratio, 3),
            "amplification": 1.2 if seuil_depasse else 1.0,
            "compression": round(1.0 - ratio, 3),
            "desequilibre": round(max(0.0, ratio - 0.5), 3),
            "seuil_critique": 0.7,
            "cout": raw_cost,
            "couche_a_activer": None,
            "couche_a_eviter": None,
            "seuil_depasse": seuil_depasse,
        }

    def _balance_bio_terrain(self, mc: dict) -> dict[str, Any]:
        bio = mc.get("bio_animal_signal", {})
        terrain_fit = float(bio.get("terrain_fit_score", 0.6))
        path_coherence = float(bio.get("path_coherence_score", 0.5))

        raw_tension = 1.0 - (terrain_fit * 0.7 + path_coherence * 0.3)
        seuil_depasse = raw_tension >= 0.45
        adaptive = bio.get("adaptive_route_suggestion", [])

        return {
            "balance": "balance_bio_terrain",
            "priority": _P3,
            "tension": round(raw_tension, 3),
            "amplification": 1.3 if seuil_depasse else 1.0,
            "compression": round(terrain_fit, 3),
            "desequilibre": round(raw_tension, 3),
            "seuil_critique": 0.45,
            "cout": 256,
            "couche_a_activer": "bio_animal_coherence_layer" if seuil_depasse else None,
            "couche_a_eviter": str(adaptive[0]) if (not seuil_depasse and adaptive) else None,
            "seuil_depasse": seuil_depasse,
        }

    def _balance_memoire(self, mc: dict) -> dict[str, Any]:
        bio = mc.get("bio_animal_signal", {})
        mem_rel = float(bio.get("memory_relevance_signal", 0.0))
        mem_relevant = bool(mc.get("memory_relevant", False))

        tension = mem_rel
        seuil_depasse = tension >= 0.7

        return {
            "balance": "balance_memoire",
            "priority": _P4,
            "tension": round(tension, 3),
            "amplification": 1.4 if seuil_depasse else 1.0,
            "compression": round(1.0 - tension, 3),
            "desequilibre": round(tension, 3),
            "seuil_critique": 0.7,
            "cout": 512 if seuil_depasse else 0,
            "couche_a_activer": "memory_selector_layer" if seuil_depasse else None,
            "couche_a_eviter": None,
            "seuil_depasse": seuil_depasse,
            "memory_selector_candidate": seuil_depasse and mem_relevant,
        }

    def _balance_causale(self, mc: dict) -> dict[str, Any]:
        os_rev = mc.get("os_reverse_signal", {})
        depth = float(os_rev.get("causal_depth_score", 0.0))
        recommended = bool(os_rev.get("os_reverse_recommended", False))

        seuil_depasse = depth >= 0.5

        return {
            "balance": "balance_causale",
            "priority": _P5,
            "tension": round(depth, 3),
            "amplification": 1.6 if seuil_depasse else 1.0,
            "compression": round(1.0 - depth, 3),
            "desequilibre": round(depth, 3),
            "seuil_critique": 0.5,
            "cout": 2048 if seuil_depasse else 128,
            "couche_a_activer": "OS_reverse_layer" if recommended else None,
            "couche_a_eviter": None,
            "seuil_depasse": seuil_depasse,
        }

    def _balance_signal_faible(self, mc: dict) -> dict[str, Any]:
        bio = mc.get("bio_animal_signal", {})
        weak = list(bio.get("weak_signal_detection", []))
        count = len(weak)
        tension = min(1.0, count * 0.35)
        seuil_depasse = count >= 1

        return {
            "balance": "balance_signal_faible",
            "priority": _P5,
            "tension": round(tension, 3),
            "amplification": 1.2 * count if seuil_depasse else 1.0,
            "compression": round(1.0 - tension, 3),
            "desequilibre": round(tension, 3),
            "seuil_critique": 0.3,
            "cout": 256 * count,
            "couche_a_activer": weak[0] if weak else None,
            "couche_a_eviter": None,
            "seuil_depasse": seuil_depasse,
            "weak_layers_detected": weak,
        }

    def _balance_symbolique(self, mc: dict) -> dict[str, Any]:
        sym = mc.get("symbolic_signal", {})
        density = float(sym.get("symbolic_density", 0.0))
        recommended = bool(sym.get("symbolic_layer_recommended", False))

        seuil_depasse = density >= 0.3

        return {
            "balance": "balance_symbolique",
            "priority": _P6,
            "tension": round(density, 3),
            "amplification": 1.3 if seuil_depasse else 1.0,
            "compression": round(1.0 - density, 3),
            "desequilibre": round(density, 3),
            "seuil_critique": 0.4,
            "cout": 1536 if seuil_depasse else 0,
            "couche_a_activer": "symbolic_layer" if recommended else None,
            "couche_a_eviter": None,
            "seuil_depasse": seuil_depasse,
        }

    def _balance_projection(self, mc: dict) -> dict[str, Any]:
        proj = mc.get("projection_not_prediction_signal", {})
        proj_allowed = bool(proj.get("projection_allowed", False))
        is_prediction = bool(proj.get("is_prediction_claim", False))

        tension = 0.6 if proj_allowed else (0.8 if is_prediction else 0.0)
        seuil_depasse = proj_allowed and not is_prediction

        return {
            "balance": "balance_projection",
            "priority": _P6,
            "tension": round(tension, 3),
            "amplification": 1.1 if seuil_depasse else 1.0,
            "compression": round(1.0 - tension, 3),
            "desequilibre": 0.8 if is_prediction else 0.0,
            "seuil_critique": 0.5,
            "cout": 1024 if seuil_depasse else 0,
            "couche_a_activer": "projection_layer" if seuil_depasse else None,
            "couche_a_eviter": None,
            "seuil_depasse": seuil_depasse,
            "is_prediction_claim": is_prediction,
        }

    # ── Coordinator ───────────────────────────────────────────────────────────

    def _coordinate(self, balances: list[dict]) -> dict[str, Any]:
        sorted_by_score = sorted(
            balances,
            key=lambda b: b["tension"] * b["amplification"],
            reverse=True,
        )
        dominant = sorted_by_score[0]["balance"] if sorted_by_score else None
        top3 = [b["balance"] for b in sorted_by_score[:3]]

        layers_to_activate: list[str] = list(self.ALWAYS_LAYERS)
        layers_to_avoid: set[str] = set()
        budget_used = self.MICRO_CORE_BUDGET

        p0_hold = False
        for b in balances:
            if b.get("hold_required"):
                p0_hold = True
                break

        for b in sorted(balances, key=lambda x: x["priority"]):
            layer = b.get("couche_a_activer")
            avoid = b.get("couche_a_eviter")

            if avoid:
                layers_to_avoid.add(avoid)

            if layer and layer not in layers_to_activate and layer not in layers_to_avoid:
                candidate_cost = b.get("cout", 0)
                if (
                    budget_used + candidate_cost <= self.MAX_BUDGET
                    and len(layers_to_activate) < _MAX_ACTIVE_LAYERS
                ):
                    layers_to_activate.append(layer)
                    budget_used += candidate_cost

        risk_level = round(
            max(
                next((b["tension"] for b in balances if b["balance"] == "balance_risque"), 0.0),
                next((b["tension"] for b in balances if b["balance"] == "balance_reversibilite"), 0.0),
            ),
            3,
        )

        return {
            "dominant_balance": dominant,
            "top3_balances": top3,
            "layers_to_activate": layers_to_activate,
            "layers_to_avoid": sorted(layers_to_avoid),
            "balance_risk_level": risk_level,
            "estimated_budget_bytes": budget_used,
            "hold_required": p0_hold,
            "advisory_only": True,
            "decision_authority": "KX108_ONLY",
            "emits_act": False,
            "can_authorize": False,
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def compute_balances(
        self,
        message: str,
        micro_core_output: dict,
        point_cloud: dict | None = None,
    ) -> dict[str, Any]:
        """
        Compute 11 balance signals + coordinator from micro_core_output.
        No IO, no decision, no ACT. DECISION_AUTHORITY=KX108_ONLY.
        """
        mc = micro_core_output or {}

        balances_raw = [
            self._balance_reversibilite(mc),
            self._balance_risque(mc),
            self._balance_exponentielle(mc),
            self._balance_coherence(mc),
            self._balance_energy_cost(mc),
            self._balance_bio_terrain(mc),
            self._balance_memoire(mc),
            self._balance_causale(mc),
            self._balance_signal_faible(mc),
            self._balance_symbolique(mc),
            self._balance_projection(mc),
        ]

        coordinator = self._coordinate(balances_raw)

        return {
            "balance_engine_version": "V3_BLOCK_1",
            "balances_count": 11,
            "io_external": False,
            "emits_act": False,
            "can_decide": False,
            "can_authorize": False,
            "decision_authority": "KX108_ONLY",
            "advisory_only": True,
            "balances": {b["balance"]: b for b in balances_raw},
            "coordinator": coordinator,
        }
