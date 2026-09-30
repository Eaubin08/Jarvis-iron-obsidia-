#!/usr/bin/env python3
"""
OS4 Canonical Agent Pipeline CLI Bridge - P1 public
Usage:
  python sigma/run_pipeline.py <domain> <json_state_or_json_file>
"""
import sys
import json
import dataclasses
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sigma.contracts import TradingState, BankState, EcomState, GpsDefenseAviationState, ToolingBuildState
from sigma.protocols import run_trading_pipeline, run_bank_pipeline, run_ecom_pipeline, run_gps_defense_aviation_pipeline, run_tooling_build_pipeline
from sigma.obsidia_sigma_v130 import ObsidiaSigmaMonitor


REQUIRED_BANK_FIELDS = {
    "transaction_type",
    "amount",
    "channel",
    "counterparty_known",
    "counterparty_age_days",
    "account_balance",
    "available_cash",
    "historical_avg_amount",
    "behavior_shift_score",
    "fraud_score",
    "policy_limit",
    "affordability_score",
    "urgency_score",
    "identity_mismatch_score",
    "narrative_conflict_score",
    "device_trust_score",
}

ALLOWED_BANK_FIELDS = {f.name for f in dataclasses.fields(BankState)}


def load_state(arg: str) -> dict:
    """
    Accept both:
      - direct JSON payload passed as argv[2]
      - path to a JSON file

    CI Sigma tests and fuzz runners pass full JSON as a command argument.
    JSON must be parsed before trying Path(arg).exists(), otherwise Linux can
    raise OSError [Errno 36] File name too long on large JSON strings.
    """
    raw = str(arg)

    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("JSON state must be an object")
        return parsed
    except json.JSONDecodeError:
        pass

    try:
        p = Path(raw)
        if p.exists() and p.is_file():
            parsed = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("JSON file must contain an object")
            return parsed
    except OSError:
        pass

    raise ValueError("Input is neither a JSON object nor a readable JSON file")

BANK_STRING_FIELDS = {
    "transaction_type",
    "channel",
}

BANK_BOOL_FIELDS = {
    "counterparty_known",
}

BANK_INT_FIELDS = {
    "counterparty_age_days",
    "recent_failed_attempts",
}

BANK_NUMERIC_FIELDS = {
    "amount",
    "account_balance",
    "available_cash",
    "historical_avg_amount",
    "behavior_shift_score",
    "fraud_score",
    "policy_limit",
    "affordability_score",
    "urgency_score",
    "identity_mismatch_score",
    "narrative_conflict_score",
    "device_trust_score",
    "elapsed_s",
    "min_required_elapsed_s",
}

BANK_UNIT_SCORE_FIELDS = {
    "behavior_shift_score",
    "fraud_score",
    "affordability_score",
    "urgency_score",
    "identity_mismatch_score",
    "narrative_conflict_score",
    "device_trust_score",
}

BANK_NON_NEGATIVE_FIELDS = {
    "amount",
    "account_balance",
    "available_cash",
    "historical_avg_amount",
    "policy_limit",
    "elapsed_s",
    "min_required_elapsed_s",
    "counterparty_age_days",
    "recent_failed_attempts",
}


def _is_plain_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _require_number(state_data: dict, field: str) -> None:
    value = state_data.get(field)

    if not _is_plain_number(value):
        raise ValueError(f"Invalid bank field type: {field} must be a finite number")

    numeric = float(value)

    if field in BANK_NON_NEGATIVE_FIELDS and numeric < 0:
        raise ValueError(f"Invalid bank field range: {field} must be >= 0")

    if field in BANK_UNIT_SCORE_FIELDS and not (0.0 <= numeric <= 1.0):
        raise ValueError(f"Invalid bank field range: {field} must be between 0 and 1")


def _require_int(state_data: dict, field: str) -> None:
    value = state_data.get(field)

    if isinstance(value, bool):
        raise ValueError(f"Invalid bank field type: {field} must be an integer")

    if isinstance(value, int):
        integer = value
    elif isinstance(value, float) and value.is_integer():
        integer = int(value)
    else:
        raise ValueError(f"Invalid bank field type: {field} must be an integer")

    if field in BANK_NON_NEGATIVE_FIELDS and integer < 0:
        raise ValueError(f"Invalid bank field range: {field} must be >= 0")


