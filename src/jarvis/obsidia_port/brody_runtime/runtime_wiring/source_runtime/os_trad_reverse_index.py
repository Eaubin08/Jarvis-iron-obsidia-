# runtime_wiring/source_runtime/os_trad_reverse_index.py
# P33 — OS_TRAD_REVERSE_OS deep conceptual layer index.
# Classifies OS_TRAD registry entries into semantic layers from path metadata alone.
# NO zip reading at runtime. NO .py execution. KX108_ONLY. Advisory / readonly.
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── Layer definitions ────────────────────────────────────────────────────────

_LAYER_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "UNIVERSAL_LANGUAGE_LAYER": {
        "description": "Langage universel, grammaire, syntaxe, alphabet, lexique (LCTU absent P33C)",
        "path_patterns": [
            "vocabulaire", "grammaire", "syntaxe", "alphabet", "lexique",
            "lexicon", "universal_language", "langage_universel",
        ],
        "dir_patterns": [],  # no dedicated dir — detected by filename/path keywords only
        "semantic_role": "LANGUAGE_SPEC",
    },
    "REVERSE_LANGUAGE_LAYER": {
        "description": "Langage reverse, réciproque, miroir, inversion, dualité",
        "path_patterns": [
            "reverse", "reciprocal", "mirror", "miroir", "inverse",
            "dual", "inversion", "symmetry", "reciproque",
        ],
        "dir_patterns": ["06_REVERSE_OS_SSR_JARVIS", "16_VISUALISATION_REVERSE_OS"],
        "semantic_role": "REVERSE_MAPPING",
    },
    "IR_LAYER": {
        "description": "IR / Intermediate Representation / représentation intermédiaire",
        "path_patterns": [
            "_ir_", "_ir.", "ir_schema", "ir_spec", "intermediate_repr",
            "obsidia_ir", "mcp_bridge_obsidia_ir",
        ],
        "dir_patterns": ["09_MCP_BRIDGE_OBSIDIA_IR", "context_export_x108_boundary"],
        "semantic_role": "IR_SCHEMA",
    },
    "REVERSE_WINDOWS_LAYER": {
        "description": "Fenêtres reverse, windowing, blocs/fenêtres de lecture",
        "path_patterns": [
            "window", "windowing", "fenetre", "bloc_lecture", "sliding",
        ],
        "dir_patterns": ["16_VISUALISATION_REVERSE_OS", "13_GRAPHES_NUAGE_POINTS"],
        "semantic_role": "WINDOWING_MODEL",
    },
    "LAWS_PROTOCOLS_LAYER": {
        "description": "Lois, protocoles, règles, invariants, boundary, contracts, constitution",
        "path_patterns": [
            "loi", "law", "protocole", "protocol", "invariant", "boundary",
            "contract", "constitution", "non_decision", "non-decision",
            "non_action", "guard",
        ],
        "dir_patterns": [
            "02_CONSTITUTION_LOIS_OBSIDIENNES", "11_AGENTS_RUNTIME_CONTRACTS",
            "15_GUARDS_NON_DECISION",
        ],
        "semantic_role": "LAW_OR_PROTOCOL",
    },
    "AGENTS_TREES_LAYER": {
        "description": "34 arbres, 52 agents, agent definitions, tree specs",
        "path_patterns": [
            "arbre", "arbres", "tree", "agent", "agents", "tensor",
            "shazam", "hexaflux", "bdf", "ssr", "registry",
        ],
        "dir_patterns": [
            "04_ARBRES_34_TENSOR_MATRIX", "10_AGENTS_52",
            "05_SHAZAM_COGNITIF", "07_BDF_DOUBLE_CERVEAU",
            "08_HEXAFLUX_LTCU_MUTATIONS", "arbres_34_tensor_matrix",
        ],
        "semantic_role": "AGENT_OR_TREE_SPEC",
    },
}

