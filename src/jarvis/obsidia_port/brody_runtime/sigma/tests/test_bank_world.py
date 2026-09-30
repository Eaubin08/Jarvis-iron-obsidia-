import json
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

def _env():
    e = os.environ.copy()
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONWARNINGS"] = "ignore"
    return e

def _run_case(filename: str):
    p = subprocess.run(
        [sys.executable, str(ROOT / "sigma" / "run_pipeline.py"), "bank", str(ROOT / "sigma" / "examples" / filename)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        env=_env(),
    )
    assert p.returncode == 0, f"{filename}\nSTDERR:\n{p.stderr}"
    return json.loads(p.stdout)

def test_bank_normal_allow():
    d = _run_case("bank_normal.json")
    assert d["x108_gate"] == "ALLOW", d
    assert d["sigma_report"]["pass"] is True
    assert d["metrics"]["deterministic"] is True

def test_bank_suspicious_not_allow():
    d = _run_case("bank_suspicious.json")
    assert d["x108_gate"] in ("HOLD", "BLOCK"), d
    assert d["sigma_report"]["pass"] is True

def test_bank_blocked_hard_block():
    d = _run_case("bank_blocked.json")
    assert d["x108_gate"] == "BLOCK", d
    assert d["severity"] == "S4", d
    assert d["sigma_report"]["pass"] is True
    assert d["metrics"]["deterministic"] is True

def test_bank_outputs_present():
    d = _run_case("bank_normal.json")
    assert "decision_id" in d
    assert "trace_id" in d
    assert "attestation_ref" in d
    assert "sigma_report" in d

def test_bank_all_sigma_pass():
    for f in ("bank_normal.json", "bank_suspicious.json", "bank_blocked.json"):
        d = _run_case(f)
        assert d["sigma_report"]["pass"] is True, f
