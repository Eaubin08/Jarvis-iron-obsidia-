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

def test_gps_nominal_smoke():
    result = run_example("gps_nominal.json")
    assert result["domain"] == "gps_defense_aviation"
    assert "x108_gate" in result
    assert "reason_code" in result
    assert "decision_id" in result
    assert "trace_id" in result
    assert "sigma_report" in result