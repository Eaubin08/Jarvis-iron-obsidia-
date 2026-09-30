# runtime_wiring/source_runtime/reverse_os_interlanguage_index.py
# P35 — REVERSE_OS_INTERLANGUAGE_CANON_V1 conceptual layer index.
# Classifies P34 pack entries into semantic layers from path metadata alone.
# NO zip reading at runtime. NO .py execution. KX108_ONLY. Advisory / readonly.
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── Layer definitions ─────────────────────────────────────────────────────────

_LAYER_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "IR_ALPHABET_LAYER": {
        "description": "Spec IR Alphabet L2 — 12 tokens VALUE/STATE/READ/WRITE/FLOW/COND/LOOP/CALL/RETURN/EVENT/TIME/ERROR",
        "path_patterns": [
            "interlanguage_canon", "ir_alphabet", "ir_spec",
            "reverse_os_interlanguage_canon_v1",
        ],
        "dir_patterns": [],
        "semantic_role": "IR_ALPHABET_SPEC",
    },
    "AUDIENCE_PROJECTION_LAYER": {
        "description": "Audience adapter packets — projection multi-cible par audience",
        "path_patterns": [
            "audience_packet", "audience_adapter", "investor", "non_tech",
        ],
        "dir_patterns": [],
        "semantic_role": "AUDIENCE_ADAPTER",
    },
    "REVERSE_OS_NARRATIVE_LAYER": {
        "description": "Architecture narrative Reverse OS — inversion paradigme, Reverse OS comme cerveau secondaire",
        "path_patterns": [
            "architecture_narrative", "narrative_reverse_os", "narrative_reverse",
        ],
        "dir_patterns": [],
        "semantic_role": "REVERSE_OS_NARRATIVE",
    },
    "PROTOCOLS_TRANSDUCTION_LAYER": {
        "description": "Protocoles et spec transduction — proof obligations, transduction doc, protocoles OS Cognitif",
        "path_patterns": [
            "proof_obligations", "interlanguage_transduction", "transduction_v1",
            "architecture_protocoles", "protocoles_os_cognitif",
        ],
        "dir_patterns": [],
        "semantic_role": "TRANSDUCTION_SPEC",
    },
    "EXECUTION_PLAN_LAYER": {
        "description": "Plan exécution industriel — SCF Réciproque, TWIN_CALL, checklist forge",
        "path_patterns": [
            "plan_execution", "checklist_forge", "execution_industriel",
            "plan_d_execution",
        ],
        "dir_patterns": [],
        "semantic_role": "EXECUTION_PLAN",
    },
    "UNIVERSAL_IO_SUPPORT_LAYER": {
        "description": "Universal IO Matrix — échantillons de support réplication alphabet_ir (non-primaires)",
        "path_patterns": [
            "matrix_cell", "universal_io_matrix",
        ],
        "dir_patterns": ["universal_io_matrix_samples"],
        "semantic_role": "UNIVERSAL_IO_SUPPORT",
    },
}

