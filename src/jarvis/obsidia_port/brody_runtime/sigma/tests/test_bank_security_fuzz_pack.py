import subprocess
import sys
import os
import json
import pytest

RUNNER = "sigma/tools/run_bank_security_fuzz_pack.py"

def test_security_fuzz_absolute_perfection():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    # Le patch sur le tool doit maintenant ramener 0 DRIFT
    p = subprocess.run([sys.executable, RUNNER], capture_output=True, text=True, env=env)
    s = json.loads(p.stdout)
    
    # Ici, on ne tolère plus de drift : tout doit être CLEAN_REJECTION
    assert s['failed_cases'] == 0
    assert s['clean_rejection_count'] + s['safe_non_allow_count'] + s.get('replay_stable_count', 0) == s['total_cases']
    assert s['unsafe_allow_count'] == 0
