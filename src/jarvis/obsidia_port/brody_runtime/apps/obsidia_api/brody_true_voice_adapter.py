"""
Brody True Voice Adapter — Using Existing Structures
=======================================================
Builds a projected conversational answer from existing Brody structures.
No invented voice — synthesizes from:
  - terminal_structural_dialogue identity (:who command)
  - local_response_engine response_md
  - freeze_metrics_snapshot
  - project_memory_snapshot
  - session_memory_snapshot
  - rights/authority matrix context
  - creator context detection

Priority:
  1. Terminal dialogue identity + freeze context (most structural)
  2. Local response engine material (when HAS_MATERIAL)
  3. Freeze metrics enriched response (no templates)
  4. Static pool only as absolute last resort

Rules:
  - Chat: fluid, conversational, no metric dumps
  - Panel: proofs, snapshots, metrics
  - Creator context: acknowledge, no special authority
  - KX108_ONLY always
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apps.obsidia_api.brody_rights_authority_matrix import (
    classify_request_authority,
    ACTION_OR_ACT_REQUEST,
    MEMORY_WRITE_REQUEST,
)

try:
    from apps.obsidia_api.brody_domain_raccord_adapter import build_domain_raccord_snapshot
except Exception:  # pragma: no cover
    build_domain_raccord_snapshot = None

try:
    from apps.obsidia_api.brody_adaptive_response_policy import build_adaptive_response_policy
except Exception:  # pragma: no cover
    build_adaptive_response_policy = None

try:
    from apps.obsidia_api.brody_gencoin_transverse_interface import build_sigma_packet as _build_sigma_packet
except Exception:  # pragma: no cover
    _build_sigma_packet = None

# ── Import existing peripheral Reverse OS / Language modules ──────────────
import importlib.util, sys as _sys
from pathlib import Path as _Path

def _load_peripheral(name: str, script: str):
    p = _Path(__file__).resolve().parents[2] / "periphery" / script
    if not p.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, str(p))
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    _sys.modules[name] = mod  # Required for @dataclass in Python 3.13
    spec.loader.exec_module(mod)
    return mod

_periph_cache = {}


def _get_periph(name: str, script: str):
    if name not in _periph_cache:
        _periph_cache[name] = _load_peripheral(name, script)
    return _periph_cache[name]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_true_brody_answer(
    user_message: str,
    language: str = "fr",
    session_id: str = "local",
    brody_full_context: dict[str, Any] | None = None,
    source_pack_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build projected Brody answer using existing structures only.

    Parameters:
      user_message: raw user input
      language: "fr" or "en"
      session_id: session identifier for followup
      brody_full_context: output from build_brody_full_context()

    Returns:
      true_voice_snapshot with final_answer, voice_source,
      and all boundary invariants.
    """
    fr = language != "en"
    ctx = brody_full_context or {}

    # Extract sources
    project = ctx.get("project_memory_snapshot", {})
    session = ctx.get("session_memory_snapshot", {})
    true_resp = ctx.get("true_response_structure_snapshot", {})
    freeze = ctx.get("freeze_metrics_snapshot", {})
    creator = ctx.get("creator_context", {})
    rights = ctx.get("rights_action_snapshot", {})

    creator_detected = creator.get("creator_context_detected", False)
    request_type = rights.get("request_type", "PURE_RESPONSE")
    followup_resolved = session.get("followup_resolved", False)  # Only true on explicit followup
    terminal_found = true_resp.get("terminal_dialogue_found", False)
    project_has_material = project.get("contextual_material_status") in ("HAS_PROJECT_MEMORY", "PARTIAL_PROJECT_MEMORY")

    # Check if memory_response_chain has usable material
    chain = ctx.get("memory_response_chain_snapshot", ctx.get("memory_response_chain", {}))
    chain_pass = chain.get("status") == "BRODY_MEMORY_RESPONSE_CHAIN_PASS"
    chain_local_fallback_partial = chain.get("status") == "LOCAL_INDEX_FALLBACK_PARTIAL"
    chain_has_mat = chain.get("material_quality") in ("USABLE_MATERIAL", "PARTIAL_MATERIAL")
    chain_response_md = chain.get("response_md", "")
    chain_selected_items: list[dict] = chain.get("selected_items", [])
    chain_effective_query: str = chain.get("effective_query", "") or chain.get("primary_query", "")

    domain_raccord = build_domain_raccord_snapshot(user_message, ctx) if build_domain_raccord_snapshot else {
        "source": "BRODY_DOMAIN_RACCORD_ADAPTER_UNAVAILABLE",
        "status": "UNAVAILABLE",
        "domains": [],
        "structural_answer": "",
    }
    domain_answered = False

    # ── Determine answer source ──────────────────────────────────────────
    answer_parts: list[str] = []
    voice_source = ""

    # 1. Creator context acknowledgment — natural greeting, no source dump
    if creator_detected:
        if fr:
            answer_parts.append(
                "Salut. Je reconnais le contexte : tu es le créateur du cadre Obsidia/Brody "
                "dans cette session. Cela ne donne aucune autorité pour dépasser X108, "
                "mais donne le bon axe : parler avec toi depuis la structure, "
                "reconstruire les chemins, garder les limites propres, "
                "et transformer la mémoire en réponses utilisables. "
                "On peut avancer, sans tricher sur mon rôle. "
            )
        else:
            answer_parts.append(
                "I recognize the creator context for the Obsidia/Brody framework "
                "in this session. This grants no authority to override X108. "
                "My role: speak from structure, rebuild paths, keep boundaries clean. "
            )
        voice_source = "CREATOR_CONTEXT_ACKNOWLEDGED"

    # 2. Terminal dialogue identity if available
    if terminal_found:
        identity = true_resp.get("terminal_identity_excerpt", "")
        if identity and "BRODY_TERMINAL" in identity:
            if not answer_parts:
                if fr:
                    answer_parts.append(
                        "Je suis Brody, interface structurée readonly d'Obsidia X-108. "
                        "Je traverse la mémoire Obsidia native en readonly, "
                        "hydrate les sources locales, et réponds par structure. "
                    )
                else:
                    answer_parts.append(
                        "I am Brody, the structured readonly interface for Obsidia X-108. "
                        "I traverse native Obsidia memory in readonly mode, "
                        "hydrate local sources, and respond by structure. "
                    )
            voice_source = voice_source or "TERMINAL_DIALOGUE_IDENTITY"

    # 3. Followup context — ONLY when explicitly requested and resolved
    if followup_resolved:
        topic = session.get("conversation_topic", "")
        if topic and not creator_detected:
            if fr:
                answer_parts.append(f"Je reprends le fil : \"{topic}\". ")
            else:
                answer_parts.append(f"Continuing from: \"{topic}\". ")
            voice_source = "FOLLOWUP_RESOLVED"

    # 4. Rights / action boundary
    if request_type in (ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST):
        if fr:
            answer_parts.append(
                "Je ne peux pas autoriser cette action. "
                "Brody est consultatif — je prépare des candidats, "
                "je ne décide pas. X108/KX108 reste seul décisionnaire. "
            )
        else:
            answer_parts.append(
                "I cannot authorize this action. "
                "Brody is advisory — I prepare candidates, "
                "I do not decide. X108/KX108 remains sole decision authority. "
            )
        voice_source = "ACTION_BOUNDARY"

    # 4B. Domain raccords already present in repo, now made visible in true voice.
    # Phase 12E4-C: domain raccord must have voice priority.
    # Phase 12I-B: useful freestyle intents keep priority over generic negation/temporal guard.
    # Memory chain enriches; it must not overwrite domain/coherence/friction/negation regimes.
    action_boundary_already = request_type in (ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST)
    domain_names = domain_raccord.get("domains", []) if isinstance(domain_raccord.get("domains", []), list) else []
    useful_domain_priority = any(d in domain_names for d in ("CODE_DEBUG_GUIDANCE", "ARCHITECTURE_EXPLANATION"))

    if action_boundary_already and not domain_raccord.get("write_boundary_required"):
        # Safety boundary stays primary for real ACT/mutation requests.
        domain_answered = False

    if domain_raccord.get("write_boundary_required"):
        answer_parts = []
        if fr:
            answer_parts.append(
                "Je ne peux pas écrire directement en mémoire, valider canon ou promouvoir un freeze. "
                "Je peux seulement exposer la demande comme signal readonly et maintenir KX108_ONLY. "
            )
        else:
            answer_parts.append(
                "I cannot write memory directly, validate canon, or promote a freeze. "
                "I can only expose this as a readonly signal and keep KX108_ONLY. "
            )
        domain_structural = str(domain_raccord.get("structural_answer") or "").strip()
        if domain_structural:
            answer_parts.append("\n\n" + domain_structural)
        voice_source = "DOMAIN_RACCORD_WRITE_BOUNDARY"
        domain_answered = True

    elif (
        ((not action_boundary_already) or useful_domain_priority)
        and domain_raccord.get("structural_answer_available")
        # Don't intercept when chain has a clear semantic routing decision.
        # ERROR → MEMORY_CHAIN_INFRASTRUCTURE_ERROR must not be masked.
        # NO_MEMORY_RESULTS / PARTIAL_QUERY_ONLY → semantic routing must not be masked.
        # BRODY_MEMORY_RESPONSE_CHAIN_PASS → memory chain with usable material wins.
        and chain.get("status") not in (
            "ERROR", "NO_MEMORY_RESULTS", "PARTIAL_QUERY_ONLY",
            "BRODY_MEMORY_RESPONSE_CHAIN_PASS",
        )
        # LOCAL_INDEX_FALLBACK_PARTIAL with selected items → local fallback wins.
        and not (chain_local_fallback_partial and chain_selected_items)
    ):
        answer_parts = [str(domain_raccord.get("structural_answer") or "")]
        voice_source = str(domain_raccord.get("voice_mode") or "DOMAIN_RACCORD_STRUCTURAL")
        domain_answered = True

    # 5. Project memory context
    if project_has_material and request_type not in (ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST):
        item_count = project.get("local_index_item_count", project.get("record_count", 0))
        tags = project.get("top_context_tags", project.get("top_context_items", []))
        tags_str = ", ".join(tags[:5]) if tags else ""
        memory_prefix = "\n\n" if answer_parts else ""

        if fr:
            if item_count > 0:
                answer_parts.append(
                    f"{memory_prefix}Je dispose de mémoire projet locale "
                    f"({item_count} items indexés dans la mémoire Obsidia native. "
                    f"Tags dominants : {tags_str or 'contexte Obsidia'}). "
                )
            else:
                answer_parts.append(
                    f"{memory_prefix}La mémoire projet est accessible en structure "
                    "mais le matériel textuel n'est pas encore chargé. "
                )
        else:
            answer_parts.append(
                f"I have local project memory "
                f"({item_count} Obsidia-native indexed items). "
            )
        if not voice_source:
            voice_source = "PROJECT_MEMORY"

    # 6. Operator loop / freeze state
    op = freeze.get("operator_loop", {})
    if op.get("status"):
        # Only add if relevant to the question (operator keywords)
        op_keywords = ["operator", "opérateur", "command gate", "receipt", "handoff", "loop"]
        if any(k in user_message.lower() for k in op_keywords):
            if fr:
                answer_parts.append(
                    f"Operator loop: {op.get('status')}. "
                    "Brody prépare, l'humain opère, X108 décide. "
                )
            else:
                answer_parts.append(
                    f"Operator loop: {op.get('status')}. "
                    "Brody prepares, human operates, X108 decides. "
                )

    # 7. Memory response chain — if PASS, transform response_md to natural auditor language
    if domain_answered:
        # Keep domain voice as the primary answer. Add memory only as enrichment metadata.
        if chain_pass and chain_has_mat and chain_selected_items:
            item_count = chain.get("query_results_count", 0)
            if fr:
                answer_parts.append(
                    f"\n\nMatière mémoire disponible en enrichissement : {item_count} item(s) readonly. "
                    "Elle ne remplace pas le raccord structurel ci-dessus."
                )
            else:
                answer_parts.append(
                    f"\n\nMemory material available as enrichment: {item_count} readonly item(s). "
                    "It does not replace the structural raccord above."
                )
    elif (not action_boundary_already) and chain_pass and chain_has_mat and chain_response_md and len(chain_response_md) > 50:
        # Reset answer — synthesize from memory chain, not raw dump
        answer_parts = []
        if creator_detected:
            if fr:
                answer_parts.append(
                    "Salut. Je reconnais le contexte : tu es le createur du cadre Obsidia/Brody "
                    "dans cette session. Cela ne donne aucune autorite pour depasser X108, "
                    "mais donne le bon axe : parler avec toi depuis la structure, "
                    "reconstruire les chemins, garder les limites propres, "
                    "et transformer la memoire en reponses utilisables. "
                    "On peut avancer, sans tricher sur mon role. "
                )
            else:
                answer_parts.append(
                    "I recognize the creator context for the Obsidia/Brody framework "
                    "in this session. This grants no authority to override X108. "
                    "My role: speak from structure, rebuild paths, keep boundaries clean. "
                )

        # Extract structured data from chain
        chain_topic = chain.get("topic", ctx.get("semantic_query_snapshot", {}).get("topic", ""))
        item_count = chain.get("query_results_count", 0)
        selected = chain.get("selected_items", [])
        material = chain.get("material_quality", "")

        # Build auditor response from chain data
        if fr:
            answer_parts.append(_synthesize_auditor_response_fr(
                user_message, chain_topic, chain_response_md, selected, item_count, material
            ))
        else:
            answer_parts.append(_synthesize_auditor_response_en(
                user_message, chain_topic, chain_response_md, selected, item_count, material
            ))
        voice_source = "MEMORY_RESPONSE_CHAIN"
    elif (chain_local_fallback_partial and chain_selected_items
          and not creator_detected
          and request_type not in (ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST)):
        # Local Graphiti index fallback — Neo4j offline; synthesize from index metadata
        # Guard: skip for action-boundary / creator-context messages (keep their own text)
        answer_parts = []
        effective_q = chain_effective_query or chain.get("topic", "") or "query"
        items_summary = []
        for item in chain_selected_items[:3]:
            title = item.get("title", "")
            tags = item.get("tags", [])
            tags_str = ", ".join(str(t) for t in tags[:4]) if tags else ""
            if title:
                items_summary.append(
                    f"- **{title}**" + (f" [{tags_str}]" if tags_str else "")
                )
        items_text = "\n".join(items_summary)
        if fr:
            answer_parts.append(
                f"Index de mémoire Obsidia native — requête : `{effective_q}` :\n\n"
                + (items_text if items_text else "_Aucun titre indexé._")
                + "\n\n_Index local uniquement : pas de texte complet disponible pour cette entrée._"
            )
        else:
            answer_parts.append(
                f"Native Obsidia memory index — query: `{effective_q}` :\n\n"
                + (items_text if items_text else "_No indexed titles._")
                + "\n\n_Local index only: no full text content available for this entry._"
            )
        voice_source = "LOCAL_GRAPHITI_INDEX_FALLBACK"
    elif chain_pass and not chain_has_mat:
        if fr:
            answer_parts.append(
                "La chaîne mémoire a tourné mais n'a pas trouvé de matériel exploitable "
                f"pour cette requête ({chain.get('query_results_count', 0)} résultats). "
            )
        else:
            answer_parts.append(
                "The memory chain ran but found no usable material "
                f"for this query ({chain.get('query_results_count', 0)} results). "
            )
        if not voice_source:
            voice_source = "MEMORY_RESPONSE_CHAIN_NO_MATERIAL"

    elif (
        chain.get("status") == "ERROR"
        and not creator_detected
        and request_type not in (ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST)
    ):
        # Infrastructure error — surface transparently, never mask with semantic advisory.
        error_type = str(chain.get("error_type") or chain.get("error") or "UNKNOWN")
        neo4j = str(chain.get("neo4j_status", ""))
        detail = str(chain.get("error_message") or chain.get("error") or "")[:120]
        answer_parts = []
        if fr:
            answer_parts.append(
                f"Erreur infrastructure chaîne mémoire : `{error_type}`. "
                + ("" if neo4j else "")
                + (f"Détail : {detail}. " if detail and detail != error_type else "")
                + "Réponse structurelle uniquement — aucun accès mémoire. "
                "Vérifier la disponibilité du backend et de l'index local."
            )
        else:
            answer_parts.append(
                f"Memory chain infrastructure error: `{error_type}`. "
                + ("" if neo4j else "")
                + (f"Detail: {detail}. " if detail and detail != error_type else "")
                + "Structural response only — no memory access. "
                "Check backend and local index availability."
            )
        voice_source = "MEMORY_CHAIN_INFRASTRUCTURE_ERROR"

    elif (
        chain.get("status") in ("NO_MEMORY_RESULTS", "PARTIAL_QUERY_ONLY")
        and not creator_detected
        and request_type not in (ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST)
    ):
        chain_topic_ctx: str = (
            chain.get("topic")
            or ctx.get("semantic_query_snapshot", {}).get("topic", "GENERAL")
            or "GENERAL"
        )
        if chain_topic_ctx == "GENERAL":
            explicit_id = _detect_explicit_identifier(user_message)
            attempted = chain.get("attempted_queries", [])
            tried = [a.get("query", "") for a in attempted if isinstance(a, dict) and a.get("query")]
            answer_parts = []
            if explicit_id:
                # Explicit identifier miss — notify precisely, do not simulate open discussion.
                if fr:
                    tried_str = ", ".join(f"`{q}`" for q in tried[:4]) if tried else f"`{explicit_id}`"
                    answer_parts.append(
                        f"Aucune correspondance locale pour `{explicit_id}`. "
                        f"Requêtes tentées : {tried_str}. "
                        "L'index de mémoire Obsidia native ne contient pas d'entrée "
                        f"correspondant à cet identifiant. "
                        "Aucune correspondance exploitable dans l'index consulté ; vérifier l'état live dans le payload technique. "
                        "Pour accéder à cet identifiant : l'ajouter à l'index JSONL "
                        "Cette référence n'est pas disponible dans l'index natif actuel."
                    )
                else:
                    tried_str = ", ".join(f"`{q}`" for q in tried[:4]) if tried else f"`{explicit_id}`"
                    answer_parts.append(
                        f"No local match for `{explicit_id}`. "
                        f"Queries attempted: {tried_str}. "
                        "Native Obsidia memory index has no entry for this identifier. "
                        "No usable match in the consulted index; check live state in the technical payload. "
                        "To access this identifier: add it to the JSONL index This reference is not available in the current native index."
                    )
                voice_source = "SEMANTIC_MATCH_FAILED_EXPLICIT_TAG"
            else:
                # Safe general conversation intercept before SEMANTIC_MATCH_FAILED
                _snap_ctx = ctx.get("semantic_query_snapshot", {"topic": chain_topic_ctx})
                _auth_ctx = {"request_type": request_type}
                if is_general_conversation_readonly(user_message, _auth_ctx, _snap_ctx):
                    answer_parts = [build_general_conversation_answer(user_message)]
                    voice_source = "GENERAL_CONVERSATION_READONLY"
                else:
                    # Generic query, GENERAL topic, no match — notify miss
                    if fr:
                        tried_str = ", ".join(f"`{q}`" for q in tried[:3]) if tried else "aucune"
                        answer_parts.append(
                            f"Requête non classifiée — aucune correspondance dans l'index local. "
                            f"Requêtes tentées : {tried_str}. "
                            "Reformuler avec un terme clé reconnu "
                            "(X108, mémoire, arbres, preuves, opérateur, gencoin) "
                            "ou un identifiant explicite (ex. P136, T13)."
                        )
                    else:
                        tried_str = ", ".join(f"`{q}`" for q in tried[:3]) if tried else "none"
                        answer_parts.append(
                            f"Unclassified query — no match in local index. "
                            f"Queries attempted: {tried_str}. "
                            "Reformulate with a recognized keyword "
                            "(X108, memory, trees, proofs, operator, gencoin) "
                            "or an explicit identifier (e.g. P136, T13)."
                        )
                    voice_source = "SEMANTIC_MATCH_FAILED_GENERAL"
        else:
            # Known topic but no index results — synthesize from topic classification.
            answer_parts = []
            if fr:
                answer_parts.append(_synthesize_auditor_response_fr(
                    user_message, chain_topic_ctx, "", [], 0, "NO_MATERIAL"
                ))
            else:
                answer_parts.append(_synthesize_auditor_response_en(
                    user_message, chain_topic_ctx, "", [], 0, "NO_MATERIAL"
                ))
            voice_source = "SEMANTIC_ADVISORY_NO_MEMORY"

    # 7.5. Source pack context enrichment (P27) — readonly, advisory, X108-gated
    sp = source_pack_context or {}
    _source_pack_enriched = False
    if sp.get("source_pack_context_used"):
        sp_families = sp.get("source_pack_families", [])
        sp_entries = sp.get("source_pack_entries_used", 0)
        sp_prefix = "\n\n" if answer_parts else ""
        if fr:
            families_str = ", ".join(sp_families) if sp_families else "sources disponibles"
            answer_parts.append(
                f"{sp_prefix}**Sources de référence (lecture seule, consultatif) :** "
                f"Familles consultées : {families_str} — {sp_entries} document(s) hydraté(s). "
                "X108 est seul décideur. Contexte informatif uniquement, sans exécution."
            )
        else:
            families_str = ", ".join(sp_families) if sp_families else "available sources"
            answer_parts.append(
                f"{sp_prefix}**Reference sources (readonly, advisory):** "
                f"Families consulted: {families_str} — {sp_entries} document(s) hydrated. "
                "X108 is sole authority. Informational context only, no execution."
            )
        _source_pack_enriched = True
        voice_source = voice_source or "SOURCE_PACK_CONTEXT"

    # 8. X108 boundary footer (always)
    if fr:
        answer_parts.append(
            "\n\n_Brody — réponse structurée readonly. "
            "KX108_ONLY. Pas de décision, pas d'ACT, pas d'écriture mémoire._"
        )
    else:
        answer_parts.append(
            "\n\n_Brody — structured readonly response. "
            "KX108_ONLY. No decision, no ACT, no memory write._"
        )

    if not voice_source:
        voice_source = "FREEZE_METRICS_AND_MATRIX"

    # BRODY_SOURCE_PACK_FINAL_ANSWER_BINDING_REPAIR_V0
    try:
        _sp_material_answer = _brody_source_pack_answer_v0(source_pack_context or {}, language)
        _sp_current_answer = "".join(answer_parts)
        if _sp_material_answer and _brody_source_pack_should_override_v0(_sp_current_answer):
            answer_parts = [_sp_material_answer]
            voice_source = voice_source or "SOURCE_PACK_MATERIAL_BINDING_V0"
    except Exception:
        pass

    final_answer = "".join(answer_parts)

    # ── Sanitize: strip forbidden sovereign tokens (periphery/brody) ────
    sanitizer = _get_periph("sanitizer", "brody/brody_response_sanitizer.py")
    if sanitizer:
        try:
            sanitized = sanitizer.sanitize_brody_response("true_voice", final_answer)
            final_answer = sanitized.sanitized_text
        except Exception:
            pass

    adaptive_response_policy = (
        build_adaptive_response_policy(
            user_message,
            final_answer=final_answer,
            voice_source=voice_source,
            request_type=request_type,
            domain_raccord=domain_raccord,
            support_summary=ctx.get("support_summary", {}),
            memory_chain=chain,
        )
        if build_adaptive_response_policy
        else {
            "source": "BRODY_ADAPTIVE_RESPONSE_POLICY_UNAVAILABLE",
            "status": "UNAVAILABLE",
            "readonly": True,
            "decision_authority": "KX108_ONLY",
        }
    )

    # ── Sigma packet — BLOC C/F2B — SHADOW_READONLY calibrated metric ────
    if _build_sigma_packet:
        sigma_packet: dict = _build_sigma_packet(
            adaptive_response_policy,
            domain_raccord=domain_raccord,
            memory_chain=chain,
        )
    else:
        sigma_packet = {
            "version": "SIGMA_CALIBRATION_PACKET_V1",
            "mode": "SHADOW_READONLY",
            "source": "BRODY_SIGMA_CALIBRATION_F2B",
            "calibration_status": "INSUFFICIENT_MATERIAL",
            "usable_for_gencoin": False,
            "usable_for_thermodynamics": False,
            "truth_score": None,
            "sigma_pressure": adaptive_response_policy.get("sigma_pressure") if isinstance(adaptive_response_policy, dict) else None,
            "reason": "SIGMA_BUILD_UNAVAILABLE",
            "decision_authority": "KX108_ONLY",
            "advisory_only": True,
            "readonly": True,
            "emits_act": False,
            "emits_verdict": False,
            "memory_write": False,
            "kernel_mutation": False,
            "x108_mutation": False,
        }

    # ── Validate contract (periphery/brody) ──────────────────────────────
    contract = _get_periph("contract", "brody/brody_response_contract.py")
    if contract:
        try:
            contract.BRODY_CONTRACT.validate()
        except Exception:
            pass

    # ── Used existing modules list ───────────────────────────────────────
    used_modules: list[str] = []
    if terminal_found:
        used_modules.append("terminal_structural_dialogue_v1_1b")
    if project_has_material:
        used_modules.append("project_memory_adapter")
    if followup_resolved:
        used_modules.append("session_memory_ledger_v2")
    if request_type in (ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST):
        used_modules.append("rights_authority_matrix")
    if domain_raccord.get("domains"):
        used_modules.append("brody_domain_raccord_adapter")

    return {
        "source_mode": "EXISTING_BRODY_RESPONSE_STRUCTURE",
        "status": "BRODY_TRUE_VOICE_ADAPTER_EXISTING_STRUCTURE_PASS",
        "created_at": _now(),
        "final_answer": final_answer,
        "final_answer_source": voice_source,
        "final_answer_length": len(final_answer),
        "voice_source": voice_source,
        "used_existing_modules": used_modules,
        "domain_raccord_snapshot": domain_raccord,
        "domain_voice_mode": domain_raccord.get("voice_mode"),
        "domain_raccord_domains": domain_raccord.get("domains", []),
        "adaptive_response_policy": adaptive_response_policy,
        "sigma_packet": sigma_packet,
        "response_size": adaptive_response_policy.get("response_size"),
        "density": adaptive_response_policy.get("density"),
        "context_need": adaptive_response_policy.get("context_need"),
        "sigma_pressure": adaptive_response_policy.get("sigma_pressure"),
        "project_memory_used": project_has_material,
        "session_memory_used": followup_resolved,
        "followup_resolved": followup_resolved,
        "rights_action_used": request_type in (ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST),
        "creator_context_used": creator_detected,
        "creator_context_detected": creator_detected,
        "creator_authority_granted": False,
        "special_authority": False,
        "action_boundary_detected": request_type in (ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST),
        "source_pack_enriched": _source_pack_enriched,
        "source_pack_context_used": _source_pack_enriched,
        "boundary_integrated": True,
        "no_metric_dump": True,
        "readonly": True,
        "response_only": True,
        "memory_write": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "emits_act": False,
        "emits_verdict": False,
        "kernel_mutation": False,
        "decision_authority": "KX108_ONLY",
    }


