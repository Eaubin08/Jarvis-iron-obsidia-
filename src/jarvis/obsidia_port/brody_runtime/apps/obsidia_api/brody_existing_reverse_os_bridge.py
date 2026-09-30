"""F18B — existing Reverse OS / IR readonly bridge.

This module adapts the already-existing Reverse OS source:
- repo periphery/reverse_os.py
- logic aligned with obsidia-engine-candidate/bridge/zip2_reverse_os_real_adapter.py

No decision. No ACT. No write. No mutation.
"""
from __future__ import annotations

import importlib.util
import hashlib
from pathlib import Path
from typing import Any

from periphery.language.lexical_calibrator import calibrate_lexical_knownness


ROOT = Path(__file__).resolve().parents[2]
REPO_REVERSE_OS = ROOT / "periphery" / "reverse_os.py"


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest()


def _tree_vector_from_runtime(
    *,
    tree_signal_packet: dict[str, Any] | None = None,
    tree_policy_snapshot: dict[str, Any] | None = None,
) -> dict[str, float]:
    vector = {f"TREE_{i:02d}": 0.0 for i in range(1, 35)}

    tree_signal_packet = tree_signal_packet or {}
    tree_policy_snapshot = tree_policy_snapshot or {}

    dom = (
        tree_signal_packet.get("dominant_trees", {})
        if isinstance(tree_signal_packet.get("dominant_trees"), dict)
        else {}
    )
    ids = dom.get("dominant_ids", [])
    if isinstance(ids, list):
        for tid in ids:
            try:
                i = int(tid)
                if 1 <= i <= 34:
                    vector[f"TREE_{i:02d}"] = 1.0
            except Exception:
                pass

    safe_trees = (
        tree_policy_snapshot.get("tree_policy", {}).get("safe_trees", [])
        if isinstance(tree_policy_snapshot.get("tree_policy"), dict)
        else []
    )
    if isinstance(safe_trees, list):
        for raw in safe_trees:
            try:
                s = str(raw)
                if s.startswith("TREE_"):
                    key = s
                else:
                    key = f"TREE_{int(s):02d}"
                if key in vector:
                    vector[key] = max(vector[key], 0.5)
            except Exception:
                pass

    return vector


