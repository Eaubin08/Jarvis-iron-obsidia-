from .common import ActionCandidate, PeripheralSignalPacket
from .constants import THETA_ENERGY,THETA_MISMATCH,THETA_THERMO_DEBT
def run_energy_thermo(a:ActionCandidate)->PeripheralSignalPacket:
    p=a.payload; o=PeripheralSignalPacket(a.action_id,a.domain); pin=max(float(p.get('pin',1.0)),1e-9); pout=float(p.get('pout',pin)); eff=pout/pin
    debt=float(p.get('energy_cost',0))+float(p.get('compute_cost',0))+float(p.get('attention_cost',0))+float(p.get('recovery_cost',0))-float(p.get('useful_work',0))
    truth=float(p.get('truth_score',1.0)); sigma=float(p.get('sigma_score',truth)); mismatch=abs(sigma-truth)
    o.extra_metrics.update({'pin':pin,'pout':pout,'energy_efficiency':eff,'thermo_debt':debt,'truth_score':truth,'sigma_score':sigma,'sigma_truth_mismatch':mismatch})
    if eff<float(p.get('theta_energy',THETA_ENERGY)): o.add_risk('ENERGY_INEFFICIENT'); o.recommended_gate='HOLD'
    if mismatch>float(p.get('theta_mismatch',THETA_MISMATCH)): o.add_risk('SIGMA_TRUTH_MISMATCH'); o.recommended_gate='HOLD'
    if p.get('collapse_disguised_high_sigma',False): o.add_contradiction('COLLAPSE_DISGUISED_HIGH_SIGMA'); o.recommended_gate='BLOCK_CANDIDATE'
    if debt>float(p.get('theta_thermo_debt',THETA_THERMO_DEBT)): o.add_risk('THERMO_DEBT_HIGH'); o.recommended_gate='HOLD'
    return o
