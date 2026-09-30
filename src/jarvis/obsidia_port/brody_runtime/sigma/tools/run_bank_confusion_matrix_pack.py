import csv
import json
import subprocess
import sys
import os
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "artifacts" / "p2_bank_confusion_matrix"

TRUTH_RUNNER = ROOT / "sigma" / "tools" / "run_bank_truth_proxy_pack.py"
REG_RUNNER = ROOT / "sigma" / "tools" / "run_bank_regulatory_proxy_pack.py"
BENCH_RUNNER = ROOT / "sigma" / "tools" / "run_bank_robo_scenario_benchmark.py"

TRUTH_REPORT = ROOT / "artifacts" / "p2_bank_truth_proxy" / "bank_truth_proxy_report.json"
REG_REPORT = ROOT / "artifacts" / "p2_bank_regulatory_proxy" / "bank_regulatory_proxy_report.json"
BENCH_REPORT = ROOT / "artifacts" / "p2_bank_bankrobo_benchmark" / "bank_robo_benchmark_report.json"

BUSINESS_POSITIVE = {"ANALYSER", "BLOQUER"}
GATE_POSITIVE = {"HOLD", "BLOCK"}

def _env():
    e = os.environ.copy()
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONWARNINGS"] = "ignore"
    return e

def run_json(cmd):
    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        env=_env(),
    )
    if p.returncode != 0:
        raise SystemExit(f"Runner failed: {' '.join(cmd)}\\nSTDOUT:\\n{p.stdout}\\nSTDERR:\\n{p.stderr}")
    try:
        return json.loads(p.stdout)
    except Exception as e:
        raise SystemExit(f"Runner output is not valid JSON for {' '.join(cmd)}\\n{e}\\nSTDOUT:\\n{p.stdout}")

def infer_reason_family(reason_code, observed_reason_family):
    if observed_reason_family:
        return observed_reason_family
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

def normalize_truth(rows):
    out = []
    for r in rows:
        biz = r.get("business_expected_decision")
        gate = r.get("x108_gate_observed")
        out.append({
            "corpus": "truth_proxy",
            "case_id": r.get("case_id"),
            "family": r.get("family"),
            "zone": None,
            "scenario_name": None,
            "business_expected_decision": biz,
            "x108_gate_observed": gate,
            "severity": r.get("severity"),
            "reason_code": r.get("reason_code"),
            "reason_family": infer_reason_family(r.get("reason_code"), r.get("observed_reason_family")),
            "gap_status": r.get("gap_status"),
            "ok": bool(r.get("ok", False)),
            "expected_positive": biz in BUSINESS_POSITIVE,
            "predicted_positive": gate in GATE_POSITIVE,
            "decision_id": r.get("decision_id"),
            "trace_id": r.get("trace_id"),
            "attestation_ref": r.get("attestation_ref"),
            "note": r.get("note"),
        })
    return out

def normalize_reg(rows):
    out = []
    for r in rows:
        biz = r.get("business_expected_decision")
        gate = r.get("x108_gate_observed")
        out.append({
            "corpus": "regulatory_proxy",
            "case_id": r.get("case_id"),
            "family": r.get("family"),
            "zone": r.get("zone"),
            "scenario_name": None,
            "business_expected_decision": biz,
            "x108_gate_observed": gate,
            "severity": r.get("severity"),
            "reason_code": r.get("reason_code"),
            "reason_family": infer_reason_family(r.get("reason_code"), r.get("observed_reason_family")),
            "gap_status": r.get("gap_status"),
            "ok": bool(r.get("ok", False)),
            "expected_positive": biz in BUSINESS_POSITIVE,
            "predicted_positive": gate in GATE_POSITIVE,
            "decision_id": r.get("decision_id"),
            "trace_id": r.get("trace_id"),
            "attestation_ref": r.get("attestation_ref"),
            "note": r.get("note"),
        })
    return out

def normalize_benchmark(rows):
    out = []
    for r in rows:
        biz = r.get("business_expected_decision")
        gate = r.get("x108_gate_observed")
        out.append({
            "corpus": "bank_robo_benchmark",
            "case_id": r.get("case_id") or r.get("scenario_name"),
            "family": "bank-robo",
            "zone": None,
            "scenario_name": r.get("scenario_name"),
            "business_expected_decision": biz,
            "x108_gate_observed": gate,
            "severity": r.get("severity"),
            "reason_code": r.get("reason_code"),
            "reason_family": infer_reason_family(r.get("reason_code"), r.get("observed_reason_family")),
            "gap_status": r.get("gap_status"),
            "ok": bool(r.get("ok", True)),
            "expected_positive": biz in BUSINESS_POSITIVE,
            "predicted_positive": gate in GATE_POSITIVE,
            "decision_id": r.get("decision_id"),
            "trace_id": r.get("trace_id"),
            "attestation_ref": r.get("attestation_ref"),
            "note": r.get("description") or r.get("note"),
        })
    return out

