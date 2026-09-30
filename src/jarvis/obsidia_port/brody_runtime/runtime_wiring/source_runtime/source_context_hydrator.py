# runtime_wiring/source_runtime/source_context_hydrator.py
# Hydrates a registry entry into a real ContextPacket by reading the actual file content.
# Calls existing family adapters from source_adapters.py.
# Read-only. No extraction. No .py execution. No ACT.

from __future__ import annotations
from typing import Any, Dict, Optional

from runtime_wiring.source_registry.registry_types import SourceFileRegistryEntry
from runtime_wiring.source_registry.registry_to_adapter_dry_run import _ADAPTER_DISPATCH
from runtime_wiring.source_runtime.source_pack_resolver import (
    MissingSourcePackError,
    resolve_source_pack,
)
from runtime_wiring.source_runtime.readonly_content_loader import (
    ForbiddenFileError,
    FileTooLargeError,
    load_file_from_pack,
    LoadedContent,
)
from runtime_wiring.packet_types import ContextPacket


class HydrationError(RuntimeError):
    """Raised when a registry entry cannot be hydrated."""


def hydrate_entry(
    entry: SourceFileRegistryEntry,
    max_preview_bytes: int = 4096,
) -> tuple[ContextPacket, LoadedContent]:
    """
    Resolve, load, and hydrate a registry entry into a real ContextPacket.

    Returns (ContextPacket, LoadedContent).
    Raises HydrationError if pack is missing or file cannot be read safely.
    """
    if entry.adapter_target not in _ADAPTER_DISPATCH:
        raise HydrationError(
            f"No adapter for {entry.adapter_target!r} in family {entry.source_family}"
        )

    # 1. Resolve source pack path
    try:
        resolved = resolve_source_pack(entry.source_zip)
    except MissingSourcePackError as exc:
        raise HydrationError(f"MISSING_SOURCE_PACK: {exc}") from exc

    # 2. Load file content (read-only, never extract)
    try:
        loaded = load_file_from_pack(resolved, entry.internal_path, max_preview_bytes)
    except ForbiddenFileError as exc:
        raise HydrationError(f"FORBIDDEN_FILE: {exc}") from exc
    except FileTooLargeError as exc:
        raise HydrationError(f"FILE_TOO_LARGE: {exc}") from exc
    except FileNotFoundError as exc:
        raise HydrationError(f"FILE_NOT_FOUND: {exc}") from exc

    # 3. Build metadata dict with real content injected
    metadata: Dict[str, Any] = {
        "registry_id": entry.registry_id,
        "source_family": entry.source_family,
        "source_zip": entry.source_zip,
        "file_name": entry.file_name,
        "extension": entry.extension,
        "size_bytes": entry.size_bytes,
        "recommended_decision": entry.recommended_decision,
        "boundary_required": entry.boundary_required,
        "claim_scope": entry.claim_scope,
        "quarantine_status": entry.quarantine_status,
        "adapter_target": entry.adapter_target,
        "source_status": resolved.source_status,
        "internal_path_label": entry.internal_path,
        # Real content (read-only preview)
        "content_preview": loaded.content_preview,
        "content_hash": loaded.content_hash,
        "bytes_read": loaded.bytes_read,
        "truncated": loaded.truncated,
        # Safety flags — always maintained
        "_zip_extraction": False,
        "_source_pack_import": False,
        "_runtime_allowed_now": False,
        "_real_content_loaded": True,
        "_read_only": True,
    }

    # 4. Call the family adapter (forces all boundary invariants)
    adapter_fn = _ADAPTER_DISPATCH[entry.adapter_target]
    context_packet = adapter_fn(metadata)

    # 5. Validate
    context_packet.validate_invariants()
    assert not context_packet.emits_act, "SAFETY: emits_act must remain False after hydration"
    assert context_packet.advisory_only, "SAFETY: advisory_only must remain True after hydration"

    return context_packet, loaded
