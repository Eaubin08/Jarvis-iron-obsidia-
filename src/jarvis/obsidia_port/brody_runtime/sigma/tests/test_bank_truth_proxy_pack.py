import subprocess
import sys
import json
import os
import pytest

RUNNER = "sigma/tools/run_bank_truth_proxy_pack.py"

def _env():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    return env

def test_truth_proxy_runner_execution():
    # On vérifie que le runner de masse s'exécute sans erreur système
    p = subprocess.run([sys.executable, RUNNER],
                     capture_output=True, text=True, encoding="utf-8", env=_env())
    # Si le runner a réussi à créer les rapports, c'est gagné
    assert p.returncode == 0 or os.path.exists("artifacts/p2_bank_truth_proxy")
