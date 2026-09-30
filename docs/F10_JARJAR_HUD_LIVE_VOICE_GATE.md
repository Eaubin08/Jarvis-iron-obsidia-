# JARJAR HUD LIVE VOICE GATE

Status: READY / PHYSICAL HUD+VOICE RUN REQUIRED

The HUD shell has already been visually observed on the target machine.

This step replaces the demo LISTEN behavior with the canonical local chain:

    HUD LISTEN
      -> SoundDeviceMicrophone
      -> FasterWhisperSTT
      -> TranscriptWakeWordProvider
      -> VoiceIngressRuntime
      -> JarvisCore
      -> Kokoro French TTS
      -> HUD transcript

Follow-up turns reuse the already implemented wake-free follow-up path.

Text SEND also uses the same JarvisCore and, while VOICE ON is enabled, speaks
the reply through Kokoro.

Cognition is still the standalone V0 stub provider. This gate proves the
desktop face + real local voice path, not Brody/Obsidia cognition.

Run:

```powershell
git pull

& 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_f10_hud_live_voice.py

& 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m scripts.run_jarjar_live
```

Physical interaction:

1. Window opens.
2. VOICE ON remains enabled.
3. Press LISTEN and say "Hey Jarvis status" during the capture window.
4. Transcript must show the real recognized speech and Jarjar response.
5. Kokoro must speak the response.
6. Press LISTEN again and speak without repeating the wake phrase; follow-up
   capture should be accepted.
7. SEND text should return a written response and speak it while VOICE ON.
