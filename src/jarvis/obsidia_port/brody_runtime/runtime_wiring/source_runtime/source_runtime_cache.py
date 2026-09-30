# runtime_wiring/source_runtime/source_runtime_cache.py
# TTL-based in-memory cache for registry entries and pack availability.
# P42B: list_available_families_cached() is now CI-safe (registry-first discovery).
# Never caches file content — only metadata and entry lists.
# KX108_ONLY. No ACT. No write. No extraction.

from __future__ import annotations
import json
import pathlib
import time
from typing import Dict, List, Optional, Tuple

from runtime_wiring.source_registry.registry_types import SourceFileRegistryEntry

_REGISTRY_TTL: float = 60.0   # seconds — registry entries
_PACK_AVAIL_TTL: float = 60.0  # seconds — pack availability probes

# Registry cache
_registry_cache: Optional[List[SourceFileRegistryEntry]] = None
_registry_loaded_at: float = 0.0

# Pack availability cache: source_zip → (available, loaded_at)
_pack_avail_cache: Dict[str, Tuple[bool, float]] = {}

# Hit/miss counters
_stats_hits: int = 0
_stats_misses: int = 0

# Fast path for family discovery — reads from committed summary JSON
_REGISTRY_SUMMARY_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "source_registry"
    / "source_registry_summary.json"
)


def load_registry_cached() -> List[SourceFileRegistryEntry]:
    """Load registry with TTL-based cache. Falls back to fresh load on miss/expiry."""
    global _registry_cache, _registry_loaded_at, _stats_hits, _stats_misses
    now = time.monotonic()
    if _registry_cache is not None and (now - _registry_loaded_at) < _REGISTRY_TTL:
        _stats_hits += 1
        return _registry_cache
    from runtime_wiring.source_registry.registry_loader import load_registry_json
    _registry_cache = load_registry_json()
    _registry_loaded_at = now
    _stats_misses += 1
    return _registry_cache


def is_pack_available_cached(source_zip: str) -> bool:
    """Check pack availability with TTL-based cache. Never extracts."""
    now = time.monotonic()
    if source_zip in _pack_avail_cache:
        result, loaded_at = _pack_avail_cache[source_zip]
        if (now - loaded_at) < _PACK_AVAIL_TTL:
            return result
    from runtime_wiring.source_runtime.source_pack_resolver import is_source_pack_available
    result = is_source_pack_available(source_zip)
    _pack_avail_cache[source_zip] = (result, now)
    return result


def list_discoverable_families() -> List[str]:
    """Return all families known to the registry (CI-safe, no local pack check).

    Fast path: reads source_registry_summary.json (committed to git, always present).
    Fallback: derives from full registry JSON.
    Returns all 8 canonical families regardless of local pack availability.
    """
    try:
        if _REGISTRY_SUMMARY_PATH.is_file():
            data = json.loads(_REGISTRY_SUMMARY_PATH.read_text(encoding="utf-8"))
            families = sorted(data.get("families", {}).keys())
            if families:
                return families
    except Exception:
        pass
    # Fallback: derive from full registry
    try:
        entries = load_registry_cached()
        return sorted({e.source_family for e in entries})
    except FileNotFoundError:
        return []


def get_family_local_pack_availability() -> Dict[str, bool]:
    """Return per-family local pack availability dict.

    True  = local pack present, full hydration possible (FULL_LOCAL).
    False = no local pack, metadata-only mode (METADATA_ONLY).
    """
    try:
        entries = load_registry_cached()
    except FileNotFoundError:
        return {}
    zips_per_family: Dict[str, set] = {}
    for e in entries:
        zips_per_family.setdefault(e.source_family, set()).add(e.source_zip)
    return {
        family: any(is_pack_available_cached(z) for z in zips)
        for family, zips in zips_per_family.items()
    }


def list_available_families_cached() -> List[str]:
    """Return families available for selection (CI-safe, registry-first).

    P42B: Returns ALL families from the canonical registry, regardless of whether
    local source packs are present. Previously returned only families with locally
    available packs — this caused CI failures because _source_packs/ is gitignored.

    Semantic change: "available" now means AVAILABLE_FOR_SELECTION (known to the
    system), not FULLY_HYDRATABLE. Use get_family_local_pack_availability() to
    distinguish FULL_LOCAL from METADATA_ONLY hydration mode per family.
    """
    return list_discoverable_families()


def clear_cache() -> None:
    """Clear all caches and reset counters. For tests and forced refresh."""
    global _registry_cache, _registry_loaded_at, _stats_hits, _stats_misses
    _registry_cache = None
    _registry_loaded_at = 0.0
    _pack_avail_cache.clear()
    _stats_hits = 0
    _stats_misses = 0


def get_cache_stats() -> dict:
    """Return current cache statistics. No side effects."""
    total = _stats_hits + _stats_misses
    return {
        "registry_cache_loaded": _registry_cache is not None,
        "registry_entry_count": len(_registry_cache) if _registry_cache else 0,
        "registry_ttl_seconds": _REGISTRY_TTL,
        "pack_avail_cached_count": len(_pack_avail_cache),
        "cache_hits": _stats_hits,
        "cache_misses": _stats_misses,
        "cache_hit_rate": round(_stats_hits / total, 3) if total > 0 else None,
        "source": "SOURCE_RUNTIME_CACHE_P28",
        "readonly": True,
        "decision_authority": "KX108_ONLY",
    }
