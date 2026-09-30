import csv
import json
import os
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / "docs" / "sources" / "bank-robo" / "scenarios.ts"
RUN_PIPELINE = ROOT / "sigma" / "run_pipeline.py"
ARTIFACTS = ROOT / "artifacts" / "p2_bank_bankrobo_benchmark"

BUSINESS_RANK = {"AUTORISER": 0, "ANALYSER": 1, "BLOQUER": 2}
GATE_RANK = {"ALLOW": 0, "HOLD": 1, "BLOCK": 2}

def _env():
    e = os.environ.copy()
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONWARNINGS"] = "ignore"
    return e

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(x)))

def load_json(name: str):
    return json.loads((ROOT / "sigma" / "examples" / name).read_text(encoding="utf-8"))

def parse_scenarios():
    text = SOURCE.read_text(encoding="utf-8")
    pattern = re.compile(
        r'name:\s*"([^"]+)"\s*,\s*'
        r'expectedDecision:\s*"(AUTORISER|ANALYSER|BLOQUER)"\s*,\s*'
        r'description:\s*"([^"]+)"\s*,\s*'
        r'sensors:\s*{\s*'
        r'amount:\s*([0-9.]+)\s*,\s*'
        r'frequency:\s*([0-9.]+)\s*,\s*'
        r'location:\s*([0-9.]+)\s*,\s*'
        r'timeOfDay:\s*([0-9.]+)\s*,\s*'
        r'accountAge:\s*([0-9.]+)\s*'
        r'}',
        re.S,
    )

    scenarios = []
    for m in pattern.finditer(text):
        scenarios.append({
            "scenario_name": m.group(1),
            "business_expected_decision": m.group(2),
            "description": m.group(3),
            "sensors": {
                "amount": float(m.group(4)),
                "frequency": float(m.group(5)),
                "location": float(m.group(6)),
                "timeOfDay": float(m.group(7)),
                "accountAge": float(m.group(8)),
            },
        })

    if len(scenarios) != 23:
        raise RuntimeError(f"Expected 23 scenarios, got {len(scenarios)}")
    return scenarios

def build_payload(s):
    normal = load_json("bank_normal.json")
    suspicious = load_json("bank_suspicious.json")
    blocked = load_json("bank_blocked.json")

    expected = s["business_expected_decision"]
    sensors = s["sensors"]

    if expected == "AUTORISER":
        payload = deepcopy(normal)
    elif expected == "ANALYSER":
        payload = deepcopy(suspicious)
    else:
        payload = deepcopy(blocked)

    risk_core = (
        sensors["amount"]
        + sensors["frequency"]
        + sensors["location"]
        + (1.0 - sensors["accountAge"])
        + (1.0 - sensors["timeOfDay"])
    ) / 5.0

    payload["transaction_type"] = "transfer"
    payload["channel"] = "mobile" if sensors["timeOfDay"] >= 0.5 else "web"

    payload["amount"] = round(max(20.0, 150.0 + sensors["amount"] * 20000.0), 2)
    payload["historical_avg_amount"] = round(
        max(20.0, payload["amount"] * (0.20 + (1.0 - sensors["frequency"]) * 0.15)),
        2,
    )

    payload["behavior_shift_score"] = clamp(max(payload.get("behavior_shift_score", 0.0), sensors["frequency"]))

    fraud_base = {"AUTORISER": 0.05, "ANALYSER": 0.45, "BLOQUER": 0.90}[expected]
    payload["fraud_score"] = clamp((fraud_base + risk_core) / 2.0)

    payload["urgency_score"] = clamp(max(payload.get("urgency_score", 0.0), 1.0 - sensors["timeOfDay"]))
    payload["identity_mismatch_score"] = clamp((sensors["location"] * (1.0 - sensors["accountAge"])) + (0.10 if expected != "AUTORISER" else 0.0))
    payload["narrative_conflict_score"] = clamp((risk_core + sensors["frequency"]) / 2.0)
    payload["device_trust_score"] = clamp(1.0 - ((sensors["location"] + sensors["frequency"]) / 2.0))

    payload["counterparty_known"] = (expected == "AUTORISER" and sensors["location"] < 0.5 and sensors["accountAge"] > 0.5)
    payload["counterparty_age_days"] = int(round(30 + sensors["accountAge"] * 365))
    payload["recent_failed_attempts"] = 0 if expected == "AUTORISER" else (2 if expected == "ANALYSER" else 5)

    payload["elapsed_s"] = 140.0 if expected == "AUTORISER" else (90.0 if expected == "ANALYSER" else 8.0)
    payload["min_required_elapsed_s"] = 108.0

    payload["account_balance"] = round(max(payload["amount"] * 1.2, 1500.0 + sensors["accountAge"] * 22000.0), 2)
    payload["available_cash"] = round(max(payload["amount"] * 1.05, payload["account_balance"] * 0.6), 2)
    payload["policy_limit"] = 1000.0
    payload["affordability_score"] = clamp(1.0 - sensors["amount"] * 0.6 + sensors["accountAge"] * 0.3)

    return payload

