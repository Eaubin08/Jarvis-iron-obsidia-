"""
CIC NCP Readonly Stub — LOCAL ONLY
NCP_ACTIVE=NO | NETWORK=NO | FETCH=NO | CRAWL=NO
ACT=NO | WRITE=NO | AUTHORITY=NONE | DECISION_AUTHORITY=KX108_ONLY
Advisory/context_signal_only — jamais souverain, jamais de réseau.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

_NCP_STUB_VERSION = "NCP_READONLY_STUB_V0"
_NCP_STUB_PREFIX = "NCP_STUB_"

_FORBIDDEN_NCP_FIELDS = frozenset({
    "network", "fetch", "crawl", "authority_result", "decision",
    "gate", "verdict", "computed_path", "path_decision",
})


def _make_stub_id(domain: str) -> str:
    payload = json.dumps(
        {"domain": domain, "stub_version": _NCP_STUB_VERSION},
        sort_keys=True,
        separators=(",", ":"),
    )
    return _NCP_STUB_PREFIX + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()


def build_ncp_readonly_stub(domain: str = "generic") -> dict[str, Any]:
    """
    Retourne un paquet NCP readonly/local déterministe.
    Aucun appel réseau, aucune écriture, aucune autorité souveraine.
    """
    stub_id = _make_stub_id(domain)

    return {
        "ncp_stub_id": stub_id,
        "ncp_stub_version": _NCP_STUB_VERSION,
        "domain": domain,
        "source": "LOCAL_STUB_ONLY",
        "no_external_data": True,
        "ncp_active": False,
        "network": False,
        "fetch": False,
        "crawl": False,
        "readonly": True,
        "advisory_only": True,
        "context_signal_only": True,
        "authority": "NONE",
        "decision_authority": "KX108_ONLY",
        "emits_act": False,
        "emits_verdict": False,
        "allowed_to_act": False,
        "allowed_to_decide": False,
        "graphiti_write": False,
        "neo4j_write": False,
        "memory_write": False,
        "kernel_mutation": False,
        "real_action": False,
    }
