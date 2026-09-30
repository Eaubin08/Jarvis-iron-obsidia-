# PORTED READ-ONLY SNAPSHOT FROM Eaubin08/obsidia-x108-proofs
# Source: scripts/obsidia_gateway_route_decision_v0.py
# Source blob SHA: 3b9fb946329b0ef2408bb0290f68c9b8af7eb5b7
# Port purpose: Jarjar integration work without modifying the canonical Obsidia repository.
# Runtime wiring: NOT ACTIVE by this copy alone.
# Keep KX108_ONLY / readonly boundaries intact.
#!/usr/bin/env python3
"""OBSIDIA CG-B — RouteDecision + RouteReceipt canoniques NON SOUVERAINS
+ API minimale mission / status / receipt / HOLD / capability-request.

RUNTIME INERTE :
  * ne rend AUCUNE décision d'exécution ni d'autorité KX
    (IS_EXECUTION_AUTHORITY = FALSE, IS_KX_AUTHORITY = FALSE) ;
  * `request_capability(...)` crée un enregistrement + une RouteDecision +
    un RouteReceipt mais N'ACCORDE AUCUN accès outil et N'ACTIVE AUCUN bail
    (CAPABILITY_REQUEST_CAN_GRANT_TOOL_ACCESS = FALSE,
     LEASE_RUNTIME_IMPLEMENTED = FALSE) ;
  * router externe ABSENT / EXCEPTION / DÉCISION MALFORMÉE
    -> HOLD STRUCTURÉ, JAMAIS de repli implicite vers Claude / un LLM
    (ROUTER_*_FAIL_OPEN = FALSE).

Ce module N'EST PAS une seconde Gateway. `scripts/obsidia_gateway.py` reste
le propriétaire ; ce module lui fournit la frontière router + les schémas.
`decision_authority = KX108_ONLY` — affirmé, jamais fixé ici.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCHEMA_VERSION = 1
DECISION_AUTHORITY = "KX108_ONLY"
ROUTE_DECISION_DOMAIN_TAG = "OBSIDIA_CGB_ROUTE_DECISION_V0"
ROUTE_RECEIPT_DOMAIN_TAG = "OBSIDIA_CGB_ROUTE_RECEIPT_V0"

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _default_store() -> Path:
    """Magasin CG-B. Redirigeable via OBSIDIA_CGB_STORE_DIR (tests, sandbox).
    Par défaut : audit/gateway_cgb/ (même famille que audit/obsidia_gateway_usage.jsonl,
    exclu localement par l'opérateur — jamais un artefact suivi)."""
    return Path(os.environ.get("OBSIDIA_CGB_STORE_DIR",
                               str(_REPO_ROOT / "audit" / "gateway_cgb")))


# Compat : certains appels historiques référencent la constante.
_DEFAULT_STORE = _default_store()

# ── Classes de route sémantiques canoniques (§C) ──────────────────────────
ROUTE_STACK_NATIVE = "ROUTE_STACK_NATIVE"
ROUTE_LLM_LANGUAGE = "ROUTE_LLM_LANGUAGE"
ROUTE_LLM_REASONING = "ROUTE_LLM_REASONING"
ROUTE_LLM_ENGINEERING = "ROUTE_LLM_ENGINEERING"
ROUTE_HUMAN_AUTHORITY = "ROUTE_HUMAN_AUTHORITY"
ROUTE_UNKNOWN = "ROUTE_UNKNOWN"
_ALL_ROUTE_CLASSES = (
    ROUTE_STACK_NATIVE, ROUTE_LLM_LANGUAGE, ROUTE_LLM_REASONING,
    ROUTE_LLM_ENGINEERING, ROUTE_HUMAN_AUTHORITY, ROUTE_UNKNOWN,
)

# ── Statut de la frontière router ────────────────────────────────────────
ROUTER_OK = "ROUTER_OK"
ROUTER_UNAVAILABLE = "ROUTER_UNAVAILABLE"
ROUTER_EXCEPTION = "ROUTER_EXCEPTION"
MALFORMED_ROUTER_DECISION = "MALFORMED_ROUTER_DECISION"
_ROUTER_HOLD_STATUSES = (ROUTER_UNAVAILABLE, ROUTER_EXCEPTION, MALFORMED_ROUTER_DECISION)

CG_B_ROUTER_COLOCATION_DEFERRED = True  # router externe non colocalisé -> HOLD structuré

# ── Statuts publics de l'API minimale ───────────────────────────────────
STATUS_SUBMITTED_ROUTED_INERT = "SUBMITTED_ROUTED_INERT"
STATUS_AWAITING_HUMAN = "AWAITING_HUMAN"
STATUS_HOLD_RESPONSE_RECORDED_INERT = "HOLD_RESPONSE_RECORDED_INERT"
STATUS_CAPABILITY_REQUEST_RECORDED_INERT = "CAPABILITY_REQUEST_RECORDED_INERT"
STATUS_API_REJECTED = "API_REJECTED"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _router_root() -> Path:
    return Path(os.environ.get("OBSIDIA_ROUTER_ROOT",
                               r"C:\Users\User\Desktop\obsidia-router"))


# ══════════════════════════════════════════════════════════════════════════
#  1 — Frontière router : disponible -> décision ; sinon -> HOLD structuré
# ══════════════════════════════════════════════════════════════════════════

def router_decide(raw: str, memory_index: Optional[dict] = None
                  ) -> "tuple[Optional[dict], str]":
    """Retourne (router_decision_dict, ROUTER_OK) ou (None, <statut HOLD>).

    JAMAIS d'exception propagée, JAMAIS de repli LLM : toute anomalie du
    router se traduit par un statut de HOLD structuré."""
    root = _router_root()
    decision_py = root / "app" / "router" / "decision.py"
    if not decision_py.is_file():
        return None, ROUTER_UNAVAILABLE
    try:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from app.router.decision import decide  # type: ignore
    except Exception:
        return None, ROUTER_UNAVAILABLE
    try:
        d = decide(raw, memory_index=memory_index or {})
    except Exception:
        return None, ROUTER_EXCEPTION
    if not isinstance(d, dict) or not isinstance(d.get("route"), str) or not d["route"].strip():
        return None, MALFORMED_ROUTER_DECISION
    if not isinstance(d.get("ir"), dict) or not isinstance(d.get("gate"), dict):
        return None, MALFORMED_ROUTER_DECISION
    return d, ROUTER_OK


# ══════════════════════════════════════════════════════════════════════════
#  2 — Normalisation en une RouteDecision canonique NON SOUVERAINE
# ══════════════════════════════════════════════════════════════════════════

_LANGUAGE_INTENTS = {"question", "explain", "explanation", "summarize", "summary",
                     "translate", "language", "dialogue", "chat"}
_REASONING_INTENTS = {"design", "architecture", "plan", "reason", "reasoning",
                      "analysis", "novel"}
_ENGINEERING_INTENTS = {"code_request", "code", "patch", "refactor", "implement",
                        "engineering"}
_STACK_NATIVE_ROUTES = {"no_model_needed", "memory_hit", "semantic_memory_hit",
                        "lean_route_only"}
_HUMAN_AUTHORITY_ROUTES = {"denied", "hold_commands_only", "clarification_needed",
                           "os_trad_risk_hold", "domain_bridge", "kernel_bridge"}
_ENGINEERING_ROUTES = {"obsidure_route_only", "obsidure_proposal"}
_LANGUAGE_ROUTES = {"brody"}


def _map_route_class(router_d: dict) -> "tuple[str, bool, bool]":
    """(route_class, human_authority_required, unknown).

    Règle de sûreté (§11) : ROUTE_LLM_ENGINEERING n'est JAMAIS un défaut —
    seulement une route Obsidure explicite ou un intent d'ingénierie
    explicite. Toute ambiguïté -> ROUTE_UNKNOWN (fail-safe), jamais LLM."""
    route = (router_d.get("route") or "").strip()
    gate_verdict = ((router_d.get("gate") or {}).get("verdict") or "").upper()
    intent = ((router_d.get("ir") or {}).get("intent_type") or "").strip().lower()

    if gate_verdict in ("DENY", "HOLD", "CLARIFY"):
        return ROUTE_HUMAN_AUTHORITY, True, False
    if route in _HUMAN_AUTHORITY_ROUTES:
        return ROUTE_HUMAN_AUTHORITY, True, False
    if route in _STACK_NATIVE_ROUTES:
        return ROUTE_STACK_NATIVE, False, False
    if route in _ENGINEERING_ROUTES or intent in _ENGINEERING_INTENTS:
        return ROUTE_LLM_ENGINEERING, False, False
    if route in _LANGUAGE_ROUTES:
        if intent in _REASONING_INTENTS:
            return ROUTE_LLM_REASONING, False, False
        return ROUTE_LLM_LANGUAGE, False, False
    # route d'escalade / fireworks / inconnue
    if intent in _LANGUAGE_INTENTS:
        return ROUTE_LLM_LANGUAGE, False, False
    if intent in _REASONING_INTENTS:
        return ROUTE_LLM_REASONING, False, False
    return ROUTE_UNKNOWN, False, True


def build_route_decision(raw: str, memory_index: Optional[dict] = None) -> dict:
    """RouteDecision canonique. NON SOUVERAINE. Router KO -> HOLD structuré."""
    router_d, status = router_decide(raw, memory_index)
    fail_closed_hold = status in _ROUTER_HOLD_STATUSES

    if fail_closed_hold:
        route_class = ROUTE_HUMAN_AUTHORITY
        human_req, unknown = True, False
        reason = f"{status}_STRUCTURED_HOLD_NO_LLM_FALLBACK"
        router_route, gate_verdict, ir, level = None, None, {}, None
    else:
        route_class, human_req, unknown = _map_route_class(router_d)
        router_route = router_d.get("route")
        gate_verdict = ((router_d.get("gate") or {}).get("verdict") or None)
        _ir = router_d.get("ir") or {}
        ir = {k: _ir.get(k) for k in ("intent_type", "target_layer", "action", "risk")}
        level = router_d.get("level")
        reason = router_d.get("reason") or f"router_route={router_route}"

    core = {
        "schema_version": SCHEMA_VERSION,
        "domain_tag": ROUTE_DECISION_DOMAIN_TAG,
        "decision_authority": DECISION_AUTHORITY,
        "is_execution_authority": False,
        "is_kx_authority": False,
        "is_sovereign": False,
        "requested_outcome_preview": (raw or "")[:200],
        "router_status": status,
        "fail_closed_hold": fail_closed_hold,
        "route_class": route_class,
        "router_route": router_route,
        "gate_verdict": gate_verdict,
        "ir": ir,
        "level": level,
        "reason": reason,
        "human_authority_required": human_req,
        "unknown": unknown,
    }
    rh = _sha256_hex(_canon(core))
    core["route_decision_hash"] = rh
    core["route_decision_id"] = "rdec-" + rh[:32]
    core["created_at"] = _now()
    return core


def verify_route_decision(d: Optional[dict]) -> "tuple[bool, Optional[str]]":
    if not isinstance(d, dict):
        return False, "ROUTE_DECISION_MISSING"
    if d.get("schema_version") != SCHEMA_VERSION:
        return False, "SCHEMA_UNSUPPORTED"
    if d.get("domain_tag") != ROUTE_DECISION_DOMAIN_TAG:
        return False, "DOMAIN_TAG_MISMATCH"
    if d.get("route_class") not in _ALL_ROUTE_CLASSES:
        return False, "ROUTE_CLASS_INVALID"
    if d.get("is_execution_authority") is not False or d.get("is_kx_authority") is not False:
        return False, "ROUTE_DECISION_CLAIMS_AUTHORITY"
    core = {k: d.get(k) for k in (
        "schema_version", "domain_tag", "decision_authority", "is_execution_authority",
        "is_kx_authority", "is_sovereign", "requested_outcome_preview", "router_status",
        "fail_closed_hold", "route_class", "router_route", "gate_verdict", "ir", "level",
        "reason", "human_authority_required", "unknown")}
    if d.get("route_decision_hash") != _sha256_hex(_canon(core)):
        return False, "ROUTE_DECISION_HASH_MISMATCH"
    if d.get("route_decision_id") != "rdec-" + d["route_decision_hash"][:32]:
        return False, "ROUTE_DECISION_ID_NOT_DERIVED"
    return True, None


# ══════════════════════════════════════════════════════════════════════════
#  3 — RouteReceipt canonique NON SOUVERAIN (§D)
# ══════════════════════════════════════════════════════════════════════════

def _sd(store_dir) -> Path:
    return Path(store_dir) if store_dir is not None else _default_store()

_RECEIPT_BOUND_FIELDS = (
    "schema_version", "domain_tag", "decision_authority",
    "requested_outcome", "route_decision_ref", "selected_route", "reason",
    "native_capability", "provider", "model_call_used", "model_call_avoided",
    "fallback_used", "fallback_reason", "human_authority_required", "unknown_ref",
    "result_status", "tools_or_organs_used", "lease_id",
)


def build_route_receipt(
    route_decision: dict, *,
    requested_outcome: str,
    selected_route: str,
    reason: str,
    native_capability: Optional[str] = None,
    provider: Optional[str] = None,
    model_call_used: bool = False,
    model_call_avoided: bool = True,
    fallback_used: bool = False,
    fallback_reason: Optional[str] = None,
    unknown_ref: Optional[str] = None,
    result_status: str = "ROUTED_NO_EXECUTION",
    tools_or_organs_used: Optional[list] = None,
    lease_id: Optional[str] = None,
    persist: bool = True,
    store_dir=None,
) -> dict:
    """CG-B : `lease_id` est TOUJOURS forcé à None (aucun bail runtime).
    Un RouteReceipt n'est PAS une autorité et n'autorise AUCUNE exécution."""
    store_dir = _sd(store_dir)
    rec = {
        "schema_version": SCHEMA_VERSION,
        "domain_tag": ROUTE_RECEIPT_DOMAIN_TAG,
        "decision_authority": DECISION_AUTHORITY,
        "is_authority": False,
        "can_authorize_execution": False,
        "requested_outcome": (requested_outcome or "")[:400],
        "route_decision_ref": route_decision.get("route_decision_id"),
        "route_decision_hash_ref": route_decision.get("route_decision_hash"),
        "selected_route": selected_route,
        "reason": reason,
        "native_capability": native_capability,
        "provider": provider,
        "model_call_used": bool(model_call_used),
        "model_call_avoided": bool(model_call_avoided),
        "fallback_used": bool(fallback_used),
        "fallback_reason": fallback_reason,
        "human_authority_required": bool(route_decision.get("human_authority_required")),
        "unknown_ref": unknown_ref,
        "result_status": result_status,
        "tools_or_organs_used": list(tools_or_organs_used or []),
        "lease_id": None,  # CG-B : aucun bail
        "router_status": route_decision.get("router_status"),
        "route_class": route_decision.get("route_class"),
        "created_at": _now(),
    }
    bound = {k: rec.get(k) for k in _RECEIPT_BOUND_FIELDS}
    h = _sha256_hex(_canon(bound))
    rec["receipt_hash"] = h
    rec["route_receipt_id"] = "rcpt-" + h[:32]
    if persist:
        _persist_receipt(rec, store_dir)
    return rec


def verify_route_receipt(rec: Optional[dict]) -> "tuple[bool, Optional[str]]":
    if not isinstance(rec, dict):
        return False, "RECEIPT_MISSING"
    if rec.get("schema_version") != SCHEMA_VERSION:
        return False, "SCHEMA_UNSUPPORTED"
    if rec.get("domain_tag") != ROUTE_RECEIPT_DOMAIN_TAG:
        return False, "DOMAIN_TAG_MISMATCH"
    if rec.get("is_authority") is not False or rec.get("can_authorize_execution") is not False:
        return False, "RECEIPT_CLAIMS_AUTHORITY"
    if rec.get("lease_id") is not None:
        return False, "RECEIPT_CARRIES_LEASE_ID_IN_CG_B"
    bound = {k: rec.get(k) for k in _RECEIPT_BOUND_FIELDS}
    if rec.get("receipt_hash") != _sha256_hex(_canon(bound)):
        return False, "RECEIPT_HASH_MISMATCH"
    if rec.get("route_receipt_id") != "rcpt-" + rec["receipt_hash"][:32]:
        return False, "RECEIPT_ID_NOT_DERIVED"
    return True, None


def _persist_receipt(rec: dict, store_dir) -> None:
    store_dir = _sd(store_dir)
    try:
        d = store_dir / "receipts"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{rec['route_receipt_id']}.json").write_text(
            json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with (store_dir / "route_receipts.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def get_receipt(route_receipt_id: str, store_dir=None) -> Optional[dict]:
    if not (isinstance(route_receipt_id, str) and route_receipt_id.startswith("rcpt-")):
        return None
    p = _sd(store_dir) / "receipts" / f"{route_receipt_id}.json"
    if not p.is_file():
        return None
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    ok, _ = verify_route_receipt(rec)
    return rec if ok else None


# ══════════════════════════════════════════════════════════════════════════
#  4 — API minimale INERTE (§E/§F) — réutilise TERMINAL_COMMAND_ENVELOPE_V1
# ══════════════════════════════════════════════════════════════════════════

CAPABILITY_REQUEST_CAN_GRANT_TOOL_ACCESS = False
LEASE_RUNTIME_IMPLEMENTED = False
COGNITIVE_CAPABILITY_LEASE_ACTIVE = False
ENGINEERING_LEASE_ACTIVE = False


def _write_record(kind_dir: str, rec_id: str, rec: dict, store_dir) -> None:
    try:
        d = _sd(store_dir) / kind_dir
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{rec_id}.json").write_text(
            json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass


def _load_record(kind_dir: str, rec_id: str, store_dir) -> Optional[dict]:
    p = _sd(store_dir) / kind_dir / f"{rec_id}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_mission_submission(mission_submission_id: str, store_dir=None) -> Optional[dict]:
    """Lecture publique d'une MissionSubmission CG-B (pour les consommateurs
    canoniques, ex. CG-C). Aucune écriture, aucune autorité."""
    if not (isinstance(mission_submission_id, str) and mission_submission_id.startswith("gsub-")):
        return None
    return _load_record("submissions", mission_submission_id, store_dir)


def load_capability_request(capability_request_id: str, store_dir=None) -> Optional[dict]:
    """Lecture publique d'une CapabilityRequest CG-B (INERTE : granted=False)."""
    if not (isinstance(capability_request_id, str) and capability_request_id.startswith("gcap-")):
        return None
    return _load_record("capability_requests", capability_request_id, store_dir)


def submit_mission(
    *, requested_outcome: str,
    mission_contract_ref: Optional[str] = None,
    human_decision_ref: Optional[str] = None,
    capability_request_refs: Optional[list] = None,
    context_request_ref: Optional[str] = None,
    memory_index: Optional[dict] = None,
    store_dir=None,
) -> dict:
    """Enregistre une soumission de mission + calcule une RouteDecision + un
    RouteReceipt. AUCUNE exécution : CG-B est inerte. Les champs réutilisent
    TERMINAL_COMMAND_ENVELOPE_V1 (pas d'enveloppe dupliquée)."""
    if not (isinstance(requested_outcome, str) and requested_outcome.strip()):
        return {"status": STATUS_API_REJECTED, "reason": "REQUESTED_OUTCOME_REQUIRED"}
    rdec = build_route_decision(requested_outcome, memory_index)
    result_status = ("AWAITING_HUMAN"
                     if (rdec["human_authority_required"] or rdec["fail_closed_hold"])
                     else "ROUTED_NO_EXECUTION")
    receipt = build_route_receipt(
        rdec, requested_outcome=requested_outcome,
        selected_route=rdec["route_class"], reason=rdec["reason"],
        native_capability=rdec.get("router_route"),
        model_call_used=False, model_call_avoided=True,
        result_status=result_status,
        unknown_ref=(("unk-" + rdec["route_decision_hash"][:24]) if rdec["unknown"] else None),
        store_dir=store_dir)
    sub = {
        "schema_version": SCHEMA_VERSION,
        "domain_tag": "OBSIDIA_CGB_MISSION_SUBMISSION_V0",
        "decision_authority": DECISION_AUTHORITY,
        "is_execution_authority": False,
        "requested_outcome": requested_outcome[:400],
        "envelope_refs": {
            "mission_contract_ref": mission_contract_ref,
            "human_decision_ref": human_decision_ref,
            "capability_request_refs": list(capability_request_refs or []),
            "context_request_ref": context_request_ref,
        },
        "route_decision": rdec,
        "route_receipt_id": receipt["route_receipt_id"],
        "status": (STATUS_AWAITING_HUMAN
                   if result_status == "AWAITING_HUMAN" else STATUS_SUBMITTED_ROUTED_INERT),
        "cg_b_inert": True,
        "created_at": _now(),
    }
    mid = "gsub-" + _sha256_hex(_canon({
        "requested_outcome": requested_outcome, "rdec": rdec["route_decision_id"],
        "created_at": sub["created_at"]}))[:32]
    sub["mission_submission_id"] = mid
    _write_record("submissions", mid, sub, store_dir)
    return {
        "status": sub["status"], "mission_submission_id": mid,
        "route_decision": rdec, "route_receipt_id": receipt["route_receipt_id"],
        "cg_b_inert": True, "execution_started": False,
    }


def get_status(mission_submission_id: str,
               store_dir=None) -> dict:
    sub = _load_record("submissions", mission_submission_id, store_dir)
    if sub is None:
        return {"status": STATUS_API_REJECTED, "reason": "MISSION_SUBMISSION_NOT_FOUND"}
    rdec = sub.get("route_decision") or {}
    return {
        "mission_submission_id": mission_submission_id,
        "status": sub.get("status"),
        "route_class": rdec.get("route_class"),
        "router_status": rdec.get("router_status"),
        "fail_closed_hold": rdec.get("fail_closed_hold"),
        "human_authority_required": rdec.get("human_authority_required"),
        "route_receipt_id": sub.get("route_receipt_id"),
        "execution_started": False, "cg_b_inert": True,
    }


def respond_to_hold(
    *, mission_submission_id: str, human_decision_ref: str, resolution: str,
    store_dir=None,
) -> dict:
    """Enregistre une réponse humaine à un HOLD. N'exécute RIEN, n'accorde
    RIEN. La reprise réelle appartient à un checkpoint ultérieur."""
    sub = _load_record("submissions", mission_submission_id, store_dir)
    if sub is None:
        return {"status": STATUS_API_REJECTED, "reason": "MISSION_SUBMISSION_NOT_FOUND"}
    if not (isinstance(human_decision_ref, str) and human_decision_ref.strip()):
        return {"status": STATUS_API_REJECTED, "reason": "HUMAN_DECISION_REF_REQUIRED"}
    hr = {
        "schema_version": SCHEMA_VERSION,
        "domain_tag": "OBSIDIA_CGB_HOLD_RESPONSE_V0",
        "decision_authority": DECISION_AUTHORITY,
        "mission_submission_id": mission_submission_id,
        "human_decision_ref": human_decision_ref,
        "resolution": str(resolution)[:400],
        "grants_capability": False, "starts_execution": False, "cg_b_inert": True,
        "created_at": _now(),
    }
    hid = "ghold-" + _sha256_hex(_canon(hr))[:32]
    hr["hold_response_id"] = hid
    _write_record("holds", hid, hr, store_dir)
    return {"status": STATUS_HOLD_RESPONSE_RECORDED_INERT,
            "hold_response_id": hid, "grants_capability": False,
            "starts_execution": False, "cg_b_inert": True}


def request_capability(
    *, mission_submission_id: str, requested_capability: str, reason: str,
    human_decision_ref: Optional[str] = None,
    memory_index: Optional[dict] = None,
    store_dir=None,
) -> dict:
    """INERTE. Crée un enregistrement de demande + une RouteDecision + un
    RouteReceipt, mais N'ACCORDE AUCUN accès outil et N'ACTIVE AUCUN bail.
    Le runtime de bail cognitif/ingénierie appartient à CG-C / CG-E."""
    sub = _load_record("submissions", mission_submission_id, store_dir)
    if sub is None:
        return {"status": STATUS_API_REJECTED, "reason": "MISSION_SUBMISSION_NOT_FOUND"}
    if not (isinstance(requested_capability, str) and requested_capability.strip()):
        return {"status": STATUS_API_REJECTED, "reason": "REQUESTED_CAPABILITY_REQUIRED"}
    ask = f"CAPABILITY_REQUEST: {requested_capability} :: {reason}"
    rdec = build_route_decision(ask, memory_index)
    receipt = build_route_receipt(
        rdec, requested_outcome=ask, selected_route=rdec["route_class"],
        reason=rdec["reason"], native_capability=rdec.get("router_route"),
        result_status="CAPABILITY_REQUEST_RECORDED_INERT", store_dir=store_dir)
    cr = {
        "schema_version": SCHEMA_VERSION,
        "domain_tag": "OBSIDIA_CGB_CAPABILITY_REQUEST_V0",
        "decision_authority": DECISION_AUTHORITY,
        "mission_submission_id": mission_submission_id,
        "requested_capability": requested_capability[:200],
        "reason": str(reason)[:400],
        "human_decision_ref": human_decision_ref,
        "route_decision": rdec,
        "route_receipt_id": receipt["route_receipt_id"],
        "granted": False,
        "grants_tool_access": False,
        "lease_runtime_implemented": False,
        "cognitive_capability_lease_active": False,
        "engineering_lease_active": False,
        "claude_self_authorizes_engineering": False,
        "cg_b_inert": True,
        "created_at": _now(),
    }
    cid = "gcap-" + _sha256_hex(_canon(cr))[:32]
    cr["capability_request_id"] = cid
    _write_record("capability_requests", cid, cr, store_dir)
    return {
        "status": STATUS_CAPABILITY_REQUEST_RECORDED_INERT,
        "capability_request_id": cid,
        "route_decision": rdec,
        "route_receipt_id": receipt["route_receipt_id"],
        "granted": False, "grants_tool_access": False,
        "lease_runtime_implemented": False,
        "cognitive_capability_lease_active": False,
        "engineering_lease_active": False,
        "cg_b_inert": True,
    }


# ══════════════════════════════════════════════════════════════════════════
#  5 — CLI mince (réutilise la Gateway comme propriétaire, pas un 2e terminal)
# ══════════════════════════════════════════════════════════════════════════

def _main(argv: "list[str]") -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="obsidia_gateway_route_decision_v0",
                                 description="CG-B RouteDecision / RouteReceipt / API inerte")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("route"); p.add_argument("text", nargs="+")
    p = sub.add_parser("submit-mission"); p.add_argument("text", nargs="+")
    p = sub.add_parser("status"); p.add_argument("mission_submission_id")
    p = sub.add_parser("receipt"); p.add_argument("route_receipt_id")
    p = sub.add_parser("respond-hold")
    p.add_argument("mission_submission_id"); p.add_argument("human_decision_ref")
    p.add_argument("resolution", nargs="+")
    p = sub.add_parser("request-capability")
    p.add_argument("mission_submission_id"); p.add_argument("requested_capability")
    p.add_argument("reason", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "route":
        out = build_route_decision(" ".join(a.text))
    elif a.cmd == "submit-mission":
        out = submit_mission(requested_outcome=" ".join(a.text))
    elif a.cmd == "status":
        out = get_status(a.mission_submission_id)
    elif a.cmd == "receipt":
        out = get_receipt(a.route_receipt_id) or {"status": "NOT_FOUND"}
    elif a.cmd == "respond-hold":
        out = respond_to_hold(mission_submission_id=a.mission_submission_id,
                              human_decision_ref=a.human_decision_ref,
                              resolution=" ".join(a.resolution))
    elif a.cmd == "request-capability":
        out = request_capability(mission_submission_id=a.mission_submission_id,
                                 requested_capability=a.requested_capability,
                                 reason=" ".join(a.reason))
    else:
        ap.print_help()
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
