# runtime_wiring/source_runtime/source_pack_resolver.py
# Resolves source_zip name → local path (zip file or directory).
# Searches _source_packs/raw/, Downloads, and known paths.
# Never extracts. Never creates files. Read-only probe only.
# Raises MissingSourcePackError if source is not found locally.

from __future__ import annotations
import pathlib
from dataclasses import dataclass
from typing import Optional

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# Search roots, in priority order
_SEARCH_ROOTS = [
    _REPO_ROOT / "_source_packs" / "OBSIDIA_UNIFIED_IMPLEMENTATION_BACKLOG_RICH_NO_DUPES_V1" / "raw",
    pathlib.Path("C:/Users/User/Downloads"),
    _REPO_ROOT / "_source_packs",
]

# NPL canonical zip (P30): preferred over Downloads directory fallback
_NPL_ZIP_NAME = "OBSIDIA_NARRATIVE_PROVENANCE_LAYER_SPEC_PACK_V1_MAX.zip"
_NPL_CANONICAL_ZIP = (
    _REPO_ROOT
    / "_source_packs"
    / "OBSIDIA_UNIFIED_IMPLEMENTATION_BACKLOG_RICH_NO_DUPES_V1"
    / "raw"
    / _NPL_ZIP_NAME
)

# NPL Downloads directory fallback (pre-P30 path)
_NPL_DIR_NAME = "OBSIDIA_NARRATIVE_PROVENANCE_LAYER_SPEC_PACK_V1_MAX"
_NPL_DIR_INNER = _NPL_DIR_NAME  # double-nested in Downloads


class MissingSourcePackError(FileNotFoundError):
    """Raised when a required source pack cannot be found locally."""


@dataclass
class ResolvedSourcePack:
    source_zip: str
    resolved_path: pathlib.Path
    source_type: str  # "zip" or "directory"
    source_status: str  # "FOUND_LOCAL", "FOUND_DOWNLOADS"
    size_bytes: int


def resolve_source_pack(source_zip: str) -> ResolvedSourcePack:
    """
    Find the local path for a given source_zip name.

    Tries _source_packs/raw/ first, then Downloads, then a directory fallback for NPL.
    Raises MissingSourcePackError if not found.
    """
    # NPL special case: it's an extracted directory, not a zip
    if "NARRATIVE_PROVENANCE" in source_zip.upper() or "NPL" in source_zip.upper():
        return _resolve_npl_directory()

    # Standard zip resolution, with directory pack fallback for _source_packs/
    for root in _SEARCH_ROOTS:
        if not root.exists():
            continue
        candidate = root / source_zip
        if candidate.is_file() and candidate.suffix == ".zip":
            status = "FOUND_DOWNLOADS" if "Downloads" in str(root) else "FOUND_LOCAL"
            return ResolvedSourcePack(
                source_zip=source_zip,
                resolved_path=candidate,
                source_type="zip",
                source_status=status,
                size_bytes=candidate.stat().st_size,
            )
        # P35: directory-based packs in _source_packs/ (not Downloads)
        if candidate.is_dir() and "Downloads" not in str(root):
            file_count = sum(1 for f in candidate.rglob("*") if f.is_file())
            return ResolvedSourcePack(
                source_zip=source_zip,
                resolved_path=candidate,
                source_type="directory",
                source_status="FOUND_LOCAL",
                size_bytes=file_count,
            )

    raise MissingSourcePackError(
        f"Source pack not found locally: {source_zip!r}. "
        f"Expected in {[str(r) for r in _SEARCH_ROOTS if r.exists()]}"
    )


def _resolve_npl_directory() -> ResolvedSourcePack:
    """Resolve the NPL pack — canonical local zip preferred (P30), Downloads directory fallback."""
    # P30: canonical zip in _source_packs/raw/ takes priority
    if _NPL_CANONICAL_ZIP.is_file():
        return ResolvedSourcePack(
            source_zip=_NPL_ZIP_NAME,
            resolved_path=_NPL_CANONICAL_ZIP,
            source_type="zip",
            source_status="FOUND_LOCAL",
            size_bytes=_NPL_CANONICAL_ZIP.stat().st_size,
        )

    # Fallback: Downloads directory (pre-P30 state)
    npl_outer = pathlib.Path("C:/Users/User/Downloads") / _NPL_DIR_NAME
    npl_inner = npl_outer / _NPL_DIR_INNER
    for candidate in (npl_inner, npl_outer):
        if candidate.is_dir():
            file_count = sum(1 for f in candidate.rglob("*") if f.is_file())
            return ResolvedSourcePack(
                source_zip=_NPL_ZIP_NAME,
                resolved_path=candidate,
                source_type="directory",
                source_status="FOUND_DOWNLOADS",
                size_bytes=file_count,
            )
    raise MissingSourcePackError(
        f"NPL not found: expected {_NPL_CANONICAL_ZIP} or {npl_inner} or {npl_outer}"
    )


def is_source_pack_available(source_zip: str) -> bool:
    """Return True if the source pack is locally available."""
    try:
        resolve_source_pack(source_zip)
        return True
    except MissingSourcePackError:
        return False


def list_available_families() -> list[str]:
    """Return list of source families that have locally available packs."""
    from runtime_wiring.source_registry.adapter_target_map import ADAPTER_TARGET_MAP
    from runtime_wiring.source_registry.registry_loader import load_registry_json

    try:
        entries = load_registry_json()
    except FileNotFoundError:
        return []

    zips_per_family: dict[str, set[str]] = {}
    for e in entries:
        zips_per_family.setdefault(e.source_family, set()).add(e.source_zip)

    available = []
    for family, zips in zips_per_family.items():
        for z in zips:
            if is_source_pack_available(z):
                available.append(family)
                break
    return sorted(set(available))