def build_existing_reverse_flow(
    *,
    user_message: str,
    intent: str,
    semantic_query_snapshot: dict[str, Any] | None = None,
    authority_snapshot: dict[str, Any] | None = None,
    tree_signal_packet: dict[str, Any] | None = None,
    tree_policy_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    semantic_query_snapshot = semantic_query_snapshot or {}
    authority_snapshot = authority_snapshot or {}

    request_type = authority_snapshot.get("request_type", "PURE_RESPONSE")
    requires_x108 = request_type != "PURE_RESPONSE" or intent in {"action_request", "creator_claim"}

    reason_code = "RC_X108_REQUIRED" if requires_x108 else "RC_CONTEXT_ONLY"
    verdict_marker = "NO_DECISION_X108_REQUIRED" if requires_x108 else "NO_DECISION_CONTEXT_ONLY"

    return {
        "agent_name": "BRODY_REVERSE_OS_SSR_REAL_BRIDGE",
        "reason_code": reason_code,
        "merkle_root": _hash_text(user_message),
        "verdict": verdict_marker,
        "tree_vector": _tree_vector_from_runtime(
            tree_signal_packet=tree_signal_packet,
            tree_policy_snapshot=tree_policy_snapshot,
        ),
        "input": {
            "semantic_query": semantic_query_snapshot.get("semantic_query") or semantic_query_snapshot.get("primary_query"),
            "topic": semantic_query_snapshot.get("topic"),
            "request_type": request_type,
            "intent": intent,
        },
        "non_decision": True,
        "decision_authority": "KX108_ONLY",
    }


def build_existing_ir_candidate(
    *,
    user_message: str,
    intent: str,
    semantic_query_snapshot: dict[str, Any] | None = None,
    authority_snapshot: dict[str, Any] | None = None,
    reverse_flow: dict[str, Any] | None = None,
) -> dict[str, Any]:
    semantic_query_snapshot = semantic_query_snapshot or {}
    authority_snapshot = authority_snapshot or {}
    reverse_flow = reverse_flow or {}

    msg = (user_message or "").lower()

    entities = []
    for token, entity in [
        ("graphiti", "GRAPHITI"),
        ("memory", "MEMORY"),
        ("mémoire", "MEMORY"),
        ("memoire", "MEMORY"),
        ("canon", "CANON"),
        ("freeze", "FREEZE"),
        ("x108", "X108"),
        ("kernel", "KERNEL"),
        ("noyau", "KERNEL"),
        ("ir", "IR"),
        ("reverse", "REVERSE_OS"),
        ("trad", "OS_TRAD"),
    ]:
        if token in msg and entity not in [e.get("entity") for e in entities]:
            entities.append({"entity": entity, "source_token": token, "readonly": True})

    constraints = [
        {"constraint": "Decision = KX108", "reason": "sovereign_decision_law"},
        {"constraint": "READONLY_ONLY", "reason": "brody_runtime_boundary"},
        {"constraint": "NO_ACT", "reason": "brody_emits_act_false"},
        {"constraint": "NO_MEMORY_WRITE", "reason": "memory_write_false"},
        {"constraint": "NO_KERNEL_MUTATION", "reason": "kernel_mutation_false"},
        {"constraint": "NO_X108_MUTATION", "reason": "x108_mutation_false"},
    ]

    if reverse_flow.get("reason_code") == "RC_X108_REQUIRED":
        constraints.append({"constraint": "X108_REQUIRED_FOR_DECISION", "reason": "reverse_flow_reason_code"})

    contradictions = []
    if intent == "action_request" or authority_snapshot.get("request_type") != "PURE_RESPONSE":
        contradictions.append("REQUEST_REQUIRES_ACTION_OR_WRITE_BUT_ROUTE_IS_READONLY")

    lexical_calibration = calibrate_lexical_knownness(
        user_message,
        "unknown",
    )

    return {
        "status": "IR_CANDIDATE_EXISTING_REVERSE_OS_BRIDGE_PASS",
        "source": "BRODY_EXISTING_REVERSE_OS_IR_BRIDGE_V1",
        "ir_kind": "OBSIDIA_IR_CANDIDATE_READONLY",
        "intent_type": intent,
        "semantic_query": semantic_query_snapshot.get("semantic_query") or semantic_query_snapshot.get("primary_query") or user_message,
        "topic": semantic_query_snapshot.get("topic", "UNKNOWN"),
        "entities": entities,
        "constraints": constraints,
        "risk_flags": ["BOUNDARY_REQUEST"] if contradictions else [],
        "unknowns": list(
            lexical_calibration.get(
                "unknowns",
                [],
            )
        ),
        "lexical_calibration": lexical_calibration,
        "contradictions": contradictions,
        "reverse_flow_reason_code": reverse_flow.get("reason_code"),
        "reverse_flow_verdict_marker": reverse_flow.get("verdict"),
        "non_decision": True,
        "executable": False,
        "readonly": True,
        "advisory_only": True,
        "allowed_to_decide": False,
        "allowed_to_act": False,
        "emits_act": False,
        "emits_verdict": False,
        "memory_write": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "decision_authority": "KX108_ONLY",
    }


def build_existing_reverse_os_projection(
    *,
    user_message: str,
    intent: str,
    semantic_query_snapshot: dict[str, Any] | None = None,
    authority_snapshot: dict[str, Any] | None = None,
    tree_signal_packet: dict[str, Any] | None = None,
    tree_policy_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reverse_flow = build_existing_reverse_flow(
        user_message=user_message,
        intent=intent,
        semantic_query_snapshot=semantic_query_snapshot,
        authority_snapshot=authority_snapshot,
        tree_signal_packet=tree_signal_packet,
        tree_policy_snapshot=tree_policy_snapshot,
    )

    reverse_mod = _load_module("brody_existing_reverse_os_source", REPO_REVERSE_OS)
    projection = reverse_mod.project(reverse_flow)
    if not isinstance(projection, dict):
        projection = {"raw_projection": projection}

    ir_candidate = build_existing_ir_candidate(
        user_message=user_message,
        intent=intent,
        semantic_query_snapshot=semantic_query_snapshot,
        authority_snapshot=authority_snapshot,
        reverse_flow=reverse_flow,
    )

    # G5: scrub secret-like patterns in user message before tokenizing alphabet_units
    try:
        from apps.obsidia_api.brody_secret_scrubber import scrub_secret_like as _ros_scrub
        def _g5_scrub_msg(s: str) -> str:
            return _ros_scrub(s)
    except Exception:
        def _g5_scrub_msg(s: str) -> str:  # type: ignore[misc]
            return s

    return {
        "status": "EXISTING_REVERSE_OS_READONLY_BRIDGE_PASS",
        "source": "BRODY_EXISTING_REVERSE_OS_BRIDGE_V1",
        "source_file": str(REPO_REVERSE_OS),
        "upstream_reference": "obsidia-engine-candidate/bridge/zip2_reverse_os_real_adapter.py",
        "reverse_flow": reverse_flow,
        "projection": projection,
        "ir_candidate": ir_candidate,
        "translation_trace": {
            "detected_language": "fr",
            "os_trad_status": "READONLY_PASS",
            "alphabet_units": [
                {
                    "index": idx,
                    "raw": token,
                    "normalized": token.lower(),
                    "readonly": True,
                    "decision_authority": "KX108_ONLY",
                }
                for idx, token in enumerate(_g5_scrub_msg(user_message or "").split())
            ],
            "alphabet_units_count": len((user_message or "").split()),
            "os_reverse_projection": projection,
            "x108_boundary_status": "READONLY",
            "readonly": True,
            "allowed_to_decide": False,
            "allowed_to_act": False,
            "memory_write": False,
            "kernel_mutation": False,
            "x108_mutation": False,
            "source": "BRODY_EXISTING_REVERSE_OS_BRIDGE_V1",
        },
        "non_decision": True,
        "readonly": True,
        "advisory_only": True,
        "allowed_to_decide": False,
        "allowed_to_act": False,
        "emits_act": False,
        "emits_verdict": False,
        "memory_write": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "decision_authority": "KX108_ONLY",
    }
