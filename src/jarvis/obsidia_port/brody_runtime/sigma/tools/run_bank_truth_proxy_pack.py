import csv
import json
import subprocess
import sys
import os
import time
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent.parent
PACK_PATH = ROOT / "sigma" / "batches" / "bank_truth_proxy_pack.json"
RUN_PIPELINE = ROOT / "sigma" / "run_pipeline.py"
OUT_DIR = ROOT / "artifacts" / "p2_bank_truth_proxy"

BUSINESS_RANK = {"AUTORISER": 0, "ANALYSER": 1, "BLOQUER": 2}
GATE_RANK = {"ALLOW": 0, "HOLD": 1, "BLOCK": 2}

def _env():
    e = os.environ.copy()
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONWARNINGS"] = "ignore"
    return e

def gate_rank(gate: str) -> int:
    return GATE_RANK.get(gate, 99)

def gap_status(expected_business: str, observed_gate: str) -> str:
    b = BUSINESS_RANK.get(expected_business)
    g = GATE_RANK.get(observed_gate)
    if b is None or g is None:
        return "UNKNOWN_MAPPING"
    if g == b:
        return "MATCH"
    if g > b:
        return "HARDER_THAN_BUSINESS"
    return "SOFTER_THAN_BUSINESS"

def observed_reason_family(reason_code: str) -> str:
    reason = (reason_code or "").upper()
    if "GUARD_ALLOW" in reason:
        return "ALLOW"
    if "TEMPORAL" in reason or "LOCK" in reason or "MATURE" in reason:
        return "TEMPORAL"
    if "CONTRADICTION" in reason:
        return "CONTRADICTION"
    if any(k in reason for k in ["FRAUD", "RISK", "LIMIT", "PRESSURE", "MISMATCH", "CONFLICT", "BLOCK"]):
        return "RISK"
    return "OTHER"

def run_case(item: dict) -> dict:
    payload = item["payload"]
    t0 = time.perf_counter()

    p = subprocess.run(
        [sys.executable, str(RUN_PIPELINE), "bank", json.dumps(payload)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_env(),
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    if p.returncode != 0:
        return {
            "case_id": item["case_id"],
            "family": item["family"],
            "business_expected_decision": item["business_expected_decision"],
            "expected_min_gate": item["expected_min_gate"],
            "expected_reason_family": item["expected_reason_family"],
            "ok": False,
            "elapsed_ms": elapsed_ms,
            "error": p.stderr.strip(),
        }

    data = json.loads(p.stdout)

    gate = data.get("x108_gate")
    sigma_ok = bool(data.get("sigma_report", {}).get("pass") is True)
    floor_ok = gate_rank(gate) >= gate_rank(item["expected_min_gate"])
    gap = gap_status(item["business_expected_decision"], gate)
    reason_family = observed_reason_family(data.get("reason_code"))
    expected_positive = item["business_expected_decision"] in ("ANALYSER", "BLOQUER")
    predicted_positive = gate in ("HOLD", "BLOCK")

    return {
        "case_id": item["case_id"],
        "family": item["family"],
        "business_expected_decision": item["business_expected_decision"],
        "expected_min_gate": item["expected_min_gate"],
        "expected_reason_family": item["expected_reason_family"],
        "observed_reason_family": reason_family,
        "reason_family_match": item["expected_reason_family"] == reason_family or item["expected_reason_family"] == "TEMPORAL_OR_RISK",
        "x108_gate_observed": gate,
        "severity": data.get("severity"),
        "reason_code": data.get("reason_code"),
        "decision_id": data.get("decision_id"),
        "trace_id": data.get("trace_id"),
        "attestation_ref": data.get("attestation_ref"),
        "sigma_ok": sigma_ok,
        "floor_ok": floor_ok,
        "ok": bool(sigma_ok and floor_ok),
        "gap_status": gap,
        "expected_positive": expected_positive,
        "predicted_positive": predicted_positive,
        "elapsed_ms": elapsed_ms,
        "note": item.get("note"),
    }

def main():
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = [run_case(item) for item in pack]
    failures = [r for r in rows if not r["ok"]]

    family_counts = Counter(r["family"] for r in rows)
    gate_counts = Counter(r.get("x108_gate_observed", "ERROR") for r in rows)
    gap_counts = Counter(r.get("gap_status", "UNKNOWN") for r in rows)
    reason_family_counts = Counter(r.get("observed_reason_family", "UNKNOWN") for r in rows)

    tp = sum(1 for r in rows if r.get("expected_positive") and r.get("predicted_positive"))
    tn = sum(1 for r in rows if (not r.get("expected_positive")) and (not r.get("predicted_positive")))
    fp = sum(1 for r in rows if (not r.get("expected_positive")) and r.get("predicted_positive"))
    fn = sum(1 for r in rows if r.get("expected_positive") and (not r.get("predicted_positive")))

    total_elapsed_ms = round(sum(r.get("elapsed_ms", 0.0) for r in rows), 3)
    mean_elapsed_ms = round(total_elapsed_ms / len(rows), 3) if rows else 0.0

    report_json = OUT_DIR / "bank_truth_proxy_report.json"
    summary_json = OUT_DIR / "bank_truth_proxy_summary.json"
    report_csv = OUT_DIR / "bank_truth_proxy_report.csv"

    report_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    with report_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case_id","family","business_expected_decision","expected_min_gate","expected_reason_family",
                "observed_reason_family","reason_family_match","x108_gate_observed","severity","reason_code",
                "gap_status","sigma_ok","floor_ok","ok","expected_positive","predicted_positive","elapsed_ms",
                "decision_id","trace_id","attestation_ref","note"
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in writer.fieldnames})

    summary = {
        "total_cases": len(rows),
        "failed_cases": len(failures),
        "families": dict(family_counts),
        "gate_counts": dict(gate_counts),
        "gap_counts": dict(gap_counts),
        "reason_family_counts": dict(reason_family_counts),
        "confusion_matrix": {
            "TP": tp,
            "TN": tn,
            "FP": fp,
            "FN": fn,
        },
        "total_elapsed_ms": total_elapsed_ms,
        "mean_elapsed_ms": mean_elapsed_ms,
        "report_json": str(report_json),
        "summary_json": str(summary_json),
        "report_csv": str(report_csv),
    }

    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    sys.exit(1 if failures else 0)

if __name__ == "__main__":
    main()
