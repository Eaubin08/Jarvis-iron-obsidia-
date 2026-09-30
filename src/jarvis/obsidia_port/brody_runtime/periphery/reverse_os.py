# Reverse OS / SSR minimal, non décisionnel
def project(flow):
    agent = flow.get("agent_name", "UNKNOWN_AGENT")
    reason_code = flow.get("reason_code", "UNKNOWN_REASON")
    merkle_root = flow.get("merkle_root", "NO_MERKLE")
    verdict = flow.get("verdict", "NO_VERDICT")
    tree_vector = flow.get("tree_vector", {})
    if isinstance(tree_vector, list):
        ranked = sorted(enumerate(tree_vector), key=lambda x: x[1], reverse=True)[:5]
    else:
        ranked = sorted(tree_vector.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "qui": agent,
        "pourquoi": reason_code,
        "preuve": merkle_root,
        "verdict_existant": verdict,
        "dominant_trees": ranked,
        "text_projection": f"{agent} / {reason_code} / preuve={merkle_root}",
        "ui_projection": {"agent": agent, "reason_code": reason_code, "verdict_existant": verdict},
        "voice_projection_stub": f"Agent {agent}, raison {reason_code}.",
        "visual_state": {"top_trees": ranked},
        "non_decision": True
    }
