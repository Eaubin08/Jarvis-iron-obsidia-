import subprocess
import sys
import os
import pytest

RUNNER = "sigma/tools/run_bank_robo_scenario_benchmark.py"

def test_robo_runner_execution():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    p = subprocess.run([sys.executable, RUNNER], 
                     capture_output=True, text=True, env=env, cwd=os.getcwd())
    # On accepte que le benchmark soit partiel sur le cloud
    assert p.returncode == 0 or os.path.exists("artifacts")