# Static evidence map from P34 canon pack
_EVIDENCE_RESULTS: Dict[str, Dict[str, Any]] = {
    "IR_ALPHABET_LAYER": {
        "found": True,
        "matching_files_count": 1,
        "confidence": "HIGH",
        "evidence_status": "CORE_PARENT_CANDIDATE",
        "zip_evidence_status": "MEDIUM_SIGNAL",
        "core_parent_evidence_status": "CORE_PARENT_CANDIDATE",
        "evidence_basis": "P34_CANON_PACK",
        "confidence_reason": "reverse_os_interlanguage_canon_v1.json définit formellement L2=IR Alphabet avec 12 tokens.",
        "source_files_count": 1,
        "strong_files_count": 1,
        "canonicalization_needed": True,
        "evidence_files": ["evidence/reverse_os_interlanguage_canon_v1.json"],
        "top_files": ["evidence/reverse_os_interlanguage_canon_v1.json"],
        "keywords_matched": ["alphabet_ir", "ir_alphabet", "VALUE STATE READ WRITE"],
        "notes": "Spec canonique P34. 12 tokens IR. KX108_ONLY. CORE_PARENT_CANDIDATE.",
    },
    "AUDIENCE_PROJECTION_LAYER": {
        "found": True,
        "matching_files_count": 2,
        "confidence": "HIGH",
        "evidence_status": "CORE_PARENT_CANDIDATE",
        "zip_evidence_status": "PARTIAL_STRONG",
        "core_parent_evidence_status": "CORE_PARENT_CANDIDATE",
        "evidence_basis": "P34_CANON_PACK",
        "confidence_reason": "2 audience packets (investor, non_tech) confirment alphabet_ir et reciproque_miroir dans concept_lines.",
        "source_files_count": 2,
        "strong_files_count": 2,
        "canonicalization_needed": False,
        "evidence_files": [
            "evidence/audience_packet_07_investor.json",
            "evidence/audience_packet_08_non_tech.json",
        ],
        "top_files": [
            "evidence/audience_packet_07_investor.json",
            "evidence/audience_packet_08_non_tech.json",
        ],
        "keywords_matched": ["alphabet_ir", "reciproque_miroir", "os_trad"],
        "notes": "Audience adapter packets. Confirment concepts IR et réciproque par audience.",
    },
    "REVERSE_OS_NARRATIVE_LAYER": {
        "found": True,
        "matching_files_count": 1,
        "confidence": "MEDIUM",
        "evidence_status": "MEDIUM_SIGNAL",
        "zip_evidence_status": "MEDIUM_SIGNAL",
        "core_parent_evidence_status": "MEDIUM_SIGNAL",
        "evidence_basis": "P34_CANON_PACK",
        "confidence_reason": "1 fichier DOCX Narrative — inversion paradigme IA, Reverse OS comme couche secondaire.",
        "source_files_count": 1,
        "strong_files_count": 0,
        "canonicalization_needed": True,
        "evidence_files": ["evidence/architecture_narrative_reverse_os.txt"],
        "top_files": ["evidence/architecture_narrative_reverse_os.txt"],
        "keywords_matched": ["inversion", "reverse os", "paradigme"],
        "notes": "Narrative Reverse OS. Conceptuel. MEDIUM_SIGNAL.",
    },
    "PROTOCOLS_TRANSDUCTION_LAYER": {
        "found": True,
        "matching_files_count": 3,
        "confidence": "HIGH",
        "evidence_status": "CORE_PARENT_CANDIDATE",
        "zip_evidence_status": "MEDIUM_SIGNAL",
        "core_parent_evidence_status": "CORE_PARENT_CANDIDATE",
        "evidence_basis": "P34_CANON_PACK",
        "confidence_reason": "3 fichiers: proof_obligations, transduction_v1, protocoles_os_cognitif. Spec formelle transduction.",
        "source_files_count": 3,
        "strong_files_count": 2,
        "canonicalization_needed": True,
        "evidence_files": [
            "evidence/interlanguage_proof_obligations_v1.md",
            "evidence/interlanguage_transduction_v1.md",
            "evidence/architecture_protocoles_os_cognitif.txt",
        ],
        "top_files": [
            "evidence/interlanguage_proof_obligations_v1.md",
            "evidence/interlanguage_transduction_v1.md",
            "evidence/architecture_protocoles_os_cognitif.txt",
        ],
        "keywords_matched": ["proof_obligations", "transduction", "TWIN_CALL", "INV:EMO/RAIS/ETH"],
        "notes": "3 fichiers spec transduction + TWIN_CALL + INVERSION_PATH. CORE_PARENT_CANDIDATE.",
    },
    "EXECUTION_PLAN_LAYER": {
        "found": True,
        "matching_files_count": 1,
        "confidence": "MEDIUM",
        "evidence_status": "MEDIUM_SIGNAL",
        "zip_evidence_status": "MEDIUM_SIGNAL",
        "core_parent_evidence_status": "MEDIUM_SIGNAL",
        "evidence_basis": "P34_CANON_PACK",
        "confidence_reason": "Plan d'Exécution Industriel: SCF Réciproque, TWIN_CALL, checklist de forge.",
        "source_files_count": 1,
        "strong_files_count": 0,
        "canonicalization_needed": True,
        "evidence_files": ["evidence/plan_execution_industriel.txt"],
        "top_files": ["evidence/plan_execution_industriel.txt"],
        "keywords_matched": ["SCF réciproque", "TWIN_CALL", "plan_execution"],
        "notes": "Plan industriel. Mentionne SCF Réciproque et TWIN_CALL. MEDIUM_SIGNAL.",
    },
    "UNIVERSAL_IO_SUPPORT_LAYER": {
        "found": True,
        "matching_files_count": 1,
        "confidence": "LOW",
        "evidence_status": "MEDIUM_SIGNAL",
        "zip_evidence_status": "PARTIAL_STRONG",
        "core_parent_evidence_status": "MEDIUM_SIGNAL",
        "evidence_basis": "P34_CANON_PACK",
        "confidence_reason": "1 échantillon matrix_cell Universal IO Matrix — réplication alphabet_ir (support seulement).",
        "source_files_count": 1,
        "strong_files_count": 0,
        "canonicalization_needed": False,
        "evidence_files": [
            "support/universal_io_matrix_samples/matrix_cell_0181_code_python_dev_plain_fr.json"
        ],
        "top_files": [
            "support/universal_io_matrix_samples/matrix_cell_0181_code_python_dev_plain_fr.json"
        ],
        "keywords_matched": ["alphabet_ir", "matrix_cell"],
        "notes": "Support seulement — réplication. Ne pas traiter comme preuve primaire.",
    },
    "UNKNOWN_RELEVANT": {
        "found": False,
        "matching_files_count": 0,
        "confidence": "NONE",
        "evidence_status": "NOT_FOUND",
        "zip_evidence_status": "NOT_FOUND",
        "core_parent_evidence_status": "NOT_FOUND",
        "evidence_basis": "P34_CANON_PACK",
        "confidence_reason": "Tous les fichiers classifiés dans des couches connues.",
        "source_files_count": 0,
        "strong_files_count": 0,
        "canonicalization_needed": False,
        "evidence_files": [],
        "top_files": [],
        "keywords_matched": [],
        "notes": "Aucun fichier non classifié.",
    },
}


