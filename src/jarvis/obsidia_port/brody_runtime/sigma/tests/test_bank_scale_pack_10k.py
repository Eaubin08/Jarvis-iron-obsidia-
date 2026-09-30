import json
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNNER = ROOT / "sigma" / "tools" / "run_bank_scale_pack.py"

def _env():
    e = os.environ.copy()
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONWARNINGS"] = "ignore"
    return e

def run_runner():
    p = subprocess.run(
        [sys.executable, str(RUNNER), "--size", "10000", "--workers", "6"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=7200,
        env=_env(),
    )
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)

def test_scale_10k_passes():
    s = run_runner()
    assert s["size"] == 10000
    assert s["failed_cases"] == 0
    assert Path(s["report_json"]).is_file()
    assert Path(s["summary_json"]).is_file()
    assert Path(s["report_csv"]).is_file()

def test_scale_10k_distribution_is_complete():
    s = run_runner()
    assert s["family_counts"] == {"allow": 3334, "hold": 3333, "block": 3333}

def test_scale_10k_no_softer():
    s = run_runner()
    assert s["gap_counts"].get("SOFTER_THAN_BUSINESS", 0) == 0

def test_scale_10k_three_gate_space_present():
    s = run_runner()
    assert s["gate_counts"].get("ALLOW", 0) > 0
    assert s["gate_counts"].get("HOLD", 0) > 0
    assert s["gate_counts"].get("BLOCK", 0) > 0

def test_scale_10k_has_positive_throughput():
    s = run_runner()
    assert s["throughput_cases_per_s"] > 0
