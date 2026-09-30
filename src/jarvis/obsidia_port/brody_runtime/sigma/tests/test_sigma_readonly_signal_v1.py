"""sigma/tests/_w6a_tests_tmp.py -- Tests W6a SigmaReadonlySignal. 27 tests."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(ROOT))
from sigma.sigma_readonly_signal import SigmaReadonlySignal, build_sigma_readonly_signal

def _build(**kw) -> SigmaReadonlySignal:
    d = dict(signal_id="sig-w6a", contradictions=["c1"], proof_status="OK", missing_context=["m1"])
    d.update(kw)
    return build_sigma_readonly_signal(**d)

# 1
def test_nominal_construction():
    s = _build()
    assert s.signal_id == "sig-w6a"
    assert s.proof_status == "OK"

# 2
def test_contradictions_exact_copy():
    s = _build(contradictions=["c1", "c2"])
    assert s.contradictions == ["c1", "c2"]

# 3
def test_missing_context_exact_copy():
    s = _build(missing_context=["m1", "m2"])
    assert s.missing_context == ["m1", "m2"]

# 4
def test_proof_status_exact():
    for st in ("OK", "MISSING", "PARTIAL", "FAILED", "UNKNOWN"):
        assert _build(proof_status=st).proof_status == st

# 5
def test_deterministic():
    kw = dict(signal_id="d", contradictions=["x"], proof_status="OK", missing_context=["y"])
    s1 = build_sigma_readonly_signal(**kw)
    s2 = build_sigma_readonly_signal(**kw)
    assert s1.signal_id == s2.signal_id
    assert s1.contradictions == s2.contradictions
    assert s1.proof_status == s2.proof_status
    assert s1.missing_context == s2.missing_context

# 6
def test_input_mutation_isolation():
    ct = ["c1"]; mc = ["m1"]
    s = build_sigma_readonly_signal("sig-iso", ct, "OK", mc)
    ct.append("c2"); mc.append("m2")
    assert s.contradictions == ["c1"]
    assert s.missing_context == ["m1"]

# 7
def test_readonly_true():
    assert _build().readonly is True

# 8
def test_advisory_only_true():
    assert _build().advisory_only is True

# 9
def test_context_signal_only_true():
    assert _build().context_signal_only is True

# 10
def test_can_decide_false():
    assert _build().can_decide is False

# 11
def test_can_emit_act_false():
    assert _build().can_emit_act is False

# 12
def test_emits_act_false():
    assert _build().emits_act is False

# 13
def test_emits_verdict_false():
    assert _build().emits_verdict is False

# 14
def test_memory_write_false():
    assert _build().memory_write is False

# 15
def test_graphiti_write_false():
    assert _build().graphiti_write is False

# 16
def test_neo4j_write_false():
    assert _build().neo4j_write is False

# 17
def test_kernel_mutation_false():
    assert _build().kernel_mutation is False

# 18
def test_x108_mutation_false():
    assert _build().x108_mutation is False

# 19
def test_decision_authority_kx108():
    assert _build().decision_authority == "KX108_ONLY"

# 20
def test_no_recommended_action():
    assert not hasattr(_build(), "recommended_action")

# 21
def test_no_x108_gate():
    assert not hasattr(_build(), "x108_gate")

# 22
def test_no_market_verdict():
    assert not hasattr(_build(), "market_verdict")

# 23
def test_no_domain_aggregate_symbol():
    import sigma.sigma_readonly_signal as m
    assert "DomainAggregate" not in m.__dict__

# 24
def test_no_agent_vote_symbol():
    import sigma.sigma_readonly_signal as m
    assert "AgentVote" not in m.__dict__

# 25
def test_no_brody_runtime_result_symbol():
    import sigma.sigma_readonly_signal as m
    assert "BrodyRuntimeResult" not in m.__dict__

# 26
def test_no_source_refs():
    assert not hasattr(_build(), "source_refs")

# 27
def test_no_provider_import():
    import sigma.sigma_readonly_signal as m
    assert "compute_sigma_guidance" not in m.__dict__
    assert "AgentLayer" not in m.__dict__
    assert "AgentResult" not in m.__dict__
