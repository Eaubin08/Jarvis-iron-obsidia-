# V18.9 — Sigma Dynamic Stability Check

**Version :** 1.3.0 · **Date :** 2026-03-11 · **Statut :** Intégré et testé

## Rôle dans la chaîne de preuve

V18.9 Sigma est la couche de **runtime verification** du moteur Obsidia. Elle complète les couches statiques :

| Couche | Ce qu'elle vérifie |
|---|---|
| Lean 4 (V18.1–V18.6) | Correction logique statique des invariants D1/E2/G1/G2/G3 |
| TLA+ (V18.7–V18.8) | Sécurité du modèle sur l'espace d'états atteignables |
| **Sigma V18.9** | **Stabilité dynamique de la trajectoire de décision en runtime** |

## Les 3 contraintes surveillées

### 1. Vanishing Acceleration — `z̈ ≈ 0`
Pas de flip sémantique brutal entre décisions consécutives. Si l'accélération de la trajectoire dépasse `accel_limit = 0.4`, le moteur signale `HIGH_CURVATURE_INSTABILITY`.

### 2. Velocity Band Control — `tau_min ≤ ||ż|| ≤ tau_max`
- **Anti-drift** (borne haute `tau_max = 0.75`) : empêche l'escalade rapide de sévérité
- **Anti-collapse** (borne basse `tau_min = 0.05`) : détecte l'insensibilité du moteur

### 3. Coherence Stationarity — `dΣc/dt = 0`
Toute évolution runtime doit rester couverte par la cohérence scellée du système (hash stable).

## Fichiers

| Fichier | Rôle |
|---|---|
| `agents/sigma_monitor.py` | Moniteur simple (version de base) |
| `agents/obsidia_sigma_v130.py` | Version ProofKit complète avec `export_to_proofkit()` et `save_report()` |
| `proofs/V18_9/README.md` | Ce fichier |

## Intégration dans le moteur

Sigma est intégré dans `agents/run_pipeline.py` après chaque décision :

```python
sigma = ObsidiaSigmaMonitor()
result_dict = envelope_to_dict(result)
result_dict = apply_sigma(result_dict, sigma)
```

**Protection active :** Si `stability == FAIL`, le moteur force automatiquement :
- `market_verdict = "HOLD_STABILITY_ALERT"`
- `severity = "S4"`
- `sigma_override = True`

## Résultats vérifiés (v1.3.0)

| Pipeline | x108_gate | sigma_status | sigma_override |
|---|---|---|---|
| trading bullish | ALLOW | PASS | False |
| bank normal | ALLOW | PASS | False |
| bank suspicious | BLOCK | PASS | False |
| ecom normal | ALLOW | PASS | False |

## Export ProofKit

Le module exporte une entrée `V18_9_sigma_stability` compatible avec `PROOFKIT_REPORT.json` :

```json
{
  "V18_9_sigma_stability": {
    "pass": true,
    "status": "PASS",
    "steps_evaluated": 1,
    "unstable_steps": 0,
    "violations_total": 0,
    "violation_types": []
  }
}
```