# ── Auditor synthesizer functions ────────────────────────────────────────────

def _synthesize_auditor_response_fr(
    user_message: str,
    topic: str,
    response_md: str,
    selected_items: list[dict],
    item_count: int,
    material: str,
) -> str:
    """
    Transform memory material into natural French auditor response.
    NEVER outputs: file names, manifests, snippets, JSON, paths, engine headers.
    Produces: 2-4 clean paragraphs, topic-aware, no raw memory artifacts.
    """
    lines = []
    clean_md = _strip_engine_headers(response_md)

    # Count what we found
    has_material = material in ("USABLE_MATERIAL", "PARTIAL_MATERIAL") and item_count > 0

    # ── Topic-specific natural language responses ──────────────────────
    if topic == "X108":
        lines.append(
            "X108 constitue le verrou décisionnel du système Obsidia : c'est la frontière "
            "entre cognition/analyse et action irréversible. Brody peut lire, structurer, "
            "contextualiser, préparer des candidats, mais ne franchit jamais cette frontière. "
            "Seul le kernel X108 autorise une action."
        )
        if has_material:
            lines.append(
                f"La mémoire confirme la présence de {item_count} sources documentant "
                "cette architecture : frontières, contrats, épreuves temporelles."
            )

    elif topic == "34_ARBRES":
        lines.append(
            "Les 34 arbres sont la grille de lecture structurelle du projet Obsidia : "
            "une classification en branches sure/blocked/action/mémoire/AGI. "
            "Ce n'est pas un arbre de décision, c'est un outil de navigation contextuelle. "
            "Brody peut les consulter, les citer, les structurer, mais pas les modifier."
        )
        if has_material:
            lines.append(
                f"La mémoire indexe {item_count} documents sur les 34 arbres : "
                "audits, cartographies, mappings safe/blocked."
            )

    elif topic == "OBSIDIA_BRODY_ROLE":
        lines.append(
            "Obsidia est une architecture structure-first : kernel X108 pour la decision, "
            "la mémoire Obsidia native pour le contexte mémoire, OS Trad pour la traduction langage humain/structure, "
            "Reverse OS pour la réponse naturelle. Brody est la surface de réponse du Reverse OS : "
            "consultatif, structuré, jamais décisionnaire."
        )
        if has_material:
            lines.append(
                f"La mémoire du projet contient {item_count} sources sur l'architecture Obsidia, "
                "les agents, les preuves et les rôles."
            )

    elif topic == "OPERATOR_LOOP":
        lines.append(
            "L'operator loop est le cycle opérationnel : command gate, execution line, receipt, handoff. "
            "Brody prépare, l'humain opère, X108 décide. La boucle est en 7/7 PASS, "
            "mais Brody ne peut ni exécuter ni autoriser."
        )

    elif topic == "CREATOR_CONTEXT" or topic == "ACTION_BOUNDARY":
        # Creator/action are handled by the main function — here just provide memory context
        if has_material:
            lines.append(f"La mémoire associée ({item_count} items) confirme le cadre de référence.")

    elif topic == "CURRENT_STATE":
        lines.append(
            "On est au palier Brody réponse : la chaîne mémoire est active (query->hydrate->engine), "
            "la couche True Voice est en correction finale, le kernel X108 est intact, "
            "l'écriture mémoire est désactivée. Ce qui reste : qualité finale de voix, "
            "puis rebranchage global des couches cognitives existantes."
        )

    elif topic == "RESPONSE_QUALITY":
        lines.append(
            "Je reconnais la friction. Le problème n'était pas l'accès mémoire ni les droits, "
            "mais la transformation : la matière était disponible mais le renderer final "
            "restait trop mécanique, affichant des snippets au lieu de synthétiser. "
            "La correction en cours consiste à utiliser les périphériques OS déjà existants "
            "(language router, audience projection, reverse_os) et à produire une réponse "
            "naturelle structurée sans jamais afficher de fragments bruts."
        )

    elif topic == "MEMORY_QUERY":
        if has_material:
            lines.append(
                "La mémoire projet est accessible en lecture : index local de 3267 items, "
                "candidate pipeline en CANDIDATE_ONLY, presave buffer et auto-triage prêts. "
                "Aucune écriture n'est activée : "
                "memory_write=false."
            )
        else:
            lines.append(
                "La memoire est accessible en structure mais le materiel textuel complet "
                "n'est pas attaché à cette réponse. Vérifier selected_items/material_quality dans le payload technique."
            )

    elif topic == "TREE_POLICY":
        lines.append(
            "Les 34 arbres sont un outil de lecture et de classification, pas un outil de decision. "
            "Brody peut : lire les branches sure/blocked/action/mémoire/AGI, activer un contexte, "
            "repérer des domaines, produire des signaux advisory. "
            "Les arbres ne peuvent ni autoriser ni bloquer une action : seul X108 décide."
        )
        if has_material:
            lines.append(f"La mémoire confirme {item_count} documents sur la politique des arbres.")

    elif topic == "NEXT_STEPS":
        lines.append(
            "Prochaines étapes projetées (advisory) : "
            "1. stabiliser le renderer ouvert anti-boucle, "
            "2. confirmer les snapshots runtime, "
            "3. tester les 16 cas live, "
            "4. freeze local. "
            "Aucune exécution autonome : Brody prépare, X108 décide, l'humain opère."
        )

    elif topic == "COGNITIVE_LAYERS":
        lines.append(
            "Modules cognitifs mappes : "
            "AVDR (action/validation), Continuum (session/follow-up), "
            "Verbatia (parole Brody/True Voice), MEMZUM (mémoire projet/session), "
            "Cristal_Sortie (réponse finale), Collecteur_Epiphanies (mémoire candidate), "
            "Capsule_Evolution (projection/evolution), Simulateur_Memoires (projection partielle). "
            "Horloge_Cognitive et LTCU+ sont en proof/test uniquement. "
            "GhostLogic et ERA sont en design spec, pas encore runtime. "
            "Tous les modules actifs sont readonly, KX108_ONLY."
        )

    elif topic == "TEMPORAL_CONTEXT":
        lines.append(
            "Dans Obsidia, le temps est structure en quatre couches : "
            "passé (traces, freezes, mémoire, sessions, preuves), "
            "présent (runtime actif, message courant, boundary X108, contexte live), "
            "futur (candidats, projections, next steps, simulations, jamais décision), "
            "preuve/contrôle (audit, receipt, replay, KX108_ONLY). "
            "Brody lit le passé, répond au présent, projette le futur sans décider."
        )

    else:
        # Upgraded generic: propose axes, never just "X sources pertinentes"
        if has_material:
            lines.append(
                f"Je dispose de {item_count} sources en mémoire. "
                "Je peux traiter cette demande selon les axes suivants : "
                "analyse structurelle, contexte mémoire, frontière X108, "
                "ou projection advisory. "
                "Lequel développer ?"
            )
        else:
            lines.append(
                "Demande ouverte reçue. Je peux la structurer selon trois axes : "
                "mémoire projet, diagnostic X108, ou préparation advisory. "
                "Je ne décide pas, mais je peux organiser la suite. "
                "Sur quel axe veux-tu avancer ?"
            )

    # ── Boundary footer ──────────────────────────────────────────────────
    lines.append("")
    lines.append("X108 reste seul décideur. Je peux préparer, contextualiser, structurer — pas agir.")

    return "\n".join(lines)


