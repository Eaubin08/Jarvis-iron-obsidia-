"""
Governed model-evidence projection.

Validated local-model evidence may become candidate human material only
after the existing cognitive governance chain has admitted it.

This module:
- does not call a model;
- does not decide;
- does not ACT;
- does not write memory;
- does not mutate the kernel;
- does not bypass C1/W1/W2;
- does not expose raw model output directly.

decision_authority = KX108_ONLY
"""

from __future__ import annotations

import ast
import hashlib
import re
import unicodedata
from typing import Any


VERSION = "GOVERNED_MODEL_PROJECTION_V0"
DECISION_AUTHORITY = "KX108_ONLY"


_FENCE_RE = re.compile(
    r"^\s*```(?:[A-Za-z0-9_+.\-]+)?[ \t]*\r?\n"
    r"(?P<body>.*?)"
    r"\r?\n```\s*$",
    re.DOTALL,
)


_SOVEREIGN_ASSIGNMENT_RE = re.compile(
    r"(?im)^\s*("
    r"DECISION_AUTHORITY"
    r"|EMITS_ACT"
    r"|EMITS_VERDICT"
    r"|ALLOWED_TO_ACT"
    r"|ALLOWED_TO_DECIDE"
    r"|KERNEL_MUTATION"
    r"|X108_MUTATION"
    r"|MEMORY_WRITE"
    r")\s*[:=]"
)


def _sha256(text: str) -> str:
    return hashlib.sha256(
        text.encode(
            "utf-8",
            errors="replace",
        )
    ).hexdigest()


def _norm(text: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        text or "",
    )

    value = "".join(
        ch
        for ch in value
        if not unicodedata.combining(ch)
    )

    return " ".join(
        value.lower().split()
    )


def _explicit_code_only(
    user_message: str,
) -> bool:
    text = _norm(user_message)

    markers = (
        "uniquement ce code",
        "uniquement le code",
        "seulement ce code",
        "seulement le code",
        "code uniquement",
        "only this code",
        "only the code",
        "code only",
    )

    return any(
        marker in text
        for marker in markers
    )


def _explicit_no_markdown(
    user_message: str,
) -> bool:
    text = _norm(user_message)

    markers = (
        "sans markdown",
        "sans format markdown",
        "no markdown",
        "without markdown",
    )

    return any(
        marker in text
        for marker in markers
    )


def _looks_like_code(
    content: str,
    user_message: str,
) -> bool:
    working = content.strip()

    if not working:
        return False

    request = _norm(user_message)

    if "python" in request:
        try:
            ast.parse(working)
        except SyntaxError:
            return False

        return True

    first = (
        working.splitlines()[0]
        .strip()
        .lower()
    )

    prefixes = (
        "def ",
        "class ",
        "import ",
        "from ",
        "function ",
        "const ",
        "let ",
        "var ",
        "public ",
        "private ",
        "protected ",
        "#include ",
        "package ",
        "fn ",
    )

    return first.startswith(prefixes)


def _blocked(
    reason: str,
    *,
    source_ref: str | None = None,
    evidence_hash: str | None = None,
) -> dict[str, Any]:
    return {
        "version": VERSION,
        "status": "BLOCKED",
        "reason": reason,
        "content": "",
        "source": "VALIDATED_MODEL_EVIDENCE",
        "source_ref": source_ref,
        "evidence_hash": evidence_hash,
        "projection_hash": None,
        "repair_operations": [],
        "readonly": True,
        "advisory_only": True,
        "allowed_to_decide": False,
        "allowed_to_act": False,
        "emits_act": False,
        "emits_verdict": False,
        "memory_write": False,
        "kernel_mutation": False,
        "decision_authority": DECISION_AUTHORITY,
        "raw_model_direct_surface": False,
    }