def confusion(rows):
    tp = sum(1 for r in rows if r["expected_positive"] and r["predicted_positive"])
    tn = sum(1 for r in rows if (not r["expected_positive"]) and (not r["predicted_positive"]))
    fp = sum(1 for r in rows if (not r["expected_positive"]) and r["predicted_positive"])
    fn = sum(1 for r in rows if r["expected_positive"] and (not r["predicted_positive"]))
    return {"TP": tp, "TN": tn, "FP": fp, "FN": fn}

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    truth_summary = run_json([sys.executable, str(TRUTH_RUNNER)])
    reg_summary = run_json([sys.executable, str(REG_RUNNER)])
    bench_summary = run_json([sys.executable, str(BENCH_RUNNER)])

    truth_rows = json.loads(TRUTH_REPORT.read_text(encoding="utf-8"))
    reg_rows = json.loads(REG_REPORT.read_text(encoding="utf-8"))
    bench_rows = json.loads(BENCH_REPORT.read_text(encoding="utf-8"))

    merged = []
    merged.extend(normalize_truth(truth_rows))
    merged.extend(normalize_reg(reg_rows))
    merged.extend(normalize_benchmark(bench_rows))

    failures = [r for r in merged if not r["ok"]]

    corpus_counts = Counter(r["corpus"] for r in merged)
    gate_counts = Counter(r.get("x108_gate_observed", "UNKNOWN") for r in merged)
    gap_counts = Counter(r.get("gap_status", "UNKNOWN") for r in merged)
    reason_family_counts = Counter(r.get("reason_family", "UNKNOWN") for r in merged)

    by_corpus = {}
    for corpus in corpus_counts:
        rows = [r for r in merged if r["corpus"] == corpus]
        by_corpus[corpus] = {
            "total_cases": len(rows),
            "gate_counts": dict(Counter(r.get("x108_gate_observed", "UNKNOWN") for r in rows)),
            "gap_counts": dict(Counter(r.get("gap_status", "UNKNOWN") for r in rows)),
            "confusion_matrix": confusion(rows),
        }

    harder_cases = [r for r in merged if r.get("gap_status") == "HARDER_THAN_BUSINESS"]
    softer_cases = [r for r in merged if r.get("gap_status") == "SOFTER_THAN_BUSINESS"]

    total = len(merged)
    global_cm = confusion(merged)

    report_json = OUT_DIR / "bank_confusion_matrix_report.json"
    summary_json = OUT_DIR / "bank_confusion_matrix_summary.json"
    report_csv = OUT_DIR / "bank_confusion_matrix_report.csv"

    report_json.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

    with report_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "corpus","case_id","scenario_name","family","zone","business_expected_decision","x108_gate_observed",
                "severity","reason_code","reason_family","gap_status","ok","expected_positive","predicted_positive",
                "decision_id","trace_id","attestation_ref","note"
            ],
        )
        writer.writeheader()
        for r in merged:
            writer.writerow({k: r.get(k) for k in writer.fieldnames})

    summary = {
        "total_cases": total,
        "failed_cases": len(failures),
        "corpus_counts": dict(corpus_counts),
        "gate_counts": dict(gate_counts),
        "gap_counts": dict(gap_counts),
        "reason_family_counts": dict(reason_family_counts),
        "confusion_matrix_global": global_cm,
        "confusion_matrix_by_corpus": by_corpus,
        "harder_cases": len(harder_cases),
        "softer_cases": len(softer_cases),
        "match_rate": round(gap_counts.get("MATCH", 0) / total, 6) if total else 0.0,
        "harder_rate": round(gap_counts.get("HARDER_THAN_BUSINESS", 0) / total, 6) if total else 0.0,
        "softer_rate": round(gap_counts.get("SOFTER_THAN_BUSINESS", 0) / total, 6) if total else 0.0,
        "source_summaries": {
            "truth_proxy": truth_summary,
            "regulatory_proxy": reg_summary,
            "bank_robo_benchmark": bench_summary,
        },
        "report_json": str(report_json),
        "summary_json": str(summary_json),
        "report_csv": str(report_csv),
    }

    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    sys.exit(1 if failures else 0)

if __name__ == "__main__":
    main()
