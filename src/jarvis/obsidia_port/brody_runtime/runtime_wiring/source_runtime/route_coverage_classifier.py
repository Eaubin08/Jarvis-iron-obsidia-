# runtime_wiring/source_runtime/route_coverage_classifier.py
# P45 — Route Coverage Classifier.
# Classifie chaque route API dans l'une des 7 catégories de couverture.
# KX108_ONLY. No ACT. No write. No execution. readonly=True.

from __future__ import annotations
from typing import Any, Dict, Tuple

# ── Catégories de couverture ──────────────────────────────────────────────────

COVERAGE_STATUSES = frozenset({
    "CONNECTED_READONLY",       # Reliée à capability router, readonly, no ACT
    "CONNECTED_BLOCKED_ACTION", # Peut représenter action/mutation — bloquée par X108
    "STATUS_ONLY",              # Health / status / metrics / readiness / manifest
    "WORKBENCH_ONLY",           # UI / preview / affichage — pas capability utilisateur
    "INTERNAL_ONLY",            # Infrastructure interne, non exposée
    "ARCHIVE_ONLY",             # Historique conservée, pas à brancher
    "DO_NOT_BIND_EXPLICIT",     # Documentée comme non bindable
})

# ── Préfixes/patterns de routes actionnelles bloquées ────────────────────────

_BLOCKED_ACTION_PATTERNS = (
    "/api/blockchain/world/gateway",
    "/api/blockchain/world/bus-dispatch",
    "/api/blockchain/world/dry-run",
    "/api/blockchain/wallet/gate",
    "/api/blockchain/policy/evaluate",
    "/api/blockchain/classifiers/fraud-check",
    "/api/blockchain/sandbox/simulate",
    "/api/blockchain/sandbox/truth-gate",
    "/api/blockchain/signature/check",
    "/api/blockchain/gencoin/compute",
    "/api/blockchain/agents/status",
    "/api/x108/memory/candidates/append",
    "/api/operator/governed-runtime",
    "/api/periphery/operator/governed-runtime",
    "/api/bus/bus/signal",
    "/api/periphery/governance/agent-run",
    "/api/memory/candidate/from-message",
)

# ── Patterns STATUS_ONLY ──────────────────────────────────────────────────────

_STATUS_ONLY_EXACT = frozenset({
    "/api/",
    "/api/health",
    "/api/readiness",
    "/api/status",
    "/api/blockchain/status",
    "/api/blockchain/agents/status",
    "/api/blockchain/world/ticket-status",
    "/api/memory/status",
    "/api/x108/status",
    "/api/worldcalls/gateway-status",
    "/api/worldcalls/sovereign-tickets",
    "/api/bus/bus/stats",
    "/api/brody-cli-registry",
    "/api/brody-historical-convergence",
    "/api/brody-trace-analyze",
})

_STATUS_ONLY_CONTAINS = (
    "/status",
    "/stats",
    "/readiness",
    "/health",
)

# ── Patterns WORKBENCH_ONLY ───────────────────────────────────────────────────

_WORKBENCH_EXACT = frozenset({
    "/api/runtime-wiring/preview",
    "/api/periphery/demo/runtime-readiness",
    "/api/periphery/workbench/runtime-connector",
    "/api/periphery/operator/runtime-panel",
    "/api/periphery/operator/runtime-panel.html",
    "/api/periphery/interface/workbench-check",
})

# ── Patterns INTERNAL_ONLY ────────────────────────────────────────────────────

_INTERNAL_ONLY_EXACT = frozenset({
    "/api/audit/events",
    "/api/bus/bus/bridge",
})

# ── Map route → (coverage_status, capability) ────────────────────────────────
# Mapping explicite pour les routes avec capability directe.

