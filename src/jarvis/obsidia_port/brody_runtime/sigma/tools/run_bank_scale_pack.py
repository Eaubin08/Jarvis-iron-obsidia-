import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy

ROOT = Path(__file__).resolve().parent.parent.parent
RUN_PIPELINE = ROOT / "sigma" / "run_pipeline.py"
EXAMPLES = ROOT / "sigma" / "examples"

GATE_RANK = {"ALLOW": 0, "HOLD": 1, "BLOCK": 2}
BUSINESS_RANK = {"AUTORISER": 0, "ANALYSER": 1, "BLOQUER": 2}

def _env():
    e = os.environ.copy()
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONWARNINGS"] = "ignore"
    return e

def gate_rank(g):
    return GATE_RANK.get(g, 99)

def business_gap(expected_business, observed_gate):
    b = BUSINESS_RANK.get(expected_business)
    g = GATE_RANK.get(observed_gate)
    if b is None or g is None:
        return "UNKNOWN_MAPPING"
    if g == b:
        return "MATCH"
    if g > b:
        return "HARDER_THAN_BUSINESS"
    return "SOFTER_THAN_BUSINESS"

def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))

NORMAL = load("bank_normal.json")
SUSPICIOUS = load("bank_suspicious.json")
BLOCKED = load("bank_blocked.json")

def build_case(i: int):
    lane = i % 3

    if lane == 0:
        p = deepcopy(NORMAL)
        amount = round(120 + (i % 200) * 17.5, 2)
        p["amount"] = amount
        p["historical_avg_amount"] = round(amount * 0.92, 2)
        p["fraud_score"] = round(0.01 + (i % 4) * 0.01, 4)
        p["behavior_shift_score"] = round(0.03 + (i % 5) * 0.01, 4)
        p["urgency_score"] = round(0.04 + (i % 3) * 0.01, 4)
        p["identity_mismatch_score"] = round(0.01 + (i % 4) * 0.01, 4)
        p["narrative_conflict_score"] = round(0.02 + (i % 3) * 0.01, 4)
        p["device_trust_score"] = round(0.96 - (i % 4) * 0.02, 4)
        p["recent_failed_attempts"] = 0
        p["elapsed_s"] = 150.0 + (i % 25)
        p["counterparty_known"] = True
        p["counterparty_age_days"] = 200 + (i % 120)
        p["account_balance"] = 20000.0 + (i % 50) * 150
        p["available_cash"] = 12000.0 + (i % 50) * 90
        p["policy_limit"] = 5000.0
        p["affordability_score"] = 0.95
        p["channel"] = "web"
        p["transaction_type"] = "transfer"
        return {
            "case_id": f"scale-allow-{i:06d}",
            "family": "allow",
            "business_expected_decision": "AUTORISER",
            "expected_min_gate": "ALLOW",
            "payload": p,
        }

    if lane == 1:
        p = deepcopy(NORMAL)
        amount = round(420 + (i % 160) * 21.0, 2)
        p["amount"] = amount
        p["historical_avg_amount"] = round(amount * 0.72, 2)
        p["fraud_score"] = round(0.06 + (i % 5) * 0.01, 4)
        p["behavior_shift_score"] = round(0.10 + (i % 4) * 0.03, 4)
        p["urgency_score"] = round(0.16 + (i % 4) * 0.04, 4)
        p["identity_mismatch_score"] = round(0.08 + (i % 4) * 0.02, 4)
        p["narrative_conflict_score"] = round(0.08 + (i % 4) * 0.02, 4)
        p["device_trust_score"] = round(0.84 - (i % 4) * 0.03, 4)
        p["recent_failed_attempts"] = 1 + (i % 2)
        p["elapsed_s"] = [2.0, 5.0, 20.0, 60.0, 90.0, 107.0][i % 6]
        p["counterparty_known"] = False
        p["counterparty_age_days"] = 1 + (i % 8)
        p["account_balance"] = 12000.0 + (i % 40) * 100
        p["available_cash"] = 7000.0 + (i % 40) * 80
        p["policy_limit"] = 2500.0
        p["affordability_score"] = 0.82
        p["channel"] = "mobile"
        p["transaction_type"] = "transfer"
        return {
            "case_id": f"scale-hold-{i:06d}",
            "family": "hold",
            "business_expected_decision": "ANALYSER",
            "expected_min_gate": "HOLD",
            "payload": p,
        }

    p = deepcopy(BLOCKED)
    amount = round(12000 + (i % 140) * 650.0, 2)
    p["amount"] = amount
    p["historical_avg_amount"] = round(max(80.0, amount * 0.03), 2)
    p["fraud_score"] = round(0.88 + (i % 4) * 0.02, 4)
    p["behavior_shift_score"] = round(0.86 + (i % 4) * 0.02, 4)
    p["urgency_score"] = round(0.90 + (i % 4) * 0.015, 4)
    p["identity_mismatch_score"] = round(0.88 + (i % 4) * 0.02, 4)
    p["narrative_conflict_score"] = round(0.88 + (i % 4) * 0.02, 4)
    p["device_trust_score"] = round(0.08 - (i % 3) * 0.01, 4)
    p["recent_failed_attempts"] = 4 + (i % 5)
    p["elapsed_s"] = 150.0 + (i % 20)
    p["counterparty_known"] = False
    p["counterparty_age_days"] = 0
    p["account_balance"] = max(18000.0, round(amount * 1.05, 2))
    p["available_cash"] = max(12000.0, round(amount * 0.92, 2))
    p["policy_limit"] = 1000.0
    p["affordability_score"] = 0.14
    p["channel"] = "api"
    p["transaction_type"] = "wire"
    return {
        "case_id": f"scale-block-{i:06d}",
        "family": "block",
        "business_expected_decision": "BLOQUER",
        "expected_min_gate": "BLOCK",
        "payload": p,
    }

