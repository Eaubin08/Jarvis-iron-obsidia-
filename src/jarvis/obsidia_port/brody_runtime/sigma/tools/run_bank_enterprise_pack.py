import csv
import json
import requests
import sys
import os
from pathlib import Path
from collections import Counter, defaultdict

# --- CONFIGURATION DES CHEMINS ---
ROOT = Path(__file__).resolve().parent.parent.parent
PACK_PATH = ROOT / "sigma" / "batches" / "bank_enterprise_pack.json"
OUT_DIR = ROOT / "artifacts" / "p2_bank_enterprise"

# F64: ragnarok bridge (localhost:3001/kernel/ragnarok) superseded by
# F63 readonly monitoring endpoint.  No POST, no bridge, no decision.
DEFAULT_API_BASE = os.environ.get("OBSIDIA_API_BASE", "http://127.0.0.1:8000")
SIGMA_BANK_MONITORING_ENDPOINT = "/api/periphery/monitoring/sigma/bank"

RANK = {"ALLOW": 0, "HOLD": 1, "BLOCK": 2}

def gate_rank(gate: str) -> int:
    return RANK.get(gate, 99)

def run_case(item: dict, api_base: str = DEFAULT_API_BASE) -> dict:
    """Observe bank domain state via F63 readonly monitoring endpoint.

    F64: per-case state dispatch to ragnarok is superseded.
    The F63 GET endpoint returns the live F62-normalized bank packet
    (advisory only, KX108_ONLY, no decision).
    """
    url = f"{api_base.rstrip('/')}{SIGMA_BANK_MONITORING_ENDPOINT}"
    try:
        response = requests.get(url, timeout=30)
        data = response.json()
    except Exception as e:
        return {
            "case_id": item["case_id"],
            "family": item["family"],
            "expected_min_gate": item["expected_min_gate"],
            "ok": False,
            "error": f"Monitoring Connection Error: {e}",
            "reconciliation": "F64_READONLY_MONITORING",
        }

    # F64: advisory observation — not a stateful gate decision.
    # pipeline_x108_gate_observed is informational only.
    observed_gate = data.get("pipeline_x108_gate_observed", "UNKNOWN")
    gate_ok = gate_rank(observed_gate) >= gate_rank(item["expected_min_gate"])
    sovereignty_ok = (
        data.get("decision_authority") == "KX108_ONLY"
        and data.get("allowed_to_decide") is False
        and data.get("readonly") is True
    )

    return {
        "case_id": item["case_id"],
        "family": item["family"],
        "expected_min_gate": item["expected_min_gate"],
        "note": item.get("note"),
        "ok": gate_ok and sovereignty_ok,
        "gate_ok": gate_ok,
        "sovereignty_ok": sovereignty_ok,
        "observed_gate": observed_gate,
        "decision_authority": data.get("decision_authority"),
        "allowed_to_decide": data.get("allowed_to_decide"),
        "packet_version": data.get("packet_version"),
        "reconciliation": "F64_READONLY_MONITORING",
    }

def main():
    if not PACK_PATH.exists():
        print(f"❌ Erreur : Pack introuvable à {PACK_PATH}")
        sys.exit(1)

    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Lancement du Stress-Test Enterprise ({len(pack)} cas)...")

    results = [run_case(item) for item in pack]
    failures = [r for r in results if not r["ok"]]

    # STATISTIQUES
    family_counts = Counter(r["family"] for r in results)
    gate_counts = Counter(r.get("x108_gate", "ERROR") for r in results)
    family_gate_counts = defaultdict(Counter)
    for r in results:
        family_gate_counts[r["family"]][r.get("x108_gate", "ERROR")] += 1

    # EXPORT DES RAPPORTS
    report_json = OUT_DIR / "bank_enterprise_report.json"
    summary_json = OUT_DIR / "bank_enterprise_summary.json"
    report_csv = OUT_DIR / "bank_enterprise_report.csv"

    report_json.write_text(json.dumps(results, indent=2), encoding="utf-8")

    with report_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case_id", "family", "expected_min_gate", "ok", "gate_ok", "sigma_ok",
                "x108_gate", "severity", "reason_code", "decision_id", "trace_id", "attestation_ref"
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k) for k in writer.fieldnames})

    summary = {
        "total_cases": len(results),
        "failed_cases": len(failures),
        "families": dict(family_counts),
        "gate_counts": dict(gate_counts),
        "family_gate_counts": {k: dict(v) for k, v in family_gate_counts.items()},
        "report_json": str(report_json),
        "summary_json": str(summary_json),
        "report_csv": str(report_csv),
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n✅ Terminé. {len(failures)} échecs détectés.")
    sys.exit(1 if failures else 0)

if __name__ == "__main__":
    main()