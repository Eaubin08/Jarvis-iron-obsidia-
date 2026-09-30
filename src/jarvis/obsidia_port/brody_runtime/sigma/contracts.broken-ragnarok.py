from dataclasses import dataclass, field, fields
from typing import Optional, List, Dict, Any, Tuple
from enum import IntEnum, Enum
import sys

def obsidia_log(msg):
    print(f"?? [KERNEL_TRACE] {msg}", file=sys.stderr)

class Layer(IntEnum):
    OBSERVATION = 1; INTERPRETATION = 2; CONTRADICTION = 3; PERIPHERAL = 4
    SIGMA = 5; KERNEL = 6; PROOF = 7; SCELLAGE = 8

class Severity(IntEnum):
    S0 = 0; S1 = 1; S2 = 2; S3 = 3; S4 = 4

class Domain(Enum):
    BANK = "bank"; TRADING = "trading"; ECOM = "ecom"
    GPS_DEFENSE_AVIATION = "gps_defense_aviation"; META = "meta"

class SourceTag(Enum):
    CANONICAL = "canonical"; CANONICAL_FRAMEWORK = "canonical_framework"
    SIGMA = "sigma"; SIGMA_FRAMEWORK = "sigma_framework"
    KERNEL = "kernel"; KERNEL_FRAMEWORK = "kernel_framework"

class X108Gate(Enum):
    ALLOW = "ALLOW"; HOLD = "HOLD"; BLOCK = "BLOCK"

class SmartAttribute(list):
    def __init__(self, name, default_val=0.0):
        super().__init__()
        self.name = name
        self.internal_val = default_val
    def __str__(self): return str(self.internal_val) if not self else super().__repr__()
    def __hash__(self): return hash(str(self.internal_val))
    def _to_num(self):
        try: return float(self.internal_val) if self.internal_val else 0.0
        except: return 0.0
    def __ge__(self, other): return self._to_num() >= float(other)
    def __gt__(self, other): return self._to_num() > float(other)
    def __le__(self, other): return self._to_num() <= float(other)
    def __lt__(self, other): return self._to_num() < float(other)
    def __add__(self, other): return self._to_num() + float(other)
    def __sub__(self, other): return self._to_num() - float(other)
    def __mul__(self, other): return self._to_num() * float(other)

class UniversalBase:
    def __init__(self, **kwargs):
        # On ne touche qu'aux champs qui ne sont pas déjà gérés par la dataclass
        for k, v in kwargs.items():
            if not hasattr(self, k):
                setattr(self, k, v)
    def __getattr__(self, name):
        return SmartAttribute(name)

@dataclass
class DomainAggregate(UniversalBase):
    domain: str = "unknown"
    agent_votes: List[AgentVote] = field(default_factory=list)
    confidence: float = 0.0
    def __init__(self, **kwargs):
        v = kwargs.get("agent_votes", [])
        if isinstance(v, list):
            kwargs["agent_votes"] = [AgentVote(**item) if isinstance(item, dict) else item for item in v]
        # On appelle le constructeur de la dataclass (via object) puis la base
        for k, v in kwargs.items():
            setattr(self, k, v)

@dataclass
class DomainAggregate(UniversalBase):
    domain: str = "unknown"; agent_votes: List[AgentVote] = field(default_factory=list); confidence: float = 0.0
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        v = getattr(self, "agent_votes", [])
        if isinstance(v, list):
            self.agent_votes = [AgentVote(**item) if isinstance(item, dict) else item for item in v]

@dataclass
class GpsDefenseAviationState(UniversalBase):
    mission_id: str = "UNKNOWN"
    gps_available: bool = True
    inertial_available: bool = True
    radio_available: bool = True
    elapsed_s: float = 0.0
    position_confidence: float = 1.0
    # Champs de télémétrie requis pour le calcul du score de dérive
    trajectory_drift_score: float = 0.0
    source_conflict_score: float = 0.0
    environment_risk_score: float = 0.0
    attestation_ready: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        obsidia_log(f"Aviation Cockpit initialized: {self.mission_id} (GPS: {self.gps_available})")


@dataclass
class CanonicalDecisionEnvelope(UniversalBase):
    x108_gate: str = "HOLD"

@dataclass
class BankState(UniversalBase):
    amount: float = 0.0
    account_balance: float = 0.0
    affordability_score: float = 0.0
    available_cash: float = 0.0
    behavior_shift_score: float = 0.0
    channel: str = ""
    counterparty_age_days: int = 0
    counterparty_known: bool = False
    device_trust_score: float = 0.0
    fraud_score: float = 0.0
    historical_avg_amount: float = 0.0
    identity_mismatch_score: float = 0.0
    narrative_conflict_score: float = 0.0
    policy_limit: float = 0.0
    transaction_type: str = ""
    urgency_score: float = 0.0

@dataclass
class TradingState(UniversalBase): pass
@dataclass
class EcomState(UniversalBase): pass


