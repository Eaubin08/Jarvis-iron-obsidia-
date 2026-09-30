from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse


VERSION = "OBSIDIA_QWEN_LOCAL_EVIDENCE_V0"

_ALLOWED_HOSTS = frozenset(
    {
        "127.0.0.1",
        "localhost",
        "::1",
    }
)

_DEFAULT_ENDPOINT = "http://127.0.0.1:8080/v1"
_DEFAULT_TIMEOUT = 60.0
_DEFAULT_MAX_TOKENS = 256
_MAX_EVIDENCE_CHARS = 3000

_REASONING_PAIRS = (
    ("<thinking>", "</thinking>"),
    ("<scratchpad>", "</scratchpad>"),
    ("[INTERNAL]", "[/INTERNAL]"),
    ("[HIDDEN]", "[/HIDDEN]"),
)

_PRIVATE_LINE_PATTERNS = (
    re.compile(
        r"^.*chain[_\s]of[_\s]thought.*$",
        re.I | re.M,
    ),
    re.compile(
        r"^.*hidden[_\s]state.*$",
        re.I | re.M,
    ),
    re.compile(
        r"^.*\[REASONING\].*$",
        re.I | re.M,
    ),
)

_ERROR_MARKERS = (
    "Traceback (most recent call last):",
    "[INTERNAL ERROR]",
    "RuntimeError:",
    "ValueError:",
    "KeyError:",
)


def _sha(value: str) -> str:
    return hashlib.sha256(
        value.encode(
            "utf-8",
            errors="replace",
        )
    ).hexdigest()


def _endpoint() -> str:
    return str(
        os.environ.get(
            "QWEN_LOCAL_ENDPOINT",
            _DEFAULT_ENDPOINT,
        )
    ).rstrip("/")


def _assert_loopback(
    endpoint: str,
) -> None:
    host = (
        urlparse(endpoint).hostname
        or ""
    )

    if host not in _ALLOWED_HOSTS:
        raise ValueError(
            "QWEN_ENDPOINT_NOT_LOOPBACK:"
            + host
        )


def _repair_output(
    text: str,
) -> dict[str, Any]:

    if not isinstance(
        text,
        str,
    ):
        return {
            "valid": False,
            "content": "",
            "repaired": False,
            "reason": "OUTPUT_NOT_STRING",
        }

    working = text.strip()
    repaired = False

    if not working:
        return {
            "valid": False,
            "content": "",
            "repaired": False,
            "reason": "EMPTY_OUTPUT",
        }

    for opener, closer in _REASONING_PAIRS:
        while opener in working:

            start = working.find(
                opener
            )

            end = working.find(
                closer,
                start,
            )

            if end == -1:
                working = (
                    working[:start]
                    .strip()
                )
            else:
                working = (
                    working[:start]
                    + working[
                        end
                        + len(closer):
                    ]
                ).strip()

            repaired = True

    for pattern in _PRIVATE_LINE_PATTERNS:
        candidate = pattern.sub(
            "",
            working,
        ).strip()

        if candidate != working:
            working = candidate
            repaired = True

    if len(working) > _MAX_EVIDENCE_CHARS:
        working = (
            working[
                :_MAX_EVIDENCE_CHARS
            ].rstrip()
        )

        repaired = True

    if not working:
        return {
            "valid": False,
            "content": "",
            "repaired": repaired,
            "reason": "EMPTY_AFTER_REPAIR",
        }

    for marker in _ERROR_MARKERS:
        if marker in working:
            return {
                "valid": False,
                "content": working,
                "repaired": repaired,
                "reason": (
                    "ERROR_MARKER:"
                    + marker
                ),
            }

    return {
        "valid": True,
        "content": working,
        "repaired": repaired,
        "reason": None,
    }