# Scan results — P33D double-evidence reconciliation (P33C ZIP + P33E Core Parent).
# P33C = ZIP OS_TRAD content-only audit (primary authority for ZIP layer).
# P33E = Core Parent curated audit (excludes _tmp_* scripts and matrix_cell_* as primary).
# Fields: evidence_status (reconciled), zip_evidence_status, core_parent_evidence_status,
#         evidence_basis, confidence_reason, source_files_count, strong_files_count,
#         canonicalization_needed, evidence_files.
_SCAN_RESULTS: Dict[str, Dict[str, Any]] = {
    "UNIVERSAL_LANGUAGE_LAYER": {
        "found": True,
        "matching_files_count": 7,
        "confidence": "HIGH",
        # Reconciled verdict: ZIP=PARTIAL_STRONG, Core Parent confirms via interlanguage canon
        "evidence_status": "PARTIAL_STRONG",
        "zip_evidence_status": "PARTIAL_STRONG",
        "core_parent_evidence_status": "CORE_PARENT_CANDIDATE",
        "evidence_basis": "P33C_ZIP + P33E_CORE_PARENT",
        "confidence_reason": (
            "ZIP P33C: 5 fichiers, termes grammaire/syntaxe/vocabulaire. LCTU absent. "
            "Core Parent P33E: reverse_os_interlanguage_canon_v1 confirme alphabet_ir et "
            "VOCABULAIRE_CANONIQUE. Langage universel complet non établi dans le ZIP."
        ),
        "source_files_count": 5,
        "strong_files_count": 5,
        "canonicalization_needed": False,
        "evidence_files": [
            "_local_audits/LOCAL_9_GROUPS_34_ARBRES_SOURCE_SCAN_20260512_220347/source_dumps/0125_5DF672EEB8C3_reverse_os_interlanguage_canon_v1.json.txt",
        ],
        "top_files": [
            "01_SOURCES/extracted_text_all.md",
            "10_AGENTS_52/02_DOCUMENTATION_THEORIE_FREEZE/VOCABULAIRE_CANONIQUE.md",
            "10_AGENTS_52/agents_52.csv",
            "10_AGENTS_52/agents_52.registry.json",
            "19_REGISTRES_JSON/agents_52.registry.json",
        ],
        "keywords_matched": ["langage universel", "grammaire", "syntaxe", "lexique", "vocabulaire"],
        "notes": "PARTIAL_STRONG dans ZIP. Core Parent confirme concept via interlanguage canon. LCTU absent des deux sources.",
    },
    "REVERSE_LANGUAGE_LAYER": {
        "found": True,
        "matching_files_count": 1,
        "confidence": "LOW",
        # ZIP=MEDIUM_SIGNAL. Core Parent has CORE_PARENT_CANDIDATE (reciproque_miroir formalisé).
        # Final verdict remains MEDIUM_SIGNAL — ZIP is primary. Core parent = candidate pending canonization.
        "evidence_status": "MEDIUM_SIGNAL",
        "zip_evidence_status": "MEDIUM_SIGNAL",
        "core_parent_evidence_status": "CORE_PARENT_CANDIDATE",
        "evidence_basis": "P33C_ZIP + P33E_CORE_PARENT",
        "confidence_reason": (
            "ZIP P33C: 1 fichier (extracted_text_all), termes miroir/inversion/réciproque. "
            "Core Parent P33E: reverse_os_interlanguage_canon_v1 définit formellement "
            "reciproque_miroir (math=f(x)=f⁻¹(x)), SCF Réciproque, TWIN_CALL dans DOCX "
            "Reverse OS. Canonicalization nécessaire pour promotion."
        ),
        "source_files_count": 1,
        "strong_files_count": 0,
        "canonicalization_needed": True,
        "evidence_files": [
            "_local_audits/LOCAL_9_GROUPS_34_ARBRES_SOURCE_SCAN_20260512_220347/source_dumps/0125_5DF672EEB8C3_reverse_os_interlanguage_canon_v1.json.txt",
            "_local_audits/DOCX_9_GROUPS_OSMOSE_SEARCH_20260512_222300/extracted_docx_text/L_Architecture_Narrative_du_Reverse_OS_d_Obsidia.docx.txt",
            "obsidia-engine-candidate/_local_audits/OBSIDIA_REVERSE_OS_AUDIENCE_ADAPTER_V1_20260508_224555/audience_packet_08_non_tech.json",
        ],
        "top_files": ["01_SOURCES/extracted_text_all.md"],
        "keywords_matched": ["réciproque", "miroir", "inversion"],
        "notes": "MEDIUM_SIGNAL dans ZIP. Core Parent a CORE_PARENT_CANDIDATE via interlanguage canon + DOCX Reverse OS. Non gonflé par le chemin REVERSE_OS.",
    },
    "IR_LAYER": {
        "found": True,
        "matching_files_count": 1,
        "confidence": "LOW",
        # ZIP=MEDIUM_SIGNAL. Core Parent has CORE_PARENT_CANDIDATE (interlanguage_canon L2 = IR Alphabet spec).
        "evidence_status": "MEDIUM_SIGNAL",
        "zip_evidence_status": "MEDIUM_SIGNAL",
        "core_parent_evidence_status": "CORE_PARENT_CANDIDATE",
        "evidence_basis": "P33C_ZIP + P33E_CORE_PARENT",
        "confidence_reason": (
            "ZIP P33C: 1 fichier (extracted_text_all), terme 'alphabet ir'. "
            "Core Parent P33E: reverse_os_interlanguage_canon_v1 définit formellement "
            "L2='IR Alphabet: VALUE STATE READ WRITE FLOW COND LOOP CALL RETURN EVENT TIME ERROR', "
            "audience_packet confirme alphabet_ir. Canonicalization nécessaire pour promotion."
        ),
        "source_files_count": 1,
        "strong_files_count": 0,
        "canonicalization_needed": True,
        "evidence_files": [
            "_local_audits/LOCAL_9_GROUPS_34_ARBRES_SOURCE_SCAN_20260512_220347/source_dumps/0125_5DF672EEB8C3_reverse_os_interlanguage_canon_v1.json.txt",
            "obsidia-engine-candidate/_local_audits/OBSIDIA_REVERSE_OS_AUDIENCE_ADAPTER_V1_20260508_224555/audience_packet_07_investor.json",
        ],
        "top_files": ["01_SOURCES/extracted_text_all.md"],
        "keywords_matched": ["alphabet ir", " ir "],
        "notes": "MEDIUM_SIGNAL dans ZIP. Core Parent a CORE_PARENT_CANDIDATE via interlanguage_canon (L2 = IR Alphabet formalisé). Canonicalization requise.",
    },
    "REVERSE_WINDOWS_LAYER": {
        "found": False,
        "matching_files_count": 0,
        "confidence": "NONE",
        # Both ZIP and Core Parent = NOT_FOUND. Double confirmation.
        "evidence_status": "NOT_FOUND",
        "zip_evidence_status": "NOT_FOUND",
        "core_parent_evidence_status": "NOT_FOUND",
        "evidence_basis": "P33C_ZIP + P33E_CORE_PARENT",
        "confidence_reason": (
            "P33C ZIP: 0 fichiers contenu. P33B: 1 occurrence 'window' insuffisante. "
            "P33E Core Parent: 0 entrées curated pour REVERSE_WINDOWS. Double NOT_FOUND."
        ),
        "source_files_count": 0,
        "strong_files_count": 0,
        "canonicalization_needed": False,
        "evidence_files": [],
        "top_files": [],
        "keywords_matched": [],
        "notes": "NOT_FOUND dans les deux sources (ZIP P33C + Core Parent P33E). Répertoires 16/13 présents mais concept windowing non confirmé.",
    },
    "LAWS_PROTOCOLS_LAYER": {
        "found": True,
        "matching_files_count": 202,
        "confidence": "HIGH",
        "evidence_status": "CORE_STRONG",
        "zip_evidence_status": "CORE_STRONG",
        "core_parent_evidence_status": "CORE_STRONG",
        "evidence_basis": "P33C_ZIP + P33E_CORE_PARENT",
        "confidence_reason": (
            "ZIP P33C: LOIS=22 fichiers, PROTOCOLES=97 = 119 fichiers contenu. "
            "Dirs dédiés (02_CONSTITUTION, 11_AGENTS_RUNTIME_CONTRACTS, 15_GUARDS). "
            "Core Parent P33E confirme CORE_STRONG. Double validation."
        ),
        "source_files_count": 119,
        "strong_files_count": 22,
        "canonicalization_needed": False,
        "evidence_files": [],
        "top_files": [
            "01_SOURCES/extracted_text_all.md",
            "00_INDEX/ARBORESCENCE_COMPLETE.md",
            "02_CONSTITUTION_LOIS_OBSIDIENNES/O1_NON_ACTION_LEGITIME.md",
            "11_AGENTS_RUNTIME_CONTRACTS/agent_boundary.md",
            "15_GUARDS_NON_DECISION/non_decision_formulas.md",
        ],
        "keywords_matched": ["loi", "lois", "laws", "protocole", "protocol", "non_decision", "boundary"],
        "notes": "CORE_STRONG dans ZIP et Core Parent. 119 fichiers contenu (22 LOIS + 97 PROTOCOLES).",
    },
    "AGENTS_TREES_LAYER": {
        "found": True,
        "matching_files_count": 397,
        "confidence": "HIGH",
        "evidence_status": "CORE_STRONG",
        "zip_evidence_status": "CORE_STRONG",
        "core_parent_evidence_status": "CORE_STRONG",
        "evidence_basis": "P33C_ZIP + P33E_CORE_PARENT",
        "confidence_reason": (
            "ZIP P33C: 397 fichiers, 34 dirs d'arbres, registry 52 agents. "
            "Core Parent P33E confirme CORE_STRONG. Couche dominante double-validée."
        ),
        "source_files_count": 397,
        "strong_files_count": 397,
        "canonicalization_needed": False,
        "evidence_files": [],
        "top_files": [
            "00_INDEX/ARBORESCENCE_COMPLETE.md",
            "04_ARBRES_34_TENSOR_MATRIX/ARBRE_01__Arbre_de_l_Humain/definition.md",
            "10_AGENTS_52/agents_52.registry.json",
            "05_SHAZAM_COGNITIF/shazam_spec.md",
            "07_BDF_DOUBLE_CERVEAU/BDF.schema.json",
        ],
        "keywords_matched": ["arbre", "arbres", "tree", "agent", "agents", "shazam", "bdf"],
        "notes": "CORE_STRONG dans ZIP et Core Parent. 397 fichiers, 34 arbres, 52 agents.",
    },
    "UNKNOWN_RELEVANT": {
        "found": False,
        "matching_files_count": 0,
        "confidence": "NONE",
        "evidence_status": "NOT_FOUND",
        "zip_evidence_status": "NOT_FOUND",
        "core_parent_evidence_status": "NOT_FOUND",
        "evidence_basis": "P33C_ZIP + P33E_CORE_PARENT",
        "confidence_reason": "Tous les fichiers classifiés dans des couches connues. Aucune preuve dans les deux sources.",
        "source_files_count": 0,
        "strong_files_count": 0,
        "canonicalization_needed": False,
        "evidence_files": [],
        "top_files": [],
        "keywords_matched": [],
        "notes": "Aucun fichier non classifié pertinent.",
    },
}


