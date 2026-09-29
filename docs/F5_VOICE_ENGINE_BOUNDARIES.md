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
- engine injected through SpeechEngine
- synthesis and playback separated from ConversationVoiceRuntime
- cancellation is Jarvis-owned through SpeechHandle
- no Kokoro/Piper/other model or voice asset is canonical yet
- engine package license and voice/model asset license must be recorded separately before selection

Wake word:
- not yet integrated
- source/model/asset licensing remains a hard gate
