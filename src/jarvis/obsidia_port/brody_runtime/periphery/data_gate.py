from .common import ActionCandidate, PeripheralSignalPacket
from .constants import THETA_FRESHNESS
from .hackathon_failures import FailureCode
def run_data_gate(a:ActionCandidate)->PeripheralSignalPacket:
    p=a.payload; o=PeripheralSignalPacket(a.action_id,a.domain)
    freshness=float(p.get('freshness_score',1.0)); source_count=int(p.get('source_count',1)); clean=bool(p.get('clean_json_ready',True))
    o.extra_metrics.update({'freshness_score':freshness,'source_count':source_count,'clean_json_ready':clean})
    if freshness<THETA_FRESHNESS: o.add_unknown(FailureCode.STALE_DATA.value); o.recommended_gate='HOLD'
    if source_count<2 and p.get('critical',False): o.add_unknown(FailureCode.MULTI_SOURCE_INSUFFICIENT.value); o.recommended_gate='HOLD'
    for key,code in [('rate_limit_active',FailureCode.RATE_LIMIT_ACTIVE),('bot_detection_active',FailureCode.BOT_DETECTION_ACTIVE),('self_healing_fetch_failed',FailureCode.SELF_HEALING_FETCH_FAILED),('dynamic_content_drift',FailureCode.DYNAMIC_CONTENT_DRIFT)]:
        if p.get(key,False): o.add_risk(code.value); o.recommended_gate='HOLD' if key!='rate_limit_active' else o.recommended_gate
    for key,code in [('js_render_failure',FailureCode.JAVASCRIPT_RENDER_FAILURE),('geo_blocked',FailureCode.GEO_BLOCKED)]:
        if p.get(key,False): o.add_unknown(code.value); o.recommended_gate='HOLD'
    if not clean: o.add_unknown(FailureCode.CLEAN_JSON_MISSING.value)
    return o
