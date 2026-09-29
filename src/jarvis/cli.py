"""Minimal local CLI for the standalone F1 runtime."""
from __future__ import annotations

from .providers.local_stub import StubCognition, StubMemory
from .runtime import TextRuntime


def main() -> int:
    runtime = TextRuntime(cognition=StubCognition(), memory=StubMemory())
    print("JARVIS_IRON_F1_READY")
    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if text.strip().lower() in {"exit", "quit"}:
            return 0
        if not text.strip():
            continue
        print(runtime.handle(text))


if __name__ == "__main__":
    raise SystemExit(main())
