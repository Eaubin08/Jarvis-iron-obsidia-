# F5 VOICE ENGINE BOUNDARIES

Status: CODE/CI CLOSED — PHYSICAL E2E HOLD

Jarvis owns:
- ConversationVoiceRuntime
- WakeInputRuntime
- VoiceIngressRuntime
- VoiceTurnRuntime
- voice state
- follow-up semantics
- barge-in semantics
- provider contracts
- cancellation handle

STT:
- adapter: FasterWhisperSTT
- engine: faster-whisper / CTranslate2
- real model gate: tiny.en
- CI proof: real model load and transcription
- linguistic/microphone quality: not yet claimed

TTS:
- Jarvis adapter: LocalTTS
- engine: KokoroEngine behind SpeechEngine
- synthesis and playback separated from ConversationVoiceRuntime
- cancellation is Jarvis-owned through SpeechHandle
- real Kokoro synthesis gate: PASS on GitHub Actions run 36605853948
- model/voice provenance remains separate from engine-package licensing

Microphone:
- canonical adapter: SoundDeviceMicrophone
- capture contract: bounded mono 16 kHz PCM16 bytes
- real microphone capture gate: READY, requires JARVIS_REAL_MIC_TEST=1
- physical-device PASS: not yet claimed

Wake word:
- canonical adapter: OpenWakeWordProvider
- model path is explicit and must already exist locally
- provider performs no model download and bundles no wake-word model
- accepted input at this seam: 16 kHz mono PCM16 bytes
- openWakeWord code: Apache-2.0
- upstream pre-trained models: CC-BY-NC-SA-4.0
- hey_jarvis: DEV/PERSONAL ONLY, never canonical production asset
- final target: Jarvis-owned/permissively licensed model after provenance review
- machine-readable provenance registry: assets/provenance.toml
- real external-model integration gate: READY, requires JARVIS_WAKEWORD_MODEL_PATH
- custom Jarvis model gate: NOT YET CLAIMED

Wake-triggered input:
- canonical composition: MicrophoneProvider -> WakeWordProvider -> SpeechToTextProvider
- no wake => STT is not called
- wake => the same captured PCM16 buffer is passed to STT
- empty microphone audio fails closed
- empty transcript after wake fails closed
- deterministic composition tests: PASS
- ingress bridge: WakeInputRuntime -> ConversationVoiceRuntime implemented
- no second STT at ingress
- positive wake transcript enters THINKING state

Full turn composition:
- VoiceTurnRuntime: ingress -> JarvisCore -> ConversationVoiceRuntime.speak
- no wake => no cognition and no TTS
- empty cognition response => fail closed
- successful response => SPEAKING with follow-up open
- speech_finished => IDLE
- deterministic full-turn composition: PASS

Physical full voice loop:
- opt-in gate: tests/test_f5_physical_voice_e2e.py
- requires JARVIS_REAL_VOICE_E2E=1
- requires JARVIS_WAKEWORD_MODEL_PATH
- no bundled/downloaded wake-word model
- physical full voice loop PASS: NOT YET CLAIMED\n- standard CI regression proof: PASS on run 36614462845
