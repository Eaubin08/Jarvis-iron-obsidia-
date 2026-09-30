import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sigma.tools.run_bank_security_fuzz_extended_pack import (
    NORMAL,
    SUSPICIOUS,
    BLOCKED,
    run_payload_dict,
    run_payload_arg,
    safe_result,
)

EXPECT_RANK = {
    "reject_only": 2,
    "reject_or_non_allow": 1,
    "non_allow": 1,
}

OUTCOME_RANK = {
    "CLEAN_REJECTION": 2,
    "SAFE_NON_ALLOW": 1,
    "REPLAY_STABLE": 1,
    "UNSAFE_ALLOW": 0,
    "UNEXPECTED_SUCCESS": 0,
    "UNKNOWN_GATE": 0,
    "UNPARSEABLE_SUCCESS": 0,
    "UNKNOWN_EXPECTATION": 0,
    "REPLAY_DRIFT": 0,
}

MISSING_FIELDS = ["amount", "fraud_score", "device_trust_score", "elapsed_s"]

UNKNOWN_FIELDS = [
    ("domain", "bank"),
    ("admin", True),
    ("__proto__", {"polluted": True}),
    ("nested_unexpected", {"x": 1, "y": ["a", "b"]}),
]

TYPE_CASES = [
    ("amount", "9999"),
    ("amount", ["9999"]),
    ("amount", {"n": 9999}),
    ("fraud_score", "0.9"),
    ("fraud_score", ["0.9"]),
    ("fraud_score", {"bad": 1}),
    ("device_trust_score", None),
    ("recent_failed_attempts", "7"),
]

def boundary_payloads():
    items = []

    p = deepcopy(NORMAL); p["amount"] = -1.0; items.append(("negative_amount", p))
    p = deepcopy(NORMAL); p["amount"] = 1e12; items.append(("huge_amount", p))
    p = deepcopy(SUSPICIOUS); p["elapsed_s"] = -10.0; items.append(("negative_elapsed", p))
    p = deepcopy(NORMAL); p["fraud_score"] = -0.1; items.append(("negative_fraud", p))
    p = deepcopy(NORMAL); p["fraud_score"] = 1.5; items.append(("fraud_over_one", p))
    p = deepcopy(NORMAL); p["device_trust_score"] = -0.2; items.append(("negative_trust", p))
    p = deepcopy(NORMAL); p["device_trust_score"] = 1.7; items.append(("trust_over_one", p))
    p = deepcopy(BLOCKED); p["recent_failed_attempts"] = 999; items.append(("failed_attempts_huge", p))

    return items

BOUNDARY_CASES = boundary_payloads()

MUTATION_GRID = []
for fraud in [0.20, 0.50, 0.90]:
    for mismatch in [0.20, 0.70, 0.95]:
        for elapsed in [2.0, 20.0, 107.0]:
            MUTATION_GRID.append((fraud, mismatch, elapsed))

FAMILIES = [
    "missing_field",
    "unknown_field",
    "type_confusion",
    "boundary",
    "path_abuse",
    "pressure",
    "replay",
    "mutation_grid",
]