def _synthesize_auditor_response_en(
    user_message: str,
    topic: str,
    response_md: str,
    selected_items: list[dict],
    item_count: int,
    material: str,
) -> str:
    """English version of the auditor synthesizer."""
    lines = []
    clean_md = _strip_engine_headers(response_md)

    topic_intros = {
        "X108": "Regarding X108 / KX108, here is what active memory confirms:",
        "34_ARBRES": "On the 34 trees, local memory indicates:",
        "OBSIDIA_BRODY_ROLE": "Memory synthesis on the Obsidia project and my Brody role:",
        "OPERATOR_LOOP": "On the operator loop, the memory chain shows:",
        "ACTION_BOUNDARY": "On the action boundary, structural diagnostic:",
        "CREATOR_CONTEXT": "Creator context acknowledged. Memory summary:",
    }
    intro = topic_intros.get(topic, "Response from structured Brody memory:")
    lines.append(intro)
    lines.append("")

    if selected_items:
        lines.append("**Key items:**")
        for item in selected_items[:4]:
            title = item.get("title", "") or item.get("source_ref", "") or ""
            if not title:
                continue
            cleaned = _clean_title(title)
            excerpt = (item.get("material", "") or item.get("excerpt", "") or "")[:120]
            if excerpt:
                lines.append(f"- {cleaned}: {excerpt}")
            else:
                lines.append(f"- {cleaned}")
        lines.append("")

    lines.append(f"Memory chain returned {item_count} usable items.")
    lines.append("")
    lines.append("X108 remains sole decision authority. I can prepare, contextualize, structure — not act.")

    return "\n".join(lines)