def validate_bank_payload(state_data: dict) -> None:
    if not isinstance(state_data, dict):
        raise ValueError("Bank payload must be a JSON object")

    missing = sorted(REQUIRED_BANK_FIELDS - set(state_data.keys()))
    if missing:
        raise ValueError(f"Missing required bank fields: {', '.join(missing)}")

    unknown = sorted(set(state_data.keys()) - ALLOWED_BANK_FIELDS)
    if unknown:
        raise ValueError(f"Unknown bank fields: {', '.join(unknown)}")

    for field in BANK_STRING_FIELDS:
        value = state_data.get(field)
        if not isinstance(value, str):
            raise ValueError(f"Invalid bank field type: {field} must be a string")

    for field in BANK_BOOL_FIELDS:
        value = state_data.get(field)
        if not isinstance(value, bool):
            raise ValueError(f"Invalid bank field type: {field} must be a boolean")

    for field in BANK_INT_FIELDS:
        if field in state_data:
            _require_int(state_data, field)

    for field in BANK_NUMERIC_FIELDS:
        if field in state_data:
            _require_number(state_data, field)



def apply_sigma(result_dict: dict, sigma: ObsidiaSigmaMonitor) -> dict:
    """
    Apply Sigma as an explicit post-Guard veto layer.

    Boundary:
      - Sigma never authorizes.
      - Sigma never promotes HOLD/BLOCK to ACT/ALLOW.
      - Sigma may only add evidence or downgrade to HOLD_STABILITY_ALERT.
    """
    pre_sigma_market_verdict = result_dict.get("market_verdict")
    pre_sigma_severity = result_dict.get("severity", "S0")

    step_report = sigma.evaluate_step(
        severity=pre_sigma_severity,
        risks=result_dict.get("risk_flags", []),
        contras=result_dict.get("contradictions", []),
    )
    sigma_report = sigma.export_to_proofkit()
    stability = sigma_report["V18_9_sigma_stability"]["status"]

    result_dict["pre_sigma_market_verdict"] = pre_sigma_market_verdict
    result_dict["pre_sigma_severity"] = pre_sigma_severity
    result_dict["sigma_override_policy"] = "POST_GUARD_VETO_ONLY"

    if stability == "FAIL":
        result_dict["market_verdict"] = "HOLD_STABILITY_ALERT"
        result_dict["severity"] = "S4"
        result_dict["sigma_override"] = True
        result_dict["sigma_authority"] = "VETO_ONLY"
    else:
        result_dict["sigma_override"] = False
        result_dict["sigma_authority"] = "REPORT_ONLY"

    result_dict["sigma_step"] = step_report
    result_dict["sigma_report"] = sigma_report["V18_9_sigma_stability"]
    return result_dict

def envelope_to_dict(env) -> dict:
    return dataclasses.asdict(env)


def _extract_trusted_action_metadata(result_dict: dict, caller_meta: dict) -> dict:
    """
    Extract action metadata only from canonical/trusted pipeline output.
    Caller payload metadata is NOT sovereign — never authorizes.
    DECISION_AUTHORITY=KX108_ONLY  ACT=NO
    """
    for source_name, source in [
        ("canonical_decision_envelope", result_dict.get("canonical_decision_envelope")),
        ("kernel_decision", result_dict.get("kernel_decision")),
        ("verified_action_context", result_dict.get("verified_action_context")),
        ("trusted_action_metadata", result_dict.get("trusted_action_metadata")),
        ("raw_engine_trusted", (result_dict.get("raw_engine") or {}).get("trusted_action_metadata")),
    ]:
        if isinstance(source, dict) and source:
            return {
                "trusted": True,
                "source": source_name,
                "irreversible_trusted": source.get("irreversible"),
                "action_type_trusted": source.get("action_type"),
                "intent_trusted": source.get("intent"),
            }
    return {
        "trusted": False,
        "source": "NONE",
        "reason": "MISSING_TRUSTED_ACTION_METADATA",
        "irreversible_trusted": None,
        "action_type_trusted": None,
        "intent_trusted": None,
    }


