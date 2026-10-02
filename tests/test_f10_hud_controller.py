from jarvis.hud_controller import HUDController
from jarvis.hud_state import HUDModel, HUDState


def test_text_turn_updates_transcript_and_returns_idle():
    model = HUDModel()
    controller = HUDController(model, lambda text: f"echo:{text}")

    reply = controller.submit_text("bonjour")

    assert reply == "echo:bonjour"
    snap = model.snapshot()
    assert snap["state"] == "idle"
    assert snap["messages"] == [
        {"speaker": "YOU", "text": "bonjour"},
        {"speaker": "JARJAR", "text": "echo:bonjour"},
    ]


def test_voice_turn_returns_idle_after_completed_voice_handler():
    model = HUDModel()
    controller = HUDController(
        model,
        lambda text: text,
        voice_turn_handler=lambda: ("salut", "bonjour"),
    )

    result = controller.run_voice_turn()

    assert result == ("salut", "bonjour")
    assert model.state is HUDState.IDLE
    controller.voice_finished()
    assert model.state is HUDState.IDLE


def test_follow_up_handler_has_separate_seam():
    model = HUDModel()
    controller = HUDController(
        model,
        lambda text: text,
        voice_turn_handler=lambda: ("wake", "one"),
        follow_up_turn_handler=lambda: ("suite", "two"),
    )

    result = controller.run_follow_up_turn()

    assert result == ("suite", "two")
    assert model.snapshot()["messages"][-2:] == [
        {"speaker": "YOU", "text": "suite"},
        {"speaker": "JARJAR", "text": "two"},
    ]


def test_voice_can_be_disabled_fail_closed():
    model = HUDModel()
    controller = HUDController(model, lambda text: text, voice_turn_handler=lambda: None)
    assert controller.toggle_voice() is False

    try:
        controller.run_voice_turn()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "disabled" in str(exc)


def test_empty_text_fails_without_fake_message():
    model = HUDModel()
    controller = HUDController(model, lambda text: text)

    try:
        controller.submit_text(" ")
        assert False, "expected ValueError"
    except ValueError:
        pass

    assert model.snapshot()["messages"] == []


def test_hud_model_tracks_conversation_session_separately_from_voice_state():
    model = HUDModel()
    assert model.snapshot()["session_open"] is False

    model.set_session_open(True)
    model.set_state(HUDState.LISTENING)
    snap = model.snapshot()
    assert snap["session_open"] is True
    assert snap["state"] == "listening"

    model.set_voice_enabled(False)
    assert model.snapshot()["session_open"] is False


def test_governed_response_projects_kx108_authority_without_granting_hud_authority():
    model = HUDModel()
    controller = HUDController(
        model,
        lambda text: "Déplacement préparé. Dis « confirme le déplacement » pour autoriser l'exécution.",
        response_source=lambda: "OBSIDIA/GOVERNED_MOVE",
    )

    reply = controller.submit_text("déplace a vers b")

    assert "préparé" in reply
    snap = model.snapshot()
    assert snap["governance_active"] is True
    assert snap["decision_authority"] == "KX108_ONLY"
    assert snap["governance_source"] == "OBSIDIA/GOVERNED_MOVE"
    assert snap["governance_phase"] == "PREPARE"
    assert snap["human_confirmation_required"] is True
    assert snap["confirmation_prompt"] == "CONFIRME LE DÉPLACEMENT"


def test_non_governed_response_clears_governance_surface():
    model = HUDModel()
    model.set_governance(
        active=True,
        decision_authority="KX108_ONLY",
        source="OBSIDIA/GOVERNED_MOVE",
    )
    controller = HUDController(
        model,
        lambda text: "réponse locale",
        response_source=lambda: "LOCAL",
    )

    controller.submit_text("status")

    snap = model.snapshot()
    assert snap["governance_active"] is False
    assert snap["decision_authority"] == ""
    assert snap["governance_source"] == ""
    assert snap["governance_phase"] == ""
    assert snap["human_confirmation_required"] is False
    assert snap["confirmation_prompt"] == ""


def test_governed_phase_surface_distinguishes_execute_rollback_and_block():
    assert HUDController._governance_phase(
        "Déplacement exécuté et prouvé : a → b.",
        "OBSIDIA/GOVERNED_MOVE",
    ) == "EXECUTE"
    assert HUDController._governance_phase(
        "Rollback préparé : b → a. Dis confirme le rollback.",
        "OBSIDIA/GOVERNED_ROLLBACK",
    ) == "ROLLBACK_PREPARE"
    assert HUDController._governance_phase(
        "Rollback exécuté et prouvé : b → a.",
        "OBSIDIA/GOVERNED_ROLLBACK",
    ) == "ROLLBACK_EXECUTE"
    assert HUDController._governance_phase(
        "Déplacement non exécuté : KX108_PRE_GATE:BLOCK",
        "OBSIDIA/GOVERNED_MOVE",
    ) == "BLOCKED"


def test_governed_phase_surface_never_marks_plain_cognition_as_governed():
    assert HUDController._governance_phase(
        "Je prépare une explication.",
        "BRODY/OBSIDIA",
    ) == ""


def test_confirmation_prompt_is_specific_to_governed_operation():
    cases = [
        (
            "Déplacement préparé. Dis « confirme le déplacement » pour autoriser l'exécution.",
            "OBSIDIA/GOVERNED_MOVE",
            "CONFIRME LE DÉPLACEMENT",
        ),
        (
            "Création de dossier préparée. Dis « confirme la création du dossier ».",
            "OBSIDIA/GOVERNED_CREATE_DIR",
            "CONFIRME LA CRÉATION DU DOSSIER",
        ),
        (
            "Création de fichier préparée. Dis « confirme la creation du fichier ».",
            "OBSIDIA/GOVERNED_FILE_OPS",
            "CONFIRME LA CRÉATION DU FICHIER",
        ),
        (
            "Patch préparé. Dis « confirme le patch ».",
            "OBSIDIA/GOVERNED_FILE_OPS",
            "CONFIRME LE PATCH",
        ),
        (
            "Rollback préparé. Dis « confirme le rollback ».",
            "OBSIDIA/GOVERNED_ROLLBACK",
            "CONFIRME LE ROLLBACK",
        ),
    ]
    for reply, source, expected in cases:
        assert HUDController._confirmation_prompt(reply, source) == expected


def test_confirmation_prompt_never_appears_for_plain_cognition():
    assert HUDController._confirmation_prompt(
        "Tu peux confirmer si tu veux.",
        "BRODY/OBSIDIA",
    ) == ""