_EXPLICIT_CAPABILITY_MAP: Dict[str, Tuple[str, str]] = {
    # Runtime-wiring source-runtime
    "/api/runtime-wiring/source-runtime/preview":       ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/runtime-wiring/source-runtime/status":        ("CONNECTED_READONLY", "OS4_ENGINE_STATUS"),
    # OS Map
    "/api/runtime-wiring/os-map/query":                 ("CONNECTED_READONLY", "ATLAS_CONTEXT_LOOKUP"),
    "/api/runtime-wiring/os-map/status":                ("STATUS_ONLY", "OS4_ENGINE_STATUS"),
    # OS-Trad IR routes
    "/api/runtime-wiring/os-trad/api/os-trad/translate": ("CONNECTED_READONLY", "OS_TRAD_ROUTE_CONTEXT"),
    "/api/runtime-wiring/os-trad/api/ir/candidate":      ("CONNECTED_READONLY", "OS_TRAD_ROUTE_CONTEXT"),
    "/api/runtime-wiring/os-trad/api/os-reverse/project": ("CONNECTED_READONLY", "OS_TRAD_ROUTE_CONTEXT"),
    # Brody
    "/api/brody/chat":                                  ("CONNECTED_READONLY", "BRODY_CHAT_ENTRYPOINT"),
    # OS3
    "/api/os3/replay/{ticket_id}":                      ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/os3/tickets":                                  ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    # Sigma
    "/api/sigma/bank":                                  ("CONNECTED_READONLY", "RSSI_SECURITY_CONTEXT"),
    "/api/sigma/domains":                               ("CONNECTED_READONLY", "RSSI_SECURITY_CONTEXT"),
    "/api/sigma/ecom":                                  ("CONNECTED_READONLY", "RSSI_SECURITY_CONTEXT"),
    "/api/sigma/evaluate":                              ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/sigma/gps-defense-aviation":                  ("CONNECTED_READONLY", "RSSI_SECURITY_CONTEXT"),
    "/api/sigma/trading":                               ("CONNECTED_READONLY", "RSSI_SECURITY_CONTEXT"),
    # Translation
    "/api/translation/trace":                           ("CONNECTED_READONLY", "OS_TRAD_TRANSLATION"),
    # Context
    "/api/context/from-message":                        ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    # Query (OS Map)
    "/api/query":                                       ("CONNECTED_READONLY", "ATLAS_CONTEXT_LOOKUP"),
    # X108 (all readonly analysis)
    "/api/x108/cognitive/dominant-trees":              ("CONNECTED_READONLY", "AGENT_TREE_LOOKUP"),
    "/api/x108/cognitive/regime-classify":             ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/x108/cognitive/shazam":                       ("CONNECTED_READONLY", "AGENT_TREE_LOOKUP"),
    "/api/x108/math/lyapunov":                          ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/x108/math/pog":                               ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/x108/math/trust-path":                        ("CONNECTED_READONLY", "LAW_PROTOCOL_LOOKUP"),
    "/api/x108/memory/candidates/read":                 ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/x108/memory/logs/sealed":                     ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/x108/memory/replay/coherence":                ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/x108/memory/replay/session":                  ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/x108/oracle/freshness":                       ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    "/api/x108/readonly-ingress":                       ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/x108/timeverse/sync":                         ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    # Memory (readonly)
    "/api/memory/candidate-ledger":                     ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/memory/candidates":                           ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/memory/promotion-policy":                     ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/memory/sources":                              ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    # Adapters monitors
    "/api/adapters/bank":                               ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    "/api/adapters/gps":                                ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    "/api/adapters/trading":                            ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    # Hexaflux
    "/api/hexaflux/ltcu-plus":                          ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/hexaflux/transition-map":                     ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    # Periphery — Brody
    "/api/periphery/brody/context-query":               ("CONNECTED_READONLY", "BRODY_CHAT_ENTRYPOINT"),
    "/api/periphery/brody/diffusion-mix":               ("CONNECTED_READONLY", "BRODY_CHAT_ENTRYPOINT"),
    "/api/periphery/brody/double-brain-route":          ("CONNECTED_READONLY", "BRODY_CHAT_ENTRYPOINT"),
    "/api/periphery/brody/language-route":              ("CONNECTED_READONLY", "OS_TRAD_TRANSLATION"),
    "/api/periphery/brody-runtime/f33/integration-packet": ("CONNECTED_READONLY", "BRODY_CHAT_ENTRYPOINT"),
    "/api/periphery/brody-runtime/f36/user-scenario":   ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/brody-runtime/f38/multi-domain-scenarios": ("CONNECTED_READONLY", "ATLAS_CONTEXT_LOOKUP"),
    # Periphery — Cognitive
    "/api/periphery/cognitive/memory-world-map":        ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/periphery/cognitive/tree-signal":             ("CONNECTED_READONLY", "AGENT_TREE_LOOKUP"),
    "/api/periphery/cognitive/trees":                   ("CONNECTED_READONLY", "AGENT_TREE_LOOKUP"),
    "/api/periphery/cognitive/trees/domain/{domain}":   ("CONNECTED_READONLY", "AGENT_TREE_LOOKUP"),
    "/api/periphery/cognitive/trees/{tree_id}":         ("CONNECTED_READONLY", "AGENT_TREE_LOOKUP"),
    # Periphery — Context
    "/api/periphery/context/build":                     ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/context/export":                    ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/context/ingress":                   ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/context/sanitize":                  ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/context/validate":                  ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    # Periphery — Graphiti
    "/api/periphery/graphiti/context-adapt":            ("CONNECTED_READONLY", "GRAPHITI_READONLY_CONTEXT"),
    "/api/periphery/graphiti/freeze-snapshot/{snapshot_id}": ("CONNECTED_READONLY", "GRAPHITI_READONLY_CONTEXT"),
    # Periphery — Ingestion
    "/api/periphery/ingestion/classify-source":         ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/ingestion/document":                ("CONNECTED_READONLY", "NARRATIVE_PROVENANCE_LAYER"),
    "/api/periphery/ingestion/hash":                    ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/ingestion/memory-sources":          ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    # Periphery — OS3
    "/api/periphery/os3/manifest":                      ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/os3/replay-compare":                ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/os3/replay-run":                    ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/os3/ticket":                        ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/os3/world-action-readiness":        ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    # Periphery — Sigma
    "/api/periphery/sigma/evaluate":                    ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    # Periphery — Education
    "/api/periphery/education/audience":                ("CONNECTED_READONLY", "ANSWER_ONLY"),
    "/api/periphery/education/format":                  ("CONNECTED_READONLY", "ANSWER_ONLY"),
    "/api/periphery/education/score":                   ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    # Periphery — Feedback
    "/api/periphery/feedback/bridge-candidate":         ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/feedback/candidate":                ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    # Periphery — Gencoin
    "/api/periphery/gencoin/avdr-phase":                ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    "/api/periphery/gencoin/balance":                   ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    "/api/periphery/gencoin/collective-summary":        ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    "/api/periphery/gencoin/consciousness-regime":      ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/periphery/gencoin/passfail":                  ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/gencoin/regime-state":              ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    # Periphery — Governance
    "/api/periphery/governance/agent-spec-check":       ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/governance/agents":                 ("STATUS_ONLY", "OS4_ENGINE_STATUS"),
    "/api/periphery/governance/benchmarks":             ("STATUS_ONLY", "OS4_ENGINE_STATUS"),
    "/api/periphery/governance/failure-classify":       ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/governance/failure-codes":          ("STATUS_ONLY", "OS4_ENGINE_STATUS"),
    "/api/periphery/governance/lifecycle":              ("CONNECTED_READONLY", "LAW_PROTOCOL_LOOKUP"),
    "/api/periphery/governance/partition-gate":         ("CONNECTED_READONLY", "LAW_PROTOCOL_LOOKUP"),
    "/api/periphery/governance/sequence-govern":        ("CONNECTED_READONLY", "LAW_PROTOCOL_LOOKUP"),
    "/api/periphery/governance/workflow-guard":         ("CONNECTED_READONLY", "LAW_PROTOCOL_LOOKUP"),
    # Periphery — Interface
    "/api/periphery/interface/bias-gate":               ("CONNECTED_READONLY", "LAW_PROTOCOL_LOOKUP"),
    "/api/periphery/interface/bias-trace":              ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/interface/log-event":               ("INTERNAL_ONLY", "NONE"),
    "/api/periphery/interface/mcp-access":              ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/interface/state-packet":            ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/interface/view-contracts":          ("STATUS_ONLY", "OS4_ENGINE_STATUS"),
    # Periphery — Pipeline
    "/api/periphery/pipeline/constants":                ("STATUS_ONLY", "OS4_ENGINE_STATUS"),
    "/api/periphery/pipeline/data-gate":                ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/pipeline/eml-compression":          ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    "/api/periphery/pipeline/energy-thermo":            ("CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT"),
    "/api/periphery/pipeline/memory-governor":          ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/periphery/pipeline/merge":                    ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/pipeline/ocs-generation":           ("CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT"),
    "/api/periphery/pipeline/operational-constance":    ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    "/api/periphery/pipeline/permission-economic":      ("CONNECTED_READONLY", "LAW_PROTOCOL_LOOKUP"),
    "/api/periphery/pipeline/provenance-gate":          ("CONNECTED_READONLY", "PROVENANCE_TRACE"),
    "/api/periphery/pipeline/run":                      ("CONNECTED_READONLY", "SOURCE_CONTEXT"),
    "/api/periphery/pipeline/validate-candidate":       ("CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT"),
    # Periphery — Workflow governance
    "/api/periphery/workflow-governance/packet":        ("CONNECTED_READONLY", "LAW_PROTOCOL_LOOKUP"),
    # Blockchain (non-action)
    "/api/blockchain/agents/status":                    ("STATUS_ONLY", "OS4_ENGINE_STATUS"),
    "/api/blockchain/world/ticket-status":              ("STATUS_ONLY", "OS4_ENGINE_STATUS"),
    # Gencoin (top-level)
    # (none at top level beyond blockchain)
}

