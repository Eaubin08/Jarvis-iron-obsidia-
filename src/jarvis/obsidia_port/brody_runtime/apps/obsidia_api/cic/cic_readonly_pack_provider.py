"""
CIC Readonly Pack Provider
SCOPE: READONLY_BINDING_PREP
PATCH: YES — new readonly adapter only
MOVE/COMMIT/FREEZE/PUSH: NO
KERNEL_BINDING: NO  |  ACT: NO  |  NCP: NO  |  SCRAPING: NO
DECISION_AUTHORITY: KX108_ONLY
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from apps.obsidia_api.cic.cic_receipt_pack import build_cic_receipt
from apps.obsidia_api.cic.cic_ncp_readonly_stub import build_ncp_readonly_stub
from apps.obsidia_api.cic.cic_scraping_readonly_stub import build_scraping_readonly_stub

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

_ZIP_CANONICAL = (
    _REPO_ROOT
    / ".local_exports"
    / "CAUSAL_IDENTITY_STRUCTURE_PACK_CIC_ONLY_REPAIRED_METRICS_V0_20260613_020551.zip"
)

_REPO_SOURCES = [
    "registries/cic_metric_mapping_v0.yaml",
    "docs/METRICS_STATUS_POLICY.md",
    "reports/CAUSAL_IDENTITY_REPO_METRICS_AUDIT.md",
    "reports/CIC_HIGH_VALUE_SOURCES_20260613_013837.txt",
    "reports/CAUSAL_IDENTITY_FINAL_PACK_REPORT.md",
]

_CONFIRMED_METRIC_FAMILIES: list[str] = [
    "guard_metrics",
    "timing_metrics",
    "reversibility_metrics",
    "proof_metrics",
    "trace_metrics",
    "context_metrics",
    "score_threshold_metrics",
    "missing_data_metrics",
]

_PARTIAL_METRIC_FAMILIES: list[str] = [
    "source_metrics",
    "capacity_metrics",
    "resource_metrics",
    "behavior_metrics",
    "path_metrics",
    "projection_metrics",
    "memory_metrics",
]

_MISSING_OR_INACTIVE: list[str] = [
    "causal_capacity_formula:NEEDS_DOMAIN_CALIBRATION",
    "anomaly_formula:NEEDS_DOMAIN_CALIBRATION",
    "ncp_targeted_fetch:STUB_V0_READONLY_PROVIDER_BOUND",
    "scraping:STUB_V0_READONLY_PROVIDER_BOUND",
    "kernel_binding:MISSING",
]

_CENTRAL_RULES: list[str] = [
    "Invariant > Reversibilite > Score > Projection",
    "A score cannot authorize what an invariant forbids.",
    "Critical missing data on irreversible action triggers HOLD / BLOCK / REVIEW.",
    "Memory is not sovereign.",
    "Projection is not prediction.",
]

_DOMAIN_RELEVANCE: dict[str, Any] = {
    "bank": {
        "confirmed": [
            "guard_metrics",
            "timing_metrics",
            "reversibility_metrics",
            "proof_metrics",
            "trace_metrics",
            "context_metrics",
            "score_threshold_metrics",
            "missing_data_metrics",
        ],
        "partial": ["source_metrics", "capacity_metrics", "resource_metrics", "behavior_metrics"],
        "missing": ["causal_capacity_formula", "anomaly_formula"],
    },
    "trading": {
        "confirmed": [
            "guard_metrics",
            "timing_metrics",
            "reversibility_metrics",
            "proof_metrics",
            "trace_metrics",
            "context_metrics",
            "score_threshold_metrics",
            "missing_data_metrics",
        ],
        "partial": ["source_metrics", "capacity_metrics", "resource_metrics", "path_metrics", "projection_metrics"],
        "missing": ["causal_capacity_formula", "anomaly_formula"],
    },
    "gps_defense_aviation": {
        "confirmed": [
            "guard_metrics",
            "timing_metrics",
            "reversibility_metrics",
            "proof_metrics",
            "trace_metrics",
            "context_metrics",
            "missing_data_metrics",
        ],
        "partial": ["source_metrics", "capacity_metrics", "path_metrics"],
        "missing": ["causal_capacity_formula", "anomaly_formula"],
    },
    "ecom": "ECOM_NOT_FOUND",
}

_FORBIDDEN_CAPABILITIES: list[str] = [
    "kernel_mutation",
    "x108_binding",
    "act",
    "decision_authority",
    "ncp_activation",
    "scraping_activation",
    "world_connection_activation",
    "memory_write",
]


def _sha256_zip(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def build_cic_readonly_context() -> dict[str, Any]:
    """
    Retourne le contexte CIC readonly complet.
    Ne jamais écrire, extraire dans le repo actif, appeler le kernel, ou émettre ACT.
    Tous les consommateurs doivent traiter ce résultat comme lecture seule.
    """
    zip_exists = _ZIP_CANONICAL.exists()
    zip_sha256 = _sha256_zip(_ZIP_CANONICAL) if zip_exists else "ZIP_NOT_FOUND"

    repo_sources_status: dict[str, str] = {}
    for src in _REPO_SOURCES:
        p = _REPO_ROOT / src
        repo_sources_status[src] = "PRESENT" if p.exists() else "MISSING"

    receipt = build_cic_receipt(
        domain="cic_readonly_pack",
        source_zip_sha256=zip_sha256,
        confirmed_metric_families=_CONFIRMED_METRIC_FAMILIES,
    )

    ncp_context = build_ncp_readonly_stub(domain="cic_readonly_pack")
    scraping_context = build_scraping_readonly_stub(domain="cic_readonly_pack")

    return {
        "source_zip_path": str(_ZIP_CANONICAL),
        "source_zip_sha256": zip_sha256,
        "source_status": "LOCAL_FREEZE_READONLY",
        "repo_sources": repo_sources_status,
        "confirmed_metric_families": _CONFIRMED_METRIC_FAMILIES,
        "partial_metric_families": _PARTIAL_METRIC_FAMILIES,
        "missing_or_inactive": _MISSING_OR_INACTIVE,
        "central_rules": _CENTRAL_RULES,
        "domain_relevance": _DOMAIN_RELEVANCE,
        "forbidden_capabilities": _FORBIDDEN_CAPABILITIES,
        "authority": "NONE",
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "emits_act": False,
        "kernel_mutation": False,
        "x108_binding": False,
        "ncp_active": False,
        "scraping_active": False,
        "cic_receipt": receipt,
        "ncp_context": ncp_context,
        "scraping_context": scraping_context,
    }
