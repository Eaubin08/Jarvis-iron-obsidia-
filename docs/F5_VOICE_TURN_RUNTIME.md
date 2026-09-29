# F5 VOICE TURN RUNTIME

Status: IMPLEMENTED / DETERMINISTICALLY TESTED

Canonical turn:

    WakeInputRuntime
        |
        v
    VoiceIngressRuntime
        |
        v
    transcript
        |
        v
    JarvisCore.handle_text()
        |
        v
    response text
        |
        v
    ConversationVoiceRuntime.speak()
        |
        v
    TextToSpeechProvider
        |
        v
    SPEAKING

Completion:

    speech_finished()
        |
        v
    IDLE

Rules:
- no wake short-circuits before cognition and TTS;
- ingress owns wake/STT composition, so VoiceTurnRuntime does not re-transcribe;
- empty cognition responses fail closed before TTS;
- successful response opens the follow-up window;
- speech completion returns the runtime to IDLE.

This checkpoint proves deterministic composition. It does not claim a physical
microphone + reviewed wake model + real STT + real cognition + Kokoro end-to-end run.
