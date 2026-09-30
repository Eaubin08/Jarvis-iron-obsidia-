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

def test_no_source_not_allow():
    result = run_example("gps_no_source.json")
    assert result["x108_gate"] in {"HOLD", "BLOCK"}

def test_source_conflict_not_allow():
    result = run_example("gps_source_conflict.json")
    assert result["x108_gate"] in {"HOLD", "BLOCK"}

def test_brownout_not_allow():
    result = run_example("gps_brownout.json")
    assert result["x108_gate"] in {"HOLD", "BLOCK"}

def test_time_skew_not_allow():
    result = run_example("gps_time_skew.json")
    assert result["x108_gate"] in {"HOLD", "BLOCK"}