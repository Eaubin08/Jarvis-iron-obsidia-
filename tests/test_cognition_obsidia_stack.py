import json

from jarvis.contracts import ContextSnapshot
from jarvis.integrations.obsidia_stack_cognition import ObsidiaStackCognition


def ctx():
    return ContextSnapshot(summary="test")


def test_obsidia_stack_provider_posts_canonical_brody_payload():
    seen = {}

    def transport(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["headers"] = dict(request.header_items())
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return json.dumps({"final_answer": "Réponse gouvernée."}).encode("utf-8")

    provider = ObsidiaStackCognition(
        endpoint="http://127.0.0.1:8000/api/brody/chat",
        api_key="test-key",
        session_id="jarjar-test",
        transport=transport,
    )
    assert provider.respond("Explique-moi Obsidia", ctx()) == "Réponse gouvernée."
    assert seen["url"].endswith("/api/brody/chat")
    assert seen["payload"]["message"] == "Explique-moi Obsidia"
    assert seen["payload"]["session_id"] == "jarjar-test"
    assert seen["payload"]["allow_provider"] is True
    assert seen["payload"]["allow_memory_candidate"] is False
    assert seen["payload"]["allow_manual_apply"] is False
    assert seen["headers"]["X-api-key"] == "test-key"


def test_obsidia_stack_provider_accepts_response_fallback_field():
    def transport(request, timeout):
        return json.dumps({"response": "Bonjour."}).encode("utf-8")

    provider = ObsidiaStackCognition(transport=transport)
    assert provider.respond("salut", ctx()) == "Bonjour."
