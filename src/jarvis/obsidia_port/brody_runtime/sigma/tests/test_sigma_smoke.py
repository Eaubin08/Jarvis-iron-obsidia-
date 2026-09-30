import json
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

def _env():
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env

def test_sigma_monitor_cli():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "sigma" / "sigma_monitor.py"), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        env=_env(),
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert "status" in data
    assert "steps_evaluated" in data

def test_sigma_run_pipeline_bank_normal():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "sigma" / "run_pipeline.py"), "bank", str(ROOT / "sigma" / "examples" / "bank_normal.json")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        env=_env(),
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert "x108_gate" in data
    assert "decision_id" in data
    assert "trace_id" in data
    assert "sigma_report" in data

def test_sigma_run_pipeline_bank_suspicious():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "sigma" / "run_pipeline.py"), "bank", str(ROOT / "sigma" / "examples" / "bank_suspicious.json")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        env=_env(),
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert "x108_gate" in data
    assert "severity" in data