def project_governed_model_evidence(
    *,
    user_message: str,
    local_model_stage: dict[str, Any],
    cognitive_join: dict[str, Any],
) -> dict[str, Any]:

    local = dict(
        local_model_stage
        or {}
    )

    join = dict(
        cognitive_join
        or {}
    )

    evidence = dict(
        join.get(
            "local_model_evidence_snapshot"
        )
        or {}
    )

    context = dict(
        join.get(
            "context_packet_v2"
        )
        or {}
    )

    runtime = dict(
        join.get(
            "w1_runtime_context_packet"
        )
        or {}
    )

    ticket = dict(
        join.get(
            "decision_ticket_dry_run"
        )
        or {}
    )

    raw_content = str(
        evidence.get("content")
        or ""
    ).strip()

    evidence_hash = str(
        evidence.get("evidence_hash")
        or (
            _sha256(raw_content)
            if raw_content
            else ""
        )
    )

    source_ref = str(
        evidence.get("source_ref")
        or ""
    ) or None

    model_ok = (
        local.get("status")
        == "EVIDENCE_READY"
        and local.get(
            "model_call_used"
        ) is True
        and local.get(
            "evidence_applied"
        ) is True
        and bool(raw_content)
    )

    if not model_ok:
        return _blocked(
            "MODEL_EVIDENCE_NOT_READY",
            source_ref=source_ref,
            evidence_hash=evidence_hash,
        )

    context_ok = (
        context.get("readonly")
        is True
        and context.get(
            "context_signal_only"
        ) is True
        and context.get(
            "allowed_to_decide"
        ) is False
        and context.get(
            "allowed_to_act"
        ) is False
        and context.get(
            "kernel_mutation"
        ) is False
        and context.get(
            "memory_write"
        ) is False
        and not list(
            context.get(
                "forbidden_tokens_detected"
            )
            or []
        )
    )

    if not context_ok:
        return _blocked(
            "CONTEXT_V2_NOT_ADMISSIBLE",
            source_ref=source_ref,
            evidence_hash=evidence_hash,
        )

    runtime_ok = (
        runtime.get("advisory_only")
        is True
        and runtime.get("readonly")
        is True
        and runtime.get(
            "runtime_allowed_now"
        ) is False
        and runtime.get(
            "emits_act"
        ) is False
        and runtime.get(
            "emits_decision"
        ) is False
        and runtime.get(
            "decision_authority"
        ) == DECISION_AUTHORITY
    )

    if not runtime_ok:
        return _blocked(
            "W1_RUNTIME_BOUNDARY_FAILED",
            source_ref=source_ref,
            evidence_hash=evidence_hash,
        )

    w2_ok = (
        ticket.get("decision")
        == "ALLOW_CONTEXT_ONLY"
        and ticket.get(
            "x108_gate_status"
        ) == "X108_EVALUATED_DRY_RUN"
        and ticket.get("dry_run")
        is True
        and ticket.get(
            "decision_authority"
        ) == DECISION_AUTHORITY
        and ticket.get("emits_act")
        is False
    )

    if not w2_ok:
        return _blocked(
            "W2_CONTEXT_ADMISSION_FAILED",
            source_ref=source_ref,
            evidence_hash=evidence_hash,
        )

    if _SOVEREIGN_ASSIGNMENT_RE.search(
        raw_content
    ):
        return _blocked(
            "MODEL_CONTENT_CLAIMS_AUTHORITY",
            source_ref=source_ref,
            evidence_hash=evidence_hash,
        )

    content = raw_content
    repairs: list[str] = []

    code_only = _explicit_code_only(
        user_message
    )

    no_markdown = _explicit_no_markdown(
        user_message
    )

    if code_only:
        match = _FENCE_RE.fullmatch(
            content
        )

        if match is not None:
            content = (
                match.group("body")
                .strip()
            )

            repairs.append(
                "strip_single_code_fence"
            )

    if code_only and "```" in content:
        return _blocked(
            "CODE_ONLY_MARKDOWN_REMAINS",
            source_ref=source_ref,
            evidence_hash=evidence_hash,
        )

    if no_markdown and "```" in content:
        return _blocked(
            "NO_MARKDOWN_CONSTRAINT_FAILED",
            source_ref=source_ref,
            evidence_hash=evidence_hash,
        )

    if (
        code_only
        and not _looks_like_code(
            content,
            user_message,
        )
    ):
        return _blocked(
            "CODE_ONLY_TASK_FIT_FAILED",
            source_ref=source_ref,
            evidence_hash=evidence_hash,
        )

    if _SOVEREIGN_ASSIGNMENT_RE.search(
        content
    ):
        return _blocked(
            "PROJECTED_CONTENT_CLAIMS_AUTHORITY",
            source_ref=source_ref,
            evidence_hash=evidence_hash,
        )

    projection_hash = _sha256(
        content
    )

    return {
        "version": VERSION,
        "status": "READY",
        "reason": None,
        "content": content,
        "source": "VALIDATED_MODEL_EVIDENCE",
        "provider": evidence.get(
            "provider"
        ),
        "model": evidence.get(
            "model"
        ),
        "source_ref": source_ref,
        "evidence_hash": evidence_hash,
        "projection_hash": projection_hash,
        "repair_operations": repairs,
        "constraints": {
            "code_only": code_only,
            "no_markdown": no_markdown,
        },
        "readonly": True,
        "advisory_only": True,
        "allowed_to_decide": False,
        "allowed_to_act": False,
        "emits_act": False,
        "emits_verdict": False,
        "memory_write": False,
        "kernel_mutation": False,
        "decision_authority": DECISION_AUTHORITY,
        "raw_model_direct_surface": False,
    }


__all__ = [
    "project_governed_model_evidence",
]