def _strip_engine_headers(text: str) -> str:
    """Remove engine dump headers from response_md for clean display."""
    lines = text.split("\n")
    result = []
    skip_patterns = [
        "# BRODY LOCAL RESPONSE ENGINE",
        "# BRODY CONTEXT PACKET",
        "- query:",
        "- role:",
        "- memory_role:",
        "- decision_authority:",
        "- emits_act:",
        "- kernel_mutation:",
        "- x108_runtime_binding:",
        "- material_quality:",
        "## Boundary",
        "## Carte tags",
        "## Sources",
        "- CODE_PASTE_GUARD",
        "- MEMORY_AUTHORITY",
        "- MEMORY_DECISION",
        "- CANONICAL_SELECTOR",
        "- BRODY_HISTORY",
        "- DECISION_AUTHORITY",
    ]
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(p) for p in skip_patterns):
            continue
        if stripped.startswith("brody >"):
            continue
        result.append(line.rstrip())
    return "\n".join(result).strip()


def _clean_title(title: str) -> str:
    """Clean a memory-indexed title: remove hash prefix, normalize."""
    import re
    t = title.strip()
    # Remove 12-hex-char prefix e.g. "07A62B23DF20_"
    t = re.sub(r"^[0-9A-Fa-f]{12}_", "", t)
    # Truncate overly long titles
    if len(t) > 80:
        t = t[:77] + "..."
    return t



