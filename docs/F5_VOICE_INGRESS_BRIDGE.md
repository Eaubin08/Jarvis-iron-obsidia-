# F5 VOICE INGRESS BRIDGE

Status: IMPLEMENTED / DETERMINISTICALLY TESTED

Canonical bridge:

    WakeInputRuntime
        |
        | WakeInputResult(woke, transcript)
        v
    VoiceIngressRuntime
        |
        v
    ConversationVoiceRuntime.accept_transcript()
        |
        v
    THINKING

Rules:
- no wake leaves the conversation runtime IDLE;
- a positive wake must contain a non-empty transcript;
- ingress does not call STT a second time;
- ingress does not invoke TTS;
- the accepted transcript transitions the conversation state to THINKING;
- follow-up is closed while the accepted turn is being processed.

This checkpoint proves provider/runtime composition only. It does not claim a
physical microphone + real wake model + real STT end-to-end execution.
