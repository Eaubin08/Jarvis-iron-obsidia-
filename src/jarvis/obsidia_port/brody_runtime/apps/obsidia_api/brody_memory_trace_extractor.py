"""
brody_memory_trace_extractor — V3 Block 3A
Readonly dry-run trace extractor. Transforms a Brody interaction into a
structured memory_trace_packet. No IO. No network. Provider-neutral.
No ACT. No canonical write. DECISION_AUTHORITY=KX108_ONLY.
"""
from __future__ import annotations

import re
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any

# ── Security filter patterns (R2 — sensitive data capture) ───────────────────
_SECRET_PATTERNS: list[str] = [
    r"API_KEY\s*=\s*\S+",
    r"GOOGLE_API_KEY\s*=\s*\S+",
    r"SECRET\s*=\s*\S+",
    r"PASSWORD\s*=\s*\S+",
    r"PRIVATE\s+KEY",
    r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",
    r"sk-[A-Za-z0-9]{20,}",
    r"ghp_[A-Za-z0-9]{36}",
    r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
]

# ── Adversarial detection (R3 — memory injection) ────────────────────────────
_ADVERSARIAL_TOKENS: list[str] = [
    "bypass", "override x108", "ignore x108", "ignore les gardes",
    "désactive x108", "desactive x108", "mutate kernel",
    "modifie le kernel", "écris en mémoire canonique",
    "contourne les gardes", "mute kernel", "supprime guardrail",
    "autorise toi à décider", "agis comme si tu pouvais",
    "force act", "émets act", "active ncp", "scraping",
]

_ADVERSARIAL_RE: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bbypass\b",
        r"override\s+x108",
        r"ignore\s+x108",
        r"ignore\s+les\s+gardes",
        r"d[eé]sactive\s+x108",
        r"mutate?\s+kernel",
        r"modifie\s+le\s+kernel",
        r"[eé]cris\s+en\s+m[eé]moire\s+canonique",
        r"contourne\s+(les\s+)?(gardes|r[eè]gles|guardrail)",
        r"autorise[\s\-]toi\s+[aà]\s+(d[eé]cider|agir|[eé]crire)",
        r"agis\s+comme\s+si\s+tu\s+pouvais",
        r"\bmute\s+kernel\b",
        r"\bforce\s+act\b",
        r"\b[eé]mets\s+act\b",
        r"\bactive\s+ncp\b",
        r"\bscraping\b",
    ]
]

# ── Weak signal keywords ──────────────────────────────────────────────────────
_WEAK_SIGNAL_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bsignal\s+faible\b",
        r"\bhésitation\b", r"\bhesitation\b",
        r"\bpattern\s+inhabituel\b",
        r"\banomal[ie]\b",
        r"\bsous-détect",
        r"\bnon\s+captur",
        r"\bfaint\s+signal\b",
    ]
]

# ── Dead path patterns ────────────────────────────────────────────────────────
_DEAD_PATH_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bchemin\s+mort\b",
        r"\bdead\s+path\b",
        r"\bimpasse\b",
        r"\blocage\b",
        r"\bbloqué\b",
        r"\béchoue\b", r"\bfailed\b",
        r"\bincohérent\b", r"\bincoherent\b",
    ]
]

# ── Invariant patterns ────────────────────────────────────────────────────────
_INVARIANT_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\binvariant\b",
        r"\bscore_cannot\b",
        r"\bmemory_not_sovereign\b",
        r"\bprojection_not_prediction\b",
        r"\bcritical_missing_data\b",
    ]
]

# ── Missing data patterns ─────────────────────────────────────────────────────
_MISSING_DATA_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bdonnée[s]?\s+manquante[s]?\b",
        r"\bmissing\s+data\b",
        r"\bmanque\s+de\s+preuves?\b",
        r"\bpreuve\s+manquante\b",
        r"\bholds?\s+required\b",
        r"\bhold_required\b",
        r"\bINCOMPLET\b",
    ]
]

# ── Contradiction patterns ────────────────────────────────────────────────────
_CONTRADICTION_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bcontradiction\b",
        r"\binconsist",
        r"\bconflit\b",
        r"\bprédiction\b.*\bprojection\b",
        r"\bprojection\b.*\bprédiction\b",
        r"\bcontredit\b",
    ]
]


