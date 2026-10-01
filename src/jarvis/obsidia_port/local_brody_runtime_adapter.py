from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


_RUNTIME_ROOT = Path(__file__).resolve().parent / "brody_runtime"

if str(_RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_ROOT))


from apps.obsidia_api.brody_cognitive_micro_core import run_micro_core
from apps.obsidia_api.brody_balance_engine import BrodyBalanceEngine
from apps.obsidia_api.brody_point_cloud_21d_selector import BrodyPointCloud21DSelector
from apps.obsidia_api.brody_memzum_activation_adapter import evaluate_memzum_activation
from apps.obsidia_api.brody_semantic_query_router import (
    build_semantic_query,
    build_memory_retrieval_queries,
)
from apps.obsidia_api.brody_native_memory_response_adapter import (
    build_native_memory_response,
)
from apps.obsidia_api.brody_real_cognitive_join import run_real_cognitive_join
from apps.obsidia_api.brody_full_runtime_reconnect import build_brody_full_context
from apps.obsidia_api.brody_true_voice_adapter import build_true_brody_answer
from apps.obsidia_api.brody_domain_raccord_adapter import build_domain_raccord_snapshot
from apps.obsidia_api.brody_adaptive_response_policy import build_adaptive_response_policy
from apps.obsidia_api.brody_anti_mismatch_signal import build_anti_mismatch_signal
from apps.obsidia_api.brody_gencoin_transverse_interface import build_sigma_packet
from apps.obsidia_api.brody_existing_reverse_os_bridge import (
    build_existing_reverse_os_projection,
)
from apps.obsidia_api.brody_v1_4_12a_final_answer_adapter import _detect_intent
from apps.obsidia_api.brody_v1_4_12a_final_answer_adapter import (
    run_brody_v1_4_12a_final_answer,
)
from scripts.providers.obsidia_qwen_local_evidence_v0 import run_local_qwen_evidence
from periphery.context.governed_model_projection import (
    project_governed_model_evidence,
)
from runtime_wiring.source_runtime.brody_source_context_bridge import (
    build_brody_context_from_source_packs,
)
from jarvis.obsidia_port.evidence_qualification import (
    build_evidence_qualification_snapshot,
    build_qualified_context,
)
from jarvis.obsidia_port.capability_admissibility import (
    build_capability_admissibility_shadow,
)
from jarvis.obsidia_port.capability_selection_shadow import (
    build_capability_selection_shadow,
)
from jarvis.obsidia_port.bounded_routing_shadow_experiment import (
    build_bounded_routing_shadow_experiment,
)
from jarvis.obsidia_port.structured_capability_hint import (
    build_structured_capability_hint,
    compare_structured_hint_with_p36,
)
from jarvis.obsidia_port.structured_p36_shadow_comparator import (
    build_structured_p36_shadow_comparison,
)
from jarvis.obsidia_port.router_core.unified_ir import build_ir


