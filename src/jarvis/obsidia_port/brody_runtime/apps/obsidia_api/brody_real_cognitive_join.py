from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from apps.obsidia_api.brody_cognitive_micro_core import run_micro_core
from apps.obsidia_api.brody_existing_reverse_os_bridge import (
    build_existing_reverse_os_projection,
)
from apps.obsidia_api.brody_semantic_query_router import build_semantic_query
from apps.obsidia_api.brody_tree_signal_packet import (
    build_tree_signal_packet as build_brody_tree_signal_packet,
)
from apps.obsidia_api.brody_v1_4_12a_final_answer_adapter import _detect_intent

from periphery.agents.data_purity_agent import run as run_data_purity
from periphery.cognitive_trees.tree_signal_packet import (
    build_tree_signal_packet as build_canonical_tree_signal_packet,
)
from periphery.common import ActionCandidate
from periphery.context.agent_result_cognitive_bridge import (
    enrich_context_packet_v2_with_agent_result,
)
from periphery.context.cognitive_context_to_runtime import (
    build_cognitive_runtime_packet,
)
from periphery.context.cognitive_x108_admission import (
    admit_cognitive_context,
)
from periphery.context.context_packet_builder_v2 import (
    build_context_packet_v2,
)
from periphery.context.sigma_readonly_signal_cognitive_bridge import (
    enrich_context_packet_v2_with_sigma_signal,
)
from periphery.context.tree_signal_cognitive_bridge import (
    enrich_context_packet_v2_with_tree_signal,
)
from sigma.evaluate import evaluate_sigma_domain
from sigma.sigma_readonly_signal import build_sigma_readonly_signal

try:
    from scripts.obsidia_readonly_pc_context_adapter_v0 import (
        readonly_pc_context_to_context_item,
    )
except Exception:
    readonly_pc_context_to_context_item = None


VERSION = "REAL_COGNITIVE_JOIN_C1_V1"
RAIL_MODE = "SHADOW_READONLY_SUPERPOSED"
TREE_PROVENANCE = "HEURISTIC_TEXT_DERIVED"

SUPPORTED_SIGMA_DOMAINS = {
    "bank",
    "trading",
    "ecom",
    "gps_defense_aviation",
}

