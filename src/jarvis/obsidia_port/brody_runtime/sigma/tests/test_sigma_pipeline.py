import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
def test_contracts_import():
    import sigma.contracts
def test_aggregation_import():
    import sigma.aggregation
def test_registry_import():
    import sigma.registry
def test_guard_import():
    import sigma.guard
def test_protocols_import():
    import sigma.protocols
def test_domains_bank():
    import sigma.domains.bank_agents
def test_domains_ecom():
    import sigma.domains.ecom_agents
def test_domains_trading():
    import sigma.domains.trading_agents
def test_domains_meta():
    import sigma.domains.meta_agents