def run_one(case, payload_dir):
    payload_path = payload_dir / f"{case['case_id']}.json"
    payload_path.write_text(json.dumps(case["payload"], indent=2, ensure_ascii=False), encoding="utf-8")

    t0 = time.perf_counter()
    p = subprocess.run(
        [sys.executable, str(RUN_PIPELINE), "bank", str(payload_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=_env(),
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    if p.returncode != 0:
        return {
            "case_id": case["case_id"],
            "family": case["family"],
            "business_expected_decision": case["business_expected_decision"],
            "expected_min_gate": case["expected_min_gate"],
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "error": {
                "returncode": p.returncode,
                "stdout": (p.stdout or "").strip(),
                "stderr": (p.stderr or "").strip(),
            },
        }

    out = json.loads(p.stdout)
    gate = out.get("x108_gate")
    floor_ok = gate_rank(gate) >= gate_rank(case["expected_min_gate"])
    return {
        "case_id": case["case_id"],
        "family": case["family"],
        "business_expected_decision": case["business_expected_decision"],
        "expected_min_gate": case["expected_min_gate"],
        "x108_gate_observed": gate,
        "severity": out.get("severity"),
        "reason_code": out.get("reason_code"),
        "decision_id": out.get("decision_id"),
        "trace_id": out.get("trace_id"),
        "attestation_ref": out.get("attestation_ref"),
        "gap_status": business_gap(case["business_expected_decision"], gate),
        "sigma_ok": bool(out.get("sigma_report", {}).get("pass") is True),
        "floor_ok": floor_ok,
        "ok": bool(out.get("sigma_report", {}).get("pass") is True and floor_ok),
        "elapsed_ms": elapsed_ms,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1000, choices=[1000, 10000, 100000])
    ap.add_argument("--workers", type=int, default=min(6, max(1, (os.cpu_count() or 4))))
    args = ap.parse_args()

    out_dir = ROOT / "artifacts" / "p2_bank_scale" / f"{args.size}_cases_{args.workers}_workers"
    payload_dir = out_dir / "_payloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload_dir.mkdir(parents=True, exist_ok=True)

    cases = [build_case(i) for i in range(args.size)]

    t0 = time.perf_counter()
    rows = []

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_one, case, payload_dir) for case in cases]
        for fut in as_completed(futs):
            rows.append(fut.result())

    total_elapsed_s = round(time.perf_counter() - t0, 3)
    rows.sort(key=lambda r: r["case_id"])

    failures = [r for r in rows if not r["ok"]]
    family_counts = Counter(r["family"] for r in rows)
    gate_counts = Counter(r.get("x108_gate_observed", "ERROR") for r in rows)
    gap_counts = Counter(r.get("gap_status", "UNKNOWN") for r in rows)

    mean_elapsed_ms = round(sum(r.get("elapsed_ms", 0.0) for r in rows) / len(rows), 3) if rows else 0.0
    throughput_cases_per_s = round(len(rows) / total_elapsed_s, 3) if total_elapsed_s > 0 else 0.0

    report_json = out_dir / "bank_scale_report.json"
    summary_json = out_dir / "bank_scale_summary.json"
    report_csv = out_dir / "bank_scale_report.csv"

    report_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    with report_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case_id","family","business_expected_decision","expected_min_gate","x108_gate_observed",
                "severity","reason_code","gap_status","sigma_ok","floor_ok","ok","elapsed_ms",
                "decision_id","trace_id","attestation_ref","error"
            ],
        )
        writer.writeheader()
        for r in rows:
            rr = dict(r)
            if "error" in rr and isinstance(rr["error"], dict):
                rr["error"] = json.dumps(rr["error"], ensure_ascii=False)
            writer.writerow({k: rr.get(k) for k in writer.fieldnames})

    summary = {
        "size": args.size,
        "workers": args.workers,
        "total_cases": len(rows),
        "failed_cases": len(failures),
        "family_counts": dict(family_counts),
        "gate_counts": dict(gate_counts),
        "gap_counts": dict(gap_counts),
        "total_elapsed_s": total_elapsed_s,
        "mean_elapsed_ms": mean_elapsed_ms,
        "throughput_cases_per_s": throughput_cases_per_s,
        "report_json": str(report_json),
        "summary_json": str(summary_json),
        "report_csv": str(report_csv),
    }

    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    sys.exit(1 if failures else 0)

if __name__ == "__main__":
    main()