# ── Fonctions de classification ───────────────────────────────────────────────


def classify_route_coverage(path: str, method: str = "GET") -> Dict[str, Any]:
    """
    Classe une route API dans l'une des 7 catégories de couverture.

    Returns:
        Dict avec coverage_status, capability, runtime_allowed_now,
        emits_act, decision_authority, classification_reason.
    """
    # 1. Explicit map lookup (highest priority)
    if path in _EXPLICIT_CAPABILITY_MAP:
        status, cap = _EXPLICIT_CAPABILITY_MAP[path]
        return _build_result(path, status, cap, "EXPLICIT_MAP")

    # 2. Blocked action patterns
    for pattern in _BLOCKED_ACTION_PATTERNS:
        if path.startswith(pattern) or path == pattern:
            return _build_result(path, "CONNECTED_BLOCKED_ACTION", "ACTION_REQUEST_BLOCKED", "BLOCKED_ACTION_PATTERN")

    # 3. Status-only exact
    if path in _STATUS_ONLY_EXACT:
        return _build_result(path, "STATUS_ONLY", "OS4_ENGINE_STATUS", "STATUS_EXACT")

    # 4. Status-only by contains
    for fragment in _STATUS_ONLY_CONTAINS:
        if fragment in path:
            return _build_result(path, "STATUS_ONLY", "OS4_ENGINE_STATUS", "STATUS_PATTERN")

    # 5. Workbench-only exact
    if path in _WORKBENCH_EXACT:
        return _build_result(path, "WORKBENCH_ONLY", "WORKBENCH_PREVIEW", "WORKBENCH_EXACT")

    # 6. Internal-only exact
    if path in _INTERNAL_ONLY_EXACT:
        return _build_result(path, "INTERNAL_ONLY", "NONE", "INTERNAL_EXACT")

    # 7. Path prefix rules
    if path.startswith("/api/bus/"):
        return _build_result(path, "INTERNAL_ONLY", "NONE", "BUS_INTERNAL")

    if path.startswith("/api/runtime-wiring/"):
        return _build_result(path, "CONNECTED_READONLY", "WORKBENCH_PREVIEW", "RUNTIME_WIRING_PREFIX")

    if path.startswith("/api/blockchain/"):
        return _build_result(path, "CONNECTED_BLOCKED_ACTION", "ACTION_REQUEST_BLOCKED", "BLOCKCHAIN_PREFIX")

    if path.startswith("/api/worldcalls/"):
        return _build_result(path, "CONNECTED_BLOCKED_ACTION", "ACTION_REQUEST_BLOCKED", "WORLDCALLS_PREFIX")

    if path.startswith("/api/x108/"):
        return _build_result(path, "CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT", "X108_PREFIX")

    if path.startswith("/api/periphery/"):
        return _build_result(path, "CONNECTED_READONLY", "SOURCE_CONTEXT", "PERIPHERY_PREFIX")

    if path.startswith("/api/memory/"):
        return _build_result(path, "CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT", "MEMORY_PREFIX")

    if path.startswith("/api/sigma/"):
        return _build_result(path, "CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT", "SIGMA_PREFIX")

    if path.startswith("/api/os3/"):
        return _build_result(path, "CONNECTED_READONLY", "PROOF_AUDIT_CONTEXT", "OS3_PREFIX")

    if path.startswith("/api/adapters/"):
        return _build_result(path, "CONNECTED_READONLY", "EXTERNAL_SIGNALS_CONTEXT", "ADAPTERS_PREFIX")

    if path.startswith("/api/hexaflux/"):
        return _build_result(path, "CONNECTED_READONLY", "MEMORY_REINTEGRATION_CONTEXT", "HEXAFLUX_PREFIX")

    # 8. Workbench/demo prefix
    if path.startswith("/api/periphery/demo/") or path.startswith("/api/periphery/workbench/"):
        return _build_result(path, "WORKBENCH_ONLY", "WORKBENCH_PREVIEW", "WORKBENCH_PREFIX")

    # Fallback — this should never be reached if all paths are covered
    return _build_result(path, "CONNECTED_READONLY", "ANSWER_ONLY", "FALLBACK_CATCH_ALL")


