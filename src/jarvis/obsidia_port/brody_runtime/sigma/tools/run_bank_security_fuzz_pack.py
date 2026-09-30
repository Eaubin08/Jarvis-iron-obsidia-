import csv
import json
import os
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent.parent
RUN_PIPELINE = ROOT / "sigma" / "run_pipeline.py"
EXAMPLES = ROOT / "sigma" / "examples"
OUT_DIR = ROOT / "artifacts" / "p2_bank_security_fuzz"

def _env():
    e = os.environ.copy()
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONWARNINGS"] = "ignore"
    return e

def load(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))

NORMAL = load("bank_normal.json")
SUSPICIOUS = load("bank_suspicious.json")
BLOCKED = load("bank_blocked.json")

def run_payload_dict(payload):
    p = subprocess.run(
        [sys.executable, str(RUN_PIPELINE), "bank", json.dumps(payload)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_env(),
    )
    return p

def run_payload_arg(arg):
    p = subprocess.run(
        [sys.executable, str(RUN_PIPELINE), "bank", arg],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_env(),
    )
    return p

def parse_err(stderr):
    s = (stderr or "").strip()
    if not s:
        return {"raw": ""}
    try:
        return json.loads(s)
    except Exception:
        return {"raw": s}

def safe_result(case_id, category, expectation, proc):
    row = {
        "case_id": case_id,
        "category": category,
        "expectation": expectation,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "ok": False,
        "safety_outcome": None,
        "x108_gate_observed": None,
        "reason_code": None,
        "severity": None,
        "detail": None,
    }

    if proc.returncode != 0:
        row["ok"] = True
        row["safety_outcome"] = "CLEAN_REJECTION"
        row["detail"] = parse_err(proc.stderr)
        return row

    try:
        out = json.loads(proc.stdout)
    except Exception:
        row["ok"] = False
        row["safety_outcome"] = "UNPARSEABLE_SUCCESS"
        row["detail"] = {"stdout": row["stdout"]}
        return row

    gate = out.get("x108_gate")
    row["x108_gate_observed"] = gate
    row["reason_code"] = out.get("reason_code")
    row["severity"] = out.get("severity")
    row["detail"] = out

    if expectation == "reject_or_non_allow":
        if gate in ("HOLD", "BLOCK"):
            row["ok"] = True
            row["safety_outcome"] = "SAFE_NON_ALLOW"
        elif gate == "ALLOW":
            row["ok"] = False
            row["safety_outcome"] = "UNSAFE_ALLOW"
        else:
            row["ok"] = False
            row["safety_outcome"] = "UNKNOWN_GATE"
        return row

    if expectation == "non_allow":
        if gate in ("HOLD", "BLOCK"):
            row["ok"] = True
            row["safety_outcome"] = "SAFE_NON_ALLOW"
        else:
            row["ok"] = False
            row["safety_outcome"] = "UNSAFE_ALLOW"
        return row

    if expectation == "reject_only":
        row["ok"] = False
        row["safety_outcome"] = "UNEXPECTED_SUCCESS"
        return row

    row["ok"] = False
    row["safety_outcome"] = "UNKNOWN_EXPECTATION"
    return row

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    # 1 unknown field
    p = deepcopy(NORMAL)
    p["domain"] = "bank"
    rows.append(safe_result("sec-unknown-field-domain", "schema", "reject_or_non_allow", run_payload_dict(p)))

    # 2 missing required field
    p = deepcopy(NORMAL)
    p.pop("amount", None)
    rows.append(safe_result("sec-missing-amount", "schema", "reject_or_non_allow", run_payload_dict(p)))

    # 3 wrong type string
    p = deepcopy(NORMAL)
    p["amount"] = "9999"
    rows.append(safe_result("sec-amount-string", "type", "reject_or_non_allow", run_payload_dict(p)))

    # 4 wrong type object
    p = deepcopy(NORMAL)
    p["fraud_score"] = {"bad": 1}
    rows.append(safe_result("sec-fraud-object", "type", "reject_or_non_allow", run_payload_dict(p)))

    # 5 null where numeric expected
    p = deepcopy(NORMAL)
    p["device_trust_score"] = None
    rows.append(safe_result("sec-device-trust-null", "type", "reject_or_non_allow", run_payload_dict(p)))

    # 6 invalid path / traversal-like
    rows.append(safe_result("sec-invalid-path-traversal-like", "path", "reject_only", run_payload_arg(r"..\..\nonexistent_payload.json")))

    # 7 directory instead of file
    rows.append(safe_result("sec-directory-arg", "path", "reject_only", run_payload_arg(str(ROOT / "sigma" / "examples"))))

    # 8 extreme hostile valid profile
    p = deepcopy(BLOCKED)
    p["amount"] = 999999999.99
    p["historical_avg_amount"] = 50.0
    p["fraud_score"] = 0.99
    p["behavior_shift_score"] = 0.99
    p["urgency_score"] = 0.99
    p["identity_mismatch_score"] = 0.99
    p["narrative_conflict_score"] = 0.99
    p["device_trust_score"] = 0.01
    p["recent_failed_attempts"] = 9
    rows.append(safe_result("sec-extreme-pressure", "pressure", "non_allow", run_payload_dict(p)))

    # 9 negative elapsed suspicious
    p = deepcopy(SUSPICIOUS)
    p["elapsed_s"] = -5.0
    rows.append(safe_result("sec-negative-elapsed", "temporal", "reject_or_non_allow", run_payload_dict(p)))

    # 10 replay hostile suspicious x8
    replay_outputs = []
    p = deepcopy(SUSPICIOUS)
    p["elapsed_s"] = 5.0
    p["identity_mismatch_score"] = 0.92
    p["narrative_conflict_score"] = 0.91
    p["device_trust_score"] = 0.08
    p["fraud_score"] = 0.93
    for i in range(8):
        proc = run_payload_dict(p)
        replay_outputs.append(safe_result(f"sec-replay-hostile-{i+1}", "replay", "non_allow", proc))
    rows.extend(replay_outputs)

    # replay stability aggregate
    replay_ok = all(r["ok"] for r in replay_outputs)
    replay_gates = sorted(set(r["x108_gate_observed"] for r in replay_outputs if r["x108_gate_observed"]))
    rows.append({
        "case_id": "sec-replay-hostile-stability",
        "category": "replay",
        "expectation": "stable_non_allow",
        "returncode": 0,
        "stdout": "",
        "stderr": "",
        "ok": bool(replay_ok and len(replay_gates) == 1 and replay_gates[0] in ("HOLD", "BLOCK")),
        "safety_outcome": "REPLAY_STABLE" if (replay_ok and len(replay_gates) == 1 and replay_gates[0] in ("HOLD", "BLOCK")) else "REPLAY_DRIFT",
        "x108_gate_observed": replay_gates[0] if len(replay_gates) == 1 else None,
        "reason_code": None,
        "severity": None,
        "detail": {"replay_gates": replay_gates},
    })

    total = len(rows)
    failed = [r for r in rows if not r["ok"]]
    outcome_counts = Counter(r.get("safety_outcome", "UNKNOWN") for r in rows)
    category_counts = Counter(r.get("category", "UNKNOWN") for r in rows)
    gate_counts = Counter(r.get("x108_gate_observed", "NONE") for r in rows if r.get("x108_gate_observed"))

    report_json = OUT_DIR / "bank_security_fuzz_report.json"
    summary_json = OUT_DIR / "bank_security_fuzz_summary.json"
    report_csv = OUT_DIR / "bank_security_fuzz_report.csv"

    report_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    with report_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case_id","category","expectation","returncode","ok","safety_outcome",
                "x108_gate_observed","reason_code","severity","stdout","stderr","detail"
            ],
        )
        writer.writeheader()
        for r in rows:
            rr = dict(r)
            if isinstance(rr.get("detail"), (dict, list)):
                rr["detail"] = json.dumps(rr["detail"], ensure_ascii=False)
            writer.writerow({k: rr.get(k) for k in writer.fieldnames})

    summary = {
        "total_cases": total,
        "failed_cases": len(failed),
        "category_counts": dict(category_counts),
        "outcome_counts": dict(outcome_counts),
        "gate_counts": dict(gate_counts),
        "unsafe_allow_count": outcome_counts.get("UNSAFE_ALLOW", 0),
        "clean_rejection_count": outcome_counts.get("CLEAN_REJECTION", 0),
        "safe_non_allow_count": outcome_counts.get("SAFE_NON_ALLOW", 0),
        "replay_stable_count": outcome_counts.get("REPLAY_STABLE", 0),
        "report_json": str(report_json),
        "summary_json": str(summary_json),
        "report_csv": str(report_csv),
    }

    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