def _apply_p3t9b_rule(result_dict: dict, caller_meta: dict, meta_keys: tuple) -> dict:
    """
    P3T9B1 hardened: fail-safe HOLD when trusted action metadata absent.
    Caller metadata is untrusted — never used to authorize or bypass.
    DECISION_AUTHORITY=KX108_ONLY  ACT=NO
    """
    _trusted = _extract_trusted_action_metadata(result_dict, caller_meta)

    _domain_trading = result_dict.get("domain") == "trading"
    _gate_allow = result_dict.get("x108_gate") == "ALLOW"
    _verdict_review = result_dict.get("market_verdict") == "REVIEW"

    if _trusted["trusted"]:
        _should_demote = (
            _domain_trading
            and _gate_allow
            and _verdict_review
            and _trusted.get("irreversible_trusted") is True
            and _trusted.get("action_type_trusted") == "trade"
            and _trusted.get("intent_trusted") == "trade_execution_review"
        )
        _caller_ignored = False
        _demoted_missing = False
        _p3t9b_rc = "IRREVERSIBLE_TRADE_REVIEW_REQUIRES_HOLD" if _should_demote else "P3T9B_NOT_APPLIED"
    else:
        # Fail-safe: no trusted metadata → HOLD on any trading ALLOW+REVIEW
        # (caller cannot bypass by omitting/forging irreversible/action_type/intent)
        _should_demote = _domain_trading and _gate_allow and _verdict_review
        _caller_ignored = True
        _demoted_missing = _should_demote
        _p3t9b_rc = "P3T9B_TRUSTED_METADATA_REQUIRED" if _should_demote else "P3T9B_NOT_APPLIED"

    if _should_demote:
        result_dict["pre_p3t9b_x108_gate"] = result_dict.get("x108_gate")
        result_dict["pre_p3t9b_reason_code"] = result_dict.get("reason_code")
        result_dict["x108_gate"] = "HOLD"
        result_dict["reason_code"] = _p3t9b_rc
        result_dict["x108_reason"] = _p3t9b_rc
        result_dict["severity"] = "S2"
        result_dict["business_semantic_verdict"] = "HOLD_REVIEW"
        result_dict["p3t9b_semantic_rule_applied"] = True
        result_dict["p3t9b_semantic_transition"] = "ALLOW_TO_HOLD"
        if not isinstance(result_dict.get("metrics"), dict):
            result_dict["metrics"] = {}
        _m = result_dict["metrics"].get("action_metadata")
        if not isinstance(_m, dict):
            _m = {}
            result_dict["metrics"]["action_metadata"] = _m
        _m["business_semantic_verdict"] = "HOLD_REVIEW"
        _m["p3t9b_semantic_rule"] = _p3t9b_rc

    result_dict["p3t9b_trusted_metadata_available"] = _trusted["trusted"]
    result_dict["p3t9b_trusted_metadata_source"] = _trusted["source"]
    result_dict["p3t9b_caller_metadata_ignored"] = _caller_ignored
    result_dict["p3t9b_demoted_for_missing_trusted_metadata"] = _demoted_missing
    result_dict["p3t9b_reason_code"] = _p3t9b_rc
    result_dict["p3t9b_caller_action_meta_untrusted"] = {
        _k: caller_meta.get(_k) for _k in meta_keys
    }
    return result_dict


REQUIRED_TOOLING_BUILD_FIELDS = {
    "session_id",
    "objective",
    "base_sha",
    "manifest_hash",
    "human_approval_status",
    "worktree_isolated",
    "branch_isolated",
    "tests_results",
    "gates_results",
    "commit_status",
    "push_status",
    "merge_status",
    "auto_commit_disabled",
    "auto_push_disabled",
    "auto_merge_disabled",
    "decision_authority",
}

ALLOWED_TOOLING_BUILD_FIELDS = {
    # Identification
    "session_id", "objective", "base_sha", "manifest_hash", "diff_hash",
    # Scope
    "approved_scope", "actual_touched_files", "new_files", "deleted_files",
    # Statuts
    "protected_scope_status", "human_approval_status", "obsidure_status",
    # Isolation
    "worktree_isolated", "branch_isolated",
    # Garde-fous
    "auto_commit_disabled", "auto_push_disabled", "auto_merge_disabled",
    # Tests/gates
    "tests_results", "gates_results", "first_failure",
    # Git ops
    "commit_status", "push_status", "merge_status",
    # Pré-conditions
    "unknowns", "contradictions", "risk_flags",
    # Autorité
    "decision_authority",
}

TOOLING_BUILD_BOOL_FIELDS = {
    "worktree_isolated", "branch_isolated",
    "auto_commit_disabled", "auto_push_disabled", "auto_merge_disabled",
}

TOOLING_BUILD_STRING_FIELDS = {
    "session_id", "objective", "base_sha", "manifest_hash", "diff_hash",
    "protected_scope_status", "human_approval_status", "obsidure_status",
    "tests_results", "gates_results", "first_failure",
    "commit_status", "push_status", "merge_status",
    "decision_authority",
}

TOOLING_BUILD_LIST_FIELDS = {
    "approved_scope", "actual_touched_files", "new_files", "deleted_files",
    "unknowns", "contradictions", "risk_flags",
}


