"""Run the readonly Jarjar G13/F12 physical-device probe."""
from __future__ import annotations

import os

from jarvis.physical_probe import format_probe_summary, run_physical_probe


def main() -> None:
    indices = tuple(
        int(x.strip())
        for x in os.getenv("JARJAR_CAMERA_INDICES", "0,1").split(",")
        if x.strip()
    )
    result = run_physical_probe(camera_indices=indices)
    print(format_probe_summary(result))


if __name__ == "__main__":
    main()
