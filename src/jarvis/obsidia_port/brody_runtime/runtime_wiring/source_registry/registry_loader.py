# runtime_wiring/source_registry/registry_loader.py
# Load and filter the source file registry — stdlib only
# No zip extraction. No source pack import. No runtime activation.

from __future__ import annotations
import csv
import json
import pathlib
from typing import Any, Callable, Dict, List, Optional

from .registry_types import SourceFileRegistryEntry, VALID_ADAPTER_TARGETS


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent.parent


def _default_registry_json() -> pathlib.Path:
    return _repo_root() / "runtime_wiring" / "source_registry" / "source_file_registry.json"


def _default_registry_csv() -> pathlib.Path:
    return _repo_root() / "runtime_wiring" / "source_registry" / "source_file_registry.csv"


def load_registry_json(path: Optional[pathlib.Path] = None) -> List[SourceFileRegistryEntry]:
    """Load registry from JSON file. Raises FileNotFoundError if absent (fail-closed)."""
    p = path or _default_registry_json()
    if not p.is_file():
        raise FileNotFoundError(f"FAIL_CLOSED: registry JSON not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    entries = []
    for row in data:
        entry = SourceFileRegistryEntry(
            registry_id=row["registry_id"],
            source_family=row["source_family"],
            source_zip=row["source_zip"],
            internal_path=row["internal_path"],
            file_name=row["file_name"],
            extension=row["extension"],
            size_bytes=int(row["size_bytes"]),
            recommended_decision=row["recommended_decision"],
            boundary_required=row["boundary_required"],
            claim_scope=row["claim_scope"],
            quarantine_status=row["quarantine_status"],
            adapter_target=row["adapter_target"],
            packet_target=row["packet_target"],
            runtime_allowed_now=bool(row.get("runtime_allowed_now", False)),
            emits_act=bool(row.get("emits_act", False)),
            emits_decision=bool(row.get("emits_decision", False)),
            source_status=row.get("source_status", "COPIED_READONLY"),
            source_subfamily=row.get("source_subfamily", ""),
            notes=row.get("notes", ""),
        )
        entries.append(entry)
    return entries


def load_registry_csv(path: Optional[pathlib.Path] = None) -> List[SourceFileRegistryEntry]:
    """Load registry from CSV file. Raises FileNotFoundError if absent (fail-closed)."""
    p = path or _default_registry_csv()
    if not p.is_file():
        raise FileNotFoundError(f"FAIL_CLOSED: registry CSV not found: {p}")
    entries = []
    with open(p, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = SourceFileRegistryEntry(
                registry_id=row["registry_id"],
                source_family=row["source_family"],
                source_zip=row["source_zip"],
                internal_path=row["internal_path"],
                file_name=row["file_name"],
                extension=row["extension"],
                size_bytes=int(row.get("size_bytes", 0)),
                recommended_decision=row["recommended_decision"],
                boundary_required=row["boundary_required"],
                claim_scope=row["claim_scope"],
                quarantine_status=row["quarantine_status"],
                adapter_target=row["adapter_target"],
                packet_target=row["packet_target"],
                runtime_allowed_now=row.get("runtime_allowed_now", "false").lower() == "true",
                emits_act=row.get("emits_act", "false").lower() == "true",
                emits_decision=row.get("emits_decision", "false").lower() == "true",
                source_status=row.get("source_status", "COPIED_READONLY"),
                source_subfamily=row.get("source_subfamily", ""),
                notes=row.get("notes", ""),
            )
            entries.append(entry)
    return entries


def filter_by_family(
    entries: List[SourceFileRegistryEntry], family: str
) -> List[SourceFileRegistryEntry]:
    return [e for e in entries if e.source_family == family]


def filter_by_adapter_target(
    entries: List[SourceFileRegistryEntry], adapter_target: str
) -> List[SourceFileRegistryEntry]:
    return [e for e in entries if e.adapter_target == adapter_target]


def filter_runtime_forbidden(
    entries: List[SourceFileRegistryEntry],
) -> List[SourceFileRegistryEntry]:
    """Return entries that must NOT be imported at runtime."""
    return [
        e for e in entries
        if e.recommended_decision in {"DO_NOT_IMPORT_RUNTIME", "ARCHIVE_ONLY", "KEEP_QUARANTINE"}
        or e.extension == ".py"
        or e.runtime_allowed_now is True
    ]


def count_by_family(entries: List[SourceFileRegistryEntry]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for e in entries:
        counts[e.source_family] = counts.get(e.source_family, 0) + 1
    return dict(sorted(counts.items()))


def count_by_field(
    entries: List[SourceFileRegistryEntry], field_name: str
) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for e in entries:
        val = str(getattr(e, field_name, "UNKNOWN"))
        counts[val] = counts.get(val, 0) + 1
    return dict(sorted(counts.items()))


def validate_registry(entries: List[SourceFileRegistryEntry]) -> List[str]:
    """
    Validate all entries. Returns list of violation strings.
    Empty list = all valid (fail-closed).
    """
    errors = []
    for entry in entries:
        try:
            entry.validate_invariants()
        except AssertionError as exc:
            errors.append(str(exc))
    return errors
