"""Thin launcher for the canonical Jarjar live runtime."""
from __future__ import annotations

from jarvis.live_runtime import run_live
from jarvis.runtime_profile import require_canonical_preflight


if __name__ == "__main__":
    require_canonical_preflight()
    run_live()
