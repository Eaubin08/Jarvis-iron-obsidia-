from pathlib import Path


def test_g12_live_launcher_is_thin_and_delegates_to_canonical_runtime():
    root = Path(__file__).resolve().parents[1]
    launcher = (root / "scripts" / "run_jarjar_live.py").read_text(encoding="utf-8")
    canonical = (root / "src" / "jarvis" / "live_runtime.py").read_text(encoding="utf-8")

    assert "from jarvis.live_runtime import run_live" in launcher
    assert "build_live_controller" not in launcher
    assert "OpenWakeWordProvider" not in launcher
    assert "FasterWhisperSTT" not in launcher
    assert "KokoroEngine" not in launcher

    assert "def build_live_controller()" in canonical
    assert "def run_live()" in canonical
    assert "GovernedMoveCommandHandler" not in canonical
    assert "governed_move_from_environment" in canonical
    assert "HUDLiveVoiceBridge" in canonical


def test_g12_text_runtime_declares_noncanonical_live_status():
    root = Path(__file__).resolve().parents[1]
    text_runtime = (root / "src" / "jarvis" / "runtime.py").read_text(encoding="utf-8")
    assert "non-canonical for Jarjar live HUD/voice execution" in text_runtime
    assert "jarvis.live_runtime" in text_runtime
