import json
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNNER = ROOT / "sigma" / "tools" / "run_bank_security_fuzz_extended_pack.py"

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
        timeout=900,
        env=_env(),
    )
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)

def test_extended_fuzz_runner_passes():
    s = run_runner()
    assert s["failed_cases"] == 0
    assert Path(s["report_json"]).is_file()
    assert Path(s["summary_json"]).is_file()
    assert Path(s["report_csv"]).is_file()

def test_total_case_count_is_expected():
    s = run_runner()
    assert s["total_cases"] == 74

def test_no_unsafe_allow():
    s = run_runner()
    assert s["unsafe_allow_count"] == 0

def test_many_clean_rejections_exist():
    s = run_runner()
    assert s["clean_rejection_count"] >= 10

def test_many_safe_non_allow_exist():
    s = run_runner()
    assert s["safe_non_allow_count"] >= 20

def test_replay_stability_present():
    s = run_runner()
    assert s["replay_stable_count"] == 1