def build_case(i: int):
    lane = i % len(FAMILIES)
    family = FAMILIES[lane]

    if family == "missing_field":
        fld = MISSING_FIELDS[(i // len(FAMILIES)) % len(MISSING_FIELDS)]
        p = deepcopy(NORMAL)
        p.pop(fld, None)
        return {
            "case_id": f"fuzz-missing-{i:06d}-{fld}",
            "family": family,
            "expectation": "reject_or_non_allow",
            "mode": "dict",
            "payload": p,
        }

    if family == "unknown_field":
        k, v = UNKNOWN_FIELDS[(i // len(FAMILIES)) % len(UNKNOWN_FIELDS)]
        p = deepcopy(NORMAL)
        p[k] = v
        return {
            "case_id": f"fuzz-unknown-{i:06d}-{k}",
            "family": family,
            "expectation": "reject_or_non_allow",
            "mode": "dict",
            "payload": p,
        }

    if family == "type_confusion":
        fld, val = TYPE_CASES[(i // len(FAMILIES)) % len(TYPE_CASES)]
        p = deepcopy(NORMAL)
        p[fld] = val
        return {
            "case_id": f"fuzz-type-{i:06d}-{fld}",
            "family": family,
            "expectation": "reject_or_non_allow",
            "mode": "dict",
            "payload": p,
        }

    if family == "boundary":
        name, payload = BOUNDARY_CASES[(i // len(FAMILIES)) % len(BOUNDARY_CASES)]
        return {
            "case_id": f"fuzz-boundary-{i:06d}-{name}",
            "family": family,
            "expectation": "reject_or_non_allow",
            "mode": "dict",
            "payload": deepcopy(payload),
        }

    if family == "path_abuse":
        arg = r"..\..\definitely_missing_payload.json" if ((i // len(FAMILIES)) % 2 == 0) else str(ROOT / "sigma" / "examples")
        return {
            "case_id": f"fuzz-path-{i:06d}",
            "family": family,
            "expectation": "reject_only",
            "mode": "arg",
            "arg": arg,
        }

    if family == "pressure":
        k = (i // len(FAMILIES)) % 4
        p = deepcopy(BLOCKED)
        p["amount"] = 10_000_000.0 + k * 1_000_000.0 + i
        p["historical_avg_amount"] = 25.0 + k
        p["fraud_score"] = min(0.99, 0.96 + k * 0.01)
        p["behavior_shift_score"] = 0.95
        p["urgency_score"] = 0.97
        p["identity_mismatch_score"] = 0.95
        p["narrative_conflict_score"] = 0.95
        p["device_trust_score"] = 0.01
        p["recent_failed_attempts"] = 8 + k
        return {
            "case_id": f"fuzz-pressure-{i:06d}",
            "family": family,
            "expectation": "non_allow",
            "mode": "dict",
            "payload": p,
        }

    if family == "replay":
        p = deepcopy(SUSPICIOUS)
        p["elapsed_s"] = 5.0
        p["identity_mismatch_score"] = 0.94
        p["narrative_conflict_score"] = 0.93
        p["device_trust_score"] = 0.05
        p["fraud_score"] = 0.94
        p["behavior_shift_score"] = 0.90
        return {
            "case_id": f"fuzz-replay-{i:06d}",
            "family": family,
            "expectation": "non_allow",
            "mode": "dict",
            "payload": p,
        }

    fraud, mismatch, elapsed = MUTATION_GRID[(i // len(FAMILIES)) % len(MUTATION_GRID)]
    p = deepcopy(SUSPICIOUS)
    p["fraud_score"] = fraud
    p["identity_mismatch_score"] = mismatch
    p["elapsed_s"] = elapsed
    return {
        "case_id": f"fuzz-grid-{i:06d}",
        "family": family,
        "expectation": "non_allow",
        "mode": "dict",
        "payload": p,
    }

def run_one(case):
    t0 = time.perf_counter()
    if case["mode"] == "dict":
        proc = run_payload_dict(case["payload"])
    else:
        proc = run_payload_arg(case["arg"])
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    row = safe_result(case["case_id"], case["family"], case["expectation"], proc)
    row["family"] = case["family"]
    row["elapsed_ms"] = elapsed_ms
    row["expected_rank"] = EXPECT_RANK.get(case["expectation"], 99)
    row["observed_rank"] = OUTCOME_RANK.get(row.get("safety_outcome"), -1)
    row["softer_drift"] = row["observed_rank"] < row["expected_rank"]
    return row

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1000, choices=[1000, 10000, 100000])
    ap.add_argument("--workers", type=int, default=min(6, max(1, (os.cpu_count() or 4))))
    args = ap.parse_args()

    out_dir = ROOT / "artifacts" / "p2_bank_fuzz_scale" / f"{args.size}_cases_{args.workers}_workers"
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = [build_case(i) for i in range(args.size)]

    t0 = time.perf_counter()
    rows = []

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_one, case) for case in cases]
        for fut in as_completed(futs):
            rows.append(fut.result())

    total_elapsed_s = round(time.perf_counter() - t0, 3)
    rows.sort(key=lambda r: r["case_id"])

    failures = [r for r in rows if not r["ok"]]
    family_counts = Counter(r["family"] for r in rows)
    outcome_counts = Counter(r.get("safety_outcome", "UNKNOWN") for r in rows)
    gate_counts = Counter(r.get("x108_gate_observed", "NONE") for r in rows if r.get("x108_gate_observed"))
    softer_drift_count = sum(1 for r in rows if r.get("softer_drift"))

    mean_elapsed_ms = round(sum(r.get("elapsed_ms", 0.0) for r in rows) / len(rows), 3) if rows else 0.0
    throughput_cases_per_s = round(len(rows) / total_elapsed_s, 3) if total_elapsed_s > 0 else 0.0

    report_json = out_dir / "bank_fuzz_scale_report.json"
    summary_json = out_dir / "bank_fuzz_scale_summary.json"
    report_csv = out_dir / "bank_fuzz_scale_report.csv"

    report_json.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    with report_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case_id","family","expectation","returncode","ok","safety_outcome",
                "x108_gate_observed","reason_code","severity","elapsed_ms",
                "softer_drift","expected_rank","observed_rank","stdout","stderr","detail"
            ],
        )
        writer.writeheader()
        for r in rows:
            rr = dict(r)
            if isinstance(rr.get("detail"), (dict, list)):
                rr["detail"] = json.dumps(rr["detail"], ensure_ascii=False)
            writer.writerow({k: rr.get(k) for k in writer.fieldnames})

    summary = {
        "size": args.size,
        "workers": args.workers,
        "total_cases": len(rows),
        "failed_cases": len(failures),
        "family_counts": dict(family_counts),
        "outcome_counts": dict(outcome_counts),
        "gate_counts": dict(gate_counts),
        "unsafe_allow_count": outcome_counts.get("UNSAFE_ALLOW", 0),
        "clean_rejection_count": outcome_counts.get("CLEAN_REJECTION", 0),
        "safe_non_allow_count": outcome_counts.get("SAFE_NON_ALLOW", 0),
        "replay_stable_count": outcome_counts.get("REPLAY_STABLE", 0),
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
