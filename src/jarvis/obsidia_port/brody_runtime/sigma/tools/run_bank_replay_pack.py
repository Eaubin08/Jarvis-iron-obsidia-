import argparse
import csv
import json
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

def _env():
    e = os.environ.copy()
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONWARNINGS"] = "ignore"
    return e

def gate_rank(g):
    return GATE_RANK.get(g, 99)

def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))

NORMAL = load("bank_normal.json")
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
            "case_id": f"replay-allow-{i:06d}",
            "family": "allow",
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
            "case_id": f"replay-hold-{i:06d}",
            "family": "hold",
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
        "case_id": f"replay-block-{i:06d}",
        "family": "block",
        "payload": p,
    }

def stable_view(out):
    return {
        "x108_gate": out.get("x108_gate"),
        "severity": out.get("severity"),
        "reason_code": out.get("reason_code"),
        "sigma_pass": bool(out.get("sigma_report", {}).get("pass") is True),
    }

def run_pipeline_once(case, payload_dir):
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
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "error": {
                "returncode": p.returncode,
                "stdout": (p.stdout or "").strip(),
                "stderr": (p.stderr or "").strip(),
            },
        }

    out = json.loads(p.stdout)
    return {
        "ok": True,
        "elapsed_ms": elapsed_ms,
        "raw": out,
        "stable": stable_view(out),
    }

def is_softer(first_gate, second_gate):
    return gate_rank(second_gate) < gate_rank(first_gate)

