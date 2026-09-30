from jarvis.core import JarvisCore
from jarvis.providers.local_stub import DeterministicStubCognition, StubMemory


def test_jarvis_runs_without_obsidia_runtime():
    jarvis = JarvisCore(cognition=DeterministicStubCognition(), memory=StubMemory())
    assert jarvis.handle_text("status") == "JARVIS_V0: status"


def test_core_module_has_no_obsidia_import():
    import inspect
    import jarvis.core

    source = inspect.getsource(jarvis.core).lower()
    assert "import obsidia" not in source
    assert "from obsidia" not in source
