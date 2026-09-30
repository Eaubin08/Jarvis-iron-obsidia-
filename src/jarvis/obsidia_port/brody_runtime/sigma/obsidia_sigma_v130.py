"""
Obsidia Sigma Monitor v1.4.1 - V18.9 Dynamic Stability Check
ProofKit-compatible version with export_to_proofkit() and save_report().

Architecture "Moteur Fixe + Config Calibree" (v1.4.1):
  - Les seuils sont lus depuis sigma/sigma_config.json si present.
  - Les valeurs par defaut v1.4.0 s'appliquent si le fichier est absent.
  - Le moteur lui-meme ne change jamais de structure (scelle).

Surveille la trajectoire de decision du moteur en temps reel:
  - Vanishing Acceleration : z_ddot ~= 0 (pas de flip brutal)
  - Velocity Band Control : tau_min <= ||z_dot|| <= tau_max
  - Coherence Stationarity : dSigma_c/dt = 0 (hash systeme stable)

Usage :
    monitor = ObsidiaSigmaMonitor()
    monitor.evaluate_step(severity, risks, contras)
    report = monitor.export_to_proofkit()
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional


SEVERITY_MAP = {"S0": 0.0, "S1": 0.25, "S2": 0.5, "S3": 0.75, "S4": 1.0}

# Valeurs par defaut v1.4.0 (utilisees si sigma_config.json absent)
_DEFAULT_TAU_MIN = 0.05
_DEFAULT_TAU_MAX = 0.75
_DEFAULT_ACCEL_LIMIT = 0.40


def _load_sigma_config(config_path: str = "sigma/sigma_config.json") -> Dict[str, Any]:
    """
    Charge la configuration Sigma depuis un fichier JSON externe.
    Retourne un dict vide si le fichier est absent ou invalide.
    """
    p = Path(config_path)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


class ObsidiaSigmaMonitor:
    """
    Moniteur de stabilite dynamique Sigma - V18.9.
    Compatible ProofKit : export_to_proofkit() et save_report().

    Les seuils sont charges depuis sigma/sigma_config.json (si present),
    ce qui permet une calibration statistique sans modifier le code moteur.
    """

    def __init__(
        self,
        tau_min: Optional[float] = None,
        tau_max: Optional[float] = None,
        accel_limit: Optional[float] = None,
        coherence_hash: Optional[str] = None,
        config_path: str = "sigma/sigma_config.json",
    ):
        # Chargement de la config externe
        cfg = _load_sigma_config(config_path)

        # Priorite : parametre explicite > config JSON > defaut v1.4.0
        self.tau_min = tau_min if tau_min is not None else cfg.get("tau_min", _DEFAULT_TAU_MIN)
        self.tau_max = tau_max if tau_max is not None else cfg.get("tau_max", _DEFAULT_TAU_MAX)
        self.accel_limit = accel_limit if accel_limit is not None else cfg.get("accel_limit", _DEFAULT_ACCEL_LIMIT)
        self.coherence_hash = coherence_hash
        self.config_source = config_path if Path(config_path).exists() else "defaults_v1.4.0"

        self.history: List[Dict[str, Any]] = []
        self.steps: List[Dict[str, Any]] = []  # trace complete de chaque step

    # ------------------------------------------------------------------
    # Auto-calibration (ajustement dynamique des seuils sur l'historique)
    # ------------------------------------------------------------------

    def auto_calibrate(self) -> None:
        """
        Ajuste tau_max base sur l'historique recent (methode 1.5x moyenne).
        Ne modifie que l'instance en memoire, pas le fichier de config.
        Necessite au moins 10 pas d'historique.
        """
        if len(self.history) < 10:
            return
        velocities = [
            abs(self.history[i]["val"] - self.history[i - 1]["val"])
            for i in range(1, len(self.history))
        ]
        avg = sum(velocities) / len(velocities)
        self.tau_max = round(avg * 1.5, 2)
        print(f"[SIGMA] Auto-calibrated tau_max to: {self.tau_max}")

    # ------------------------------------------------------------------
    # Vecteur latent z_t
    # ------------------------------------------------------------------

    def _to_vector(self, severity: str, risk_count: int, contra_count: int) -> float:
        base = SEVERITY_MAP.get(severity, 0.0)
        return round(base + (risk_count * 0.05) + (contra_count * 0.1), 6)

    # ------------------------------------------------------------------
    # Evaluation d'un step
    # ------------------------------------------------------------------

    def evaluate_step(
        self,
        severity: str,
        risks: List[Any],
        contras: List[Any],
        current_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evalue un step de decision et met a jour l'historique.
        Retourne le rapport de stabilite du step.
        """
        z_t = self._to_vector(severity, len(risks), len(contras))
        t_t = time.time()

        step_report: Dict[str, Any] = {
            "step": len(self.steps),
            "severity": severity,
            "z": z_t,
            "z_t": z_t,
            "velocity": 0.0,
            "acceleration": 0.0,
            "stability_status": "STABLE",
            "violations": [],
            "coherence_ok": True,
        }

        # --- Velocity ---
        if len(self.history) >= 1:
            dt = t_t - self.history[-1]["ts"]
            if dt > 0:
                v_t = abs(z_t - self.history[-1]["val"]) / dt
                step_report["velocity"] = round(v_t, 6)

                if v_t < self.tau_min:
                    step_report["violations"].append("POTENTIAL_COLLAPSE")
                elif v_t > self.tau_max:
                    step_report["violations"].append("LATENT_DRIFT")

                # --- Acceleration ---
                if len(self.history) >= 2:
                    dt_prev = self.history[-1]["ts"] - self.history[-2]["ts"]
                    if dt_prev > 0:
                        v_prev = abs(self.history[-1]["val"] - self.history[-2]["val"]) / dt_prev
                        a_t = abs(step_report["velocity"] - v_prev) / dt
                        step_report["acceleration"] = round(a_t, 6)
                        if a_t > self.accel_limit:
                            step_report["violations"].append("HIGH_CURVATURE_INSTABILITY")

        # --- Coherence Stationarity ---
        if self.coherence_hash and current_hash:
            coherence_ok = self.coherence_hash == current_hash
            step_report["coherence_ok"] = coherence_ok
            if not coherence_ok:
                step_report["violations"].append("COHERENCE_STATIONARITY_VIOLATED")

        # --- Statut global ---
        if step_report["violations"]:
            step_report["stability_status"] = "UNSTABLE"

        # --- Mise a jour historique ---
        self.history.append({"val": z_t, "ts": t_t})
        if len(self.history) > 10:
            self.history.pop(0)

        self.steps.append(step_report)
        return step_report

    # ------------------------------------------------------------------
    # Export ProofKit
    # ------------------------------------------------------------------

    def export_to_proofkit(self) -> Dict[str, Any]:
        """
        Exporte le rapport V18.9 au format ProofKit.
        Compatible avec PROOFKIT_REPORT.json.
        """
        if not self.steps:
            return {
                "V18_9_sigma_stability": {
                    "pass": False,
                    "status": "NO_DATA",
                    "steps_evaluated": 0,
                    "violations_total": 0,
                    "violation_types": [],
                    "stdout": "NO_DATA - no steps evaluated\n",
                }
            }

        total_violations = sum(len(s["violations"]) for s in self.steps)
        all_violation_types = list({v for s in self.steps for v in s["violations"]})
        unstable_steps = [s for s in self.steps if s["stability_status"] == "UNSTABLE"]
        passed = len(unstable_steps) == 0
        status = "PASS" if passed else "FAIL"

        velocities = [s["velocity"] for s in self.steps if s["velocity"] > 0]
        mean_velocity = round(sum(velocities) / len(velocities), 6) if velocities else 0.0

        summary_lines = [
            f"V18.9 Sigma Dynamic Stability - {status}",
            f"Steps evaluated : {len(self.steps)}",
            f"Unstable steps  : {len(unstable_steps)}",
            f"Total violations: {total_violations}",
            f"Config source   : {self.config_source}",
            f"tau_max         : {self.tau_max}",
            f"accel_limit     : {self.accel_limit}",
        ]
        if all_violation_types:
            summary_lines.append(f"Violation types : {', '.join(all_violation_types)}")
        else:
            summary_lines.append("No violations detected.")

        return {
            "V18_9_sigma_stability": {
                "pass": passed,
                "status": status,
                "steps_evaluated": len(self.steps),
                "unstable_steps": len(unstable_steps),
                "violations_total": total_violations,
                "violation_types": all_violation_types,
                "metrics": {
                    "mean_velocity": mean_velocity,
                    "total_steps": len(self.steps),
                    "tau_max_used": self.tau_max,
                    "accel_limit_used": self.accel_limit,
                },
                "constraints": {
                    "vanishing_acceleration": "VOLATILE" if any(
                        "HIGH_CURVATURE_INSTABILITY" in s["violations"] for s in self.steps
                    ) else "OK",
                    "velocity_band": "DRIFT" if any(
                        "LATENT_DRIFT" in s["violations"] for s in self.steps
                    ) else "OK",
                    "coherence_stationarity": "VIOLATED" if any(
                        "COHERENCE_STATIONARITY_VIOLATED" in s["violations"] for s in self.steps
                    ) else "OK",
                },
                "steps_detail": self.steps,
                "stdout": "\n".join(summary_lines) + "\n",
            }
        }

    # ------------------------------------------------------------------
    # Save report
    # ------------------------------------------------------------------

    def save_report(self, report_path: str = "proofs/PROOFKIT_REPORT.json") -> None:
        """
        Fusionne le rapport V18.9 dans PROOFKIT_REPORT.json existant.
        Cree le fichier s'il n'existe pas.
        """
        path = Path(report_path)
        sigma_entry = self.export_to_proofkit()

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        else:
            existing = {}

        existing.update(sigma_entry)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

        print(f"[Sigma] Report saved to {report_path}")

    # ------------------------------------------------------------------
    # Coherence hash helper
    # ------------------------------------------------------------------

    @staticmethod
    def compute_coherence_hash(files: List[str]) -> str:
        """Calcule un hash SHA-256 sur une liste de fichiers."""
        h = hashlib.sha256()
        for fp in sorted(files):
            p = Path(fp)
            if p.exists():
                h.update(p.read_bytes())
        return h.hexdigest()