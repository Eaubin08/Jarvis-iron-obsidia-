# runtime_wiring/source_runtime/source_runtime_query.py
# Query the source registry for relevant entries, then hydrate them in read-only mode.
# Returns hydrated ContextPackets ready for X108 routing.
# P42B: two-tier hydration — FULL_LOCAL (pack present) or METADATA_ONLY (pack absent, CI-safe).
# Never loads all 15298 entries — targeted, limit-enforced queries only.

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from runtime_wiring.source_registry.registry_types import SourceFileRegistryEntry
from runtime_wiring.source_registry.registry_to_adapter_dry_run import (
    _FORBIDDEN_DECISIONS,
    _FORBIDDEN_QUARANTINE,
)
from runtime_wiring.source_runtime.source_runtime_cache import (
    load_registry_cached,
    is_pack_available_cached,
)
from runtime_wiring.source_runtime.source_context_hydrator import (
    HydrationError,
    hydrate_entry,
)
from runtime_wiring.packet_types import ContextPacket

_PREFERRED_EXTENSIONS = frozenset({".md", ".yaml", ".yml"})
_DEFAULT_LIMIT = 5
_MAX_LIMIT = 20


@dataclass
class QueryResult:
    family: str
    registry_id: str
    file_name: str
    internal_path: str
    context_packet: ContextPacket
    content_preview: str
    content_hash: str
    bytes_read: int
    hydration_status: str  # "OK", "METADATA_ONLY", or "SKIPPED:<reason>"


def _is_routable(entry: SourceFileRegistryEntry) -> bool:
    """True if entry can be fully hydrated (not forbidden, pack available, safe extension)."""
    if entry.recommended_decision in _FORBIDDEN_DECISIONS:
        return False
    if entry.quarantine_status in _FORBIDDEN_QUARANTINE:
        return False
    if entry.extension.lower() in (".py", ".pyc"):
        return False
    if not is_pack_available_cached(entry.source_zip):
        return False
    return True


def _is_discoverable(entry: SourceFileRegistryEntry) -> bool:
    """True if entry qualifies for metadata-only context (no pack availability required).

    Same safety gates as _is_routable(), minus the local pack check.
    Used for CI-safe discovery when source packs are not locally available.
    """
    if entry.recommended_decision in _FORBIDDEN_DECISIONS:
        return False
    if entry.quarantine_status in _FORBIDDEN_QUARANTINE:
        return False
    if entry.extension.lower() in (".py", ".pyc"):
        return False
    return True


def _build_metadata_only_packet(entry: SourceFileRegistryEntry) -> ContextPacket:
    """Build a metadata-only ContextPacket for a discoverable entry without a local pack.

    All safety invariants are enforced: advisory_only=True, readonly=True,
    emits_act=False, runtime_allowed_now=False, decision_authority=KX108_ONLY.
    """
    pkt = ContextPacket(
        context_id=f"METADATA_ONLY:{entry.registry_id}",
        source=f"registry:{entry.source_family}",
        source_status="MISSING_LOCAL_PACK_METADATA_ONLY",
        claim_scope=entry.claim_scope or "REGISTRY_METADATA",
        boundary="HARD_READONLY_ADVISORY_ONLY",
        timestamp_or_tick="REGISTRY_STATIC",
        advisory_only=True,
        readonly=True,
        runtime_allowed_now=False,
        emits_act=False,
        emits_decision=False,
        decision_authority="KX108_ONLY",
        labels=["METADATA_ONLY", "MISSING_LOCAL_PACK", "CI_SAFE"],
        payload={
            "registry_id": entry.registry_id,
            "source_family": entry.source_family,
            "source_zip": entry.source_zip,
            "file_name": entry.file_name,
            "extension": entry.extension,
            "adapter_target": entry.adapter_target,
            "source_resolution_status": "MISSING_LOCAL_PACK_METADATA_ONLY",
            "hydration_mode": "METADATA_ONLY",
            "hydration_warning": (
                "Local pack absent in this environment — registry metadata only, "
                "no file content loaded. Safe for selection, not for full analysis."
            ),
        },
        notes="metadata-only: local pack not available in this environment",
    )
    pkt.validate_invariants()
    return pkt


