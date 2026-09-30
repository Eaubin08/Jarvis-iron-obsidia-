"""
CIC Scraping Readonly Stub — LOCAL ONLY
SCRAP_ACTIVE=NO | NETWORK=NO | FETCH=NO | CRAWL=NO | EXTERNAL_HTTP=NO
ACT=NO | WRITE=NO | AUTHORITY=NONE | DECISION_AUTHORITY=KX108_ONLY
web_scrape reste QUARANTINED dans source_classifier — immuable.
Advisory/context_signal_only — jamais souverain, jamais de réseau.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

_SCRAPING_STUB_VERSION = "SCRAPING_READONLY_STUB_V0"
_SCRAPING_STUB_PREFIX = "SCRAP_STUB_"

_FORBIDDEN_SCRAPING_FIELDS = frozenset({
    "network", "fetch", "crawl", "external_http", "authority_result",
    "decision", "gate", "verdict", "computed_path", "path_decision",
})


def _make_stub_id(domain: str) -> str:
    payload = json.dumps(
        {"domain": domain, "stub_version": _SCRAPING_STUB_VERSION},
        sort_keys=True,
        separators=(",", ":"),
    )
    return _SCRAPING_STUB_PREFIX + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16].upper()


def build_scraping_readonly_stub(domain: str = "generic") -> dict[str, Any]:
    """
    Retourne un paquet Scraping readonly/local déterministe.
    Aucune requête HTTP externe, aucune écriture, aucune autorité souveraine.
    web_scrape reste QUARANTINED dans source_classifier (garde externe immuable).
    """
    stub_id = _make_stub_id(domain)

    return {
        "scraping_stub_id": stub_id,
        "scraping_stub_version": _SCRAPING_STUB_VERSION,
        "domain": domain,
        "source": "LOCAL_STUB_ONLY",
        "no_external_data": True,
        "scraping_active": False,
        "network": False,
        "fetch": False,
        "crawl": False,
        "external_http": False,
        "ingestion_auto": False,
        "web_scrape_allowed": False,
        "quarantine_policy": "WEB_SCRAPE_QUARANTINED",
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
