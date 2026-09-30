"""Physical smoke for the local Qwen text provider."""
from __future__ import annotations

from jarvis.contracts import ContextSnapshot
from jarvis.integrations.local_qwen_cognition import from_environment


def main() -> int:
    qwen = from_environment()
    print(f"QWEN_TEXT_SMOKE: endpoint={qwen.endpoint} model={qwen.model}")
    try:
        answer = qwen.respond(
            "Réponds en une phrase courte : pourquoi le ciel paraît-il bleu ?",
            ContextSnapshot("physical qwen text smoke"),
        )
    except Exception as exc:
        print(f"QWEN_TEXT_PHYSICAL: FAIL {type(exc).__name__}: {exc}")
        return 2

    print("QWEN_TEXT_RESPONSE_BEGIN")
    print(answer)
    print("QWEN_TEXT_RESPONSE_END")
    print("QWEN_TEXT_PHYSICAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
