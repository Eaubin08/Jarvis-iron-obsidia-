"""
apps/obsidia_api/auth.py — API Key guard (F76b)

Pass-through in dev/test (APP_ENV not prod, OBSIDIA_AUTH_ENABLED not true).
In prod: 503 if OBSIDIA_API_KEY is empty — no silent bypass.
KX108_ONLY. Readonly. No ACT.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException

_APP_ENV = os.getenv("APP_ENV", "dev").lower()
_AUTH_ENABLED: bool = (
    _APP_ENV not in ("dev", "development", "test")
    or os.getenv("OBSIDIA_AUTH_ENABLED", "").lower() == "true"
)
_EXPECTED_API_KEY: str = os.getenv("OBSIDIA_API_KEY", "")

_BOUNDARY = {
    "decision_authority": "KX108_ONLY",
    "readonly": True,
    "emits_act": False,
}


async def require_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> None:
    """Enforce API key in prod. Pass-through in dev/test.

    Prod with empty OBSIDIA_API_KEY → 503 (never silent bypass).
    Prod with wrong key → 401.
    Dev/test → always pass.
    """
    if not _AUTH_ENABLED:
        return

    if not _EXPECTED_API_KEY:
        raise HTTPException(
            status_code=503,
            detail={"error": "AUTH_MISCONFIGURED", **_BOUNDARY},
        )

    if x_api_key != _EXPECTED_API_KEY:
        raise HTTPException(
            status_code=401,
            detail={"error": "INVALID_API_KEY", **_BOUNDARY},
        )
