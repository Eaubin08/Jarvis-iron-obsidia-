"""
brody_point_cloud_21d_selector — V3 Block 1
Active 21D selector engine. Transforms prompt into a 21-axis vector
and selects active_layers, forbidden_layers, and budget.
No IO. No ACT. No decision. DECISION_AUTHORITY=KX108_ONLY.
"""
from __future__ import annotations

import re
from typing import Any

_MAX_ACTIVE_LAYERS = 6
_MAX_BUDGET = 8192
_MICRO_CORE_BUDGET = 1792

# ── Layer registry ────────────────────────────────────────────────────────────
_ALL_LAYERS = [
    "authority_layer",
    "cic_core_layer",
    "semantic_router_layer",
    "bio_animal_coherence_layer",
    "symbolic_layer",
    "fractal_layer",
    "OS_reverse_layer",
    "projection_layer",
    "reflex_layer",
    "memory_selector_layer",
    "domain_bank_layer",
    "domain_trading_layer",
    "domain_gps_defense_aviation_layer",
    "reciprocal_layer",
    "LCTU_LTCU_layer",
    "universal_language_layer",
    "temporal_layer",
    "proof_layer",
]

_ALWAYS_LAYERS = ["authority_layer", "cic_core_layer"]

# Axis 12 keywords (projection)
_PROJ_PATTERNS = [
    r"\bprojection\b", r"\bsc[eé]nario\b", r"\bhypoth[eè]se\b",
    r"\banticiper\b", r"\bsi\s+x\s+alors\b", r"\bestimer\b",
]

# Axis 14 (symbolic)
_SYM_PATTERNS = [
    r"\bsymbolisme\b", r"\bencodage\s+symbolique\b",
    r"\bsymbole\s+cic\b", r"\brepr[eé]sentation\s+symbolique\b",
]

# Axis 15 (fractal)
_FRAC_PATTERNS = [
    r"\bfractal[e]?\b", r"\bauto.similarit[eé]\b", r"\br[eé]cursif\b",
]

# Axis 7 (temporalite)
_TEMP_PATTERNS = [
    r"\bpass[eé]\b", r"\bpr[eé]sent\b", r"\bfutur\b",
    r"\btempor[e]?l\b", r"\bchronologie\b",
]

# Axis 6 (preuve)
_PROOF_PATTERNS = [
    r"\bpreuve\b", r"\bproof\b", r"\blean\b", r"\btla\b",
    r"\bmerkle\b", r"\bos3\b",
]

# Axis 8 (source fiabilite)
_SOURCE_PATTERNS = [
    r"\bsource\b", r"\bfiabilit[eé]\b", r"\bconfirm[eé]?\b",
    r"\bv[eé]rifi[eé]?\b", r"\bcheck\b",
]

# Axis 9 (ressource)
_RESOURCE_PATTERNS = [
    r"\bressource\b", r"\bbudget\b", r"\bco[uû]t\b",
    r"\bm[eé]moire\s+disponible\b", r"\bcapacit[eé]\b",
]

# Axis 10 (trajectoire)
_TRAJ_PATTERNS = [
    r"\btrajectoire\b", r"\bchemin\b", r"\bitinéraire\b",
    r"\broute\b", r"\bparcours\b",
]

# Axis 11 (comportement)
_BEHAV_PATTERNS = [
    r"\bcomportement\b", r"\baction\b", r"\bd[eé]cision\b",
    r"\bstrat[eé]gie\b",
]


