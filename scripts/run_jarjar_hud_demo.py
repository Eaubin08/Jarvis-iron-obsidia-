"""Launch the Jarjar HUD without external models.

This is a physical UI gate only. It proves the interface, text path, avatar and
voice-state controls without claiming production cognition.
"""
from jarvis.hud_app import run_hud
from jarvis.hud_controller import HUDController
from jarvis.hud_state import HUDModel


def demo_text(text: str) -> str:
    return f"Reçu. Mode démo HUD actif. Tu as écrit : {text}"


def demo_voice():
    return ("test vocal", "Canal vocal de démonstration actif.")


if __name__ == "__main__":
    run_hud(
        HUDController(
            model=HUDModel(),
            text_handler=demo_text,
            voice_turn_handler=demo_voice,
        )
    )
