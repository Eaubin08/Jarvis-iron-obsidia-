from jarvis.physical_probe import ProbeItem, format_probe_summary


def test_g13_probe_summary_is_readonly_and_explicit():
    result = {
        "readonly": True,
        "decision_authority": "KX108_ONLY",
        "pass_count": 2,
        "fail_count": 1,
        "evidence_file": "runtime_data/g13_physical_probe/g13_physical_probe.json",
        "items": [
            {"name": "monitors", "ok": True, "data": {"count": 2}, "error": None},
            {"name": "windows", "ok": True, "data": {"windows": [{}, {}]}, "error": None},
            {"name": "camera_1", "ok": False, "data": {}, "error": "RuntimeError:camera unavailable"},
        ],
    }
    summary = format_probe_summary(result)
    assert "readonly=True" in summary
    assert "decision_authority=KX108_ONLY" in summary
    assert "monitors: PASS count=2" in summary
    assert "camera_1: FAIL" in summary