def replay_one(case, payload_dir):
    first = run_pipeline_once(case, payload_dir)
    second = run_pipeline_once(case, payload_dir)

    if not first["ok"] or not second["ok"]:
        return {
            "case_id": case["case_id"],
            "family": case["family"],
            "ok": False,
            "first_ok": first["ok"],
            "second_ok": second["ok"],
            "first_gate": first.get("stable", {}).get("x108_gate", "ERROR"),
            "second_gate": second.get("stable", {}).get("x108_gate", "ERROR"),
            "gate_match": False,
            "verdict_match": False,
            "reason_match": False,
            "sigma_match": False,
            "replay_stable": False,
            "unsafe_allow": False,
            "softer_drift": False,
            "elapsed_ms": round(first.get("elapsed_ms", 0.0) + second.get("elapsed_ms", 0.0), 3),
            "first_error": first.get("error"),
            "second_error": second.get("error"),
        }

    first_stable = first["stable"]
    second_stable = second["stable"]

    first_gate = first_stable.get("x108_gate")
    second_gate = second_stable.get("x108_gate")

    gate_match = first_gate == second_gate
    verdict_match = first_stable.get("severity") == second_stable.get("severity")
    reason_match = first_stable.get("reason_code") == second_stable.get("reason_code")
    sigma_match = first_stable.get("sigma_pass") == second_stable.get("sigma_pass")
    replay_stable = gate_match and verdict_match and reason_match and sigma_match
    unsafe_allow = first_gate != "ALLOW" and second_gate == "ALLOW"
    softer_drift = is_softer(first_gate, second_gate)

    return {
        "case_id": case["case_id"],
        "family": case["family"],
        "ok": replay_stable,
        "first_ok": True,
        "second_ok": True,
        "first_gate": first_gate,
        "second_gate": second_gate,
        "first_severity": first_stable.get("severity"),
        "second_severity": second_stable.get("severity"),
        "first_reason_code": first_stable.get("reason_code"),
        "second_reason_code": second_stable.get("reason_code"),
        "first_sigma_pass": first_stable.get("sigma_pass"),
        "second_sigma_pass": second_stable.get("sigma_pass"),
        "gate_match": gate_match,
        "verdict_match": verdict_match,
        "reason_match": reason_match,
        "sigma_match": sigma_match,
        "replay_stable": replay_stable,
        "unsafe_allow": unsafe_allow,
        "softer_drift": softer_drift,
        "elapsed_ms": round(first["elapsed_ms"] + second["elapsed_ms"], 3),
        "first_decision_id": first["raw"].get("decision_id"),
        "second_decision_id": second["raw"].get("decision_id"),
        "first_trace_id": first["raw"].get("trace_id"),
        "second_trace_id": second["raw"].get("trace_id"),
        "first_attestation_ref": first["raw"].get("attestation_ref"),
        "second_attestation_ref": second["raw"].get("attestation_ref"),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1000, choices=[1000, 10000, 100000])
    ap.add_argument("--workers", type=int, default=min(6, max(1, (os.cpu_count() or 4))))
    args = ap.parse_args()

    out_dir = ROOT / "artifacts" / "p2_bank_replay" / f"{args.size}_cases_{args.workers}_workers"
    payload_dir = out_dir / "_payloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload_dir.mkdir(parents=True, exist_ok=True)

    cases = [build_case(i) for i in range(args.size)]

    t0 = time.perf_counter()
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(replay_one, case, payload_dir) for case in cases]
        for fut in as_completed(futs):
            rows.append(fut.result())
    total_elapsed_s = round(time.perf_counter() - t0, 3)

    rows.sort(key=lambda r: r["case_id"])

    failures = [r for r in rows if not r["ok"]]
    family_counts = Counter(r["family"] for r in rows)
    first_gate_counts = Counter(r.get("first_gate", "ERROR") for r in rows)
    second_gate_counts = Counter(r.get("second_gate", "ERROR") for r in rows)

    replay_stable_count = sum(1 for r in rows if r.get("replay_stable"))
    replay_gate_match_count = sum(1 for r in rows if r.get("gate_match"))
    replay_verdict_match_count = sum(1 for r in rows if r.get("verdict_match"))
    replay_reason_match_count = sum(1 for r in rows if r.get("reason_match"))
    replay_hash_match_count = sum(1 for r in rows if r.get("sigma_match"))
    unsafe_allow_count = sum(1 for r in rows if r.get("unsafe_allow"))
    softer_drift_count = sum(1 for r in rows if r.get("softer_drift"))

    mean_elapsed_ms = round(sum(r.get("elapsed_ms", 0.0) for r in rows) / len(rows), 3) if rows else 0.0
    throughput_cases_per_s = round(len(rows) / total_elapsed_s, 3) if total_elapsed_s > 0 else 0.0

    report_json = out_dir / "bank_replay_report.json"
    summary_json = out_dir / "bank_replay_summary.json"
    report_csv = out_dir / "bank_replay_report.csv"

    report_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    with report_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case_id","family","ok","first_ok","second_ok",
                "first_gate","second_gate",
                "first_severity","second_severity",
                "first_reason_code","second_reason_code",
                "first_sigma_pass","second_sigma_pass",
                "gate_match","verdict_match","reason_match","sigma_match",
                "replay_stable","unsafe_allow","softer_drift","elapsed_ms",
                "first_decision_id","second_decision_id",
                "first_trace_id","second_trace_id",
                "first_attestation_ref","second_attestation_ref",
                "first_error","second_error",
            ],
        )
        writer.writeheader()
        for r in rows:
            rr = dict(r)
            if "first_error" in rr and isinstance(rr["first_error"], dict):
                rr["first_error"] = json.dumps(rr["first_error"], ensure_ascii=False)
            if "second_error" in rr and isinstance(rr["second_error"], dict):
                rr["second_error"] = json.dumps(rr["second_error"], ensure_ascii=False)
            writer.writerow({k: rr.get(k) for k in writer.fieldnames})

    summary = {
        "size": args.size,
        "workers": args.workers,
        "total_cases": len(rows),
        "failed_cases": len(failures),
        "family_counts": dict(family_counts),
        "first_gate_counts": dict(first_gate_counts),
        "second_gate_counts": dict(second_gate_counts),
        "replay_stable_count": replay_stable_count,
        "replay_gate_match_count": replay_gate_match_count,
        "replay_verdict_match_count": replay_verdict_match_count,
        "replay_reason_match_count": replay_reason_match_count,
        "replay_hash_match_count": replay_hash_match_count,
        "unsafe_allow_count": unsafe_allow_count,
        "softer_drift_count": softer_drift_count,
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