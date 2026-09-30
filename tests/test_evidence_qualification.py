from jarvis.obsidia_port.evidence_qualification import (
    CLAIM_SUPPORT,
    SUPPORTING_MATERIAL,
    build_evidence_qualification_snapshot,
    build_qualified_context,
)


def test_obsidia_size_number_without_relation_is_not_claim_support():
    snapshot = build_evidence_qualification_snapshot(
        user_message="Quelle est la taille d'Obsidia ?",
        semantic_snapshot={"primary_query": "obsidia"},
        requested_memory_target="obsidia",
        native_memory_selected_items=[{
            "title": "Obsidia architecture source",
            "excerpt": (
                "Obsidia est cite comme projet. Le meme paquet contient "
                "aussi 34 arbres et des regroupements ontologiques."
            ),
        }],
        source_pack_hydrated_entries=[],
    )

    assert snapshot["claim_support_required"] is True
    assert snapshot["claim_support_available"] is False
    assert snapshot["qualified_items"][0]["qualification"] == SUPPORTING_MATERIAL
    assert snapshot["counts_by_qualification"][CLAIM_SUPPORT] == 0


def test_obsidia_size_explicit_relation_is_claim_support():
    snapshot = build_evidence_qualification_snapshot(
        user_message="Quelle est la taille d'Obsidia ?",
        semantic_snapshot={"primary_query": "obsidia"},
        requested_memory_target="obsidia",
        native_memory_selected_items=[{
            "title": "Obsidia metrics",
            "excerpt": "La taille d'Obsidia est de 34 arbres dans ce gel.",
        }],
        source_pack_hydrated_entries=[],
    )

    assert snapshot["claim_support_available"] is True
    assert snapshot["qualified_items"][0]["qualification"] == CLAIM_SUPPORT


def test_jarjar_role_metadata_only_is_not_claim_support():
    snapshot = build_evidence_qualification_snapshot(
        user_message="Quel est ton role en tant que Jarjar ?",
        semantic_snapshot={"topic": "OBSIDIA_BRODY_ROLE"},
        requested_memory_target="jarjar",
        native_memory_selected_items=[{
            "title": "COGNITIVE_REINTEGRATION",
            "source_ref": "47_memory_packet.yaml",
        }],
        source_pack_hydrated_entries=[],
    )

    assert snapshot["claim_support_required"] is True
    assert snapshot["claim_support_available"] is False
    assert snapshot["qualified_items"][0]["qualification"] != CLAIM_SUPPORT


def test_no_requested_property_does_not_require_claim_support():
    snapshot = build_evidence_qualification_snapshot(
        user_message="Parle-moi d'Obsidia.",
        semantic_snapshot={"primary_query": "obsidia"},
        requested_memory_target="obsidia",
        native_memory_selected_items=[{
            "title": "Obsidia overview",
            "excerpt": "Obsidia est mentionne dans ce materiel readonly.",
        }],
        source_pack_hydrated_entries=[],
    )

    assert snapshot["requested_subjects"] == ["OBSIDIA"]
    assert snapshot["requested_properties"] == []
    assert snapshot["claim_support_required"] is False
    assert snapshot["claim_support_available"] is False
    assert "claim_support_required=False" in build_qualified_context(snapshot)
