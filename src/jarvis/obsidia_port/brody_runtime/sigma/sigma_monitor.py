#!/usr/bin/env python3
import sys
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sigma.obsidia_sigma_v130 import ObsidiaSigmaMonitor

def run_example(name: str) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "sigma" / "run_pipeline.py"),
        "gps_defense_aviation",
        str(ROOT / "sigma" / "examples" / name),
    ]
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)

def main():
    monitor = ObsidiaSigmaMonitor(config_path=str(ROOT / "sigma" / "sigma_config.json"))
    monitor.evaluate_step("S1", ["smoke_risk"], [])
    report = monitor.export_to_proofkit()["V18_9_sigma_stability"]

    payload = {
        "status": report["status"],
        "steps_evaluated": report["steps_evaluated"],
        "violations_total": report["violations_total"],
    }

    gps_cases = [
        "gps_nominal.json",
        "gps_no_source.json",
        "gps_source_conflict.json",
        "gps_brownout.json",
        "gps_time_skew.json",
    ]

    for name in gps_cases:
        key = Path(name).stem
        try:
            result = run_example(name)
            payload[f"{key}_gate"] = result.get("x108_gate")
            payload[f"{key}_reason_code"] = result.get("reason_code")
            payload[f"{key}_market_verdict"] = result.get("market_verdict")
        except Exception as e:
            payload[f"{key}_error"] = str(e)

    if "--json" in sys.argv:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print("Sigma monitor public")
        print(f"status                     : {payload['status']}")
        print(f"steps_evaluated            : {payload['steps_evaluated']}")
        print(f"violations_total           : {payload['violations_total']}")
        for name in gps_cases:
            key = Path(name).stem
            gate = payload.get(f"{key}_gate", "ERR")
            reason = payload.get(f"{key}_reason_code", payload.get(f"{key}_error", ""))
            print(f"{key:26}: {gate} {reason}")

if __name__ == "__main__":
    main()