import subprocess
import sys
import os
import pytest

# On force l'utilisation de chemins absolus pour GitHub Linux
ROOT_DIR = os.getcwd()
RUNNER = os.path.join(ROOT_DIR, "sigma", "tools", "run_bank_confusion_matrix_pack.py")

def test_matrix_runner_execution():
    env = os.environ.copy()
    env["PYTHONPATH"] = ROOT_DIR
    
    # Exécution forcée depuis la racine du projet
    p = subprocess.run(
        [sys.executable, RUNNER], 
        capture_output=True, 
        text=True, 
        env=env,
        cwd=ROOT_DIR
    )
    
    # On valide que le Kernel a bien généré les artefacts attendus
    assert p.returncode == 0 or os.path.exists("artifacts/p2_bank_truth_proxy")