BOUNDARY = {
    "decision_authority": "KX108_ONLY",
    "readonly": True,
    "advisory_only": True,
    "context_signal_only": True,
    "allowed_to_decide": False,
    "allowed_to_act": False,
    "emits_act": False,
    "emits_verdict": False,
    "memory_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "real_execution": False,
    "response_governance_applied": False,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uniq(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        value = str(value)
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


_SOURCE_ROUTING_REF_LIMIT = 8
_SOURCE_ROUTING_LIST_LIMIT = 8


def _compact_list(values: Any, limit: int = _SOURCE_ROUTING_LIST_LIMIT) -> list[str]:
    if values is None:
        return []
    raw = values if isinstance(values, list) else [values]
    out: list[str] = []
    for value in raw:
        if isinstance(value, dict):
            text = (
                value.get("path")
                or value.get("internal_path")
                or value.get("file_name")
                or value.get("source")
                or value.get("id")
                or ""
            )
        else:
            text = value
        item = str(text).strip()
        if item and item not in out:
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _compact_selected_path(path: Any) -> dict[str, Any]:
    if not isinstance(path, dict):
        return {}
    return {
        "modules": _compact_list(path.get("modules")),
        "adapters": _compact_list(path.get("adapters")),
        "routes": _compact_list(path.get("routes")),
        "source_families": _compact_list(path.get("source_families")),
        "source_subfamilies": _compact_list(path.get("source_subfamilies")),
        "evidence_packs": _compact_list(path.get("evidence_packs")),
        "x108_decision": str(path.get("x108_decision") or ""),
    }


def _source_routing_projection(
    source_pack_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compact already-built source-pack routing for C1; never hydrates or reads."""
    if not isinstance(source_pack_context, dict) or not source_pack_context:
        return {
            "status": "UNAVAILABLE",
            "applied": False,
            "reason": "NO_SOURCE_PACK_CONTEXT",
            "readonly": True,
            "advisory_only": True,
            "source_context_authority": "NONE",
            "source_context_mode": "ADVISORY_ONLY",
            "memory_write": False,
            "emits_act": False,
        }

    x108_decision = str(
        source_pack_context.get("x108_decision")
        or source_pack_context.get("x108_decision_path")
        or ""
    )
    used = bool(source_pack_context.get("source_pack_context_used"))
    admitted = used and x108_decision == "ALLOW_CONTEXT_ONLY"

    selected_path = _compact_selected_path(
        source_pack_context.get("selected_runtime_path")
    )
    families = _compact_list(
        source_pack_context.get("selected_source_families")
        or source_pack_context.get("source_pack_families")
        or selected_path.get("source_families")
    )
    subfamilies = _compact_list(
        source_pack_context.get("selected_source_subfamilies")
        or selected_path.get("source_subfamilies")
    )
    evidence_packs = _compact_list(
        source_pack_context.get("selected_evidence_packs")
        or selected_path.get("evidence_packs")
    )
    refs = _compact_list(
        source_pack_context.get("source_file_refs"),
        limit=_SOURCE_ROUTING_REF_LIMIT,
    )
    summary = str(
        source_pack_context.get("context_summary_for_brody")
        or source_pack_context.get("source_pack_context_summary")
        or ""
    )

    material_basis = {
        "families": families,
        "subfamilies": subfamilies,
        "evidence_packs": evidence_packs,
        "refs": refs,
        "x108_decision": x108_decision,
    }
    material_key = hashlib.sha256(
        json.dumps(material_basis, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

    return {
        "status": (
            "READY:SOURCE_ROUTING_ADVISORY"
            if admitted
            else "SKIPPED_SOURCE_CONTEXT_NOT_ADMITTED"
        ),
        "applied": admitted,
        "source_pack_context_used": used,
        "x108_decision": x108_decision,
        "x108_gate_status": str(
            source_pack_context.get("x108_gate_status") or ""
        ),
        "source_context_authority": "NONE",
        "source_context_mode": "ADVISORY_ONLY",
        "readonly": True,
        "advisory_only": True,
        "allow_context_only": admitted,
        "selected_runtime_path": selected_path,
        "detected_intents": _compact_list(
            source_pack_context.get("detected_intents")
        ),
        "required_capabilities": _compact_list(
            source_pack_context.get("required_capabilities")
        ),
        "selected_source_families": families,
        "selected_source_subfamilies": subfamilies,
        "selected_evidence_packs": evidence_packs,
        "source_refs": refs,
        "source_refs_count": len(refs),
        "summary_available": bool(summary.strip()),
        "summary_char_count": len(summary),
        "entries_used": int(
            source_pack_context.get("source_pack_entries_used") or 0
        ),
        "material_key": material_key,
        "unique_role": "SOURCE_SELECTION_ROUTING_PROVENANCE",
        "overlaps_native_memory": False,
        "overlaps_reverse_os": bool(
            set(families) & {"OS_TRAD_REVERSE_OS"}
        ),
        "overlaps_tree_34d": bool(
            set(families) & {"OS_TRAD_REVERSE_OS"}
        ),
        "memory_write": False,
        "emits_act": False,
        "raw_content_included": False,
    }


def _asdict(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value


def _error(stage: str, exc: Exception) -> str:
    return f"{stage}:DEGRADED:{type(exc).__name__}:{str(exc)[:240]}"


def _signal_id(message: str, session_id: str) -> str:
    raw = f"{session_id}|{message}".encode("utf-8", errors="replace")
    return "cog-" + hashlib.sha256(raw).hexdigest()[:20]


def _normalize_domain(raw: Any) -> str | None:
    if raw is None:
        return None
    if hasattr(raw, "value"):
        raw = raw.value

    value = str(raw).strip().lower()
    if value.startswith("domain."):
        value = value.split(".", 1)[1]

    aliases = {
        "gps": "gps_defense_aviation",
        "gps_defense": "gps_defense_aviation",
        "aviation": "gps_defense_aviation",
        "ecommerce": "ecom",
        "e-commerce": "ecom",
    }
    value = aliases.get(value, value)
    return value or None


def _extract_activations(wrapper: dict[str, Any]) -> list[float]:
    packet = wrapper.get("tree_signal_packet", wrapper)
    if not isinstance(packet, dict):
        raise TypeError("TREE_WRAPPER_PACKET_NOT_DICT")

    vector = packet.get("activation_vector", {})
    if not isinstance(vector, dict):
        raise TypeError("TREE_ACTIVATION_VECTOR_NOT_DICT")

    activations = vector.get("activations")
    if not isinstance(activations, list):
        raise TypeError("TREE_ACTIVATIONS_NOT_LIST")
    if len(activations) != 34:
        raise ValueError(
            f"TREE_ACTIVATIONS_LENGTH_EXPECTED_34_GOT_{len(activations)}"
        )

    return [float(x) for x in activations]


def _micro_context(
    micro: dict[str, Any],
) -> tuple[list[str], list[str]]:
    risk_flags: list[str] = []
    unknowns: list[str] = []

    if bool(micro.get("is_adversarial")):
        risk_flags.append("MICRO_CORE:ADVERSARIAL")

    if bool(micro.get("hold_required")):
        risk_flags.append("MICRO_CORE:HOLD_REQUIRED")

    if bool(micro.get("survival_risk_flag")):
        risk_flags.append("MICRO_CORE:SURVIVAL_RISK")

    projection = micro.get("projection_not_prediction_signal", {})
    if isinstance(projection, dict) and bool(
        projection.get("is_prediction_claim")
    ):
        risk_flags.append("MICRO_CORE:PREDICTION_CLAIM")

    bio = micro.get("bio_animal_signal", {})
    if isinstance(bio, dict):
        dead_paths = bio.get("dead_path_detection", [])
        if isinstance(dead_paths, list):
            unknowns.extend(
                f"MICRO_DEAD_PATH:{item}" for item in dead_paths
            )

    return _uniq(risk_flags), _uniq(unknowns)


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return round(float(value), 3)
    return None


def _deep_signal_projection(
    *,
    balance_signal: dict[str, Any] | None = None,
    point_cloud_21d: dict[str, Any] | None = None,
    memzum_activation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    balance = (
        dict(balance_signal)
        if isinstance(balance_signal, dict)
        else {}
    )
    point_cloud = (
        dict(point_cloud_21d)
        if isinstance(point_cloud_21d, dict)
        else {}
    )
    memzum = (
        dict(memzum_activation)
        if isinstance(memzum_activation, dict)
        else {}
    )

    coordinator = (
        balance.get("coordinator", {})
        if isinstance(balance.get("coordinator"), dict)
        else {}
    )
    balances = (
        balance.get("balances", {})
        if isinstance(balance.get("balances"), dict)
        else {}
    )
    balance_memoire = (
        balances.get("balance_memoire", {})
        if isinstance(balances.get("balance_memoire"), dict)
        else {}
    )

    vector = (
        point_cloud.get("vector_21d", {})
        if isinstance(point_cloud.get("vector_21d"), dict)
        else {}
    )
    dominant_axes = point_cloud.get("dominant_axes", [])
    active_layers = point_cloud.get("active_layers", [])
    forbidden_layers = point_cloud.get("forbidden_layers", [])

    activation_basis = (
        memzum.get("activation_basis", {})
        if isinstance(memzum.get("activation_basis"), dict)
        else {}
    )

    available = {
        "balance": bool(balance),
        "point_cloud_21d": bool(point_cloud),
        "memzum": bool(memzum),
    }

    return {
        "status": (
            "READY:PRECOMPUTED"
            if any(available.values())
            else "SKIPPED_OPTIONAL_NOT_PROVIDED"
        ),
        "available": available,
        "balance_snapshot": {
            "role": "WEIGHTING_COGNITIVE_STATE",
            "version": balance.get("balance_engine_version"),
            "balances_count": balance.get("balances_count"),
            "dominant_balance": coordinator.get("dominant_balance"),
            "top3_balances": coordinator.get("top3_balances", []),
            "layers_to_activate": coordinator.get(
                "layers_to_activate",
                [],
            ),
            "layers_to_avoid": coordinator.get("layers_to_avoid", []),
            "balance_risk_level": _as_float(
                coordinator.get("balance_risk_level")
            ),
            "balance_memoire_tension": _as_float(
                balance_memoire.get("tension")
            ),
            "advisory_only": True,
            "decision_authority": "KX108_ONLY",
        },
        "point_cloud_21d_snapshot": {
            "role": "SELECTION_COGNITIVE_POSITION_GATING",
            "version": point_cloud.get("selector_version"),
            "dimensions": point_cloud.get("dimensions"),
            "dominant_axes": (
                list(dominant_axes)
                if isinstance(dominant_axes, list)
                else []
            ),
            "active_layers": (
                list(active_layers)
                if isinstance(active_layers, list)
                else []
            ),
            "forbidden_layers": (
                list(forbidden_layers)
                if isinstance(forbidden_layers, list)
                else []
            ),
            "memory_packet_required": bool(
                point_cloud.get("memory_packet_required", False)
            ),
            "domain_packet_required": bool(
                point_cloud.get("domain_packet_required", False)
            ),
            "compact_vector_21d": {
                str(key): _as_float(value)
                for key, value in vector.items()
                if _as_float(value) is not None
            },
            "advisory_only": True,
            "decision_authority": "KX108_ONLY",
        },
        "memzum_activation_snapshot": {
            "role": "MEMORY_GATE_CONTEXT_PROVENANCE",
            "module": memzum.get("module"),
            "version": memzum.get("version"),
            "status": memzum.get("status"),
            "memory_required": bool(memzum.get("memory_required", False)),
            "reason": memzum.get("reason"),
            "activation_basis": {
                "memory_packet_required": bool(
                    activation_basis.get(
                        "memory_packet_required",
                        False,
                    )
                ),
                "axis_13_memory": _as_float(
                    activation_basis.get("axis_13_memory")
                ),
                "memory_relevance_signal": _as_float(
                    activation_basis.get(
                        "memory_relevance_signal"
                    )
                ),
                "balance_memoire_tension": _as_float(
                    activation_basis.get(
                        "balance_memoire_tension"
                    )
                ),
                "domain_detected": activation_basis.get(
                    "domain_detected"
                ),
                "intent_type": activation_basis.get("intent_type"),
                "is_adversarial": bool(
                    activation_basis.get("is_adversarial", False)
                ),
            },
            "advisory_only": True,
            "memory_write": False,
            "decision_authority": "KX108_ONLY",
        },
        "readonly": True,
        "context_signal_only": True,
        "allowed_to_decide": False,
        "allowed_to_act": False,
        "memory_write": False,
        "emits_act": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }


def _tree_34d_projection(
    *,
    tree_wrapper: dict[str, Any] | None = None,
    canonical_tree: dict[str, Any] | None = None,
    tree_provenance: str = TREE_PROVENANCE,
    computation_mode: str = "UNAVAILABLE",
) -> dict[str, Any]:
    wrapper = (
        dict(tree_wrapper)
        if isinstance(tree_wrapper, dict)
        else {}
    )
    packet = wrapper.get("tree_signal_packet", wrapper)
    if not isinstance(packet, dict):
        packet = {}

    canonical = (
        dict(canonical_tree)
        if isinstance(canonical_tree, dict)
        else {}
    )

    activation_vector = (
        packet.get("activation_vector", {})
        if isinstance(packet.get("activation_vector"), dict)
        else {}
    )
    activations = activation_vector.get("activations", [])
    vector_34d = [
        _as_float(value)
        for value in activations
        if _as_float(value) is not None
    ] if isinstance(activations, list) else []

    dominant_wrapper = (
        packet.get("dominant_trees", {})
        if isinstance(packet.get("dominant_trees"), dict)
        else {}
    )
    dominant_ids_source = (
        canonical.get("dominant_ids")
        if isinstance(canonical.get("dominant_ids"), list)
        else dominant_wrapper.get("dominant_ids")
    )
    dominant_ids = (
        list(dominant_ids_source)
        if isinstance(dominant_ids_source, list)
        else []
    )
    dominant_tree_ids = [dim + 1 for dim in dominant_ids if isinstance(dim, int)]
    dominant_names_source = (
        canonical.get("dominant_trees")
        if isinstance(canonical.get("dominant_trees"), list)
        else dominant_wrapper.get("dominant_trees")
    )
    dominant_names = (
        list(dominant_names_source)
        if isinstance(dominant_names_source, list)
        else []
    )
    dominant_weights = {
        str(dim + 1): vector_34d[dim]
        for dim in dominant_ids
        if isinstance(dim, int)
        and 0 <= dim < len(vector_34d)
    }

    shazam = (
        packet.get("shazam", {})
        if isinstance(packet.get("shazam"), dict)
        else {
            "patterns_detected": canonical.get(
                "patterns_detected",
                [],
            ),
            "context_signal_only": canonical.get(
                "context_signal_only",
                True,
            ),
            "can_decide": canonical.get("can_decide", False),
            "can_emit_act": canonical.get("can_emit_act", False),
        }
    )
    memory_world = (
        packet.get("memory_world", {})
        if isinstance(packet.get("memory_world"), dict)
        else {
            "active_domains": canonical.get("active_domains", []),
            "memory_relevance": canonical.get("memory_relevance"),
            "world_relevance": canonical.get("world_relevance"),
            "context_signal_only": canonical.get(
                "context_signal_only",
                True,
            ),
            "can_decide": canonical.get("can_decide", False),
            "can_emit_act": canonical.get("can_emit_act", False),
        }
    )
    metrics = (
        packet.get("metrics", {})
        if isinstance(packet.get("metrics"), dict)
        else {}
    )

    vector_available = len(vector_34d) == 34
    shazam_patterns = (
        list(shazam.get("patterns_detected", []))
        if isinstance(shazam.get("patterns_detected"), list)
        else []
    )
    active_domains = (
        list(memory_world.get("active_domains", []))
        if isinstance(memory_world.get("active_domains"), list)
        else []
    )

    return {
        "status": (
            "READY:COMPACT_34D"
            if vector_available
            else "UNAVAILABLE"
        ),
        "role": "CONTEXT_WEIGHTING_COGNITIVE_ORIENTATION",
        "version": packet.get("version") or canonical.get("version"),
        "provenance": tree_provenance,
        "computation_mode": computation_mode,
        "tree_count": packet.get("tree_count") or 34,
        "vector_length": len(vector_34d),
        "activation_vector_34d": vector_34d,
        "tree_order": "canonical_tree_registry_id_1_to_34",
        "dominant_state": {
            "dominant_ids_0_based": dominant_ids,
            "dominant_tree_ids": dominant_tree_ids,
            "dominant_tree_names": dominant_names,
            "dominant_count": (
                canonical.get("dominant_count")
                if canonical.get("dominant_count") is not None
                else dominant_wrapper.get("dominant_count")
            ),
            "dominant_weights": dominant_weights,
            "theta": dominant_wrapper.get("theta") or packet.get("theta"),
        },
        "shazam_state": {
            "available": bool(shazam),
            "patterns_detected": shazam_patterns,
            "pattern_count": len(shazam_patterns),
            "context_signal_only": bool(
                shazam.get("context_signal_only", True)
            ),
            "can_decide": bool(shazam.get("can_decide", False)),
            "can_emit_act": bool(shazam.get("can_emit_act", False)),
        },
        "memory_world_context": {
            "available": bool(memory_world),
            "active_domains": active_domains,
            "memory_relevance": _as_float(
                memory_world.get("memory_relevance")
            ),
            "world_relevance": _as_float(
                memory_world.get("world_relevance")
            ),
            "context_signal_only": bool(
                memory_world.get("context_signal_only", True)
            ),
            "can_decide": bool(memory_world.get("can_decide", False)),
            "can_emit_act": bool(memory_world.get("can_emit_act", False)),
        },
        "metrics": {
            "activation_sum": _as_float(metrics.get("activation_sum")),
            "activation_density": _as_float(
                metrics.get("activation_density")
            ),
            "memory_relevance": _as_float(
                metrics.get("memory_relevance")
            ),
            "world_relevance": _as_float(
                metrics.get("world_relevance")
            ),
        },
        "readonly": True,
        "context_signal_only": True,
        "advisory_only": True,
        "allowed_to_decide": False,
        "allowed_to_act": False,
        "memory_write": False,
        "emits_act": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }


def _blocked_receipt(
    *,
    signal_id: str,
    components: dict[str, str],
    errors: list[str],
    stage: str,
) -> dict[str, Any]:
    return {
        "version": VERSION,
        "rail_mode": RAIL_MODE,
        "signal_id": signal_id,
        "created_at": _now(),
        "status": "BLOCKED_READONLY",
        "completeness": "BLOCKED",
        "blocked_stage": stage,
        "errors": list(errors),
        "components": dict(components),
        "tree_provenance": TREE_PROVENANCE,
        "kx108_admission": "DRY_RUN_NOT_COMPLETED",
        **BOUNDARY,
    }


def run_real_cognitive_join(
    *,
    message: str,
    language: str = "fr",
    session_id: str = "local",
    precomputed_micro_core: dict[str, Any] | None = None,
    precomputed_semantic_query: dict[str, Any] | None = None,
    precomputed_intent: str | None = None,
    authority_snapshot: dict[str, Any] | None = None,
    tree_policy_snapshot: dict[str, Any] | None = None,
    precomputed_reverse_os: dict[str, Any] | None = None,
    precomputed_tree_wrapper: dict[str, Any] | None = None,
    precomputed_brody_runtime: dict[str, Any] | None = None,
    precomputed_memory_chain: dict[str, Any] | None = None,
    precomputed_balance_signal: dict[str, Any] | None = None,
    precomputed_point_cloud_21d: dict[str, Any] | None = None,
    precomputed_memzum_activation: dict[str, Any] | None = None,
    precomputed_model_evidence: dict[str, Any] | None = None,
    precomputed_source_pack_context: dict[str, Any] | None = None,
    precomputed_readonly_pc_context: dict[str, Any] | None = None,
) -> dict[str, Any]:

    signal_id = _signal_id(message, session_id)
    errors: list[str] = []

    components: dict[str, str] = {
        "LANGUAGE": "READY:REQUEST_LANGUAGE",
        "SEMANTIC_QUERY": "PENDING",
        "INTENT": "PENDING",
        "MICRO_CORE": "PENDING",
        "DEEP_COGNITIVE_SIGNALS": "PENDING",
        "REVERSE_OS": "PENDING",
        "TREE_34D_SHAZAM_MEMORY_WORLD": "PENDING",
        "SOURCE_ROUTING": "SKIPPED_OPTIONAL_NOT_PROVIDED",
        "READONLY_PC_CONTEXT": "SKIPPED_OPTIONAL_NOT_PROVIDED",
        "SIGMA": "PENDING",
        "DATA_PURITY_AGENT": "PENDING",
        "CONTEXT_PACKET_V2": "PENDING",
        "W1_RUNTIME_JOIN": "PENDING",
        "W2_X108_ADMISSION": "PENDING",
        "W3_BRODY": (
            "SKIPPED_BY_PATH_POLICY:"
            "NO_PRECOMPUTED_BRODY_RUNTIME"
        ),
        "W4_MEMORY_RETRIEVAL": (
            "SKIPPED_BY_PATH_POLICY:"
            "MEMORY_RETRIEVAL_NOT_PRECOMPUTED"
        ),
        "W4B_LOCAL_MODEL_EVIDENCE": (
            "SKIPPED_BY_PATH_POLICY:"
            "MODEL_EVIDENCE_NOT_PRECOMPUTED"
        ),
        "NPL": "SKIPPED_NOT_AVAILABLE:NPL_RUNTIME_NOT_MATERIALIZED",
        "LYAPUNOV": (
            "SKIPPED_NOT_AVAILABLE:"
            "NO_STRUCTURED_METRICS_FROM_UPSTREAM"
        ),
    }

    # --------------------------------------------------------
    # 1 — Semantic query
    # --------------------------------------------------------
    semantic: dict[str, Any] = {}

    try:
        if isinstance(precomputed_semantic_query, dict):
            semantic = dict(precomputed_semantic_query)
            components["SEMANTIC_QUERY"] = "READY:PRECOMPUTED"
        else:
            semantic = build_semantic_query(message)
            components["SEMANTIC_QUERY"] = "READY:DERIVED_NOW"
    except Exception as exc:
        errors.append(_error("SEMANTIC_QUERY", exc))
        components["SEMANTIC_QUERY"] = errors[-1]
        semantic = {}

    # --------------------------------------------------------
    # 2 — Canonical intent
    # --------------------------------------------------------
    intent = "unknown"

    try:
        if precomputed_intent:
            intent = str(precomputed_intent)
            components["INTENT"] = "READY:PRECOMPUTED"
        else:
            intent = str(_detect_intent(message))
            components["INTENT"] = "READY:DERIVED_NOW"
    except Exception as exc:
        errors.append(_error("INTENT", exc))
        components["INTENT"] = errors[-1]

    # --------------------------------------------------------
    # 3 — Micro core
    # --------------------------------------------------------
    micro: dict[str, Any] = {}

    try:
        if isinstance(precomputed_micro_core, dict):
            micro = dict(precomputed_micro_core)
            components["MICRO_CORE"] = "READY:PRECOMPUTED"
        else:
            micro = run_micro_core(
                message,
                session_id=session_id,
                language=language,
            )
            components["MICRO_CORE"] = "READY:DERIVED_NOW"
    except Exception as exc:
        errors.append(_error("MICRO_CORE", exc))
        components["MICRO_CORE"] = errors[-1]
        micro = {}

    micro_risks, micro_unknowns = _micro_context(micro)

    deep_cognitive_signal = _deep_signal_projection(
        balance_signal=precomputed_balance_signal,
        point_cloud_21d=precomputed_point_cloud_21d,
        memzum_activation=precomputed_memzum_activation,
    )
    components["DEEP_COGNITIVE_SIGNALS"] = (
        deep_cognitive_signal.get("status")
        if isinstance(deep_cognitive_signal, dict)
        else "SKIPPED_OPTIONAL_NOT_PROVIDED"
    )

    # --------------------------------------------------------
    # 4 — Reverse OS
    #
    # Production-faithful C1:
    # current product builds Reverse OS before tree packet and
    # supplies tree_signal_packet={}. Do not fabricate a future
    # semantic 34D producer here.
    # --------------------------------------------------------
    reverse_os: dict[str, Any] = {}

    try:
        if isinstance(precomputed_reverse_os, dict):
            reverse_os = dict(precomputed_reverse_os)
            components["REVERSE_OS"] = "READY:PRECOMPUTED"
        else:
            reverse_os = build_existing_reverse_os_projection(
                user_message=message,
                intent=intent,
                semantic_query_snapshot=semantic,
                authority_snapshot=authority_snapshot or {},
                tree_signal_packet={},
                tree_policy_snapshot=tree_policy_snapshot or {},
            )
            components["REVERSE_OS"] = "READY:DERIVED_NOW"
    except Exception as exc:
        errors.append(_error("REVERSE_OS", exc))
        components["REVERSE_OS"] = errors[-1]
        reverse_os = {}

    ir_candidate = (
        reverse_os.get("ir_candidate", {})
        if isinstance(reverse_os, dict)
        else {}
    )

    ir_risks: list[str] = []
    ir_unknowns: list[str] = []
    ir_contradictions: list[str] = []

    if isinstance(ir_candidate, dict):
        if isinstance(ir_candidate.get("risk_flags"), list):
            ir_risks = list(ir_candidate["risk_flags"])
        if isinstance(ir_candidate.get("unknowns"), list):
            ir_unknowns = list(ir_candidate["unknowns"])
        if isinstance(ir_candidate.get("contradictions"), list):
            ir_contradictions = list(ir_candidate["contradictions"])

    # --------------------------------------------------------
    # 5 — Existing Brody tree wrapper
    #     provenance remains HEURISTIC_TEXT_DERIVED in C1.
    # --------------------------------------------------------
    tree_wrapper: dict[str, Any] = {}
    tree_computation_mode = "DERIVED_NOW"
    activations: list[float] | None = None

    try:
        if isinstance(precomputed_tree_wrapper, dict):
            tree_wrapper = dict(precomputed_tree_wrapper)
            tree_computation_mode = "PRECOMPUTED"
        else:
            tree_wrapper = build_brody_tree_signal_packet(text=message)

        activations = _extract_activations(tree_wrapper)

    except Exception as exc:
        errors.append(_error("TREE_34D_INPUT", exc))
        components["TREE_34D_SHAZAM_MEMORY_WORLD"] = errors[-1]

    # --------------------------------------------------------
    # 6 — Sigma only when a real supported domain was detected.
    # --------------------------------------------------------
    domain = _normalize_domain(micro.get("domain_detected"))
    sigma_result: dict[str, Any] | None = None
    sigma_signal = None

    if domain is None:
        components["SIGMA"] = (
            "SKIPPED_NOT_AVAILABLE:DOMAIN_NOT_DETECTED"
        )
    elif domain not in SUPPORTED_SIGMA_DOMAINS:
        components["SIGMA"] = (
            f"SKIPPED_NOT_AVAILABLE:UNSUPPORTED_DOMAIN:{domain}"
        )
    else:
        try:
            sigma_result = evaluate_sigma_domain(domain, None)

            contradictions = (
                list(sigma_result.get("contradictions", []))
                if isinstance(
                    sigma_result.get("contradictions", []),
                    list,
                )
                else []
            )

            missing_context = (
                list(sigma_result.get("unknowns", []))
                if isinstance(
                    sigma_result.get("unknowns", []),
                    list,
                )
                else []
            )

            sigma_signal = build_sigma_readonly_signal(
                signal_id=f"{signal_id}:sigma:{domain}",
                contradictions=contradictions,
                proof_status=str(
                    sigma_result.get("proof_status")
                    or "RUNTIME_SIGMA_DOMAIN_READONLY_NOT_LEAN_PROVEN"
                ),
                missing_context=missing_context,
            )

            components["SIGMA"] = f"READY:{domain}"

        except Exception as exc:
            errors.append(_error("SIGMA", exc))
            components["SIGMA"] = errors[-1]

    # --------------------------------------------------------
    # 7 — Canonical formal TreeSignalPacket from the exact
    #     existing 34D activation vector.
    # --------------------------------------------------------
    canonical_tree = None
    canonical_tree_dict: dict[str, Any] = {}

    if activations is not None:
        try:
            canonical_tree = build_canonical_tree_signal_packet(
                signal_id=f"{signal_id}:tree34",
                activations=activations,
                theta=0.15,
                domain_sigma_envelope=sigma_result,
            )

            canonical_tree_dict = canonical_tree.to_dict()

            components["TREE_34D_SHAZAM_MEMORY_WORLD"] = (
                f"READY:{tree_computation_mode}:"
                f"{TREE_PROVENANCE}"
            )

        except Exception as exc:
            errors.append(_error("TREE_CANONICAL", exc))
            components["TREE_34D_SHAZAM_MEMORY_WORLD"] = errors[-1]

    tree_34d_signal = _tree_34d_projection(
        tree_wrapper=tree_wrapper,
        canonical_tree=canonical_tree_dict,
        tree_provenance=TREE_PROVENANCE,
        computation_mode=tree_computation_mode,
    )

    source_routing_signal = _source_routing_projection(
        precomputed_source_pack_context
    )
    if source_routing_signal.get("applied") is True:
        components["SOURCE_ROUTING"] = "READY:PRECOMPUTED:ADVISORY_ONLY"
    elif isinstance(precomputed_source_pack_context, dict):
        components["SOURCE_ROUTING"] = str(
            source_routing_signal.get("status")
            or "SKIPPED_SOURCE_CONTEXT_NOT_ADMITTED"
        )

    # --------------------------------------------------------
    # 8 — Build ContextPacketV2 base
    # --------------------------------------------------------
    semantic_text = (
        semantic.get("semantic_query")
        or semantic.get("primary_query")
        or semantic.get("normalized_message")
        or message
    )

    context_items = [
        f"SEMANTIC:{semantic_text}",
        f"INTENT:{intent}",
        f"MICRO_CORE:{micro.get('micro_core_version', 'UNKNOWN')}",
        f"REVERSE_OS:{reverse_os.get('status', 'UNAVAILABLE')}",
    ]

    if isinstance(deep_cognitive_signal, dict):
        availability = deep_cognitive_signal.get("available", {})
        if isinstance(availability, dict):
            if any(bool(value) for value in availability.values()):
                context_items.extend(
                    [
                        (
                            "BALANCE_STATE_AVAILABLE:"
                            f"{bool(availability.get('balance'))}"
                        ),
                        (
                            "POINT_CLOUD_21D_AVAILABLE:"
                            f"{bool(availability.get('point_cloud_21d'))}"
                        ),
                        (
                            "MEMZUM_STATE_AVAILABLE:"
                            f"{bool(availability.get('memzum'))}"
                        ),
                    ]
                )

        balance_snapshot = deep_cognitive_signal.get(
            "balance_snapshot",
            {},
        )
        if isinstance(balance_snapshot, dict) and availability.get(
            "balance"
        ):
            context_items.append(
                "BALANCE_DOMINANT:"
                f"{balance_snapshot.get('dominant_balance')}"
            )

        point_snapshot = deep_cognitive_signal.get(
            "point_cloud_21d_snapshot",
            {},
        )
        if isinstance(point_snapshot, dict) and availability.get(
            "point_cloud_21d"
        ):
            context_items.append(
                "POINT_CLOUD_21D_SELECTION:"
                f"dimensions={point_snapshot.get('dimensions')};"
                f"active_layers={len(point_snapshot.get('active_layers', []))};"
                f"memory_packet_required="
                f"{bool(point_snapshot.get('memory_packet_required'))}"
            )

        memzum_snapshot = deep_cognitive_signal.get(
            "memzum_activation_snapshot",
            {},
        )
        if isinstance(memzum_snapshot, dict) and availability.get(
            "memzum"
        ):
            context_items.append(
                "MEMZUM_GATE:"
                f"memory_required={bool(memzum_snapshot.get('memory_required'))};"
                f"reason={memzum_snapshot.get('reason')}"
            )

    if isinstance(tree_34d_signal, dict) and tree_34d_signal.get(
        "status"
    ) == "READY:COMPACT_34D":
        dominant_state = tree_34d_signal.get("dominant_state", {})
        shazam_state = tree_34d_signal.get("shazam_state", {})
        memory_world_context = tree_34d_signal.get(
            "memory_world_context",
            {},
        )
        context_items.extend(
            [
                "TREE_34D_STATE_AVAILABLE:True",
                (
                    "TREE_34D_VECTOR_LENGTH:"
                    f"{tree_34d_signal.get('vector_length')}"
                ),
                (
                    "TREE_DOMINANT_STATE_AVAILABLE:"
                    f"{bool(dominant_state)}"
                ),
                (
                    "TREE_DOMINANT_COUNT:"
                    f"{dominant_state.get('dominant_count')}"
                ),
                (
                    "TREE_SHAZAM_STATE_AVAILABLE:"
                    f"{bool(shazam_state.get('available'))}"
                ),
                (
                    "TREE_MEMORY_WORLD_CONTEXT_AVAILABLE:"
                    f"{bool(memory_world_context.get('available'))}"
                ),
            ]
        )

    shazam_dict = (
        canonical_tree_dict.get("shazam", {})
        if isinstance(canonical_tree_dict, dict)
        else {}
    )

    if isinstance(shazam_dict, dict):
        patterns = shazam_dict.get("patterns_detected", [])
        if isinstance(patterns, list):
            context_items.extend(
                f"SHAZAM:{pattern}"
                for pattern in patterns
                if str(pattern).strip()
            )

    source_refs_from_routing: list[str] = []
    if source_routing_signal.get("applied") is True:
        families = source_routing_signal.get("selected_source_families", [])
        subfamilies = source_routing_signal.get(
            "selected_source_subfamilies",
            [],
        )
        evidence_packs = source_routing_signal.get(
            "selected_evidence_packs",
            [],
        )
        context_items.extend(
            [
                "SOURCE_ROUTING_STATE_AVAILABLE:True",
                f"SOURCE_FAMILY_SELECTED:{','.join(families) or 'NONE'}",
                (
                    "SOURCE_SUBFAMILY_SELECTED:"
                    f"{','.join(subfamilies) or 'NONE'}"
                ),
                (
                    "SOURCE_EVIDENCE_PACK_AVAILABLE:"
                    f"{bool(evidence_packs)}"
                ),
                "SOURCE_CONTEXT_ADVISORY_ONLY:True",
                "SOURCE_CONTEXT_AUTHORITY:NONE",
                "SOURCE_X108_MODE:ALLOW_CONTEXT_ONLY",
            ]
        )
        source_refs_from_routing = [
            "brody:source_routing",
            *[
                f"source:{ref}"
                for ref in source_routing_signal.get("source_refs", [])
            ],
        ]

    readonly_pc_context_ref: list[str] = []
    if isinstance(precomputed_readonly_pc_context, dict):
        if precomputed_readonly_pc_context.get("kind") == (
            "READONLY_PC_CONTEXT"
        ):
            readonly_pc_context_item = None
            if readonly_pc_context_to_context_item is not None:
                try:
                    readonly_pc_context_item = (
                        readonly_pc_context_to_context_item(
                            precomputed_readonly_pc_context,
                        )
                    )
                except Exception as exc:
                    errors.append(_error("READONLY_PC_CONTEXT", exc))
            if readonly_pc_context_item:
                context_items.append(readonly_pc_context_item)
                readonly_pc_context_ref = ["jarvis:readonly_pc_context"]
                components["READONLY_PC_CONTEXT"] = (
                    "READY:ADVISORY_ONLY"
                )
            else:
                components["READONLY_PC_CONTEXT"] = "UNAVAILABLE"
        else:
            components["READONLY_PC_CONTEXT"] = (
                "SKIPPED_CONTEXT_KIND_MISMATCH"
            )

    risk_flags = _uniq([
        *micro_risks,
        *ir_risks,
        *[
            f"COGNITIVE_COMPONENT_DEGRADED:{name}"
            for name, status in components.items()
            if str(status).startswith(
                (
                    "SEMANTIC_QUERY:DEGRADED",
                    "INTENT:DEGRADED",
                    "MICRO_CORE:DEGRADED",
                    "REVERSE_OS:DEGRADED",
                    "TREE_34D_INPUT:DEGRADED",
                    "TREE_CANONICAL:DEGRADED",
                )
            )
        ],
    ])

    unknowns = _uniq([
        *micro_unknowns,
        *ir_unknowns,
    ])

    contradictions = _uniq(ir_contradictions)

    try:
        v2 = build_context_packet_v2(
            query=message,
            language=language,
            context_items=context_items,
            source_refs=[
                "brody:semantic_query",
                "brody:micro_core",
                "brody:reverse_os",
                *source_refs_from_routing,
                *readonly_pc_context_ref,
                *(
                    [
                        "brody:tree_34d",
                        "brody:tree_34d:activation_vector",
                        "brody:tree_34d:shazam",
                        "brody:tree_34d:memory_world",
                    ]
                    if tree_34d_signal.get("status")
                    == "READY:COMPACT_34D"
                    else []
                ),
                *(
                    [
                        "brody:balance_engine",
                    ]
                    if deep_cognitive_signal.get(
                        "available",
                        {},
                    ).get("balance")
                    else []
                ),
                *(
                    [
                        "brody:point_cloud_21d",
                    ]
                    if deep_cognitive_signal.get(
                        "available",
                        {},
                    ).get("point_cloud_21d")
                    else []
                ),
                *(
                    [
                        "brody:memzum_activation",
                    ]
                    if deep_cognitive_signal.get(
                        "available",
                        {},
                    ).get("memzum")
                    else []
                ),
            ],
            risk_flags=risk_flags,
            unknowns=unknowns,
            contradictions=contradictions,
            memory_status="CANDIDATE_ONLY",
        )

        components["CONTEXT_PACKET_V2"] = "READY"

    except Exception as exc:
        errors.append(_error("CONTEXT_PACKET_V2", exc))
        components["CONTEXT_PACKET_V2"] = errors[-1]
        return _blocked_receipt(
            signal_id=signal_id,
            components=components,
            errors=errors,
            stage="CONTEXT_PACKET_V2",
        )

    # --------------------------------------------------------
    # C2A - W3 REAL BRODY RESPONSE ENRICHMENT
    #
    # Uses an already-executed Brody runtime result.
    # Never executes Brody a second time.
    # --------------------------------------------------------
    brody_cognitive_response = None

    if isinstance(precomputed_brody_runtime, dict):
        try:
            from apps.obsidia_api.brody_real_response_cognitive_adapter import (
                adapt_real_brody_runtime_to_response,
            )
            from periphery.context.brody_cognitive_bridge import (
                enrich_context_packet_v2_with_brody,
            )

            brody_cognitive_response = (
                adapt_real_brody_runtime_to_response(
                    precomputed_brody_runtime,
                    query=message,
                    language=language,
                )
            )

            v2 = enrich_context_packet_v2_with_brody(
                v2,
                brody_cognitive_response,
            )

            components["W3_BRODY"] = (
                "READY:REAL_RUNTIME_ADAPTER"
            )

        except Exception as exc:
            errors.append(
                _error(
                    "W3_BRODY",
                    exc,
                )
            )
            components["W3_BRODY"] = errors[-1]

    # --------------------------------------------------------
    # C2B-M4B2A - W4 PROVIDER-NEUTRAL MEMORY RETRIEVAL
    #
    # Precomputed retrieval is context evidence only.
    # No retrieval executes here.
    # No memory write.
    # No ACT.
    # No decision authority.
    # --------------------------------------------------------
    memory_retrieval_applied = False
    memory_retrieval_status = None

    if isinstance(
        precomputed_memory_chain,
        dict,
    ):
        try:
            from periphery.context.memory_retrieval_cognitive_bridge import (
                enrich_context_packet_v2_with_memory_retrieval,
            )

            v2 = (
                enrich_context_packet_v2_with_memory_retrieval(
                    v2,
                    precomputed_memory_chain,
                )
            )

            memory_retrieval_status = str(
                precomputed_memory_chain.get(
                    "retrieval_status"
                )
                or precomputed_memory_chain.get(
                    "status"
                )
                or "UNKNOWN"
            )

            components[
                "W4_MEMORY_RETRIEVAL"
            ] = (
                "READY:REAL_RETRIEVAL:"
                f"{memory_retrieval_status}"
            )

            memory_retrieval_applied = True

        except Exception as exc:
            errors.append(
                _error(
                    "W4_MEMORY_RETRIEVAL",
                    exc,
                )
            )

            components[
                "W4_MEMORY_RETRIEVAL"
            ] = errors[-1]

    # --------------------------------------------------------
    # 9 — W5 Tree enrichment
    # --------------------------------------------------------
    # W4B ? provider-neutral model evidence.
    #
    # The model, if any, has already executed elsewhere.
    # This join does not invoke inference.
    # Evidence remains context only; KX108 remains authority.
    model_evidence_applied = False
    model_evidence_status = None

    if isinstance(
        precomputed_model_evidence,
        dict,
    ):
        try:
            from periphery.context.model_evidence_cognitive_bridge import (
                enrich_context_packet_v2_with_model_evidence,
            )

            v2 = (
                enrich_context_packet_v2_with_model_evidence(
                    v2,
                    precomputed_model_evidence,
                )
            )

            model_evidence_status = (
                "ACCEPTED_READONLY_EVIDENCE"
            )

            provider = str(
                precomputed_model_evidence.get(
                    "provider"
                )
                or "UNKNOWN"
            )

            components[
                "W4B_LOCAL_MODEL_EVIDENCE"
            ] = (
                "READY:EVIDENCE:"
                + provider
            )

            model_evidence_applied = True

        except Exception as exc:
            errors.append(
                _error(
                    "W4B_LOCAL_MODEL_EVIDENCE",
                    exc,
                )
            )

            components[
                "W4B_LOCAL_MODEL_EVIDENCE"
            ] = errors[-1]

    if canonical_tree is not None:
        try:
            v2 = enrich_context_packet_v2_with_tree_signal(
                v2,
                canonical_tree,
            )
        except Exception as exc:
            errors.append(_error("W5_TREE_BRIDGE", exc))
            components["TREE_34D_SHAZAM_MEMORY_WORLD"] = errors[-1]

    # --------------------------------------------------------
    # 10 — W6b Sigma enrichment
    # --------------------------------------------------------
    if sigma_signal is not None:
        try:
            v2 = enrich_context_packet_v2_with_sigma_signal(
                v2,
                sigma_signal,
            )
        except Exception as exc:
            errors.append(_error("W6B_SIGMA_BRIDGE", exc))
            components["SIGMA"] = errors[-1]

    # --------------------------------------------------------
    # 11 — C8: ONLY DATA_PURITY_AGENT in C1.
    # --------------------------------------------------------
    agent_result = None

    try:
        action = ActionCandidate(
            action_id=f"{signal_id}:data-purity",
            domain=domain or "cognitive_context",
            actor_id="BRODY_COGNITIVE_RUNTIME",
            intent=intent,
            action_type="COGNITIVE_CONTEXT_BUILD",
            irreversible=False,
            timestamp_plan=_now(),
            timestamp_exec=None,
            payload={},
        )

        agent_result = run_data_purity(action)

        v2 = enrich_context_packet_v2_with_agent_result(
            v2,
            agent_result,
        )

        components["DATA_PURITY_AGENT"] = "READY"

    except Exception as exc:
        errors.append(_error("DATA_PURITY_AGENT", exc))
        components["DATA_PURITY_AGENT"] = errors[-1]

    # --------------------------------------------------------
    # 12 — W1 canonical join
    # --------------------------------------------------------
    try:
        runtime_packet = build_cognitive_runtime_packet(
            v2,
            signal_id,
        )
        components["W1_RUNTIME_JOIN"] = "READY"

    except Exception as exc:
        errors.append(_error("W1_RUNTIME_JOIN", exc))
        components["W1_RUNTIME_JOIN"] = errors[-1]

        return _blocked_receipt(
            signal_id=signal_id,
            components=components,
            errors=errors,
            stage="W1_RUNTIME_JOIN",
        )

    # --------------------------------------------------------
    # 13 — W2 X108 dry-run admission
    # --------------------------------------------------------
    critical_action_requested = bool(
        micro.get("hold_required", False)
    )

    try:
        ticket = admit_cognitive_context(
            v2,
            signal_id,
            critical_action_requested=critical_action_requested,
        )
        components["W2_X108_ADMISSION"] = "READY:DRY_RUN"

    except Exception as exc:
        errors.append(_error("W2_X108_ADMISSION", exc))
        components["W2_X108_ADMISSION"] = errors[-1]

        return _blocked_receipt(
            signal_id=signal_id,
            components=components,
            errors=errors,
            stage="W2_X108_ADMISSION",
        )

    # Known C1 missing surfaces mean this is deliberately DEGRADED,
    # even when every currently materialized join component succeeded.
    unavailable = any(
        status.startswith("SKIPPED_NOT_AVAILABLE")
        for status in components.values()
    )

    completeness = (
        "DEGRADED"
        if unavailable or errors
        else "COMPLETE"
    )

    return {
        "version": VERSION,
        "rail_mode": RAIL_MODE,
        "signal_id": signal_id,
        "created_at": _now(),
        "status": "READY_SHADOW_READONLY",
        "completeness": completeness,

        "language": language,
        "semantic_query_snapshot": semantic,
        "intent": intent,
        "micro_core_trace": micro,
        "deep_cognitive_signal_snapshot": deep_cognitive_signal,
        "source_routing_signal_snapshot": source_routing_signal,
        "reverse_os_projection": reverse_os,

        "domain_detected": domain,

        "tree_provenance": TREE_PROVENANCE,
        "tree_computation_mode": tree_computation_mode,
        "tree_34d_signal_snapshot": tree_34d_signal,
        "brody_tree_signal_packet": tree_wrapper,
        "canonical_tree_signal_packet": canonical_tree_dict,

        "brody_cognitive_response": (
            brody_cognitive_response.to_dict()
            if brody_cognitive_response is not None
            else None
        ),

        "memory_response_chain_snapshot": (
            precomputed_memory_chain
            if isinstance(
                precomputed_memory_chain,
                dict,
            )
            else None
        ),

        "memory_retrieval_applied": (
            memory_retrieval_applied
        ),

        "memory_retrieval_status": (
            memory_retrieval_status
        ),

        "local_model_evidence_snapshot": (
            precomputed_model_evidence
            if isinstance(
                precomputed_model_evidence,
                dict,
            )
            else None
        ),

        "local_model_evidence_applied": (
            model_evidence_applied
        ),

        "local_model_evidence_status": (
            model_evidence_status
        ),

        "readonly_pc_context": (
            precomputed_readonly_pc_context
            if isinstance(
                precomputed_readonly_pc_context,
                dict,
            )
            else None
        ),

        "sigma_domain_packet": sigma_result,
        "sigma_readonly_signal": (
            _asdict(sigma_signal)
            if sigma_signal is not None
            else None
        ),

        "data_purity_agent_result": (
            _asdict(agent_result)
            if agent_result is not None
            else None
        ),

        "context_packet_v2": v2.to_dict(),
        "w1_runtime_context_packet": _asdict(runtime_packet),

        "critical_action_requested": critical_action_requested,

        "kx108_admission": "DRY_RUN",
        "decision_ticket_dry_run": _asdict(ticket),

        "components": components,
        "errors": errors,

        **BOUNDARY,
    }


__all__ = [
    "run_real_cognitive_join",
    "VERSION",
    "RAIL_MODE",
    "TREE_PROVENANCE",
    "BOUNDARY",
]
