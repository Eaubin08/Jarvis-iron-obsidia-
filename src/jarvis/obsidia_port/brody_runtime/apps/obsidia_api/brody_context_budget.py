"""
brody_context_budget — V3 Block 2
Controls the logical context budget. No IO. No ACT. Advisory only.
DECISION_AUTHORITY=KX108_ONLY.
"""
from __future__ import annotations

from typing import Any

_GLOBAL_BUDGET = 8192
_MICRO_CORE_BUDGET = 1792
_AVAILABLE_BUDGET = _GLOBAL_BUDGET - _MICRO_CORE_BUDGET  # 6400
_SIMPLE_TARGET = 4864    # bank/trading/gps simple — target

_ALWAYS_LAYERS = frozenset({"authority_layer", "cic_core_layer"})

_LAYER_COST: dict[str, int] = {
    "authority_layer": 512,
    "cic_core_layer": 512,
    "bio_animal_coherence_layer": 2048,
    "OS_reverse_layer": 2048,
    "domain_bank_layer": 2048,
    "domain_trading_layer": 2048,
    "domain_gps_defense_aviation_layer": 2048,
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

# Max active layers by scenario
_MAX_LAYERS_ADVERSARIAL = 4
_MAX_LAYERS_SIMPLE = 4
_MAX_LAYERS_MEMORY = 6
_MAX_LAYERS_DEFAULT = 5


class BrodyContextBudget:
    """
    Enforces context budget. Drops layers that exceed budget or scenario limits.
    Cannot authorize. Cannot decide. DECISION_AUTHORITY=KX108_ONLY.
    """

    def compute(
        self,
        active_layers: list[str],
        point_cloud: dict | None = None,
        balance_output: dict | None = None,
        is_adversarial: bool = False,
        domain_detected: str | None = None,
        memory_explicit: bool = False,
    ) -> dict[str, Any]:
        """
        Enforce budget on active_layers list.
        Returns allowed_layers, dropped_layers, budget_bytes, max_layers.
        No IO. No ACT. No decision. DECISION_AUTHORITY=KX108_ONLY.
        """
        pc = point_cloud or {}
        bal = balance_output or {}

        # Determine max layers for this scenario
        if is_adversarial:
            max_layers = _MAX_LAYERS_ADVERSARIAL
            scenario = "ADVERSARIAL"
        elif memory_explicit:
            max_layers = _MAX_LAYERS_MEMORY
            scenario = "MEMORY_EXPLICIT"
        elif domain_detected in ("bank", "trading", "gps_defense_aviation"):
            max_layers = _MAX_LAYERS_SIMPLE
            scenario = f"DOMAIN_{domain_detected.upper()}"
        else:
            max_layers = _MAX_LAYERS_DEFAULT
            scenario = "DEFAULT"

        # Enforce: always layers first, then budget-ordered selection
        allowed: list[str] = [l for l in _ALWAYS_LAYERS if l in active_layers]
        # Add always layers even if not in list (they are always required)
        for l in _ALWAYS_LAYERS:
            if l not in allowed:
                allowed.append(l)

        candidates = [l for l in active_layers if l not in _ALWAYS_LAYERS and l in _LAYER_COST]



        budget_used = sum(_LAYER_COST.get(l, 256) for l in allowed) + _MICRO_CORE_BUDGET
        dropped: list[str] = []

        for layer in candidates:
            if len(allowed) >= max_layers:
                dropped.append(layer)
                continue
            cost = _LAYER_COST.get(layer, 256)
            if budget_used + cost <= _GLOBAL_BUDGET:
                allowed.append(layer)
                budget_used += cost
            else:
                dropped.append(layer)

        # Drop any remaining candidates beyond max_layers
        while len(allowed) > max_layers:
            extra = allowed.pop()  # drop last (lowest priority)
            dropped.append(extra)
            # Never drop always layers
            for al in _ALWAYS_LAYERS:
                if al not in allowed:
                    allowed.append(al)


        return {
            "budget_version": "V3_BLOCK_2",
            "scenario": scenario,
            "max_layers": max_layers,
            "allowed_layers": allowed,
            "dropped_layers": dropped,
            "budget_bytes": budget_used,
            "always_layers_present": all(l in allowed for l in _ALWAYS_LAYERS),
            "layers_count": len(allowed),
            "emits_act": False,
            "decision_authority": "KX108_ONLY",
            "advisory_only": True,
        }


# ── Module-level instance ─────────────────────────────────────────────────────

_BUDGET = BrodyContextBudget()


def compute_context_budget(
    active_layers: list[str],
    point_cloud: dict | None = None,
    balance_output: dict | None = None,
    is_adversarial: bool = False,
    domain_detected: str | None = None,
    memory_explicit: bool = False,
) -> dict[str, Any]:
    """Convenience function. Never raises. No IO."""
    try:
        return _BUDGET.compute(
            active_layers=active_layers,
            point_cloud=point_cloud,
            balance_output=balance_output,
            is_adversarial=is_adversarial,
            domain_detected=domain_detected,
            memory_explicit=memory_explicit,
        )
    except Exception as e:
        return {
            "budget_version": "V3_BLOCK_2_FALLBACK",
            "scenario": "ERROR",
            "max_layers": _MAX_LAYERS_DEFAULT,
            "allowed_layers": list(_ALWAYS_LAYERS),
            "dropped_layers": [],
            "budget_bytes": _MICRO_CORE_BUDGET,
            "always_layers_present": True,
            "layers_count": len(_ALWAYS_LAYERS),
            "emits_act": False,
            "decision_authority": "KX108_ONLY",
            "advisory_only": True,
            "error": str(e),
        }
