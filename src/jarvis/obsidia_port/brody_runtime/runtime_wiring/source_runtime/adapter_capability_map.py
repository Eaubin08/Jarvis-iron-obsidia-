"""
P48 — Adapter → Capability / Route Map.
Carte explicite des 10 adapters du runtime Obsidia X-108.
Tous : runtime_allowed_now=False, emits_act=False, KX108_ONLY.
NO ACT. NO write. READONLY.
"""
from __future__ import annotations

from typing import Any

ADAPTER_CAPABILITY_MAP: dict[str, dict[str, Any]] = {
    # ── 1 — Cognitive Reintegration ───────────────────────────────────────────
    "cognitive_to_context_packet": {
        "coverage_status": "CONNECTED_CONTEXT_PACKET",
        "capabilities": ["SOURCE_CONTEXT_HYDRATOR", "COGNITIVE_REINTEGRATION_ADVISORY"],
        "source_families": ["COGNITIVE_REINTEGRATION"],
        "boundary": "COGNITIVE_REINTEGRATION_ADVISORY_ONLY",
        "source_pack": "F07 pending",
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
    },
    # ── 2 — RSSI + RGPD ───────────────────────────────────────────────────────
    "rssi_rgpd_to_context_packet": {
        "coverage_status": "CONNECTED_CONTEXT_PACKET",
        "capabilities": ["SOURCE_CONTEXT_HYDRATOR", "RSSI_RGPD_EVIDENCE"],
        "source_families": ["RSSI_RGPD"],
        "boundary": "RSSI_EVIDENCE_ONLY|RGPD_COMPLIANCE_SCOPE_GUARD",
        "source_pack": "F03 pending",
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
    },
    # ── 3 — Atlas Branchable ──────────────────────────────────────────────────
    "atlas_to_context_packet": {
        "coverage_status": "CONNECTED_CONTEXT_PACKET",
        "capabilities": ["SOURCE_CONTEXT_HYDRATOR", "ATLAS_READONLY_ADVISORY"],
        "source_families": ["ATLAS_BRANCHABLE"],
        "boundary": "ATLAS_READONLY_ADVISORY_ONLY",
        "source_pack": "F06 pending (1738 files, 92 duplicates)",
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "note": "_atlas_can_execute=false — aucun agent Atlas exécutable",
    },
    # ── 4 — Compliance / RGPD Primary ─────────────────────────────────────────
    "compliance_to_context_packet": {
        "coverage_status": "CONNECTED_CONTEXT_PACKET",
        "capabilities": ["SOURCE_CONTEXT_HYDRATOR", "RGPD_COMPLIANCE_ADVISORY"],
        "source_families": ["COMPLIANCE_RGPD"],
        "boundary": "RGPD_COMPLIANCE_SCOPE_GUARD|RSSI_EVIDENCE_ONLY",
        "source_pack": "F10 pending",
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "note": "_rgpd_compliant=false — ISO readiness ≠ legal compliance",
    },
    # ── 5 — RSSI Security Presentation ───────────────────────────────────────
    "rssi_security_to_context_packet": {
        "coverage_status": "CONNECTED_CONTEXT_PACKET",
        "capabilities": ["SOURCE_CONTEXT_HYDRATOR", "RSSI_SECURITY_EVIDENCE"],
        "source_families": ["RSSI_SECURITY"],
        "boundary": "RSSI_EVIDENCE_ONLY",
        "source_pack": "F11/P24 (835 files, 80 .py DO_NOT_IMPORT_RUNTIME)",
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "note": "_py_files_excluded=true — .py DO_NOT_IMPORT_RUNTIME",
    },
    # ── 6 — External Signals (incl. Timeverse C459) ───────────────────────────
    "external_signals_to_context_packet": {
        "coverage_status": "CONNECTED_CONTEXT_PACKET",
        "capabilities": ["SOURCE_CONTEXT_HYDRATOR", "EXTERNAL_SIGNALS_ADVISORY"],
        "source_families": ["EXTERNAL_SIGNALS"],
        "boundary": "EXTERNAL_SIGNALS_SIGNAL_ONLY",
        "source_pack": "F04 (0 .py, specs/external_signals/)",
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "note": "_timeverse_advisory_only=true, _can_emit_act=false",
    },
    # ── 7 — Narrative Provenance Layer ────────────────────────────────────────
    "npl_to_context_packet": {
        "coverage_status": "CONNECTED_CONTEXT_PACKET",
        "capabilities": ["SOURCE_CONTEXT_HYDRATOR", "NPL_ADVISORY"],
        "source_families": ["NARRATIVE_PROVENANCE_LAYER"],
        "boundary": "NPL_ADVISORY_ONLY",
        "source_pack": "F12/P24 (103 files, all .md/.json, 0 .py)",
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "note": "_npl_narrative_not_truth=true — expose la chaîne narrative, ne décide pas du récit vrai",
    },
    # ── 8 — OS Trad / Reverse OS ──────────────────────────────────────────────
    "os_trad_reverse_to_context_packet": {
        "coverage_status": "CONNECTED_SOURCE_RUNTIME",
        "capabilities": ["SOURCE_CONTEXT_HYDRATOR", "OS_TRAD_REVERSE_OS", "IR_LAYER_CLASSIFICATION"],
        "source_families": ["OS_TRAD_REVERSE_OS"],
        "boundary": "OS_TRAD_REVERSE_OS_ADVISORY_ONLY",
        "source_pack": "P32/P33 (629 files, 546 safe .md/.json, 63 .py DO_NOT_IMPORT_RUNTIME)",
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "uses_index": "runtime_wiring/source_runtime/os_trad_reverse_index.py",
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "note": "Enrichi P33 — os_trad_layer + semantic_role via classify_entry_layer. _34_arbres_advisory_only=true",
    },
    # ── 9 — Reverse OS Interlanguage Canon V1 ────────────────────────────────
    "reverse_os_interlanguage_to_context_packet": {
        "coverage_status": "CONNECTED_SOURCE_RUNTIME",
        "capabilities": [
            "SOURCE_CONTEXT_HYDRATOR",
            "REVERSE_OS_INTERLANGUAGE",
            "IR_ALPHABET_MAPPING",
            "RECIPROQUE_MIROIR",
        ],
        "source_families": ["REVERSE_OS_INTERLANGUAGE"],
        "boundary": "REVERSE_OS_INTERLANGUAGE_ADVISORY_ONLY",
        "source_pack": "REVERSE_OS_INTERLANGUAGE_CANON_V1 / P34/P35",
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "uses_index": "runtime_wiring/source_runtime/reverse_os_interlanguage_index.py",
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "note": "IR Alphabet 12-token spec. Réciproque/miroir formalisé. evidence_pack=REVERSE_OS_INTERLANGUAGE_CANON_V1",
    },
    # ── 10 — Route Entry Dispatcher ───────────────────────────────────────────
    "route_entry_to_context_packet": {
        "coverage_status": "CONNECTED_CAPABILITY",
        "capabilities": ["SOURCE_REGISTRY_DISPATCH", "DRY_RUN_PACKET_ROUTER"],
        "source_families": ["SOURCE_REGISTRY_DISPATCH"],
        "boundary": "DRY_RUN_ONLY_NO_ZIP",
        "source_pack": "source_file_registry (metadata only)",
        "routes": ["/api/runtime-wiring/source-runtime/preview"],
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "note": "Dispatcher: routes SourceFileRegistryEntry via _ADAPTER_DISPATCH → les 9 adapters source. Raises ValueError sur FORBIDDEN. Never reads zip.",
    },
}


def get_adapter_capability_map() -> dict[str, dict[str, Any]]:
    return ADAPTER_CAPABILITY_MAP


def get_adapter_classification(adapter_name: str) -> dict[str, Any]:
    return ADAPTER_CAPABILITY_MAP.get(adapter_name, {})


def build_adapter_coverage_summary() -> dict[str, Any]:
    """Résumé P48 — 10 adapters classifiés, unclassified=0, coverage=100%."""
    total = len(ADAPTER_CAPABILITY_MAP)
    counts: dict[str, int] = {}
    unclassified = 0

    for entry in ADAPTER_CAPABILITY_MAP.values():
        status = entry.get("coverage_status", "UNCLASSIFIED")
        if status == "UNCLASSIFIED":
            unclassified += 1
        counts[status] = counts.get(status, 0) + 1

    covered = total - unclassified
    percent = (covered / total * 100.0) if total > 0 else 0.0

    return {
        "adapter_coverage_status": "FULL_COVERAGE" if percent >= 100.0 else "PARTIAL_COVERAGE",
        "adapters_total": total,
        "adapters_classified": covered,
        "adapters_unclassified_count": unclassified,
        "adapter_coverage_percent": percent,
        "coverage_counts": counts,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
    }
