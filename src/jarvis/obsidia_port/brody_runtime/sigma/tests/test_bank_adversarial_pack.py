import subprocess
import sys
import json
import os
import tempfile
import pytest

RUN_PIPELINE = "sigma/run_pipeline.py"

def _env():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    return env

def load_fixture(name):
    p = f"sigma/examples/{name}"
    if os.path.exists(p):
        with open(p, "r") as f:
            return json.load(f)
    raise FileNotFoundError(f"Impossible de trouver {name}")

def run_payload(payload):
    fd, temp_path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, 'w') as tmp:
            json.dump(payload, tmp)
        p = subprocess.run(
            [sys.executable, RUN_PIPELINE, "bank", temp_path],
            capture_output=True, text=True, encoding="utf-8", env=_env()
        )
        return json.loads(p.stdout)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_repeatability_same_normal_profile_keeps_same_verdict():
    payload = load_fixture("bank_normal.json")
    outputs = [run_payload(payload) for _ in range(4)]
    # On valide la stabilité du VERDICT (Gate), pas de l'ID (qui doit être unique)
    gates = [o.get('x108_gate') or o.get('gate') for o in outputs]
    assert len(set(gates)) == 1
    assert gates[0] is not None

def test_suspicious_boundary_protection():
    base = load_fixture("bank_suspicious.json")
    p = base.copy()
    p["elapsed_s"] = 2.0
    d = run_payload(p)
    # On cherche la clé x108_gate renvoyée par ton Kernel
    gate = d.get('x108_gate') or d.get('gate') or d.get('verdict')
    assert gate in ['BLOCK', 'ANALYZE', 'HOLD', 'REVIEW']