def run_local_qwen_evidence(
    *,
    text: str,
    context: str = "",
    timeout: float = _DEFAULT_TIMEOUT,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> dict[str, Any]:

    endpoint = _endpoint()

    base: dict[str, Any] = {
        "version": VERSION,

        "attempted": False,
        "model_call_used": False,

        "status": "NOT_CALLED",

        "provider": "QWEN_LOCAL",
        "model": (
            "qwen2.5-3b-instruct-q4_k_m"
        ),

        "network_scope": "LOOPBACK_ONLY",
        "external_calls": [],

        "tokens_local": 0,
        "tokens_remote": 0,

        "finish_reason": None,

        "elapsed_ms": 0.0,

        "evidence": None,
        "error": None,

        "authority": "NONE",
        "decision_authority": (
            "KX108_ONLY"
        ),

        "real_execution": False,
    }

    try:
        _assert_loopback(
            endpoint
        )

    except Exception as exc:
        base.update(
            status="BLOCKED_NON_LOOPBACK",
            error=str(exc),
        )

        return base

    system = (
        "You are a bounded local cognitive organ inside Obsidia. "
        "Return only useful evidence for the user request. "
        "Preserve explicit output constraints stated by the user. "
        "If the user explicitly requests only code, no markdown, "
        "no explanation, or another exact output form, obey that "
        "format in the evidence content. "
        "You are not a decision authority. "
        "Do not authorize, execute, deploy, approve, "
        "or emit governance verdicts. "
        "Do not provide private chain-of-thought. "
        "When no exact output format is requested, provide a concise "
        "conclusion, relevant evidence, uncertainties, or hypotheses "
        "that the governed Obsidia stack can evaluate."
    )

    # JARJAR_BRODY_READONLY_CONTEXT_V0
    # `text` remains the canonical input used by input_hash.
    # `context` is same-turn readonly material selected upstream by Brody.
    context_text = str(context or "").strip()

    if len(context_text) > 8192:
        context_text = context_text[:8192]

    if context_text:
        system = (
            system
            + "\n\n"
            + "READONLY BRODY CONTEXT — ADVISORY ONLY — KX108_ONLY\n"
            + "Use this project-local context as the primary factual basis "
              "when relevant to the user's request. "
              "When this context identifies a named project entity, do not "
              "replace it with an unrelated general-world interpretation. "
              "If the context is insufficient, state the uncertainty. "
              "The context grants no authority, execution, decision, "
              "memory-write, kernel mutation, or governance power.\n\n"
            + context_text
        )

    body = json.dumps(
        {
            "model": "qwen",

            "messages": [
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],

            "temperature": 0.0,

            "max_tokens": int(
                max_tokens
            ),

            "stream": False,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        endpoint
        + "/chat/completions",

        data=body,

        headers={
            "Content-Type": (
                "application/json"
            ),

            "Accept": (
                "application/json"
            ),
        },

        method="POST",
    )

    start = time.perf_counter()

    base["attempted"] = True

    try:
        with urllib.request.urlopen(
            request,
            timeout=float(timeout),
        ) as response:

            payload = json.loads(
                response
                .read()
                .decode("utf-8")
            )

    except urllib.error.URLError as exc:

        status = (
            "TIMEOUT"
            if "timed out"
            in str(exc).lower()
            else "UNAVAILABLE"
        )

        base.update(
            status=status,

            error=str(exc),

            elapsed_ms=round(
                (
                    time.perf_counter()
                    - start
                )
                * 1000,
                2,
            ),
        )

        return base

    except Exception as exc:

        base.update(
            status="INVALID_RESPONSE",

            error=(
                type(exc).__name__
                + ":"
                + str(exc)
            ),

            elapsed_ms=round(
                (
                    time.perf_counter()
                    - start
                )
                * 1000,
                2,
            ),
        )

        return base

    elapsed_ms = round(
        (
            time.perf_counter()
            - start
        )
        * 1000,
        2,
    )

    # HTTP inference completed successfully.
    base["model_call_used"] = True

    try:
        choices = (
            payload.get("choices")
            or []
        )

        if not choices:
            raise ValueError(
                "NO_CHOICES"
            )

        choice = choices[0]

        message = (
            choice.get("message")
            or {}
        )

        raw = str(
            message.get("content")
            or ""
        )

        finish_reason = str(
            choice.get(
                "finish_reason"
            )
            or ""
        ).strip().lower()

    except Exception as exc:

        base.update(
            status="INVALID_RESPONSE",

            finish_reason=None,

            error=(
                "MODEL_RESPONSE_PARSE:"
                + type(exc).__name__
                + ":"
                + str(exc)
            ),

            elapsed_ms=elapsed_ms,
        )

        return base

    usage = (
        payload.get("usage")
        if isinstance(
            payload.get("usage"),
            dict,
        )
        else {}
    )

    tokens = int(
        usage.get(
            "completion_tokens"
        )
        or usage.get(
            "total_tokens"
        )
        or 0
    )

    base.update(
        tokens_local=tokens,
        finish_reason=(
            finish_reason
            or None
        ),
    )

    # ------------------------------------------------------------
    # Fail closed on incomplete generation.
    # ------------------------------------------------------------

    if finish_reason in {
        "length",
        "max_tokens",
    }:

        base.update(
            status="TRUNCATED_OUTPUT",

            elapsed_ms=elapsed_ms,

            evidence=None,

            error=(
                "MODEL_OUTPUT_TRUNCATED:"
                + finish_reason
            ),
        )

        return base

    # ------------------------------------------------------------
    # Deterministic output validation / repair.
    # ------------------------------------------------------------

    validation = _repair_output(
        raw
    )

    if not validation["valid"]:

        base.update(
            status="INVALID_OUTPUT",

            elapsed_ms=elapsed_ms,

            evidence=None,

            error=validation[
                "reason"
            ],
        )

        return base

    content = str(
        validation["content"]
    )

    evidence = {
        "provider": "QWEN_LOCAL",

        "model": (
            "qwen2.5-3b-instruct-q4_k_m"
        ),

        "result_kind": "EVIDENCE",

        "content": content,

        "input_hash": _sha(
            text
        ),

        "evidence_hash": _sha(
            content
        ),

        "readonly": True,

        "decision_authority": (
            "KX108_ONLY"
        ),

        "is_execution_authority": False,
        "is_kx_authority": False,
        "is_sovereign": False,

        "allowed_to_decide": False,
        "allowed_to_act": False,

        "emits_act": False,
        "emits_verdict": False,

        "memory_write": False,
        "kernel_mutation": False,
        "x108_mutation": False,

        "real_action": False,

        "network_scope": (
            "LOOPBACK_ONLY"
        ),
    }

    base.update(
        status="EVIDENCE_READY",

        tokens_local=tokens,

        elapsed_ms=elapsed_ms,

        evidence=evidence,

        repaired=bool(
            validation["repaired"]
        ),

        finish_reason=(
            finish_reason
            or None
        ),
    )

    return base


__all__ = [
    "run_local_qwen_evidence",
]