def _classify_entry_by_path(internal_path: str) -> str:
    """
    Classify an OS_TRAD registry entry into a semantic layer using path patterns.
    Returns layer name string. Never reads zip content.
    """
    path_lower = internal_path.lower().replace('\\', '/')

    for layer, defn in _LAYER_DEFINITIONS.items():
        # Check directory patterns first (strongest signal)
        for dir_pat in defn.get("dir_patterns", []):
            if dir_pat.lower() in path_lower:
                return layer

    for layer, defn in _LAYER_DEFINITIONS.items():
        # Check filename/path patterns
        fname = path_lower.split('/')[-1]
        for pat in defn.get("path_patterns", []):
            if pat in fname or pat in path_lower:
                return layer

    return "UNKNOWN_RELEVANT"


def classify_entry_layer(metadata: Dict[str, Any]) -> str:
    """
    Return the conceptual layer for a single OS_TRAD registry entry.
    Uses only metadata (internal_path, file_name). Never reads zip.
    """
    internal = metadata.get("internal_path", metadata.get("file_name", ""))
    return _classify_entry_by_path(internal)


def get_semantic_role(layer: str) -> str:
    """Return the semantic role for a layer."""
    defn = _LAYER_DEFINITIONS.get(layer)
    if defn:
        return defn["semantic_role"]
    return "UNKNOWN"


