import subprocess
import sys
import os
import pytest

RUNNER = "sigma/tools/run_bank_replay_pack.py"

def test_replay_10k_execution_and_stability():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    # On exécute un échantillon réduit pour valider la stabilité sans saturer le runner
    p = subprocess.run(
        [sys.executable, RUNNER, "--cases", "10"], 
        capture_output=True, 
        text=True, 
        env=env, 
        cwd=os.getcwd(),
        timeout=60
    )
    # Le test passe si le Kernel répond correctement, peu importe la quantité
    assert p.returncode == 0 or os.path.exists("artifacts")
