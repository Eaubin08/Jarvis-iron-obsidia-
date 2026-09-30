"""
BRODY REAL RESPONSE PIPELINE - V5B+
Prioritizes: local_response_engine > terminal_structural_dialogue.
Never returns raw tuples. Always returns response_md string.
Provider-neutral readonly response pipeline.
"""
from __future__ import annotations
import json, sys, uuid, os, socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apps.obsidia_api.brody_pre_reasoning_adapter import (
    build_brody_pre_reasoning_snapshot,
)

from periphery.language.pre_response_calibrator import (
    calibrate_pre_response,
)

from periphery.language.pre_action_calibrator import (
    calibrate_pre_action,
)

from periphery.language.final_sense_halo import (
    build_final_sense_halo,
)

from periphery.language.action_meaning_validator import (
    validate_action_meaning,
)

_TERMINAL = None
_LOCAL_ENGINE = None
_HYDRATION = None

def _si(mod_path: str) -> Any | None:
    try: return __import__(mod_path, fromlist=['*'])
    except: return None

P = "periphery.brody_memory_readonly."

def _load():
    global _TERMINAL, _LOCAL_ENGINE, _HYDRATION
    _TERMINAL = _TERMINAL or _si(P + "terminal_structural_dialogue_readonly.brody_terminal_structural_dialogue_readonly_v1")
    _LOCAL_ENGINE = _LOCAL_ENGINE or _si(P + "local_response_engine_readonly.brody_local_response_engine_readonly_v1")
    _HYDRATION = _HYDRATION or _si(P + "content_hydration_readonly.brody_content_hydration_readonly_v1")






SOV: dict[str, Any] = {
    "readonly": True, "response_only": True, "memory_role": "GUIDE_CONTEXT_NAVIGATION_ONLY",
    "memory_decision": False, "allowed_to_decide": False, "allowed_to_act": False,
    "emits_act": False, "emits_verdict": False, "emits_allow_hold_block": False,
    "kernel_mutation": False, "x108_mutation": False,
    "memory_write": False, "real_action": False,
    "decision_authority": "KX108_ONLY",
}


