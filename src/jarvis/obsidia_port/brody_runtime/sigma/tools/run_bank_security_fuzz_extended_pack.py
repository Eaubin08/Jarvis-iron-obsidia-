import csv
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent.parent
RUN_PIPELINE = ROOT / "sigma" / "run_pipeline.py"
EXAMPLES = ROOT / "sigma" / "examples"
OUT_DIR = ROOT / "artifacts" / "p2_bank_security_fuzz_extended"

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
    return subprocess.run(
        [sys.executable, str(RUN_PIPELINE), "bank", json.dumps(payload)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_env(),
    )

def run_payload_arg(arg):
    return subprocess.run(
        [sys.executable, str(RUN_PIPELINE), "bank", arg],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_env(),
    )

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

    if expectation == "reject_only":
        row["ok"] = False
        row["safety_outcome"] = "UNEXPECTED_SUCCESS"
        return row

    if expectation in ("reject_or_non_allow", "non_allow"):
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

    row["ok"] = False
    row["safety_outcome"] = "UNKNOWN_EXPECTATION"
    return row

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    # missing required fields (4)
    for fld in ["amount", "fraud_score", "device_trust_score", "elapsed_s"]:
        p = deepcopy(NORMAL)
        p.pop(fld, None)
        rows.append(safe_result(f"fx-missing-{fld}", "missing_field", "reject_or_non_allow", run_payload_dict(p)))

    # unknown fields (4)
    unknowns = {
        "domain": "bank",
        "admin": True,
        "__proto__": {"polluted": True},
        "nested_unexpected": {"x": 1, "y": ["a", "b"]},
    }
    for k, v in unknowns.items():
        p = deepcopy(NORMAL)
        p[k] = v
        rows.append(safe_result(f"fx-unknown-{k}", "unknown_field", "reject_or_non_allow", run_payload_dict(p)))

    # type confusion (8)
    type_cases = [
        ("amount", "9999"),
        ("amount", ["9999"]),
        ("amount", {"n": 9999}),
        ("fraud_score", "0.9"),
        ("fraud_score", ["0.9"]),
        ("fraud_score", {"bad": 1}),
        ("device_trust_score", None),
        ("recent_failed_attempts", "7"),
    ]
    for i, (fld, val) in enumerate(type_cases, 1):
        p = deepcopy(NORMAL)
        p[fld] = val
        rows.append(safe_result(f"fx-type-{i:02d}-{fld}", "type_confusion", "reject_or_non_allow", run_payload_dict(p)))

    # boundary values (8)
    boundary_payloads = []

    p = deepcopy(NORMAL); p["amount"] = -1.0; boundary_payloads.append(("negative_amount", p))
    p = deepcopy(NORMAL); p["amount"] = 1e12; boundary_payloads.append(("huge_amount", p))
    p = deepcopy(SUSPICIOUS); p["elapsed_s"] = -10.0; boundary_payloads.append(("negative_elapsed", p))
    p = deepcopy(NORMAL); p["fraud_score"] = -0.1; boundary_payloads.append(("negative_fraud", p))
    p = deepcopy(NORMAL); p["fraud_score"] = 1.5; boundary_payloads.append(("fraud_over_one", p))
    p = deepcopy(NORMAL); p["device_trust_score"] = -0.2; boundary_payloads.append(("negative_trust", p))
    p = deepcopy(NORMAL); p["device_trust_score"] = 1.7; boundary_payloads.append(("trust_over_one", p))
    p = deepcopy(BLOCKED); p["recent_failed_attempts"] = 999; boundary_payloads.append(("failed_attempts_huge", p))

    for name, payload in boundary_payloads:
        rows.append(safe_result(f"fx-boundary-{name}", "boundary", "reject_or_non_allow", run_payload_dict(payload)))

    # path abuse (2)
    rows.append(safe_result("fx-path-nonexistent", "path_abuse", "reject_only", run_payload_arg(r"..\..\definitely_missing_payload.json")))
    rows.append(safe_result("fx-path-directory", "path_abuse", "reject_only", run_payload_arg(str(ROOT / "sigma" / "examples"))))

    # extreme valid hostile pressure (4)
    for i in range(4):
        p = deepcopy(BLOCKED)
        p["amount"] = 10_000_000.0 + i * 1_000_000.0
        p["historical_avg_amount"] = 25.0 + i
        p["fraud_score"] = 0.96 + i * 0.01
        p["behavior_shift_score"] = 0.95
        p["urgency_score"] = 0.97
        p["identity_mismatch_score"] = 0.95
        p["narrative_conflict_score"] = 0.95
        p["device_trust_score"] = 0.01
        p["recent_failed_attempts"] = 8 + i
        rows.append(safe_result(f"fx-pressure-{i+1}", "pressure", "non_allow", run_payload_dict(p)))

    # replay hostile x16
    replay_outputs = []
    p = deepcopy(SUSPICIOUS)
    p["elapsed_s"] = 5.0
    p["identity_mismatch_score"] = 0.94
    p["narrative_conflict_score"] = 0.93
    p["device_trust_score"] = 0.05
    p["fraud_score"] = 0.94
    p["behavior_shift_score"] = 0.90
    for i in range(16):
        replay_outputs.append(safe_result(f"fx-replay-{i+1}", "replay", "non_allow", run_payload_dict(p)))
    rows.extend(replay_outputs)

    replay_ok = all(r["ok"] for r in replay_outputs)
    replay_gates = sorted(set(r["x108_gate_observed"] for r in replay_outputs if r["x108_gate_observed"]))
    rows.append({
        "case_id": "fx-replay-stability",
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

    # mutation grid over suspicious profiles (27)
    idx = 0
    for fraud in [0.20, 0.50, 0.90]:
        for mismatch in [0.20, 0.70, 0.95]:
            for elapsed in [2.0, 20.0, 107.0]:
                idx += 1
                p = deepcopy(SUSPICIOUS)
                p["fraud_score"] = fraud
                p["identity_mismatch_score"] = mismatch
                p["elapsed_s"] = elapsed
                rows.append(safe_result(f"fx-grid-{idx:02d}", "mutation_grid", "non_allow", run_payload_dict(p)))

    total = len(rows)
    failed = [r for r in rows if not r["ok"]]
    outcome_counts = Counter(r.get("safety_outcome", "UNKNOWN") for r in rows)
    category_counts = Counter(r.get("category", "UNKNOWN") for r in rows)
    gate_counts = Counter(r.get("x108_gate_observed", "NONE") for r in rows if r.get("x108_gate_observed"))

    report_json = OUT_DIR / "bank_security_fuzz_extended_report.json"
    summary_json = OUT_DIR / "bank_security_fuzz_extended_summary.json"
    report_csv = OUT_DIR / "bank_security_fuzz_extended_report.csv"

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