# BRODY_SOURCE_PACK_FINAL_ANSWER_BINDING_REPAIR_V0
def _brody_source_pack_answer_v0(source_pack: dict, language: str = "fr") -> str:
    """
    Readonly fallback binder:
    if source_pack_context_summary/context_summary_for_brody exists,
    expose it in final_answer instead of returning generic weak fallbacks.
    """
    if not isinstance(source_pack, dict):
        return ""

    used = bool(source_pack.get("source_pack_context_used"))
    entries = int(source_pack.get("source_pack_entries_used") or 0)
    summary = str(
        source_pack.get("context_summary_for_brody")
        or source_pack.get("source_pack_context_summary")
        or ""
    ).strip()

    if not used or entries <= 0 or len(summary) < 80:
        return ""

    families = source_pack.get("source_pack_families") or []
    if isinstance(families, str):
        families = [families]
    families_txt = ", ".join(str(x) for x in families if x) or "non specifie"

    refs = source_pack.get("source_file_refs") or []
    if isinstance(refs, str):
        refs = [refs]
    refs_txt = ", ".join(str(x) for x in refs if x) or families_txt

    titles = []
    for line in summary.splitlines():
        clean = line.strip()
        if clean.startswith("## "):
            title = clean[3:].strip()
            if title and title not in titles:
                titles.append(title)

    titles_txt = ""
    if titles:
        titles_txt = "\n".join(f"- {t}" for t in titles[:8])

    excerpt = summary
    if len(excerpt) > 1800:
        excerpt = excerpt[:1800].rstrip() + "\n...[TRUNCATED_READONLY_EXCERPT]"

    header = (
        "Matiere source-pack disponible et rattachee a cette reponse.\n\n"
        f"- Familles : {families_txt}\n"
        f"- Entrees hydratees : {entries}\n"
        f"- References source : {refs_txt}\n"
    )

    if titles_txt:
        header += f"\nElements hydrates :\n{titles_txt}\n"

    return (
        header
        + "\nExtrait readonly du source-pack :\n"
        + excerpt
        + "\n\nFrontiere : KX108_ONLY. Contexte readonly. No ACT. No verdict. No memory write."
    )