class LocalBrodyRuntimeAdapter:
    """
    Jarjar-owned adapter around the vendored Brody readonly runtime.

    Boundary:
    - cognition only
    - no ACT
    - no memory write
    - KX108_ONLY
    """

    def respond(
        self,
        message: str,
        *,
        session_id: str = "jarjar-local",
        language: str = "fr",
    ) -> dict[str, Any]:
        try:
            micro = run_micro_core(
                message=message,
                session_id=session_id,
                language=language,
            )

            balance = BrodyBalanceEngine().compute_balances(
                message=message,
                micro_core_output=micro,
            )

            point = BrodyPointCloud21DSelector().compute_vector(
                message=message,
                micro_core_output=micro,
                balance_output=balance,
            )

            memzum = evaluate_memzum_activation(
                micro_core=micro,
                balance_output=balance,
                point_cloud=point,
            )

            semantic = build_semantic_query(message)
            unified_ir = build_ir(message)

            memory_required = bool(memzum.get("memory_required"))

            queries = (
                build_memory_retrieval_queries(message)
                if memory_required
                else []
            )

            # Preserve source runtime policy:
            # first retrieval query -> semantic query -> primary query -> message.
            # Canonical semantic routes have already identified the
            # project/domain entity. Preserve that entity for retrieval
            # instead of allowing generic surface words to outrank it.
            if (
                semantic.get("is_canonical") is True
                and semantic.get("primary_query")
            ):
                primary = str(
                    semantic.get("primary_query")
                ).strip()

                concrete_terms = []
                for term in queries:
                    term_s = str(term or "").strip()
                    if (
                        term_s
                        and term_s.lower() != primary.lower()
                        and term_s.lower() not in {
                            "peux",
                            "peut",
                            "dire",
                            "tant",
                        }
                    ):
                        concrete_terms.append(term_s)

                memory_query = " ".join(
                    [primary] + concrete_terms[:3]
                ).strip()
            else:
                memory_query = str(
                    (queries[0] if queries else None)
                    or semantic.get("semantic_query")
                    or semantic.get("primary_query")
                    or message
                ).strip()

            semantic["memory_retrieval_queries"] = list(queries)
            semantic["memory_retrieval_query"] = (
                memory_query if memory_required else ""
            )
            requested_memory_query = memory_query if memory_required else ""

            memory = build_native_memory_response(
                user_message=message,
                semantic_query=memory_query or message,
                memory_required=memory_required,
                limit=5,
                max_items=3,
            )

            # Jarjar-owned readonly retrieval fallback.
            # MEMZUM remains the authority on whether memory is required.
            # We only broaden lookup terms after a required lookup returned empty.
            if (
                memory_required
                and memory.get("retrieval_status") == "MEMORY_REQUIRED_EMPTY"
            ):
                retrieval_candidates = []

                def _add_candidate(value):
                    value = str(value or "").strip()
                    if value and value not in retrieval_candidates:
                        retrieval_candidates.append(value)

                # Most specific first.
                _add_candidate(memory_query)

                # Preserve concrete terms extracted from the user's wording.
                for value in queries:
                    _add_candidate(value)

                # Then canonical entity/topic fallbacks.
                _add_candidate(semantic.get("primary_query"))

                for value in semantic.get("fallback_queries", []):
                    _add_candidate(value)

                # Jarjar is a surface alias; Brody is the indexed project identity.
                if "jarjar" in message.lower():
                    _add_candidate("brody")

                for candidate in retrieval_candidates:
                    if candidate == memory_query:
                        continue

                    retry = build_native_memory_response(
                        user_message=message,
                        semantic_query=candidate,
                        memory_required=True,
                        limit=5,
                        max_items=3,
                    )

                    if retry.get("retrieval_status") == "MEMORY_USABLE":
                        memory = retry
                        memory_query = candidate
                        semantic["memory_retrieval_query"] = candidate
                        break

            source_pack = build_brody_context_from_source_packs(
                query=message,
                limit=5,
            )

            evidence_qualification = build_evidence_qualification_snapshot(
                user_message=message,
                semantic_snapshot=semantic,
                requested_memory_target=requested_memory_query,
                native_memory_selected_items=memory.get("selected_items"),
                source_pack_hydrated_entries=source_pack.get(
                    "hydrated_entries"
                ),
            )

            join = run_real_cognitive_join(
                message=message,
                language=language,
                session_id=session_id,
                precomputed_micro_core=micro,
                precomputed_semantic_query=semantic,
                precomputed_memory_chain=memory,
                precomputed_source_pack_context=source_pack,
            )

            full = build_brody_full_context(
                user_message=message,
                language=language,
                session_id=session_id,
                context_packet=join,
                memory_response_chain_snapshot=memory,
                semantic_query_snapshot=semantic,
            )

            # ---------------------------------------------------------
            # PRE-INFERENCE RESPONSE POLICY
            # Uses the existing Brody policy only.
            # No new cognitive hierarchy is introduced here.
            # ---------------------------------------------------------
            domain_raccord_pre = build_domain_raccord_snapshot(
                message,
                full,
            )

            rights_pre = full.get("rights_action_snapshot", {})
            request_type_pre = (
                rights_pre.get("request_type")
                if isinstance(rights_pre, dict)
                else None
            ) or "PURE_RESPONSE"

            response_policy_pre = build_adaptive_response_policy(
                message,
                final_answer="",
                voice_source="",
                request_type=request_type_pre,
                domain_raccord=domain_raccord_pre,
                support_summary=full.get("support_summary", {}),
                memory_chain=memory,
            )

            response_size_pre = str(
                response_policy_pre.get("response_size") or "MEDIUM"
            )

            qwen_budget_map = {
                "BOUNDARY_COMPACT": 128,
                "SHORT": 192,
                "MEDIUM": 320,
                "DEEP": 512,
            }

            qwen_max_tokens = qwen_budget_map.get(
                response_size_pre,
                320,
            )

            # Explicit shadow opt-in for now.
            # Do NOT make local Qwen mandatory until the canonical
            # Brody/AMD sufficiency gate is recovered.
            # ---------------------------------------------------------
            # SAME-TURN BRODY CONTEXT FOR LOCAL QWEN
            #
            # Selection remains Brody-owned.
            # Qwen receives only already-selected readonly material.
            # No second retrieval and no whole-corpus dump.
            # ---------------------------------------------------------
            qwen_context_parts: list[str] = []

            semantic_query_for_model = str(
                semantic.get("semantic_query")
                or semantic.get("primary_query")
                or ""
            ).strip()

            if semantic_query_for_model:
                qwen_context_parts.append(
                    "[SEMANTIC QUERY]\n"
                    + semantic_query_for_model
                )

            requested_target_for_model = str(
                requested_memory_query
                or ""
            ).strip()

            retrieval_target_for_model = str(
                memory.get("effective_query")
                or memory_query
                or ""
            ).strip()

            if requested_target_for_model:
                qwen_context_parts.append(
                    "[REQUESTED MEMORY TARGET - ROUTING METADATA]\n"
                    + requested_target_for_model
                )

            if retrieval_target_for_model:
                qwen_context_parts.append(
                    "[EFFECTIVE MEMORY TARGET - ROUTING METADATA]\n"
                    + retrieval_target_for_model
                )

            qualified_context = build_qualified_context(
                evidence_qualification
            )
            if qualified_context:
                qwen_context_parts.append(qualified_context)

            qwen_context = "\n\n".join(qwen_context_parts)

            # Approx. OpenJarvis-style ~2k-token envelope using a char bound.
            if len(qwen_context) > 8192:
                qwen_context = qwen_context[:8192]

            qwen_stage = {
                "status": "NOT_CALLED",
                "attempted": False,
                "model_call_used": False,
                "evidence": None,
            }

            governed_projection = {
                "status": "NOT_AVAILABLE",
                "readonly": True,
                "advisory_only": True,
                "decision_authority": "KX108_ONLY",
            }

            final_adapter = {}
            join_final = join

            # Canonical Brody IR path:
            # intent -> Existing Reverse OS -> IR Candidate.
            brody_intent = _detect_intent(message)

            reverse_os_bridge_pre = build_existing_reverse_os_projection(
                user_message=message,
                intent=brody_intent,
                semantic_query_snapshot=semantic,
                authority_snapshot={},
                tree_signal_packet={},
                tree_policy_snapshot={},
            )

            ir_candidate_pre = (
                reverse_os_bridge_pre.get("ir_candidate", {})
                if isinstance(reverse_os_bridge_pre, dict)
                else {}
            )

            if not isinstance(ir_candidate_pre, dict):
                ir_candidate_pre = {}

            structured_capability_hint = build_structured_capability_hint(
                ir=unified_ir,
                semantic=semantic,
                memzum=memzum,
            )

            p36_required_capabilities = (
                source_pack.get("required_capabilities")
                if isinstance(source_pack, dict)
                else []
            )

            capability_route_comparison = compare_structured_hint_with_p36(
                structured_capability_hints=structured_capability_hint.get(
                    "structured_capability_hints"
                ),
                p36_required_capabilities=p36_required_capabilities,
            )

            structured_p36_shadow_comparison = (
                build_structured_p36_shadow_comparison(
                    structured_capability_snapshot=structured_capability_hint,
                    p36_snapshot={
                        "detected_intents": source_pack.get(
                            "detected_intents"
                        ),
                        "required_capabilities": p36_required_capabilities,
                        "selected_runtime_path": source_pack.get(
                            "selected_runtime_path"
                        ),
                        "selected_source_families": source_pack.get(
                            "selected_source_families"
                        ),
                        "hydration_plan": source_pack.get("hydration_plan"),
                    },
                    unified_ir_snapshot=unified_ir,
                    semantic_snapshot=semantic,
                    memzum_snapshot=memzum,
                )
            )

            capability_admissibility_shadow = (
                build_capability_admissibility_shadow(
                    structured_capability_snapshot=structured_capability_hint,
                    p36_snapshot={
                        "detected_intents": source_pack.get(
                            "detected_intents"
                        ),
                        "required_capabilities": p36_required_capabilities,
                        "selected_runtime_path": source_pack.get(
                            "selected_runtime_path"
                        ),
                    },
                    comparator_snapshot=structured_p36_shadow_comparison,
                    unified_ir_snapshot=unified_ir,
                    semantic_snapshot=semantic,
                    memzum_snapshot=memzum,
                )
            )

            capability_selection_shadow = (
                build_capability_selection_shadow(
                    capability_admissibility_snapshot=(
                        capability_admissibility_shadow
                    ),
                    comparator_snapshot=structured_p36_shadow_comparison,
                )
            )

            bounded_routing_shadow_experiment = (
                build_bounded_routing_shadow_experiment(
                    capability_selection_snapshot=capability_selection_shadow,
                    legacy_p36_snapshot={
                        "selected_runtime_path": source_pack.get(
                            "selected_runtime_path"
                        ),
                        "hydration_plan": source_pack.get("hydration_plan"),
                    },
                    available_families=source_pack.get("available_families"),
                )
            )

            qwen_anti_mismatch = {}
            qwen_sigma_initial = {}
            qwen_sigma_final = {}
            qwen_quality_gate_pass = False
            qwen_quality_gate_reason = "QWEN_NOT_ENABLED"

            if __import__("os").environ.get(
                "JARJAR_BRODY_QWEN_SHADOW",
                "0",
            ) == "1":
                qwen_stage = run_local_qwen_evidence(
                    text=message,
                    context=qwen_context,
                    timeout=90.0,
                    max_tokens=qwen_max_tokens,
                )

                evidence = qwen_stage.get("evidence")

                qwen_quality_gate_reason = "QWEN_EVIDENCE_NOT_READY"

                if (
                    qwen_stage.get("status") == "EVIDENCE_READY"
                    and isinstance(evidence, dict)
                ):
                    qwen_candidate_answer = str(
                        evidence.get("content") or ""
                    ).strip()

                    qwen_candidate_snapshot = {
                        "final_answer": qwen_candidate_answer,
                    }

                    # Canonical Brody sequence:
                    # Sigma initial -> Anti-Mismatch -> Sigma final.
                    qwen_sigma_initial = build_sigma_packet(
                        adaptive_response_policy=response_policy_pre,
                        ir_candidate=ir_candidate_pre,
                        domain_raccord=domain_raccord_pre,
                        memory_chain=memory,
                        true_voice_snapshot=qwen_candidate_snapshot,
                    )

                    anti_raw = build_anti_mismatch_signal(
                        ir_candidate=ir_candidate_pre,
                        true_voice_snapshot=qwen_candidate_snapshot,
                        adaptive_response_policy=response_policy_pre,
                        domain_raccord=domain_raccord_pre,
                        sigma_packet=qwen_sigma_initial,
                        memory_chain=memory,
                    )

                    qwen_anti_mismatch = (
                        anti_raw.get("anti_mismatch_packet", {})
                        if isinstance(anti_raw, dict)
                        else {}
                    )

                    qwen_sigma_final = build_sigma_packet(
                        adaptive_response_policy=response_policy_pre,
                        ir_candidate=ir_candidate_pre,
                        domain_raccord=domain_raccord_pre,
                        memory_chain=memory,
                        true_voice_snapshot=qwen_candidate_snapshot,
                        anti_mismatch_packet=qwen_anti_mismatch,
                    )

                    qwen_mismatch_signals = (
                        qwen_anti_mismatch.get("signals", {})
                        if isinstance(qwen_anti_mismatch, dict)
                        else {}
                    )

                    # Promotion policy for governed local-model evidence.
                    # Anti-Mismatch/Sigma remain advisory and unchanged.
                    # Jarjar simply refuses to surface a model candidate
                    # when the existing signals identify a severe under-answer.
                    project_scoped_query = bool(
                        memory_required
                        or semantic.get("is_canonical") is True
                        or micro.get("project_context_relevant") is True
                    )

                    qwen_candidate_lower = qwen_candidate_answer.lower()
                    qwen_grounded_insufficiency = any(
                        marker in qwen_candidate_lower
                        for marker in (
                            "n'a pas été explicitement",
                            "n’est pas explicitement",
                            "n'est pas explicitement",
                            "n’est pas explicitement décrit",
                            "n'est pas explicitement décrit",
                            "n’est pas explicitement décrite",
                            "n'est pas explicitement décrite",
                            "ne permet pas d'établir",
                            "ne permet pas d’etablir",
                            "ne l'établit pas",
                            "ne l’etablit pas",
                            "pas décrit",
                            "pas de donnée",
                            "pas d'information",
                            "pas d’information",
                            "does not establish",
                            "not established",
                            "not described",
                            "insufficient context",
                        )
                    )

                    qwen_critical_underanswer = bool(
                        project_scoped_query
                        and qwen_mismatch_signals.get("structural_gap")
                        and qwen_mismatch_signals.get(
                            "sigma_high_but_answer_empty"
                        )
                        and not qwen_grounded_insufficiency
                    )

                    qwen_quality_gate_pass = (
                        qwen_anti_mismatch.get("risk_level") != "HIGH"
                        and qwen_sigma_final.get("calibration_status")
                        != "CALIBRATED_WITH_MISMATCH_RISK"
                        and not qwen_critical_underanswer
                    )

                    if qwen_quality_gate_pass:
                        qwen_quality_gate_reason = (
                            "QWEN_QUALITY_GATE_PASS"
                        )
                    elif qwen_critical_underanswer:
                        qwen_quality_gate_reason = (
                            "QWEN_QUALITY_GATE_CRITICAL_UNDERANSWER"
                        )
                    else:
                        qwen_quality_gate_reason = (
                            "QWEN_QUALITY_GATE_MISMATCH_RISK"
                        )

                if (
                    qwen_stage.get("status") == "EVIDENCE_READY"
                    and isinstance(evidence, dict)
                    and qwen_quality_gate_pass
                ):
                    join_final = run_real_cognitive_join(
                        message=message,
                        language=language,
                        session_id=session_id,
                        precomputed_micro_core=micro,
                        precomputed_semantic_query=semantic,
                        precomputed_memory_chain=memory,
                        precomputed_model_evidence=evidence,
                        precomputed_source_pack_context=source_pack,
                    )

                    # Projection consumes the post-join admission state,
                    # not the raw provider result alone.
                    local_model_stage = dict(qwen_stage)
                    local_model_stage["evidence_applied"] = bool(
                        join_final.get("local_model_evidence_applied")
                    )
                    local_model_stage["evidence_status"] = (
                        join_final.get("local_model_evidence_status")
                    )

                    governed_projection = project_governed_model_evidence(
                        user_message=message,
                        local_model_stage=local_model_stage,
                        cognitive_join=join_final,
                    )

                    final_adapter = run_brody_v1_4_12a_final_answer(
                        user_message=message,
                        language=language,
                        context_packet=join_final,
                        governed_model_projection=governed_projection,
                    )

                    projected_answer = str(
                        final_adapter.get("final_answer") or ""
                    ).strip()

                    if (
                        final_adapter.get(
                            "governed_model_projection_selected"
                        ) is True
                        and projected_answer
                    ):
                        full = build_brody_full_context(
                            user_message=message,
                            language=language,
                            session_id=session_id,
                            context_packet=join_final,
                            memory_response_chain_snapshot=memory,
                            semantic_query_snapshot=semantic,
                        )

                        full["governed_model_projection"] = (
                            governed_projection
                        )
                        full["governed_model_final_answer"] = (
                            projected_answer
                        )

            join = join_final

            voice = build_true_brody_answer(
                user_message=message,
                language=language,
                session_id=session_id,
                brody_full_context=full,
                source_pack_context=source_pack,
            )

            # ---------------------------------------------------------
            # GOVERNED FINAL SURFACE ARBITRATION
            #
            # True Voice remains the default canonical surface.
            # A model answer may replace it ONLY after:
            #   Qwen evidence
            #   -> Cognitive Join admission
            #   -> Governed Model Projection READY
            #   -> V1.4.12A explicit projection selection
            #
            # Raw model output is never surfaced here.
            # ---------------------------------------------------------
            voice_answer = str(
                voice.get("final_answer") or ""
            ).strip()

            governed_answer = str(
                final_adapter.get("final_answer") or ""
            ).strip()

           
            canonical_voice_priority = (
                str(semantic.get("topic") or "")
                in {"OBSIDIA_BRODY_ROLE"}
            )

            governed_selected = (
                isinstance(final_adapter, dict)
                and final_adapter.get(
                    "governed_model_projection_selected"
                ) is True
                and governed_projection.get("status") == "READY"
                and bool(governed_answer)
                and not canonical_voice_priority
            )

            if governed_selected:
                visible_answer = governed_answer
                visible_answer_source = (
                    final_adapter.get("v1_4_12a_source")
                    or "GOVERNED_MODEL_PROJECTION_V1412A"
                )
            else:
                visible_answer = voice_answer
                visible_answer_source = (
                    voice.get("voice_source")
                    or voice.get("final_answer_source")
                )

            components = join.get("components") or {}

            authority = (
                voice.get("decision_authority")
                or join.get("decision_authority")
                or "KX108_ONLY"
            )

            readonly = bool(
                voice.get("readonly", join.get("readonly", True))
            )

            # Fail closed on authority drift.
            if authority != "KX108_ONLY" or not readonly:
                return {
                    "status": "LOCAL_BRODY_AUTHORITY_GUARD_FAIL",
                    "available": False,
                    "final_answer": None,
                    "decision_authority": authority,
                    "readonly": readonly,
                    "fallback_allowed": True,
                }

            return {
                "status": "LOCAL_BRODY_RUNTIME_PASS",
                "available": True,
                "final_answer": visible_answer,
                "voice_source": visible_answer_source,
                "true_voice_final_answer": voice.get("final_answer"),
                "true_voice_source": voice.get("voice_source"),
                "governed_final_selected": governed_selected,
                "canonical_voice_priority": canonical_voice_priority,
                "v1412a_projection_selected": (
                    final_adapter.get(
                        "governed_model_projection_selected"
                    )
                    if isinstance(final_adapter, dict)
                    else False
                ),
                "v1412a_runtime_status": (
                    final_adapter.get("v1_4_12a_runtime_status")
                    if isinstance(final_adapter, dict)
                    else None
                ),
                "decision_authority": authority,
                "readonly": readonly,

                "memory_required": memory_required,
                "memory_query": memory_query if memory_required else "",
                "memory_status": memory.get("status"),
                "memory_source_mode": memory.get("source_mode"),
                "retrieval_status": memory.get("retrieval_status"),
                "selected_items_count": memory.get("selected_items_count"),                "memory_requested_query": requested_memory_query,

                "memory_effective_query": memory.get("effective_query"),
                "memory_selected_titles": [
                    str(item.get("title") or item.get("id") or "")
                    for item in (memory.get("selected_items") or [])[:3]
                    if isinstance(item, dict)
                ],

                "source_pack_status": source_pack.get("status"),
                "source_pack_context_used": source_pack.get("source_pack_context_used"),
                "source_pack_families": source_pack.get("source_pack_families"),
                "source_pack_entries_used": source_pack.get("source_pack_entries_used"),
                "source_pack_x108_decision": source_pack.get("x108_decision"),
                "selected_runtime_path": source_pack.get("selected_runtime_path"),
                "selected_source_families": source_pack.get("selected_source_families"),
                "hydration_plan": source_pack.get("hydration_plan"),
                "structured_capability_hints": (
                    structured_capability_hint.get(
                        "structured_capability_hints"
                    )
                ),
                "structured_primary_capability": (
                    structured_capability_hint.get(
                        "primary_capability_hint"
                    )
                ),
                "capability_hint_confidence": (
                    structured_capability_hint.get("confidence_class")
                ),
                "p36_required_capabilities": p36_required_capabilities,
                "capability_route_agreement": (
                    capability_route_comparison.get(
                        "capability_route_agreement"
                    )
                ),
                "capability_route_divergence": (
                    capability_route_comparison.get(
                        "capability_route_divergence"
                    )
                ),
                "structured_p36_shadow_comparator": (
                    structured_p36_shadow_comparison
                ),
                "capability_admissibility_shadow": (
                    capability_admissibility_shadow
                ),
                "capability_selection_shadow": (
                    capability_selection_shadow
                ),
                "bounded_routing_shadow_experiment": (
                    bounded_routing_shadow_experiment
                ),

                "memzum_status": memzum.get("status"),
                "cognitive_join_status": join.get("status"),
                "reverse_os_status": components.get("REVERSE_OS"),
                "w4_memory_retrieval_status": components.get(
                    "W4_MEMORY_RETRIEVAL"
                ),

                "true_voice_status": voice.get("status"),

                "response_policy_pre_status": response_policy_pre.get("status"),
                "response_size_pre": response_size_pre,
                "qwen_max_tokens": qwen_max_tokens,

                "evidence_qualification_status": (
                    evidence_qualification.get("status")
                ),
                "evidence_claim_support_required": (
                    evidence_qualification.get("claim_support_required")
                ),
                "evidence_claim_support_available": (
                    evidence_qualification.get("claim_support_available")
                ),
                "evidence_qualification_counts": (
                    evidence_qualification.get("counts_by_qualification")
                ),
                "evidence_requested_subjects": (
                    evidence_qualification.get("requested_subjects")
                ),
                "evidence_requested_properties": (
                    evidence_qualification.get("requested_properties")
                ),

                "qwen_context_chars": len(qwen_context),
                "qwen_context_used": bool(qwen_context),
                "qwen_context_preview": qwen_context[:3000],
                "qwen_raw_evidence_content": (
                    (qwen_stage.get("evidence") or {}).get("content")
                    if isinstance(qwen_stage, dict)
                    else None
                ),
                "governed_projection_content": (
                    governed_projection.get("content")
                    if isinstance(governed_projection, dict)
                    else None
                ),
                "v1412a_final_answer": (
                    final_adapter.get("final_answer")
                    if isinstance(final_adapter, dict)
                    else None
                ),
                "qwen_anti_mismatch_score": (
                    qwen_anti_mismatch.get("mismatch_score")
                    if isinstance(qwen_anti_mismatch, dict)
                    else None
                ),
                "qwen_anti_mismatch_risk": (
                    qwen_anti_mismatch.get("risk_level")
                    if isinstance(qwen_anti_mismatch, dict)
                    else None
                ),
                "qwen_anti_mismatch_signals": (
                    qwen_anti_mismatch.get("signals")
                    if isinstance(qwen_anti_mismatch, dict)
                    else None
                ),
                "qwen_sigma_initial_status": (
                    qwen_sigma_initial.get("calibration_status")
                    if isinstance(qwen_sigma_initial, dict)
                    else None
                ),
                "qwen_sigma_final_status": (
                    qwen_sigma_final.get("calibration_status")
                    if isinstance(qwen_sigma_final, dict)
                    else None
                ),
                "qwen_quality_gate_pass": qwen_quality_gate_pass,
                "qwen_quality_gate_reason": qwen_quality_gate_reason,
                "qwen_grounded_insufficiency": (
                    qwen_grounded_insufficiency
                    if "qwen_grounded_insufficiency" in locals()
                    else False
                ),
                "qwen_stage_status": qwen_stage.get("status"),
                "qwen_model_call_used": qwen_stage.get("model_call_used"),
                "qwen_tokens_local": qwen_stage.get("tokens_local"),
                "qwen_finish_reason": qwen_stage.get("finish_reason"),

                "governed_model_projection_status": (
                    governed_projection.get("status")
                    if isinstance(governed_projection, dict)
                    else None
                ),
                "governed_model_projection_reason": (
                    governed_projection.get("reason")
                    if isinstance(governed_projection, dict)
                    else None
                ),

                "local_model_evidence_status": join.get(
                    "local_model_evidence_status"
                ),
                "local_model_evidence_applied": join.get(
                    "local_model_evidence_applied"
                ),

                "fallback_allowed": False,
            }

        except Exception as exc:
            return {
                "status": "LOCAL_BRODY_RUNTIME_UNAVAILABLE",
                "available": False,
                "final_answer": None,
                "decision_authority": "KX108_ONLY",
                "readonly": True,
                "fallback_allowed": True,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }


_default_adapter = LocalBrodyRuntimeAdapter()


def respond_local_brody(
    message: str,
    *,
    session_id: str = "jarjar-local",
    language: str = "fr",
) -> dict[str, Any]:
    return _default_adapter.respond(
        message,
        session_id=session_id,
        language=language,
    )