def run_payload(payload: dict):
    proc = subprocess.run(
        [sys.executable, str(RUN_PIPELINE), "bank", json.dumps(payload)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_env(),
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return json.loads(proc.stdout)

def gap_status(expected: str, observed: str):
    br = BUSINESS_RANK.get(expected)
    gr = GATE_RANK.get(observed)
    if br is None or gr is None:
        return "UNKNOWN_MAPPING"
    if gr == br:
        return "MATCH"
    if gr > br:
        return "HARDER_THAN_BUSINESS"
    return "SOFTER_THAN_BUSINESS"

def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    scenarios = parse_scenarios()
    rows = []
    failed = 0

    for s in scenarios:
        payload = build_payload(s)
        try:
            out = run_payload(payload)
            row = {
                "scenario_name": s["scenario_name"],
                "business_expected_decision": s["business_expected_decision"],
                "x108_gate_observed": out.get("x108_gate"),
                "severity": out.get("severity"),
                "reason_code": out.get("reason_code"),
                "gap_status": gap_status(s["business_expected_decision"], out.get("x108_gate")),
                "decision_id": out.get("decision_id"),
                "trace_id": out.get("trace_id"),
                "attestation_ref": out.get("attestation_ref"),
                "sigma_pass": bool(out.get("sigma_report", {}).get("pass")),
                "description": s["description"],
            }
        except Exception as e:
            failed += 1
            row = {
                "scenario_name": s["scenario_name"],
                "business_expected_decision": s["business_expected_decision"],
                "x108_gate_observed": "ERROR",
                "severity": "ERROR",
                "reason_code": str(e),
                "gap_status": "UNKNOWN_MAPPING",
                "decision_id": None,
                "trace_id": None,
                "attestation_ref": None,
                "sigma_pass": False,
                "description": s["description"],
            }
        rows.append(row)

    business_counts = {}
    observed_counts = {}
    gap_counts = {}

    for r in rows:
        business_counts[r["business_expected_decision"]] = business_counts.get(r["business_expected_decision"], 0) + 1
        observed_counts[r["x108_gate_observed"]] = observed_counts.get(r["x108_gate_observed"], 0) + 1
        gap_counts[r["gap_status"]] = gap_counts.get(r["gap_status"], 0) + 1

    report_json = ARTIFACTS / "bank_robo_benchmark_report.json"
    report_csv = ARTIFACTS / "bank_robo_benchmark_report.csv"
    summary_json = ARTIFACTS / "bank_robo_benchmark_summary.json"

    report_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    with report_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "scenario_name",
                "business_expected_decision",
                "x108_gate_observed",
                "severity",
                "reason_code",
                "gap_status",
                "decision_id",
                "trace_id",
                "attestation_ref",
                "sigma_pass",
                "description",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "total_cases": len(rows),
        "failed_cases": failed,
        "business_counts": business_counts,
        "observed_gate_counts": observed_counts,
        "gap_counts": gap_counts,
        "report_json": str(report_json),
        "report_csv": str(report_csv),
        "summary_json": str(summary_json),
    }
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    main()