def _contains_secret(text: str) -> bool:
    for pat in _SECRET_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def _is_adversarial_text(text: str) -> bool:
    ltext = text.lower()
    for tok in _ADVERSARIAL_TOKENS:
        if tok in ltext:
            return True
    for pat in _ADVERSARIAL_RE:
        if pat.search(text):
            return True
    return False


def _scrub_secrets(text: str) -> str:
    result = text
    for pat in _SECRET_PATTERNS:
        result = re.sub(pat, "[REDACTED]", result, flags=re.IGNORECASE)
    return result


def _compute_memory_relevance_score(
    micro_core: dict,
    balance_output: dict,
    point_cloud: dict,
) -> float:
    """Heuristic [0.0–1.0] — how memory-relevant is this interaction."""
    score = 0.0

    # memory axis from point_cloud (axis_13)
    axes = point_cloud.get("axes", {})
    mem_axis = float(axes.get("axis_13_memory", 0.0))
    score += 0.3 * mem_axis

    # balance_memoire tension
    balances = balance_output.get("balances", {})
    bal_mem = balances.get("balance_memoire", {})
    mem_tension = float(bal_mem.get("tension", 0.0))
    score += 0.3 * mem_tension

    # path_coherence from micro_core
    path_c = float(micro_core.get("path_coherence_score", 0.5))
    score += 0.2 * path_c

    # provider-neutral memory activation signal
    # Memory relevance must not depend on any retrieval provider.
    memory_packet_required = bool(
        point_cloud.get("memory_packet_required", False)
    )
    score += 0.2 if memory_packet_required else 0.0

    return round(min(1.0, max(0.0, score)), 4)


def _extract_tags_from_text(text: str, patterns: list[re.Pattern]) -> list[str]:
    found: list[str] = []
    for pat in patterns:
        m = pat.search(text)
        if m:
            found.append(m.group(0)[:60])
    return found


def _build_point_cloud_snapshot(point_cloud: dict) -> dict:
    """Compact 21D snapshot — only the axes dict + top fields."""
    return {
        "axes": dict(point_cloud.get("axes", {})),
        "active_layers": list(point_cloud.get("active_layers", []))[:6],
        "memory_packet_required": bool(point_cloud.get("memory_packet_required", False)),
        "memory_packet_required": bool(point_cloud.get("memory_packet_required", False)),
        "domain_detected": point_cloud.get("domain_detected"),
    }


def _build_balance_snapshot(balance_output: dict) -> dict:
    """Compact balance snapshot — tension per balance."""
    balances_raw = balance_output.get("balances", {})
    snapshot: dict[str, Any] = {}
    for bal_id, bal_data in balances_raw.items():
        if isinstance(bal_data, dict):
            snapshot[bal_id] = {
                "tension": round(float(bal_data.get("tension", 0.0)), 4),
                "seuil_depasse": bool(bal_data.get("seuil_depasse", False)),
                "priority": int(bal_data.get("priority", 99)),
            }
    return snapshot


