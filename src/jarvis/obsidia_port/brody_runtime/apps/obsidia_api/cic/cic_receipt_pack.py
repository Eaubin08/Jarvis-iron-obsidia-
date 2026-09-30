"""
CIC Receipt Pack — READONLY ONLY
Génère un receipt traçable et rejouable pour chaque invocation CIC.
ACT=NO | GRAPHITI_WRITE=NO | NEO4J_WRITE=NO | KERNEL_MUTATION=NO
DECISION_AUTHORITY=KX108_ONLY | AUTHORITY=NONE
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

_RECEIPT_PREFIX = "CIC_RCP_"
_CIC_CONTEXT_VERSION = "CIC_READONLY_PACK_V0"

_SOVEREIGN_KEYS = frozenset({"ALLOW", "BLOCK", "HOLD", "decision", "gate", "verdict"})


def _make_invocation_hash(
    domain: str,
    source_zip_sha256: str,
    confirmed_metric_families: list[str],
) -> str:
    payload = json.dumps(
        {
            "confirmed_metric_families": sorted(confirmed_metric_families),
            "domain": domain,
            "source_zip_sha256": source_zip_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_cic_receipt(
    domain: str,
    source_zip_sha256: str,
    confirmed_metric_families: list[str],
    source_files_count: int | None = None,
) -> dict[str, Any]:
    """
    Produit un receipt CIC readonly + rejouable.
    receipt_id et invocation_hash sont déterministes (pas de timestamp volatile).
    Aucun champ souverain (ALLOW/BLOCK/HOLD). Aucune écriture. Aucun ACT.
    """
    invocation_hash = _make_invocation_hash(domain, source_zip_sha256, confirmed_metric_families)
    receipt_id = _RECEIPT_PREFIX + invocation_hash[:16].upper()

    replay_inputs: dict[str, Any] = {
        "domain": domain,
        "source_zip_sha256": source_zip_sha256,
        "confirmed_metric_families": sorted(confirmed_metric_families),
        "cic_context_version": _CIC_CONTEXT_VERSION,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "emits_act": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "kernel_mutation": False,
        "memory_write": False,
        "real_action": False,
        "authority": "NONE",
    }
    if source_files_count is not None:
        replay_inputs["source_files_count"] = source_files_count

    return {
        "receipt_id": receipt_id,
        "invocation_hash": invocation_hash,
        "replay_inputs": replay_inputs,
        "readonly": True,
        "emits_act": False,
        "kernel_mutation": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "canonical_write": False,
        "memory_write": False,
        "real_action": False,
        "decision_authority": "KX108_ONLY",
        "authority": "NONE",
        "cic_context_version": _CIC_CONTEXT_VERSION,
    }
