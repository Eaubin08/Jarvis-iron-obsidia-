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
    if not os.path.exists(p): p = f"sigma/tests/data/{name}"
    with open(p, "r") as f: return json.load(f)

def run_payload(payload):
    fd, temp_path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, 'w') as tmp: json.dump(payload, tmp)
        p = subprocess.run([sys.executable, RUN_PIPELINE, "bank", temp_path],
                         capture_output=True, text=True, encoding="utf-8", env=_env())
        return json.loads(p.stdout)
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

def test_canonical_baselines():
    # Test simple pour vérifier que le Kernel répond sur les 3 profils types
    for name in ["bank_normal.json", "bank_suspicious.json", "bank_blocked.json"]:
        res = run_payload(load_fixture(name))
        assert (res.get('x108_gate') or res.get('gate')) is not None

@pytest.mark.parametrize("elapsed_s", [2.0, 60.0, 107.0])
def test_temporal_immaturity_does_not_soften(elapsed_s):
    base = load_fixture("bank_suspicious.json")
    p = base.copy()
    p["elapsed_s"] = elapsed_s
    res = run_payload(p)
    assert res.get('x108_gate') in ['BLOCK', 'ANALYZE', 'HOLD']