class BrodyMemoryTraceExtractor:
    """
    Readonly dry-run trace extractor for Block 3A.
    Transforms a Brody interaction into a memory_trace_packet.
    Never writes. Never decides. Never emits ACT.
    canonical_write=False always. DECISION_AUTHORITY=KX108_ONLY.
    """

    # Structural invariants — never mutable
    READONLY: bool = True
    CANONICAL_WRITE: bool = False
    MEMORY_WRITE: bool = False
    KERNEL_MUTATION: bool = False
    EMITS_ACT: bool = False
    DECISION_AUTHORITY: str = "KX108_ONLY"
    HUMAN_VALIDATION_REQUIRED: bool = True
    BLOCK: str = "V3_BLOCK_3A"

    def extract(
        self,
        *,
        message: str,
        response_text: str,
        v3_dryrun_packet: dict | None = None,
        session_id: str = "",
        timestamp: str = "",
        source_type: str = "pipeline",
    ) -> dict:
        """
        Extract a structured readonly memory_trace_packet from a Brody interaction.

        Returns a dict with all required fields + invariant fields always set to
        safe values (readonly=True, canonical_write=False, etc.).
        Never raises — returns an error trace on unexpected failure.
        """
        try:
            return self._extract_inner(
                message=message,
                response_text=response_text,
                v3_dryrun_packet=v3_dryrun_packet or {},
                session_id=session_id,
                timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
                source_type=source_type,
            )
        except Exception as exc:
            return self._error_trace(session_id, timestamp, str(exc))

    def _extract_inner(
        self,
        *,
        message: str,
        response_text: str,
        v3_dryrun_packet: dict,
        session_id: str,
        timestamp: str,
        source_type: str,
    ) -> dict:
        # ── 0. Security pre-check (R2 + R3) ──────────────────────────────────
        message_has_secret = _contains_secret(message)
        response_has_secret = _contains_secret(response_text)
        is_adversarial_msg = _is_adversarial_text(message)

        # Scrub secrets from summaries
        safe_message = _scrub_secrets(message) if message_has_secret else message
        safe_response = _scrub_secrets(response_text) if response_has_secret else response_text

        # ── 1. Unpack v3_dryrun_packet ────────────────────────────────────────
        micro_core: dict = v3_dryrun_packet.get("micro_core", {})
        balance_output: dict = v3_dryrun_packet.get("balance_engine", {})
        point_cloud: dict = v3_dryrun_packet.get("point_cloud_21d", {})
        memzum: dict = v3_dryrun_packet.get("memzum", {})
        context_budget: dict = v3_dryrun_packet.get("context_budget", {})
        fastpath: dict = v3_dryrun_packet.get("fastpath", {})

        # ── 2. Core signals from micro_core ───────────────────────────────────
        is_adversarial: bool = (
            bool(micro_core.get("is_adversarial", False)) or is_adversarial_msg
        )
        domain_detected: str | None = micro_core.get("domain_detected")
        intent_type: str = micro_core.get("intent_type", "unknown")
        path_coherence: float = float(micro_core.get("path_coherence_score", 0.5))
        latency_ms: float = float(micro_core.get("latency_ms", 0.0))
        invariant_violations: list = list(micro_core.get("invariant_violations", []))
        memory_required: bool = bool(memzum.get("memory_required", False))

        # ── 3. Fastpath info ──────────────────────────────────────────────────
        fastpath_type: str | None = fastpath.get("fastpath_type") if fastpath else None
        fastpath_triggered: bool = bool(fastpath.get("fastpath_allowed", False))

        # Override source_type if fastpath
        if fastpath_triggered and source_type == "pipeline":
            source_type = "fastpath"

        # ── 4. Risk flags ─────────────────────────────────────────────────────
        risk_flags: list[str] = []
        if is_adversarial:
            risk_flags.append("adversarial_prompt")
        if message_has_secret:
            risk_flags.append("secret_detected_in_message")
        if response_has_secret:
            risk_flags.append("secret_detected_in_response")
        if latency_ms > 20000:
            risk_flags.append("latency_pathologique")
        if invariant_violations:
            risk_flags.append(f"invariant_violations:{len(invariant_violations)}")

        # balance_risque composite
        balances = balance_output.get("balances", {})
        bal_risk = balances.get("balance_risque", {})
        risk_composite = float(bal_risk.get("tension", 0.0))
        if risk_composite > 0.5:
            risk_flags.append(f"risk_composite:{round(risk_composite, 3)}")

        # ── 5. Missing data flags ─────────────────────────────────────────────
        combined_text = f"{safe_message} {safe_response}"
        missing_data_flags: list[str] = _extract_tags_from_text(
            combined_text, _MISSING_DATA_PATTERNS
        )

        # ── 6. Contradiction flags ────────────────────────────────────────────
        contradiction_flags: list[str] = _extract_tags_from_text(
            combined_text, _CONTRADICTION_PATTERNS
        )

        # ── 7. Weak signal tags ───────────────────────────────────────────────
        weak_signal_tags: list[str] = _extract_tags_from_text(
            combined_text, _WEAK_SIGNAL_PATTERNS
        )
        # also from balance
        bal_ws = balances.get("balance_signal_faible", {})
        if float(bal_ws.get("tension", 0.0)) > 0.1:
            weak_signal_tags.append(f"balance_signal_faible:{round(float(bal_ws.get('tension',0)),3)}")

        # ── 8. Dead path tags ─────────────────────────────────────────────────
        dead_path_tags: list[str] = _extract_tags_from_text(
            combined_text, _DEAD_PATH_PATTERNS
        )
        if path_coherence < 0.4:
            dead_path_tags.append(f"path_coherence_low:{round(path_coherence, 3)}")
        if risk_composite > 0.5:
            dead_path_tags.append("risk_composite_exceeds_threshold")
        if is_adversarial:
            dead_path_tags.append("adversarial_excluded")

        # ── 9. Useful path tags ───────────────────────────────────────────────
        useful_path_tags: list[str] = []
        if not is_adversarial and path_coherence >= 0.6 and not risk_flags:
            useful_path_tags.append(f"coherent_path:{round(path_coherence, 3)}")
        if memory_required:
            useful_path_tags.append("memory_required")
        if fastpath_type and "adversarial" not in (fastpath_type or ""):
            useful_path_tags.append(f"fastpath:{fastpath_type}")

        # ── 10. Memory relevance score ────────────────────────────────────────
        memory_relevance_score: float = _compute_memory_relevance_score(
            micro_core, balance_output, point_cloud
        )

        # ── 11. Snapshots ─────────────────────────────────────────────────────
        point_cloud_snapshot = _build_point_cloud_snapshot(point_cloud)
        balance_tags_snapshot = _build_balance_snapshot(balance_output)

        # ── 12. Summaries (scrubbed, truncated) ───────────────────────────────
        message_summary = safe_message[:200].strip()
        response_summary = safe_response[:400].strip()

        # ── 13. Trace ID ──────────────────────────────────────────────────────
        _id_source = f"{session_id}:{timestamp}:{message_summary[:50]}"
        trace_id = "TR_" + hashlib.sha256(_id_source.encode()).hexdigest()[:16].upper()

        # ── 14. Assemble packet ───────────────────────────────────────────────
        packet: dict[str, Any] = {
            # Identity
            "trace_id": trace_id,
            "session_id": session_id,
            "timestamp": timestamp,
            "source_type": source_type,

            # Content (scrubbed)
            "message_summary": message_summary,
            "response_summary": response_summary,

            # Domain / intent
            "domain_detected": domain_detected,
            "intent_type": intent_type,

            # Flags
            "risk_flags": risk_flags,
            "missing_data_flags": missing_data_flags,
            "contradiction_flags": contradiction_flags,
            "weak_signal_tags": weak_signal_tags,
            "dead_path_tags": dead_path_tags,
            "useful_path_tags": useful_path_tags,

            # Scores
            "memory_relevance_score": memory_relevance_score,
            "path_coherence_score": round(path_coherence, 4),
            "risk_composite": round(risk_composite, 4),

            # V3 snapshots
            "point_cloud_21d_snapshot": point_cloud_snapshot,
            "balance_tags_snapshot": balance_tags_snapshot,

            # Fastpath
            "fastpath_type": fastpath_type,
            "fastpath_triggered": fastpath_triggered,

            # Provider-neutral memory activation
            "memory_required": memory_required,

            # ── Invariant fields — ALWAYS these values ────────────────────────
            "readonly": True,
            "canonical_write": False,
            "memory_write": False,
            "kernel_mutation": False,
            "emits_act": False,
            "decision_authority": "KX108_ONLY",
            "human_validation_required": True,
            "advisory_only": True,
            "block": "V3_BLOCK_3A",

            # Security audit
            "security_flags": {
                "is_adversarial": is_adversarial,
                "secret_in_message": message_has_secret,
                "secret_in_response": response_has_secret,
                "scrubbed": message_has_secret or response_has_secret,
            },
        }

        return packet

    def _error_trace(self, session_id: str, timestamp: str, error: str) -> dict:
        return {
            "trace_id": "TR_ERROR_" + uuid.uuid4().hex[:8].upper(),
            "session_id": session_id,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "source_type": "error",
            "error": error,
            "memory_required": False,
            "readonly": True,
            "canonical_write": False,
            "memory_write": False,
            "kernel_mutation": False,
            "emits_act": False,
            "decision_authority": "KX108_ONLY",
            "human_validation_required": True,
            "advisory_only": True,
            "block": "V3_BLOCK_3A",
            "memory_relevance_score": 0.0,
        }


def extract_memory_trace(
    *,
    message: str,
    response_text: str,
    v3_dryrun_packet: dict | None = None,
    session_id: str = "",
    timestamp: str = "",
    source_type: str = "pipeline",
) -> dict:
    """Module-level convenience wrapper. Never raises."""
    return BrodyMemoryTraceExtractor().extract(
        message=message,
        response_text=response_text,
        v3_dryrun_packet=v3_dryrun_packet,
        session_id=session_id,
        timestamp=timestamp,
        source_type=source_type,
    )