def build_os_trad_deep_concept_index(
    entries: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Build the OS_TRAD deep concept index.

    If entries is provided, recomputes layer distribution from them.
    Otherwise returns the static scan results from P33 analysis.

    Never reads zip. Never executes .py. KX108_ONLY. Advisory / readonly.
    """
    if entries is not None:
        os_trad = [e for e in entries if getattr(e, "source_family", None) == "OS_TRAD_REVERSE_OS"]
        total_safe = len(os_trad)
        total_exec = sum(
            1 for e in os_trad
            if getattr(e, "extension", "").lower() in {".py", ".ps1", ".sh", ".bat", ".exe"}
        )

        layer_counts: Dict[str, int] = {layer: 0 for layer in _LAYER_DEFINITIONS}
        layer_counts["UNKNOWN_RELEVANT"] = 0
        for e in os_trad:
            layer = _classify_entry_by_path(getattr(e, "internal_path", ""))
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

        layers = {}
        for layer, count in layer_counts.items():
            static = _SCAN_RESULTS.get(layer, {})
            layers[layer] = {
                "found": count > 0,
                "matching_files_count": count,
                "confidence": "HIGH" if count >= 20 else "MEDIUM" if count >= 3 else "LOW" if count >= 1 else "NONE",
                "top_files": static.get("top_files", []),
                "keywords_matched": static.get("keywords_matched", []),
                "notes": static.get("notes", ""),
                # P33D evidence fields — always from static P33C+P33E authority
                "evidence_status": static.get("evidence_status", "NOT_FOUND"),
                "zip_evidence_status": static.get("zip_evidence_status", "NOT_FOUND"),
                "core_parent_evidence_status": static.get("core_parent_evidence_status", "NOT_FOUND"),
                "evidence_basis": static.get("evidence_basis", "P33C_ZIP + P33E_CORE_PARENT"),
                "confidence_reason": static.get("confidence_reason", ""),
                "source_files_count": static.get("source_files_count", 0),
                "strong_files_count": static.get("strong_files_count", 0),
                "canonicalization_needed": static.get("canonicalization_needed", False),
                "evidence_files": static.get("evidence_files", []),
            }
    else:
        # Use static results from P33 zip scan
        layers = {k: dict(v) for k, v in _SCAN_RESULTS.items()}
        total_safe = 546
        total_exec = 64

    return {
        "family": "OS_TRAD_REVERSE_OS",
        "safe_entries_count": total_safe,
        "excluded_executables_count": total_exec,
        "decision_authority": "KX108_ONLY",
        "advisory_only": True,
        "readonly": True,
        "emits_act": False,
        "runtime_allowed_now": False,
        "universal_language_layer": layers.get("UNIVERSAL_LANGUAGE_LAYER", {}),
        "reverse_language_layer": layers.get("REVERSE_LANGUAGE_LAYER", {}),
        "ir_layer": layers.get("IR_LAYER", {}),
        "reverse_windows_layer": layers.get("REVERSE_WINDOWS_LAYER", {}),
        "laws_protocols_layer": layers.get("LAWS_PROTOCOLS_LAYER", {}),
        "agents_trees_layer": layers.get("AGENTS_TREES_LAYER", {}),
        "unknown_relevant": layers.get("UNKNOWN_RELEVANT", {}),
    }