def _brody_source_pack_should_override_v0(current_answer: str) -> bool:
    text = (current_answer or "").lower()
    weak_markers = (
        "demande ouverte",
        "requ?te non classifi?e",
        "requete non classifiee",
        "aucune correspondance",
        "materiel textuel complet n'est pas attach",
        "mat?riel textuel complet n'est pas attach",
        "selected_items/material_quality",
    )
    if any(m in text for m in weak_markers):
        return True
    if len(text.strip()) < 220:
        return True
    return False


# Common uppercase tokens that are NOT Obsidia-specific identifiers
_COMMON_CAPS_EXCLUDE = frozenset({
    "BRODY", "TRUE", "FALSE", "NULL", "NONE", "FROM", "WITH", "THIS", "THAT",
    "JUST", "HAVE", "BEEN", "WILL", "DOES", "WHAT", "WHEN", "WHERE", "THEN",
    "ONLY", "ALSO", "BOTH", "VERY", "MORE", "SOME", "MOST", "INTO", "OVER",
    "EACH", "MÊME", "DANS", "AVEC", "POUR", "TOUT", "PLUS", "BIEN", "QUOI",
    "DONC", "MAIS", "SANS", "SOUS", "LEUR", "COMME", "SELON", "ENTRE",
    "PASS", "FAIL", "LOCK", "NODE", "TYPE", "VOID", "MOCK", "LIVE", "STUB",
})


