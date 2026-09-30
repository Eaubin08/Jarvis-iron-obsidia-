"""Physical audio/media smoke for Jarjar on Windows.

The smoke measures and restores master volume/mute through Core Audio.
Media transport keys are injected through Win32; no player is launched.
"""
from __future__ import annotations

import json
import time

from jarvis.integrations.win32_driver import Win32Driver


def dump(label: str, value: object) -> None:
    print(f"{label}: {json.dumps(value, ensure_ascii=False, default=str)}")


def main() -> int:
    driver = Win32Driver()

    try:
        initial = driver.audio_status()
        dump("AUDIO_INITIAL", initial)

        initial_percent = int(initial["volume_percent"])
        initial_muted = bool(initial["muted"])

        target = min(100, initial_percent + 5)
        if target == initial_percent:
            target = max(0, initial_percent - 5)

        changed = driver.audio_set_volume(target)
        dump("AUDIO_VOLUME_CHANGED", changed)
        if int(changed["volume_percent"]) != target:
            raise RuntimeError(
                f"volume verification failed: expected {target}, got {changed['volume_percent']}"
            )

        restored = driver.audio_set_volume(initial_percent)
        dump("AUDIO_VOLUME_RESTORED", restored)
        if abs(int(restored["volume_percent"]) - initial_percent) > 1:
            raise RuntimeError("volume restore verification failed")

        toggled = driver.audio_set_mute(not initial_muted)
        dump("AUDIO_MUTE_CHANGED", toggled)
        if bool(toggled["muted"]) == initial_muted:
            raise RuntimeError("mute verification failed")

        mute_restored = driver.audio_set_mute(initial_muted)
        dump("AUDIO_MUTE_RESTORED", mute_restored)
        if bool(mute_restored["muted"]) != initial_muted:
            raise RuntimeError("mute restore verification failed")

        for key in ("media_play_pause", "media_next", "media_previous"):
            result = driver.media_key(key)
            dump("MEDIA_KEY", result)
            time.sleep(0.15)

    except Exception as exc:
        print(f"AUDIO_MEDIA_PHYSICAL: FAIL {type(exc).__name__}: {exc}")
        return 2

    print("AUDIO_MEDIA_PHYSICAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