def _match(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


def _score(text: str, patterns: list[str], max_val: float = 1.0) -> float:
    count = sum(1 for p in patterns if re.search(p, text))
    return round(min(max_val, count * 0.35), 3)


class BrodyPointCloud21DSelector:
    """
    21D active selector. Computes a 21-axis vector and drives layer selection.
    No IO, no ACT, no decision. DECISION_AUTHORITY=KX108_ONLY.
    """

    def _compute_raw_vector(
        self,
        msg: str,
        mc: dict,
        bal: dict | None,
    ) -> dict[str, float | int]:
        """Compute raw 21 axis values from message + micro_core + balance signals."""
        bal = bal or {}
        coordinator = bal.get("coordinator", {})
        balances = bal.get("balances", {})
        bio = mc.get("bio_animal_signal", {})
        rev = mc.get("reversibility_signal", {})

        # Axis 1 — domaine (0=none, 1=bank, 2=trading, 3=gps_defense_aviation)
        domain = mc.get("domain_detected")
        ax1 = {"bank": 1, "trading": 2, "gps_defense_aviation": 3}.get(domain or "", 0)

        # Axis 2 — autorite (1=X108 confirmed, 0=compromised)
        is_adv = bool(mc.get("is_adversarial", False))
        ax2: float = 0.0 if is_adv else 1.0

        # Axis 3 — reversibilite (0=irreversible, 1=reversible)
        ax3 = float(rev.get("reversibility_score", 1.0))

        # Axis 4 — pression_invariant
        irrev = float(rev.get("irreversibility_score", 0.0))
        ax4 = round(max(0.9 if is_adv else 0.0, irrev), 3)

        # Axis 5 — donnees_manquantes
        hold = bool(mc.get("hold_required", False))
        ax5 = 1.0 if hold else (0.3 if is_adv else 0.0)

        # Axis 6 — preuve
        ax6 = _score(msg, _PROOF_PATTERNS) if mc.get("proof_detected") else 0.0

        # Axis 7 — temporalite
        ax7 = _score(msg, _TEMP_PATTERNS) if mc.get("temporal_detected") else 0.0

        # Axis 8 — source fiabilite
        ax8 = _score(msg, _SOURCE_PATTERNS)

        # Axis 9 — ressource
        ax9 = _score(msg, _RESOURCE_PATTERNS)

        # Axis 10 — trajectoire
        ax10 = _score(msg, _TRAJ_PATTERNS)

        # Axis 11 — comportement
        ax11 = _score(msg, _BEHAV_PATTERNS)

        # Axis 12 — projection
        proj = mc.get("projection_not_prediction_signal", {})
        ax12 = 0.7 if proj.get("projection_allowed") else (0.2 if proj.get("projection_detected") else 0.0)

        # Axis 13 — memoire
        bal_mem = balances.get("balance_memoire", {})
        ax13 = round(float(bal_mem.get("tension", 0.0)), 3)

        # Axis 14 — symbolique
        sym = mc.get("symbolic_signal", {})
        ax14 = round(float(sym.get("symbolic_density", 0.0)), 3)

        # Axis 15 — fractal
        frac = mc.get("fractal_signal", {})
        ax15 = 1.0 if frac.get("fractal_pattern_detected") else 0.0

        # Axis 16 — os_reverse
        os_rev = mc.get("os_reverse_signal", {})
        ax16 = round(float(os_rev.get("causal_depth_score", 0.0)), 3)

        # Axis 17 — bio_coherence (0-1)
        ax17 = round(float(bio.get("path_coherence_score", 0.5)), 3)

        # Axis 18 — energy_cost (int bytes)
        raw_cost = int(bio.get("energy_cost_estimate", _MICRO_CORE_BUDGET))
        risk_level = float(coordinator.get("balance_risk_level", 0.0))
        ax18 = max(raw_cost, int(risk_level * 4096))

        # Axis 19 — path_coherence
        ax19 = round(float(bio.get("path_coherence_score", 0.5)), 3)

        # Axis 20 — weak_signal_tracking
        weak = bio.get("weak_signal_detection", [])
        ax20 = round(min(1.0, len(weak) * 0.4), 3)

        # Axis 21 — terrain_adaptation
        terrain_fit = float(bio.get("terrain_fit_score", 0.6))
        domain_confirmed = ax1 > 0
        ax21 = round(terrain_fit * (1.2 if domain_confirmed else 1.0), 3)

        return {
            1: ax1, 2: ax2, 3: ax3, 4: ax4, 5: ax5, 6: ax6,
            7: ax7, 8: ax8, 9: ax9, 10: ax10, 11: ax11, 12: ax12,
            13: ax13, 14: ax14, 15: ax15, 16: ax16, 17: ax17,
            18: ax18, 19: ax19, 20: ax20, 21: ax21,
        }

    def _apply_axis_rules(
        self, vector: dict, mc: dict, bal: dict | None
    ) -> tuple[list[str], list[str]]:
        """Apply axis-based rules to produce layer votes and forbidden votes."""
        bal = bal or {}
        coordinator = bal.get("coordinator", {})
        balances = bal.get("balances", {})
        bio = mc.get("bio_animal_signal", {})
        is_adv = bool(mc.get("is_adversarial", False))

        votes: dict[str, int] = {}
        forbidden: set[str] = set()

        def vote(layer: str, weight: int = 1) -> None:
            votes[layer] = votes.get(layer, 0) + weight

        # Axis 2 → authority
        if vector[2] < 0.5:
            vote("authority_layer", 3)
            vote("reflex_layer", 2)
            forbidden.add("symbolic_layer")

        # Axis 3 → reversibility block
        if vector[3] < 0.3:
            vote("authority_layer", 3)

        # Axis 4 → invariant pressure
        if vector[4] >= 0.5:
            vote("reflex_layer", 2)
            vote("authority_layer", 2)

        # Axis 5 → missing data → HOLD
        if vector[5] >= 0.8:
            vote("authority_layer", 2)

        # Axis 6 → proof needed
        if vector[6] > 0.3:
            vote("proof_layer", 2)

        # Axis 7 → temporal context
        if vector[7] > 0.3:
            vote("temporal_layer", 1)

        # Axis 12 → projection layer
        if vector[12] >= 0.5:
            vote("projection_layer", 2)

        # Axis 13 → memory needed
        if vector[13] >= 0.7:
            vote("memory_selector_layer", 2)

        # Axis 14 → symbolic
        if vector[14] >= 0.3:
            vote("symbolic_layer", 2)

        # Axis 15 → fractal
        if vector[15] >= 0.5:
            vote("fractal_layer", 1)

        # Axis 16 → OS reverse
        if vector[16] >= 0.4:
            vote("OS_reverse_layer", 2)

        # Axis 17 → bio coherence (low = bio needed)
        if vector[17] < 0.5:
            vote("bio_animal_coherence_layer", 2)


        # Axis 19 → path coherence (low = recalibrate)
        if vector[19] < 0.4:
            vote("reflex_layer", 1)

        # Axis 20 → weak signals → rare layers
        weak_layers = list(bio.get("weak_signal_detection", []))
        if vector[20] > 0:
            for wl in weak_layers[:2]:
                vote(wl, 2)

        # Axis 21 → terrain adaptation → domain
        domain = mc.get("domain_detected")
        if domain and vector[21] > 0.5:
            domain_layer = {
                "bank": "domain_bank_layer",
                "trading": "domain_trading_layer",
                "gps_defense_aviation": "domain_gps_defense_aviation_layer",
            }.get(domain)
            if domain_layer:
                vote(domain_layer, 3)

        # Axis 1 → domain detected at all
        if vector[1] > 0:
            domain_layer = {
                1: "domain_bank_layer",
                2: "domain_trading_layer",
                3: "domain_gps_defense_aviation_layer",
            }.get(int(vector[1]))
            if domain_layer:
                vote(domain_layer, 2)

        # Balance engine votes (override over axis votes)
        bal_layers = coordinator.get("layers_to_activate", [])
        bal_avoid = coordinator.get("layers_to_avoid", [])
        for l in bal_layers:
            if l not in _ALWAYS_LAYERS:
                vote(l, 4)
        for l in bal_avoid:
            forbidden.add(l)

        # Dead paths from bio
        dead = bio.get("dead_path_detection", [])
        for dp in dead:
            forbidden.add(dp)

        return votes, forbidden

    def _select_layers(
        self,
        votes: dict[str, int],
        forbidden: set[str],
        budget_remaining: int,
        balances: dict,
    ) -> list[str]:
        """Select up to MAX_ACTIVE_LAYERS layers from votes, respecting budget."""
        selected = list(_ALWAYS_LAYERS)
        sorted_candidates = sorted(
            [(layer, score) for layer, score in votes.items() if layer not in selected],
            key=lambda x: x[1],
            reverse=True,
        )

        budget_used = _MICRO_CORE_BUDGET
        _LAYER_COSTS = {
            "OS_reverse_layer": 2048,
            "domain_bank_layer": 2048,
            "domain_trading_layer": 2048,
            "domain_gps_defense_aviation_layer": 2048,
            "bio_animal_coherence_layer": 2048,
            "symbolic_layer": 1536,
            "projection_layer": 1024,
            "fractal_layer": 1024,
            "reflex_layer": 1024,
            "memory_selector_layer": 512,
            "temporal_layer": 512,
            "proof_layer": 512,
            "reciprocal_layer": 512,
            "semantic_router_layer": 256,
        }

        for layer, _ in sorted_candidates:
            if len(selected) >= _MAX_ACTIVE_LAYERS:
                break
            if layer in forbidden:
                continue
            cost = _LAYER_COSTS.get(layer, 256)
            if budget_used + cost <= _MAX_BUDGET:
                selected.append(layer)
                budget_used += cost

        return selected, budget_used

    # ── Public API ─────────────────────────────────────────────────────────────

    def compute_vector(
        self,
        message: str,
        micro_core_output: dict,
        balance_output: dict | None = None,
    ) -> dict[str, Any]:
        """
        Compute 21D vector and produce layer selection.
        No IO, no ACT. DECISION_AUTHORITY=KX108_ONLY.
        """
        mc = micro_core_output or {}
        bal = balance_output or {}
        msg_lower = (message or "").lower()
        is_adv = bool(mc.get("is_adversarial", False))

        # Step 1 — compute raw 21D vector
        vector = self._compute_raw_vector(msg_lower, mc, bal)

        # Step 2 — apply axis rules → votes + forbidden
        votes, forbidden = self._apply_axis_rules(vector, mc, bal)
        votes = {layer: weight for layer, weight in votes.items() if layer in _ALL_LAYERS}
        forbidden = {layer for layer in forbidden if layer in _ALL_LAYERS}

        # Step 3 — budget enforcement
        budget_available = _MAX_BUDGET - _MICRO_CORE_BUDGET

        # Step 4 — select layers
        active_layers, budget_used = self._select_layers(
            votes, forbidden, budget_available, bal.get("balances", {})
        )


        # Step 6 — forbidden layers (cleaned, no duplicates)
        forbidden_clean = sorted(set(forbidden) - set(active_layers))

        # Step 7 — packet assembly
        dominant_axes = sorted(
            [(k, v) for k, v in vector.items() if isinstance(v, float) and v > 0.5],
            key=lambda x: x[1],
            reverse=True,
        )[:5]
        dominant_axes_ids = [a[0] for a in dominant_axes]

        coordinator = bal.get("coordinator", {})
        domain_detected = mc.get("domain_detected")

        memory_packet_required = vector[13] >= 0.7 and not is_adv
        domain_packet_required = domain_detected is not None and vector[21] > 0.4

        risk_flags: list[str] = []
        if is_adv:
            risk_flags.append("ADVERSARIAL_DETECTED")
        if mc.get("hold_required"):
            risk_flags.append("HOLD_REQUIRED_IRREVERSIBLE")
        if vector[4] >= 0.5:
            risk_flags.append("INVARIANT_PRESSURE_HIGH")

        return {
            "selector_version": "V3_BLOCK_1",
            "dimensions": 21,
            "io_external": False,
            "emits_act": False,
            "decision_authority": "KX108_ONLY",
            "advisory_only": True,
            "vector_21d": vector,
            "dominant_axes": dominant_axes_ids,
            "active_layers": active_layers,
            "forbidden_layers": forbidden_clean,
            "budget_estimate": budget_used,
            "memory_packet_required": memory_packet_required,
            "domain_packet_required": domain_packet_required,
            "domain_detected": domain_detected,
            "balance_packet": {
                "dominant_balance": coordinator.get("dominant_balance"),
                "top3": coordinator.get("top3_balances", []),
                "risk_level": coordinator.get("balance_risk_level", 0.0),
                "hold_required": coordinator.get("hold_required", False),
            },
            "risk_flags": risk_flags,
        }
