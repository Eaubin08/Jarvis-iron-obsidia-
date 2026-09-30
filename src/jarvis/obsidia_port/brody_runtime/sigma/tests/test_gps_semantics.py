import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def run_example(name: str):
    cmd = [
        sys.executable,
        str(ROOT / "sigma" / "run_pipeline.py"),
        "gps_defense_aviation",
        str(ROOT / "sigma" / "examples" / name),
    ]
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)

def test_nominal_market_verdict():
    result = run_example("gps_nominal.json")
    assert result["market_verdict"] == "TRAJECTORY_VALID"
    assert result["x108_gate"] == "ALLOW"

def test_no_source_market_verdict():
    result = run_example("gps_no_source.json")
    assert result["market_verdict"] == "RECALC_TRAJECTORY"
    assert result["x108_gate"] == "HOLD"

def test_source_conflict_market_verdict():
    result = run_example("gps_source_conflict.json")
    assert result["market_verdict"] == "ABORT_TRAJECTORY"
    assert result["x108_gate"] == "BLOCK"

def test_brownout_market_verdict():
    result = run_example("gps_brownout.json")
    assert result["market_verdict"] == "DEGRADED_NAVIGATION"
    assert result["x108_gate"] == "HOLD"

def test_time_skew_market_verdict():
    result = run_example("gps_time_skew.json")
    assert result["market_verdict"] == "RECALC_TRAJECTORY"
    assert result["x108_gate"] == "HOLD"