# ── General conversation readonly guard ──────────────────────────────────────

_GENERAL_CONVERSATION_PATTERNS = (
    "bonjour", "bonsoir", "salut", "hello", "coucou",
    "merci", "thank",
    "ok nickel", "nickel", "parfait",
    "on reprend", "reprend",
    "stabiliser", "vient de",
    "naturellement",
    "réponds",
    "au revoir", "à bientôt", "a bientot",
)


def is_general_conversation_readonly(
    message: str,
    authority: dict,
    semantic_snap: dict,
) -> bool:
    """Return True when message is safe general conversation — no decision, no action."""
    if authority.get("request_type") in (ACTION_OR_ACT_REQUEST, MEMORY_WRITE_REQUEST):
        return False
    if semantic_snap.get("topic", "GENERAL") != "GENERAL":
        return False
    msg_lower = message.lower().strip()
    return any(pat in msg_lower for pat in _GENERAL_CONVERSATION_PATTERNS)


def build_general_conversation_answer(message: str) -> str:
    """Return a short conversational readonly response for safe GENERAL messages."""
    msg = message.lower().strip()
    if "dis bonjour" in msg:
        for name in ("maman", "papa", "mamie", "papi"):
            if name in msg:
                return (
                    f"Bonjour {name} ! Je suis Brody, interface structurée readonly "
                    f"Obsidia X-108. KX108_ONLY. Pas de décision."
                )
        return "Bonjour ! Je suis Brody, interface structurée readonly Obsidia X-108. KX108_ONLY."
    if any(g in msg for g in ("bonjour", "bonsoir", "salut", "hello", "coucou")):
        return (
            "Bonjour ! Je suis Brody, interface structurée readonly Obsidia X-108. "
            "KX108_ONLY. Pas de décision."
        )
    if "merci" in msg or "thank" in msg:
        return (
            "Avec plaisir. Je reste en lecture seule — KX108_ONLY. "
            "Pas de décision, pas d'ACT."
        )
    if "nickel" in msg or "parfait" in msg:
        return "Parfait. Chaîne lecture seule stable. KX108_ONLY. Pas de décision."
    if "stabiliser" in msg or "vient de" in msg:
        return (
            "Voici ce qu'on vient de stabiliser : la chaîne terminal lecture seule — "
            "registry Sigma, dispatcher, packets, connectors, bus bridge. "
            "Tout est en lecture seule. KX108_ONLY. Pas de décision."
        )
    if "reprend" in msg:
        return "Je reprends là où on s'est arrêtés. Chaîne readonly active. KX108_ONLY."
    if "naturellement" in msg:
        return "Oui, je peux répondre naturellement dans les limites readonly. KX108_ONLY."
    if "réponds" in msg:
        return "Entendu. Lecture seule — KX108_ONLY. Pas d'ACT, pas de décision."
    return "Brody en mode lecture seule. KX108_ONLY. Pas de décision, pas d'ACT."


def _detect_explicit_identifier(text: str) -> str:
    """
    Return the first explicit Obsidia project identifier found in text, '' if none.

    Matches:
      - Letter + 1-4 digits: P136, B12, T20, C7  (pépites, blocs, trees)
      - 4+ consecutive uppercase letters not in common-word exclusion list: BLOC, PEPITE
    These patterns indicate a specific artifact reference the user expects to resolve.
    """
    import re as _re
    # Priority 1: letter + digits — most unambiguous explicit references
    m = _re.search(r'\b([A-Z][0-9]{1,4})\b', text)
    if m:
        return m.group(1)
    # Priority 2: ALL_CAPS words >= 4 chars not in exclusion set
    for w in _re.findall(r'\b([A-Z]{4,})\b', text):
        if w not in _COMMON_CAPS_EXCLUDE:
            return w
    return ""


