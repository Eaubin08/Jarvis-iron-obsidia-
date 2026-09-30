"""
Brody Structured Response Engine Adapter
==========================================
Exposes the QUERY → CONSUMER → ENGINE chain as structured_response_snapshot.

Chain source (from source docs):
  brody_context_packet_query_readonly_v1 (readonly context query)
  → context_packet_consumer_readonly     (hydration)
  → brody_local_response_engine_readonly (structured response)
  [orchestrated via terminal_structural_dialogue_readonly_v1]

This adapter wraps brody_real_response_pipeline (which already runs the chain)
and converts its result into the canonical structured_response_snapshot format.

Source doc refs (validated 2026-05-13):
  BRODY_REAL_ARCHITECTURE_MAP_READONLY_20260513_190155 — flux complet
  BRODY_NEXT_BUILD_ROADMAP_READONLY_20260513_212134 — Context packet chain = CHAIN_PASS
  BRODY_SESSION_CHECKPOINT_20260513_FINAL — état stabilisé

Boundary: readonly, no memory write, KX108_ONLY
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_BOUNDARY: dict[str, Any] = {
    "readonly": True,
    "memory_write": False,
    "emits_act": False,
    "emits_verdict": False,
    "kernel_mutation": False,
    "decision_authority": "KX108_ONLY",
}

_SOURCE_DOC_REFS = [
    "BRODY_REAL_ARCHITECTURE_MAP_READONLY_20260513_190155",
    "BRODY_NEXT_BUILD_ROADMAP_READONLY_20260513_212134",
    "BRODY_SESSION_CHECKPOINT_20260513_FINAL",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_structured_response_snapshot(pipeline_result: dict[str, Any]) -> dict[str, Any]:
    """
    Convert brody_real_response_pipeline result to structured_response_snapshot.

    No duplicate backend calls; repackages what the pipeline already computed.
    Chain: terminal_structural_dialogue → context_packet_query → local_response_engine
    """
    engine_status = pipeline_result.get("engine_status", "")
    material_quality = pipeline_result.get("material_quality", "")
    response_md = pipeline_result.get("response_md", "")
    memory_query = pipeline_result.get("memory_query", "")
    selected_items = pipeline_result.get("selected_items", []) or []
    context_items_count = len(selected_items)

    response_available = bool(str(response_md).strip())
    query_available = bool(str(memory_query).strip())
    engine_pass = (
        engine_status
        == "BRODY_LOCAL_RESPONSE_ENGINE_READONLY_PASS"
    )

    if engine_pass and response_available:
        query_stage = "PASS" if query_available else "NOT_REQUIRED"
        consumer_stage = "PASS"
        engine_stage = "PASS"
        status = "STRUCTURED_RESPONSE_ENGINE_PASS"
    elif response_available:
        query_stage = "PASS" if query_available else "NOT_REQUIRED"
        consumer_stage = "PASS"
        engine_stage = engine_status or "TERMINAL_FALLBACK"
        status = "STRUCTURED_RESPONSE_ENGINE_PARTIAL"
    else:
        query_stage = "PASS" if query_available else "NOT_REQUIRED"
        consumer_stage = "UNAVAILABLE"
        engine_stage = engine_status or "UNAVAILABLE"
        status = "STRUCTURED_RESPONSE_ENGINE_UNAVAILABLE"

    if material_quality == "USABLE_MATERIAL":
        text_material_status = "HAS_MATERIAL"
    elif material_quality == "PARTIAL_MATERIAL":
        text_material_status = "PARTIAL_MATERIAL"
    elif material_quality == "LOW_MATERIAL":
        text_material_status = "LOW_MATERIAL"
    elif response_available:
        text_material_status = "NO_MATERIAL"
    else:
        text_material_status = "CHAIN_UNAVAILABLE"

    return {
        "status": status,
        "query_stage": query_stage,
        "consumer_stage": consumer_stage,
        "engine_stage": engine_stage,
        "context_items_count": context_items_count,
        "text_material_status": text_material_status,
        "response_md": response_md,
        "memory_query": memory_query,
        "selected_items": selected_items,
        "tag_counts": pipeline_result.get("tag_counts", {}),
        "chain_source": (
            "BRODY_REAL_RESPONSE_PIPELINE"
            ":terminal_structural_dialogue+context_packet_query+local_response_engine"
        ),
        "source_doc_refs": _SOURCE_DOC_REFS,
        "created_at": _now(),
        **_BOUNDARY,
    }


def chain_md_to_final_answer(chain_md: str, language: str = "fr") -> str:
    """
    Convert LOCAL_RESPONSE_ENGINE response_md to a conversational final_answer.
    Strips metadata header/footer, keeps the actual content sections.
    Returns "" if no usable content found.
    """
    if not chain_md:
        return ""

    lines = chain_md.split("\n")
    content_lines: list[str] = []
    in_content = False

    _SKIP_PREFIXES = (
        "# BRODY LOCAL RESPONSE",
        "# BRODY CONTEXT PACKET",
        "- query:", "- role:", "- memory_role:", "- decision_authority:",
        "- emits_act:", "- kernel_mutation:", "- x108_runtime_binding:",
        "- material_quality:", "- x108_merge:", "- brody_role:",
    )
    _CONTENT_HEADERS = (
        "## Réponse locale",
        "## Lecture active",
        "## Response",
        "## Active reading",
        "## Items structurants",
    )
    _STOP_HEADERS = ("## Boundary", "## Sources", "## Carte tags")

    for line in lines:
        # Skip metadata header lines
        if any(line.startswith(p) for p in _SKIP_PREFIXES):
            continue
        # Stop at boundary/sources/tags section
        if any(line.startswith(h) for h in _STOP_HEADERS):
            break
        # Start including at content headers
        if any(line.startswith(h) for h in _CONTENT_HEADERS):
            in_content = True
            continue
        if in_content:
            content_lines.append(line)

    content = "\n".join(content_lines).strip()

    # Skip if only fallback noise
    _NO_CONTENT_MARKERS = (
        "Aucun extrait local hydraté",
        "NO_LOCAL_EXCERPT_AVAILABLE",
        "BINARY_CONTENT_FILTERED",
    )
    if not content or any(m in content for m in _NO_CONTENT_MARKERS):
        return ""

    footer = (
        "\n\n_Brody — réponse contextuelle readonly. KX108_ONLY._"
        if language == "fr"
        else "\n\n_Brody — contextual readonly response. KX108_ONLY._"
    )
    return content + footer
