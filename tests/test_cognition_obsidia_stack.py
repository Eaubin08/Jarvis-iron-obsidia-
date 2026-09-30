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


def test_obsidia_stack_provider_records_routing_metadata():
    def transport(request, timeout):
        return json.dumps({
            "final_answer": "Réponse.",
            "source": "LOCAL_STRUCTURAL",
            "provider_status": "DISABLED_BY_POLICY",
            "provider_called": False,
            "selected_provider": None,
            "fastpath": False,
            "decision_authority": "KX108_ONLY",
            "readonly": True,
        }).encode("utf-8")

    provider = ObsidiaStackCognition(transport=transport)
    assert provider.respond("question", ctx()) == "Réponse."
    assert provider.last_trace["provider_status"] == "DISABLED_BY_POLICY"
    assert provider.last_trace["provider_called"] is False
    assert provider.last_trace["decision_authority"] == "KX108_ONLY"


def test_obsidia_stack_rejects_legacy_memory_pass_without_native_memory():
    def transport(request, timeout):
        return json.dumps({
            "source": "REAL_BRODY_RUNTIME_NO_GRAPHITI",
            "voice_runtime": "BRODY_OBSIDIEN_V1_4_12A",
            "memory_response_chain_snapshot": {
                "source_mode": "LOCAL_GRAPHITI_INDEX_FALLBACK",
                "chain_source": "local_graphiti_index→hydrate_packet→local_response_engine",
                "status": "BRODY_MEMORY_RESPONSE_CHAIN_PASS",
                "material_quality": "USABLE_MATERIAL",
                "response_md": "Legacy memory material that should not be trusted.",
            },
            "true_voice_snapshot": {
                "final_answer": "Legacy answer presented as a successful chain.",
                "final_answer_source": "MEMORY_RESPONSE_CHAIN",
            },
            "decision_authority": "KX108_ONLY",
            "readonly": True,
        }).encode("utf-8")

    provider = ObsidiaStackCognition(transport=transport)
    answer = provider.respond("Explique-moi Obsidia", ctx())

    assert "ancien fallback Graphiti" in answer
    assert provider.last_trace["native_memory_active"] is False
    assert provider.last_trace["legacy_memory_active"] is True


def test_obsidia_stack_accepts_memory_independent_domain_raccord_on_legacy_memory():
    def transport(request, timeout):
        return json.dumps({
            "source": "REAL_BRODY_RUNTIME_NO_GRAPHITI",
            "voice_runtime": "BRODY_OBSIDIEN_V1_4_12A",
            "memory_response_chain_snapshot": {
                "source_mode": "LOCAL_GRAPHITI_INDEX_FALLBACK",
                "chain_source": "local_graphiti_index→hydrate_packet→local_response_engine",
                "status": "BRODY_MEMORY_RESPONSE_CHAIN_PASS",
            },
            "true_voice_snapshot": {
                "final_answer": "Legacy memory answer that must not win.",
                "final_answer_source": "MEMORY_RESPONSE_CHAIN",
                "domain_voice_mode": "DOMAIN_RACCORD_READONLY_STATE",
                "domain_raccord_snapshot": {
                    "status": "DOMAIN_RACCORD_READY",
                    "structural_answer_available": True,
                    "structural_answer": "Brody observe le runtime en lecture seule. Autorité : KX108_ONLY.",
                    "memory_dependency": "NONE",
                    "memory_enrichment": "OPTIONAL",
                },
            },
            "decision_authority": "KX108_ONLY",
            "readonly": True,
        }).encode("utf-8")

    provider = ObsidiaStackCognition(transport=transport)
    answer = provider.respond("Quel est ton rôle en tant que Jarjar ?", ctx())

    assert answer == "Brody observe le runtime en lecture seule. Autorité : KX108_ONLY."
    assert provider.last_trace["legacy_memory_active"] is True
    assert provider.last_trace["domain_structural_answer_available"] is True
    assert provider.last_trace["domain_memory_dependency"] == "NONE"


def test_obsidia_stack_capability_scope_governance_beats_legacy_true_voice():
    def transport(request, timeout):
        return json.dumps({
            "source": "REAL_BRODY_RUNTIME_NO_GRAPHITI",
            "voice_runtime": "BRODY_OBSIDIEN_V1_4_12A",
            "memory_response_chain_snapshot": {
                "source_mode": "LOCAL_GRAPHITI_INDEX_FALLBACK",
                "chain_source": "local_graphiti_index→hydrate_packet→local_response_engine",
                "status": "BRODY_MEMORY_RESPONSE_CHAIN_PASS",
            },
            "authority_snapshot": {
                "request_type": "CAPABILITY_SCOPE",
                "response_mode": "CAPABILITY_SCOPE",
                "brody_may": [
                    "repondre_naturellement",
                    "expliquer_ce_que_brody_peut_faire",
                    "expliquer_ce_que_brody_ne_peut_pas_faire",
                    "expliquer_role_humain_operateur",
                    "expliquer_role_kx108_decision_authority",
                    "expliquer_role_memoire_candidate_only",
                    "lister_capacites_et_limites",
                    "expliquer_automation_snapshot",
                    "expliquer_boundary_complet",
                ],
                "brody_must_not": [
                    "decider",
                    "emettre_act",
                    "emettre_hold_block_allow_comme_verdict",
                    "ecrire_memoire_automatiquement",
                    "executer",
                    "bypass_x108",
                ],
                "requires_kx108_decision": False,
                "decision_authority": "KX108_ONLY",
            },
            "true_voice_snapshot": {
                "final_answer": "Legacy memory answer that must not win.",
                "final_answer_source": "MEMORY_RESPONSE_CHAIN",
                "domain_raccord_snapshot": {
                    "status": "NO_DOMAIN_RACCORD",
                    "structural_answer_available": False,
                    "memory_dependency": "NONE",
                },
            },
            "decision_authority": "KX108_ONLY",
            "readonly": True,
        }).encode("utf-8")

    provider = ObsidiaStackCognition(transport=transport)
    answer = provider.respond("Qui peut faire quoi entre Brody, X108 et humain mémoire ?", ctx())

    assert "Jarjar est la surface locale" in answer
    assert "KX108/X108 reste l'unique autorité de décision" in answer
    assert "Native Memory n'est pas active" in answer
    assert provider.last_trace["authority_request_type"] == "CAPABILITY_SCOPE"
    assert provider.last_trace["authority_response_mode"] == "CAPABILITY_SCOPE"