def validate_tooling_build_payload(state_data: dict) -> None:
    if not isinstance(state_data, dict):
        raise ValueError("tooling_build payload must be a JSON object")

    missing = sorted(REQUIRED_TOOLING_BUILD_FIELDS - set(state_data.keys()))
    if missing:
        raise ValueError(f"Missing required tooling_build fields: {', '.join(missing)}")

    unknown = sorted(set(state_data.keys()) - ALLOWED_TOOLING_BUILD_FIELDS)
    if unknown:
        raise ValueError(f"Unknown tooling_build fields: {', '.join(unknown)}")

    for f in TOOLING_BUILD_BOOL_FIELDS:
        if f in state_data and not isinstance(state_data[f], bool):
            raise ValueError(f"Invalid tooling_build field type: {f} must be a boolean")

    for f in TOOLING_BUILD_STRING_FIELDS:
        if f in state_data and not isinstance(state_data[f], str):
            raise ValueError(f"Invalid tooling_build field type: {f} must be a string")

    for f in TOOLING_BUILD_LIST_FIELDS:
        val = state_data.get(f)
        if val is not None and not isinstance(val, list):
            raise ValueError(f"Invalid tooling_build field type: {f} must be a list")

    if state_data.get("decision_authority") != "KX108_ONLY":
        raise ValueError("Invalid tooling_build field: decision_authority must be 'KX108_ONLY'")


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: run_pipeline.py <domain> <json_state_or_json_file>"}), file=sys.stderr)
        sys.exit(1)

    domain = sys.argv[1].lower()
    try:
        state_data = load_state(sys.argv[2])
    except Exception as e:
        print(json.dumps({"error": f"Invalid JSON input: {e}"}), file=sys.stderr)
        sys.exit(1)

    _P3T8B_META_KEYS = (
        "irreversible", "action_type", "intent",
        "action_scope", "can_execute_real_action", "business_semantic_verdict",
    )
    _p3t8b_action_meta: dict = {}
    for _k in _P3T8B_META_KEYS:
        if _k in state_data:
            _p3t8b_action_meta[_k] = state_data.pop(_k)
    for _nested_key in ("action", "action_metadata"):
        _nested = state_data.pop(_nested_key, None)
        if isinstance(_nested, dict):
            for _k in _P3T8B_META_KEYS:
                if _k in _nested and _k not in _p3t8b_action_meta:
                    _p3t8b_action_meta[_k] = _nested[_k]

    sigma = ObsidiaSigmaMonitor(config_path=str(ROOT / "sigma" / "sigma_config.json"))

    try:
        if domain == "trading":
            state = TradingState(**state_data)
            result = run_trading_pipeline(state)
        elif domain == "bank":
            validate_bank_payload(state_data)
            state = BankState(**state_data)
            result = run_bank_pipeline(state)
        elif domain == "ecom":
            state = EcomState(**state_data)
            result = run_ecom_pipeline(state)
        elif domain == "gps_defense_aviation":
            state = GpsDefenseAviationState(**state_data)
            result = run_gps_defense_aviation_pipeline(state)
        elif domain == "tooling_build":
            state_data.pop("domain", None)
            validate_tooling_build_payload(state_data)
            state = ToolingBuildState(**state_data)
            result = run_tooling_build_pipeline(state)
        else:
            print(json.dumps({"error": f"Unknown domain: {domain}. Use trading|bank|ecom|gps_defense_aviation|tooling_build"}), file=sys.stderr)
            sys.exit(1)

        result_dict = envelope_to_dict(result)
        for _k in _P3T8B_META_KEYS:
            result_dict.setdefault(_k, _p3t8b_action_meta.get(_k))
        if isinstance(result_dict.get("metrics"), dict):
            result_dict["metrics"].setdefault(
                "action_metadata",
                {_k: _p3t8b_action_meta.get(_k) for _k in _P3T8B_META_KEYS},
            )
        # P3T9B1_HOLD_REVIEW_RULE — hardened with canonical metadata check
        # Safety demotion only; preserves BLOCK > HOLD > ALLOW; no Guard/consensus mutation.
        result_dict = _apply_p3t9b_rule(result_dict, _p3t8b_action_meta, _P3T8B_META_KEYS)

        result_dict = apply_sigma(result_dict, sigma)
        print(json.dumps(result_dict, ensure_ascii=False))
    except (TypeError, ValueError) as e:
        print(json.dumps({"error": f"State validation error: {e}"}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Pipeline error: {e}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
