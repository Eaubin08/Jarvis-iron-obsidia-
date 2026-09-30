import json
import subprocess
import sys
import os
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent.parent
PACK_PATH = ROOT / "sigma" / "batches" / "bank_regulatory_proxy_pack.json"
RUNNER = ROOT / "sigma" / "tools" / "run_bank_regulatory_proxy_pack.py"

def _env():
    e = os.environ.copy()
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONWARNINGS"] = "ignore"
    return e

def run_runner():
    p = subprocess.run(
        [sys.executable, str(RUNNER)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
        env=_env(),
    )
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)

def test_pack_has_54_cases():
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    assert len(pack) == 54

def test_pack_has_balanced_zone_distribution():
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    c = Counter(item["zone"] for item in pack)
    assert c == Counter({"allow": 18, "hold": 18, "block": 18})

def test_pack_has_all_families():
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    c = Counter(item["family"] for item in pack)
    assert c == Counter({
        "aml": 9,
        "kyc": 9,
        "beneficiary": 9,
        "urgency": 9,
        "anomaly": 9,
        "combined": 9,
    })

def test_runner_passes_and_writes_artifacts():
    s = run_runner()
    assert s["total_cases"] == 54
    assert s["failed_cases"] == 0
    assert Path(s["report_json"]).is_file()
    assert Path(s["summary_json"]).is_file()
    assert Path(s["report_csv"]).is_file()

def test_hold_zone_is_actually_present():
    s = run_runner()
    assert s["gate_counts"].get("HOLD", 0) > 0
    assert s["gate_counts"].get("ALLOW", 0) > 0
    assert s["gate_counts"].get("BLOCK", 0) > 0

def test_no_softer_than_business():
    s = run_runner()
    assert s["gap_counts"].get("SOFTER_THAN_BUSINESS", 0) == 0
