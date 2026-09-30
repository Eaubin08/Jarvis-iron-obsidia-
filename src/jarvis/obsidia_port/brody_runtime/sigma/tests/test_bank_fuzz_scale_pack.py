import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNNER = ROOT / "sigma" / "tools" / "run_bank_fuzz_scale_pack.py"

EXPECTED_FAMILIES = {
    "missing_field",
    "unknown_field",
    "type_confusion",
    "boundary",
    "path_abuse",
    "pressure",
    "replay",
    "mutation_grid",
}

def _env():
    e = os.environ.copy()
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONWARNINGS"] = "ignore"
    return e

def run_runner():
    p = subprocess.run(
        [sys.executable, str(RUNNER), "--size", "1000", "--workers", "6"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=2400,
        env=_env(),
    )
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)

def test_fuzz_scale_1k_passes():
    s = run_runner()
    assert s["failed_cases"] == 0
    assert Path(s["report_json"]).is_file()
    assert Path(s["summary_json"]).is_file()
    assert Path(s["report_csv"]).is_file()

def test_fuzz_scale_1k_total_case_count_is_expected():
    s = run_runner()
    assert s["total_cases"] == 1000

def test_fuzz_scale_1k_no_unsafe_allow():
    s = run_runner()
    assert s["unsafe_allow_count"] == 0

def test_fuzz_scale_1k_no_softer_drift():
    s = run_runner()
    assert s["softer_drift_count"] == 0

def test_fuzz_scale_1k_family_coverage_is_complete():
    s = run_runner()
    assert set(s["family_counts"].keys()) == EXPECTED_FAMILIES
    assert all(v > 0 for v in s["family_counts"].values())

def test_fuzz_scale_1k_has_positive_throughput():
    s = run_runner()
    assert s["throughput_cases_per_s"] > 0