def query_source_packs(
    families: Optional[List[str]] = None,
    keyword: Optional[str] = None,
    extensions: Optional[List[str]] = None,
    limit: int = _DEFAULT_LIMIT,
    prefer_short_files: bool = True,
) -> List[QueryResult]:
    """
    Query the source registry, hydrate matching entries in read-only mode.

    P42B two-tier hydration:
    - Tier 1 (FULL_LOCAL): entries where local pack is available → full file content.
    - Tier 2 (METADATA_ONLY): entries from discoverable families without local packs →
      registry metadata only, no file content. CI-safe.

    Tier 1 entries are selected first. For families not covered by Tier 1, one
    METADATA_ONLY entry is added per uncovered family (up to limit).

    Args:
        families: Restrict to these source families. None = all.
        keyword: Filter by keyword in file_name or internal_path (case-insensitive).
        extensions: Restrict to these extensions (e.g. [".md", ".yaml"]).
        limit: Max entries to hydrate. Capped at _MAX_LIMIT.
        prefer_short_files: Prefer shorter files (faster preview loading).

    Returns:
        List of QueryResult. Never raises — failed hydrations are marked SKIPPED.
        hydration_status values: "OK", "METADATA_ONLY", "SKIPPED:<reason>".
    """
    limit = min(max(1, limit), _MAX_LIMIT)
    exts = frozenset(e.lower() for e in extensions) if extensions else _PREFERRED_EXTENSIONS

    try:
        all_entries = load_registry_cached()
    except FileNotFoundError:
        return []

    # Separate candidates into two tiers
    routable_candidates: List[SourceFileRegistryEntry] = []
    meta_candidates: List[SourceFileRegistryEntry] = []

    for e in all_entries:
        if families and e.source_family not in families:
            continue
        if exts and e.extension.lower() not in exts:
            continue
        if keyword and (
            keyword.lower() not in e.file_name.lower()
            and keyword.lower() not in e.internal_path.lower()
        ):
            continue
        if _is_routable(e):
            routable_candidates.append(e)
        elif _is_discoverable(e):
            meta_candidates.append(e)

    # Sort by size for preview efficiency
    if prefer_short_files:
        routable_candidates.sort(key=lambda e: e.size_bytes)
        meta_candidates.sort(key=lambda e: e.size_bytes)

    # Per-family limit based on all candidate families combined
    all_candidate_families = (
        {e.source_family for e in routable_candidates}
        | {e.source_family for e in meta_candidates}
    )
    target_family_count = len(all_candidate_families) or 1
    per_family_limit = max(1, limit // target_family_count)

    # Tier 1 selection: routable entries (full hydration)
    selected_full: List[SourceFileRegistryEntry] = []
    per_family_full: Dict[str, int] = {}
    for e in routable_candidates:
        if len(selected_full) >= limit:
            break
        count = per_family_full.get(e.source_family, 0)
        if count >= per_family_limit:
            continue
        selected_full.append(e)
        per_family_full[e.source_family] = count + 1

    # Track which families are already covered by full entries
    covered_families = {e.source_family for e in selected_full}

    # Tier 2 selection: one metadata-only entry per uncovered family
    selected_meta: List[SourceFileRegistryEntry] = []
    added_meta_families: set = set()
    for e in meta_candidates:
        if len(selected_full) + len(selected_meta) >= limit:
            break
        if e.source_family in covered_families:
            continue
        if e.source_family in added_meta_families:
            continue
        selected_meta.append(e)
        added_meta_families.add(e.source_family)

    # Hydrate Tier 1 entries (full)
    results: List[QueryResult] = []
    for entry in selected_full:
        try:
            pkt, loaded = hydrate_entry(entry)
            results.append(QueryResult(
                family=entry.source_family,
                registry_id=entry.registry_id,
                file_name=entry.file_name,
                internal_path=entry.internal_path,
                context_packet=pkt,
                content_preview=loaded.content_preview,
                content_hash=loaded.content_hash,
                bytes_read=loaded.bytes_read,
                hydration_status="OK",
            ))
        except Exception as exc:
            results.append(QueryResult(
                family=entry.source_family,
                registry_id=entry.registry_id,
                file_name=entry.file_name,
                internal_path=entry.internal_path,
                context_packet=None,  # type: ignore[arg-type]
                content_preview="",
                content_hash="",
                bytes_read=0,
                hydration_status=f"SKIPPED:{type(exc).__name__}:{exc}",
            ))

    # Hydrate Tier 2 entries (metadata-only)
    for entry in selected_meta:
        try:
            pkt = _build_metadata_only_packet(entry)
            results.append(QueryResult(
                family=entry.source_family,
                registry_id=entry.registry_id,
                file_name=entry.file_name,
                internal_path=entry.internal_path,
                context_packet=pkt,
                content_preview=(
                    f"[METADATA_ONLY:{entry.source_family}] {entry.file_name} "
                    f"(local pack absent — CI-safe registry metadata)"
                ),
                content_hash="",
                bytes_read=0,
                hydration_status="METADATA_ONLY",
            ))
        except Exception as exc:
            results.append(QueryResult(
                family=entry.source_family,
                registry_id=entry.registry_id,
                file_name=entry.file_name,
                internal_path=entry.internal_path,
                context_packet=None,  # type: ignore[arg-type]
                content_preview="",
                content_hash="",
                bytes_read=0,
                hydration_status=f"SKIPPED:{type(exc).__name__}:{exc}",
            ))

    return results
