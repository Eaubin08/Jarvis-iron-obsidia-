# F5 VOICE ENGINE BOUNDARIES

Status: IN PROGRESS

Jarvis owns:
- ConversationVoiceRuntime
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
- real microphone + custom-model wake-word gate: NOT YET CLAIMED