def _classify_entry_by_path(internal_path: str) -> str:
    """
    Classify an interlanguage canon entry into a semantic layer using path patterns.
    Checks dir_patterns first (strongest), then path_patterns.
    Never reads file content.
    """
    path_lower = internal_path.lower().replace("\\", "/")

    for layer, defn in _LAYER_DEFINITIONS.items():
        for dir_pat in defn.get("dir_patterns", []):
            if dir_pat.lower() in path_lower:
                return layer

    for layer, defn in _LAYER_DEFINITIONS.items():
        fname = path_lower.split("/")[-1]
        for pat in defn.get("path_patterns", []):
            if pat in fname or pat in path_lower:
                return layer

    return "UNKNOWN_RELEVANT"


def classify_entry_layer(metadata: Dict[str, Any]) -> str:
    """Return the conceptual layer for a single P34 pack entry. Uses path only."""
    internal = metadata.get("internal_path", metadata.get("file_name", ""))
    return _classify_entry_by_path(internal)


def get_semantic_role(layer: str) -> str:
    """Return the semantic role for a layer."""
    defn = _LAYER_DEFINITIONS.get(layer)
    if defn:
        return defn["semantic_role"]
    return "UNKNOWN"


def build_reverse_os_interlanguage_index(
    entries: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Build the REVERSE_OS_INTERLANGUAGE_CANON_V1 deep concept index.

    If entries provided, recomputes layer distribution from them.
    Otherwise returns the static evidence map from P34 analysis.

    Never reads zip. Never executes .py. KX108_ONLY. Advisory / readonly.
    """
    if entries is not None:
        il_entries = [
            e for e in entries
            if getattr(e, "source_subfamily", "") == "REVERSE_OS_INTERLANGUAGE_CANON_V1"
            or getattr(e, "adapter_target", "") == "reverse_os_interlanguage_to_context_packet"
        ]
        total_safe = len(il_entries)
        total_exec = sum(
            1 for e in il_entries
            if getattr(e, "extension", "").lower() in {".py", ".ps1", ".sh", ".bat", ".exe"}
        )

        layer_counts: Dict[str, int] = {layer: 0 for layer in _LAYER_DEFINITIONS}
        layer_counts["UNKNOWN_RELEVANT"] = 0
        for e in il_entries:
            layer = _classify_entry_by_path(getattr(e, "internal_path", ""))
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

        layers = {}
        for layer, count in layer_counts.items():
            static = _EVIDENCE_RESULTS.get(layer, {})
            layers[layer] = {
                "found": count > 0,
                "matching_files_count": count,
                "confidence": "HIGH" if count >= 5 else "MEDIUM" if count >= 2 else "LOW" if count >= 1 else "NONE",
                "top_files": static.get("top_files", []),
                "keywords_matched": static.get("keywords_matched", []),
                "notes": static.get("notes", ""),
                "evidence_status": static.get("evidence_status", "NOT_FOUND"),
                "zip_evidence_status": static.get("zip_evidence_status", "NOT_FOUND"),
                "core_parent_evidence_status": static.get("core_parent_evidence_status", "NOT_FOUND"),
                "evidence_basis": static.get("evidence_basis", "P34_CANON_PACK"),
                "confidence_reason": static.get("confidence_reason", ""),
                "source_files_count": static.get("source_files_count", 0),
                "strong_files_count": static.get("strong_files_count", 0),
                "canonicalization_needed": static.get("canonicalization_needed", False),
                "evidence_files": static.get("evidence_files", []),
            }
    else:
        layers = {k: dict(v) for k, v in _EVIDENCE_RESULTS.items()}
        total_safe = 9
        total_exec = 0

    return {
        "family": "OS_TRAD_REVERSE_OS",
        "source_subfamily": "REVERSE_OS_INTERLANGUAGE_CANON_V1",
        "safe_entries_count": total_safe,
        "excluded_executables_count": total_exec,
        "decision_authority": "KX108_ONLY",
        "advisory_only": True,
        "readonly": True,
        "emits_act": False,
        "runtime_allowed_now": False,
        "canonization_source": "P34",
        "evidence_pack": "REVERSE_OS_INTERLANGUAGE_CANON_V1",
        "ir_alphabet_layer": layers.get("IR_ALPHABET_LAYER", {}),
        "audience_projection_layer": layers.get("AUDIENCE_PROJECTION_LAYER", {}),
        "reverse_os_narrative_layer": layers.get("REVERSE_OS_NARRATIVE_LAYER", {}),
        "protocols_transduction_layer": layers.get("PROTOCOLS_TRANSDUCTION_LAYER", {}),
        "execution_plan_layer": layers.get("EXECUTION_PLAN_LAYER", {}),
        "universal_io_support_layer": layers.get("UNIVERSAL_IO_SUPPORT_LAYER", {}),
        "unknown_relevant": layers.get("UNKNOWN_RELEVANT", {}),
    }