def _build_result(
    path: str,
    status: str,
    capability: str,
    reason: str,
) -> Dict[str, Any]:
    """Build a classification result dict with all required fields."""
    # Action safety: blocked/internal routes always have explicit constraints
    is_action = status == "CONNECTED_BLOCKED_ACTION"
    x108_decision = "BLOCK_OR_HOLD_CONTEXT_ONLY" if is_action else "ALLOW_CONTEXT_ONLY"

    return {
        "path": path,
        "coverage_status": status,
        "capability": capability,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "x108_decision": x108_decision,
        "classification_reason": reason,
        "readonly": status != "CONNECTED_BLOCKED_ACTION",
        "is_action_route": is_action,
    }


def coverage_status_label(status: str) -> str:
    """Human-readable label for a coverage status."""
    labels = {
        "CONNECTED_READONLY": "Connected — readonly context",
        "CONNECTED_BLOCKED_ACTION": "Connected — action blocked by X108",
        "STATUS_ONLY": "Status / health check",
        "WORKBENCH_ONLY": "Workbench / UI display only",
        "INTERNAL_ONLY": "Internal infrastructure",
        "ARCHIVE_ONLY": "Archive / legacy",
        "DO_NOT_BIND_EXPLICIT": "Explicit: do not bind",
    }
    return labels.get(status, status)
