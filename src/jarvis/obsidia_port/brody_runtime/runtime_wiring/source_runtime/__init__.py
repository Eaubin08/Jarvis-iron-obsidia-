# runtime_wiring/source_runtime/__init__.py
# P26 Real Engine Source Runtime — read-only hydration layer
# Connects source packs to Brody context pipeline.
# NO extraction, NO .py execution, NO ACT, NO write. KX108_ONLY.

__version__ = "P26_SOURCE_RUNTIME"
__status__ = "REAL_ENGINE_READONLY"
__decision_authority__ = "KX108_ONLY"
__emits_act__ = False
__zip_extraction__ = False
__memory_write__ = False
__graph_write__ = False
__kernel_mutation__ = False
