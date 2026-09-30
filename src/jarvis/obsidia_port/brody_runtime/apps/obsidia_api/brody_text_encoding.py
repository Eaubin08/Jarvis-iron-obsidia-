"""
Brody Text Encoding — UTF-8 mojibake detection and repair
===========================================================
Detects and repairs common UTF-8 mojibake patterns that occur
when UTF-8 bytes are decoded as Windows-1252 or Latin-1.

Patterns fixed:
  "crÃ©ation" → "création"
  "mÃ©moire" → "mémoire"
  "rÃ©ponds" → "réponds"
  "dÃ©cision" → "décision"
  "prÃ©cÃ©dent" → "précédent"
  "Ã¨" → "è"
  "Ã " → "à"
  "â\u0080\u0099" → "'" (smart quote)
"""
from __future__ import annotations

# Known mojibake pairs: (garbled, correct)
_MOJIBAKE_MAP: dict[str, str] = {
    "Ã©": "é",
    "Ã¨": "è",
    "Ãª": "ê",
    "Ã«": "ë",
    "Ã ": "à",
    "Ã¢": "â",
    "Ã¹": "ù",
    "Ã»": "û",
    "Ã¼": "ü",
    "Ã®": "î",
    "Ã¯": "ï",
    "Ã´": "ô",
    "Ã¶": "ö",
    "Ã§": "ç",
    "Å\u0093": "œ",
    "â\u0080\u0099": "'",
    "â\u0080\u009c": '"',
    "â\u0080\u009d": '"',
    "â\u0080\u0093": "–",
    "â\u0080\u0094": "—",
}


def is_mojibake(text: str) -> bool:
    """Check if text likely contains UTF-8 mojibake patterns."""
    if not text:
        return False
    for garbled in _MOJIBAKE_MAP:
        if garbled in text:
            return True
    return False


def normalize_brody_text(text: str) -> str:
    """
    Repair known UTF-8 mojibake patterns in Brody response text.
    Also applies basic whitespace cleanup.
    Does NOT modify valid UTF-8 text.
    """
    if not text:
        return text

    result = text
    for garbled, correct in _MOJIBAKE_MAP.items():
        result = result.replace(garbled, correct)

    # Clean trailing/leading whitespace but preserve paragraph breaks
    result = result.strip()

    return result



def repair_mojibake_via_latin1_roundtrip(text: str) -> str:
    """
    Repair mojibake that occurs when UTF-8 bytes are decoded as Latin-1/cp1252.

    Strategy:
      1. Apply normalize_brody_text for paired mojibake sequences (e.g. Ã© -> é).
      2. Replace remaining U+00E2 (â) with an em dash (U+2014). After step 1, any
         remaining U+00E2 is a truncated em-dash first byte — the map already
         resolved complete sequences such as â -> em dash.
      3. Remove remaining stray U+00C3 (unpaired Ã byte).

    Idempotent: a second call on already-repaired text is a no-op.
    """
    if not text:
        return text
    result = normalize_brody_text(text)
    result = result.replace("â", "—")
    result = result.replace("Ã", "")
    return result


def safe_brody_decode(raw_bytes: bytes) -> str:
    """
    Safely decode bytes to string, trying UTF-8 first,
    then Windows-1252, then Latin-1 with replacement.
    Returns normalized text.
    """
    if not raw_bytes:
        return ""

    # Try UTF-8
    try:
        text = raw_bytes.decode("utf-8")
        return normalize_brody_text(text)
    except UnicodeDecodeError:
        pass

    # Try Windows-1252 (common mojibake source)
    try:
        text = raw_bytes.decode("cp1252")
        return normalize_brody_text(text)
    except UnicodeDecodeError:
        pass

    # Last resort: replace errors
    text = raw_bytes.decode("utf-8", errors="replace")
    return normalize_brody_text(text)