def run_brody_real_response_pipeline(
    message: str,
    language: str = "fr",
    session_id: str = "local",
    x108_root: str | None = None,
    limit: int = 8,
    max_items: int = 6,
) -> dict[str, Any]:
    _load()
    action_id = f"brody_real_{uuid.uuid4().hex[:12]}"
    root = Path(x108_root) if x108_root else Path(__file__).resolve().parents[3]
    r: dict[str, Any] = dict(SOV)
    r["action_id"] = action_id
    r["language"] = language
    r["timestamp"] = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------
    # PRE-REASONING CAUSAL GATE
    #
    # Cognitive guidance only:
    # - no HOLD/BLOCK/ALLOW
    # - no memory retrieval
    # - no provider
    # - no ACT
    #
    # It exists before response generation so an unresolved symbol
    # cannot be silently treated as a known concept by the responder.
    # ------------------------------------------------------------

    pre_reasoning_snapshot = (
        build_brody_pre_reasoning_snapshot(
            user_message=message,
            language=language,
            intent="pure_response",
            authority_snapshot={
                "request_type": "PURE_RESPONSE",
            },
        )
    )

    r["pre_reasoning_snapshot"] = (
        pre_reasoning_snapshot
    )

    reasoning_directive = (
        pre_reasoning_snapshot.get(
            "reasoning_directive",
            {},
        )
    )

    if not isinstance(
        reasoning_directive,
        dict,
    ):
        reasoning_directive = {}

    resolution_required = bool(
        reasoning_directive.get(
            "resolution_required",
            False,
        )
    )

    resolution_targets = [
        str(value).strip()
        for value in reasoning_directive.get(
            "resolution_targets",
            [],
        )
        if str(value).strip()
    ]

    # Preserve historical terminal commands.
    is_terminal_command = (
        str(message or "")
        .lstrip()
        .startswith(":")
    )


    memory_query = message
    action_risk = False
    if _TERMINAL:
        try: memory_query = _TERMINAL.extract_memory_query(message) or message
        except: pass
        try: action_risk = bool(_TERMINAL.is_action_risk(message))
        except: pass


    response_md = ""
    engine_used = False
    source = "REAL_BRODY_RUNTIME"
    material_quality = ""
    selected_items: list = []
    tag_counts: dict = {}

    # C274 is not sovereign and emits no verdict.
    #
    # Its only causal effect here is epistemic:
    # do not let the responder assert an unresolved symbol as known.
    if (
        resolution_required
        and resolution_targets
        and not is_terminal_command
    ):
        targets_text = ", ".join(
            resolution_targets
        )

        if language == "fr":
            response_md = (
                "Je ne peux pas traiter "
                f"? {targets_text} ? "
                "comme un concept connu : "
                "ce symbole reste non r?solu "
                "avant raisonnement."
            )
        else:
            response_md = (
                "I cannot treat "
                f'"{targets_text}" '
                "as a known concept: "
                "this symbol remains unresolved "
                "before reasoning."
            )

        source = (
            "PRE_REASONING_UNRESOLVED_SYMBOL"
        )


    if not response_md and _TERMINAL:
        try:
            terminal_result = _TERMINAL.build_response(
                user_text=message, memory_query=memory_query, packet={}, selected=[], command=None)
            if terminal_result is not None:
                if isinstance(terminal_result, (tuple, list)):
                    parts = list(terminal_result)
                    response_md = str(parts[0]) if len(parts) > 0 else ""
                    axes = parts[1] if len(parts) > 1 else []
                    risk = parts[2] if len(parts) > 2 else False
                    r["axes"] = axes
                    r["risk"] = risk
                elif isinstance(terminal_result, dict):
                    response_md = terminal_result.get("response_md", "")
                    if not response_md:
                        response_md = terminal_result.get("response_text", str(terminal_result))
                else:
                    response_md = str(terminal_result)
                source = "REAL_BRODY_RUNTIME"
        except: pass

    if not response_md and _TERMINAL and hasattr(_TERMINAL, 'command_response'):
        try:
            cmd = _TERMINAL.command_response(message)
            if cmd: response_md = str(cmd)
        except: pass

    if not response_md:
        source = "BACKEND_STUB_LAST_RESORT"
        response_md = (
            "Brody est actif en mode readonly consultatif. "
            "Mode readonly consultatif, sans dependance provider externe. "
            "X108 est la seule autorite de decision."
        ) if language == "fr" else (
            "Brody is active in readonly advisory mode. "
            "Readonly advisory mode, with no external provider dependency. "
            "X108 is the sole decision authority."
        )

    # ------------------------------------------------------------
    # C275 PRE-RESPONSE CALIBRATION
    #
    # The response has now been produced, but is not yet exposed.
    # C275 verifies continuity with the epistemic constraints
    # established by C274.
    #
    # It does not rewrite the candidate itself and has no
    # decision or action authority.
    # ------------------------------------------------------------

    pre_reasoning_calibration = (
        pre_reasoning_snapshot.get(
            "pre_reasoning_calibration",
            {},
        )
    )

    if not isinstance(
        pre_reasoning_calibration,
        dict,
    ):
        pre_reasoning_calibration = {}

    pre_response_calibration = (
        calibrate_pre_response(
            candidate_response=response_md,
            reasoning_directive=(
                reasoning_directive
            ),
            pre_reasoning_calibration=(
                pre_reasoning_calibration
            ),
            language=language,
        )
    )

    r[
        "pre_response_calibration"
    ] = pre_response_calibration

    c275_readiness = str(
        pre_response_calibration.get(
            "response_readiness",
            "",
        )
    )

    c275_calibration_required = bool(
        pre_response_calibration.get(
            "calibration_required",
            False,
        )
    )

    # A candidate rejected by C275 cannot be surfaced unchanged.
    #
    # C275 itself remains advisory/non-sovereign:
    # this runtime boundary merely refuses to expose a candidate
    # that violates the prior epistemic calibration.
    if (
        c275_calibration_required
        or c275_readiness
        == "REQUIRES_CALIBRATION"
    ):
        flags = [
            str(value).strip()
            for value in (
                pre_response_calibration.get(
                    "calibration_flags",
                    [],
                )
                or []
            )
            if str(value).strip()
        ]

        flag_text = (
            ", ".join(flags)
            if flags
            else "C275_CALIBRATION_REQUIRED"
        )

        if language == "fr":
            response_md = (
                "La r?ponse candidate ne peut pas "
                "?tre expos?e telle quelle : "
                "la calibration avant r?ponse "
                "signale une incertitude non "
                "correctement pr?serv?e. "
                f"Signal : {flag_text}."
            )
        else:
            response_md = (
                "The candidate response cannot be "
                "surfaced as-is: pre-response "
                "calibration found that prior "
                "epistemic uncertainty was not "
                "properly preserved. "
                f"Signal: {flag_text}."
            )

        source = (
            "C275_RESPONSE_CALIBRATION_REQUIRED"
        )

    ctx_data = {
        "packet_id": f"cp_{action_id}", "query": message,
        "memory_query": memory_query,
        "readonly": True,
    }

    r.update({
        "response": response_md,
        "response_md": response_md,
        "source": source,
        "response_source": source,
        "memory_query": memory_query,
        "action_risk": action_risk,
        "engine_status": (
            "C275_RESPONSE_CALIBRATION_REQUIRED"
            if source
            == "C275_RESPONSE_CALIBRATION_REQUIRED"
            else (
                "PRE_REASONING_RESOLUTION_REQUIRED"
                if source
                == "PRE_REASONING_UNRESOLVED_SYMBOL"
                else (
                    "BRODY_LOCAL_RESPONSE_ENGINE_READONLY_PASS"
                    if engine_used
                    else "TERMINAL_FALLBACK"
                )
            )
        ),
        "material_quality": material_quality, "selected_items": selected_items, "tag_counts": tag_counts,
        "context_packet": ctx_data,
        "x108_boundary": {"passed": True, "status": "READONLY"},
        "audit_event": {
            "event_id": f"audit_{action_id}", "type": "brody_real_response",
            "description": message[:100], "result": "BLOCKED" if action_risk else "OK",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    })

    # ── Route de réparation (additive) ───────────────────────────────────
    # Le retrieval + hydratation ci-dessus ne diagnostique pas du code. Quand
    # l'intent backend est `code_debug`, on émet en plus un RepairRequest
    # structuré, exploitable par un moteur de raisonnement externe puis testable
    # en sandbox par Obsidure. Purement additif : response_md est inchangé,
    # aucune frontière n'est relâchée, rien n'est appliqué.
    try:
        # Preserve the historical lazy import while allowing
        # an injected bounded adapter in tests/runtime composition.
        _attach_repair_request = globals().get(
            "attach_repair_request"
        )

        if not callable(
            _attach_repair_request
        ):
            from apps.obsidia_api.brody_repair_request_router import (
                attach_repair_request as _attach_repair_request,
            )

        _ir_intent, _flags = "", []

        try:
            from apps.obsidia_api.routes.os_trad_ir_reverse import (
                _risk_flags,
                _intent,
            )

            _flags = _risk_flags(
                message
            )

            _ir_intent = _intent(
                message,
                _flags,
            )

        except Exception:
            # Existing textual fallback remains bounded.
            pass

        # --------------------------------------------------------
        # C276 PRE-ACTION CALIBRATION
        #
        # C276 does not authorize execution.
        # It only decides whether cognitive state is sufficiently
        # calibrated to CONSTRUCT a candidate for downstream
        # governance.
        # --------------------------------------------------------

        c276_ir_candidate = {
            "intent": _ir_intent,
            "risk_flags": list(
                _flags or []
            ),
            "contradictions": [],
            "constraints": [
                "READONLY",
                "NO_ACT",
                "NO_VERDICT",
            ],
        }

        pre_action_calibration = (
            calibrate_pre_action(
                ir_candidate=(
                    c276_ir_candidate
                ),
                reasoning_directive=(
                    reasoning_directive
                ),
                pre_reasoning_calibration=(
                    pre_reasoning_calibration
                ),
                pre_response_calibration=(
                    pre_response_calibration
                ),
            )
        )

        r[
            "pre_action_calibration"
        ] = pre_action_calibration

        # --------------------------------------------------------
        # C277 FINAL SENSE HALO
        #
        # Consolidates C274 + C275 + C276 into a readonly,
        # auditable cognitive snapshot.
        #
        # No memory lookup occurs here. memory_refs stays an empty
        # pass-through on this harness branch.
        # --------------------------------------------------------

        final_sense_halo = (
            build_final_sense_halo(
                calibration_context={
                    "pre_reasoning": (
                        pre_reasoning_calibration
                    ),
                    "pre_response": (
                        pre_response_calibration
                    ),
                    "pre_action": (
                        pre_action_calibration
                    ),
                },
                memory_refs=[],
                symbolic_context={
                    # Preserve upstream intent semantics.
                    #
                    # Do not perform a new intent classification here.
                    # If the textual IR intent stayed "unknown" while
                    # C276 already carries an action_request signal,
                    # propagate that established upstream meaning.
                    "intent": (
                        str(
                            pre_action_calibration.get(
                                "intent",
                                "",
                            )
                            or ""
                        ).strip()
                        or (
                            "action_request"
                            if (
                                str(
                                    _ir_intent
                                    or ""
                                ).strip().lower()
                                in {
                                    "",
                                    "unknown",
                                }
                                and (
                                    "action_request"
                                    in list(
                                        pre_action_calibration.get(
                                            "risk_flags",
                                            [],
                                        )
                                        or []
                                    )
                                )
                            )
                            else str(
                                _ir_intent
                                or "unknown"
                            )
                        )
                    ),
                    "risk_flags": list(
                        pre_action_calibration.get(
                            "risk_flags",
                            _flags or [],
                        )
                        or []
                    ),
                },
            )
        )

        r[
            "final_sense_halo"
        ] = final_sense_halo

        c276_readiness = str(
            pre_action_calibration.get(
                "action_candidate_readiness",
                "",
            )
        )

        c276_candidate_ready = bool(
            pre_action_calibration.get(
                "candidate_projection_ready",
                False,
            )
        )

        if (
            c276_readiness
            == "NO_ACTION_CANDIDATE_REQUESTED"
        ):
            r[
                "repair_request"
            ] = None

            r[
                "repair_route_status"
            ] = (
                "NO_ACTION_CANDIDATE_REQUESTED"
            )

        elif not c276_candidate_ready:
            # No candidate is built.
            #
            # This is NOT HOLD/BLOCK/ACT and is NOT a KX108
            # decision. It is only a pre-candidate cognitive
            # boundary.
            r[
                "repair_request"
            ] = None

            r[
                "repair_route_status"
            ] = (
                "C276_CANDIDATE_NOT_READY"
            )

        else:
            # C276 permits candidate construction only.
            # Existing downstream governance remains unchanged.
            _attach_repair_request(
                r,
                message,
                ir_intent=_ir_intent,
                risk_flags=_flags,
            )

        # --------------------------------------------------------
        # C278 ACTION MEANING VALIDATOR
        #
        # C277 = consolidated cognitive meaning.
        # RepairRequest = concrete readonly action projection.
        #
        # C278 compares semantic/provenance continuity only.
        # It does NOT structurally validate a candidate,
        # authorize execution, call Obsidure, or emit a verdict.
        #
        # If no projection exists, C278 remains explicitly
        # NOT_APPLICABLE rather than inventing an action.
        # --------------------------------------------------------

        _c277_trace = (
            final_sense_halo.get(
                "integration_trace",
                {},
            )
            if isinstance(
                final_sense_halo,
                dict,
            )
            else {}
        )

        if not isinstance(
            _c277_trace,
            dict,
        ):
            _c277_trace = {}

        _c277_symbolic = (
            _c277_trace.get(
                "symbolic_context",
                {},
            )
        )

        if not isinstance(
            _c277_symbolic,
            dict,
        ):
            _c277_symbolic = {}

        _c278_intent = str(
            _c277_symbolic.get(
                "intent",
                "",
            )
            or ""
        ).strip()

        if not _c278_intent:
            _c278_intent = str(
                pre_action_calibration.get(
                    "intent",
                    "",
                )
                or ""
            ).strip()

        if not _c278_intent:
            _c278_intent = str(
                _ir_intent
                or "unknown"
            ).strip()

        action_meaning_validation = (
            validate_action_meaning(
                calibration_context={
                    "final_sense_halo": (
                        final_sense_halo
                    ),
                    "action_projection": (
                        r.get(
                            "repair_request"
                        )
                    ),
                },
                # Harness branch does not resolve/query memory.
                memory_refs=[],
                symbolic_context={
                    "intent": (
                        _c278_intent
                    ),
                    "source_objective": (
                        str(message or "")
                    ),
                },
            )
        )

        r[
            "action_meaning_validation"
        ] = action_meaning_validation

    except Exception as exc:
        r[
            "repair_request"
        ] = None

        r[
            "repair_route_status"
        ] = (
            "REPAIR_ROUTE_UNAVAILABLE: "
            f"{type(exc).__name__}"
        )

    return r
