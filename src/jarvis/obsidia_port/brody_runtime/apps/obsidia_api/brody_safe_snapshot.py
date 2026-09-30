"""
Brody Safe Snapshot — Fail-soft wrapper for all adapter calls
===============================================================
Every adapter function wrapped with try/except.
If a source fails:
  - Status = "ERROR"
  - Error detail captured
  - Fallback snapshot returned
  - Boundary invariants preserved

Used by routes/brody.py to guarantee HTTP 200 regardless of
peripheral source availability.
"""
from __future__ import annotations

from typing import Any, Callable

FAIL_SOFT_BOUNDARY: dict[str, Any] = {
    "readonly": True,
    "memory_write": False,
    "graphiti_write": False,
    "neo4j_write": False,
    "emits_act": False,
    "emits_verdict": False,
    "kernel_mutation": False,
    "decision_authority": "KX108_ONLY",
}


def safe_call_snapshot(
    name: str,
    fn: Callable[..., dict[str, Any]],
    *args: Any,
    fallback_extra: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Call a snapshot-builder function safely.

    Parameters:
      name: Human-readable snapshot name for error reporting
      fn: The snapshot builder function to call
      *args, **kwargs: Passed to fn
      fallback_extra: Extra fields to merge into fallback on error

    Returns:
      The snapshot dict from fn, or a FAIL_SOFT fallback if fn raises.
    """
    try:
        result = fn(*args, **kwargs)
        if not isinstance(result, dict):
            return {
                "status": "ERROR",
                "source_mode": "FAIL_SOFT",
                "error_type": "INVALID_RETURN_TYPE",
                "error_message": f"{name} returned non-dict: {type(result).__name__}",
                "snapshot_name": name,
                **FAIL_SOFT_BOUNDARY,
            }
        # Mark as successfully sourced
        result.setdefault("snapshot_name", name)
        return result
    except Exception as exc:
        fallback: dict[str, Any] = {
            "status": "ERROR",
            "source_mode": "FAIL_SOFT",
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:300],
            "snapshot_name": name,
            **FAIL_SOFT_BOUNDARY,
        }
        if fallback_extra:
            fallback.update(fallback_extra)
        return fallback


def empty_snapshot(name: str, reason: str = "NOT_BUILT") -> dict[str, Any]:
    """Return a minimal NOT_BUILT snapshot."""
    return {
        "status": "NOT_BUILT",
        "source_mode": "FAIL_SOFT",
        "error_type": "NOT_BUILT",
        "error_message": reason,
        "snapshot_name": name,
        **FAIL_SOFT_BOUNDARY,
    }
