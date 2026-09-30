import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

def test_monitor_import():
    import sigma.sigma_monitor

def test_monitor_is_module():
    import sigma.sigma_monitor as m
    assert m is not None