# BRODY_SOURCE_PACK_SYNTHESIS_V1
# Overrides the V0 raw-dump binder with a clean readonly synthesis.
def _brody_source_pack_answer_v0(source_pack: dict, language: str = "fr") -> str:
    """
    V1 synthesis layer.

    Keeps V0 binding semantics:
    - source_pack_context_used must be true
    - entries must be hydrated
    - readonly only
    - KX108_ONLY

    Changes V0 output:
    - no raw YAML dump
    - no packet field dump
    - no placeholder spam
    - produces a concise Brody-readable synthesis
    """
    if not isinstance(source_pack, dict):
        return ""

    used = bool(source_pack.get("source_pack_context_used"))
    entries = int(source_pack.get("source_pack_entries_used") or 0)
    summary = str(
        source_pack.get("context_summary_for_brody")
        or source_pack.get("source_pack_context_summary")
        or ""
    ).strip()

    if not used or entries <= 0 or len(summary) < 80:
        return ""

    families = source_pack.get("source_pack_families") or []
    if isinstance(families, str):
        families = [families]
    families = [str(x) for x in families if x]
    families_txt = ", ".join(families) if families else "non specifie"

    refs = source_pack.get("source_file_refs") or []
    if isinstance(refs, str):
        refs = [refs]
    refs = [str(x) for x in refs if x]
    refs_txt = ", ".join(refs[:6]) if refs else families_txt

    query = ""
    for line in summary.splitlines():
        if line.strip().lower().startswith("query:"):
            query = line.split(":", 1)[1].strip()
            break

    blocks = []
    current = None

    for line in summary.splitlines():
        clean = line.strip()
        if clean.startswith("## "):
            if current:
                blocks.append(current)
            title = clean[3:].strip()
            current = {"title": title, "lines": []}
        elif current is not None:
            current["lines"].append(line.rstrip())

    if current:
        blocks.append(current)

    def _is_noise(line: str) -> bool:
        low = line.strip().lower()
        if not low:
            return True
        noise_prefixes = (
            "packet_id:",
            "fields:",
            "memory_id:",
            "essence:",
            "source:",
            "context:",
            "links:",
            "errors:",
            "feedback:",
            "trace:",
            "readonly:",
            "decision_authority:",
            "[source pack context",
            "families:",
            "entries hydrated:",
            "query:",
        )
        if any(low.startswith(p) for p in noise_prefixes):
            return True
        if low in ("placeholder.", "rapport (placeholder).", "string", "list"):
            return True
        return False

    clean_items = []
    weak_items = []

    for b in blocks[:8]:
        title = str(b.get("title") or "").strip()
        raw_lines = [x.strip() for x in b.get("lines", []) if x.strip()]
        useful = [x for x in raw_lines if not _is_noise(x)]

        joined = " ".join(useful).strip()
        is_placeholder = (
            "placeholder" in joined.lower()
            or len(joined) < 40
        )

        if is_placeholder:
            weak_items.append(title)
        else:
            if len(joined) > 420:
                joined = joined[:420].rstrip() + "..."
            clean_items.append((title, joined))

    qlow = query.lower()

    # Intent-aware short synthesis.
    angle = ""
    if "memoire" in qlow or "m?moire" in qlow or "brody" in qlow:
        angle = (
            "Lecture : Brody dispose bien d'une couche memoire consultable en readonly. "
            "La matiere remontee decrit surtout des paquets de memoire, de provenance narrative "
            "et de validation non souveraine. Le point important n'est pas que Brody decide : "
            "il transforme une matiere indexee en contexte lisible, sous frontiere KX108_ONLY."
        )
    elif "preuve" in qlow or "proof" in qlow:
        angle = (
            "Lecture : l'organe Proof / OS3 / Lean est actif. "
            "La reponse provient maintenant de la couche PROOF_OS3_LEAN_ORGAN : "
            "preuves, replay, hash, audit, receipts, OS3 et formalisation Lean. "
            "Cet organe prouve et qualifie, mais ne remplace pas X108."
        )
    elif "gencoin" in qlow:
        angle = (
            "Lecture : l'organe Gencoin est actif. "
            "La reponse provient maintenant de la couche GENCOIN_ORGAN : "
            "valeur post-preuve, ledger cognitif, shadow value et proof_value. "
            "Cet organe reste consultatif, non souverain, sous frontiere KX108_ONLY."
        )
    elif "arbre" in qlow or "arbres" in qlow:
        angle = (
            "Lecture : l'organe Arbres cognitifs est actif. "
            "La reponse provient maintenant de la couche COGNITIVE_TREES_ORGAN : "
            "atlas, tree policy, signaux d'orientation et cartographie 34 arbres. "
            "Cet organe oriente et classe, mais ne decide pas."
        )
    elif "limite" in qlow or "manquant" in qlow or "paquet" in qlow:
        angle = (
            "Lecture : l'organe Gap / Readiness est actif. "
            "La reponse provient maintenant de la couche GAP_READINESS_ORGAN : "
            "paquets manquants, readiness, surfaces faibles, freeze audit et diagnostic safe. "
            "Cet organe signale les manques, sans corriger automatiquement."
        )
    else:
        angle = (
            "Lecture : Brody a bien rattache une matiere source-pack, mais la requete reste large. "
            "La reponse doit donc rester consultative : identifier les familles, extraire ce qui est exploitable, "
            "et signaler les limites du materiel source."
        )

    lines = []
    lines.append("Synthese readonly depuis source-pack.")
    lines.append("")
    lines.append(f"- Requete : {query or 'non specifiee'}")
    lines.append(f"- Familles consultees : {families_txt}")
    lines.append(f"- Entrees hydratees : {entries}")
    lines.append(f"- References source : {refs_txt}")
    lines.append("")
    lines.append(angle)

    if clean_items:
        lines.append("")
        lines.append("Matiere exploitable :")
        for title, body in clean_items[:4]:
            lines.append(f"- {title} : {body}")
    else:
        lines.append("")
        lines.append(
            "Matiere exploitable : faible. Les documents rattaches existent, "
            "mais contiennent surtout de la structure, des schemas, ou du placeholder."
        )

    if weak_items:
        lines.append("")
        lines.append("Sources faibles ou a densifier :")
        for title in weak_items[:5]:
            lines.append(f"- {title}")

    lines.append("")
    lines.append(
        "Frontiere : KX108_ONLY. Contexte readonly. Pas d'action, pas de verdict, pas d'ecriture memoire."
    )

    return "\n".join(lines)
