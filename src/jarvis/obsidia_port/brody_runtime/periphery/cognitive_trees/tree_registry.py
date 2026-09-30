"""
Cognitive Tree Registry — 34 canonical cognitive trees.
TreeSpace = R^34, a_i ∈ [0,1].
Output is context signal only. Never a decision.
Restored from Freeze Candidate Matrix - Canonical Version.
Semantic compilation — ARBRES_34 batch 1 (ROW_IDs 4-8, 12-16) and batch 2 (ROW_IDs 17-18, 22, 29, 32, 34).
Source: 4353_CURRENT_REPOSITORY_BRANCHING_RECONCILIATION_REV2D
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Provenance reference for batch-1 arbres.
# Individual MMONDE file SHAs are unavailable (NOT_COMPUTED in V0).
# Reference uses documentary chain: ART01 ledger + ART31 provenance + ART39 external ledger.
_BATCH1_SOURCE_REF = (
    "ART01_LEDGER"
    "|ART31_SOURCE_PACK=MMONDE_OS_TRAD_34_ARBRES"
    "|ART39_SHA=407f744338503957eb4baec2e2d995fa9f119dff42983b80ae48dc6220adb5d9"
)


def _prov(tree_id: int, source_row_id: int | None = None) -> dict:
    """Provenance metadata for a batch-1 TREE_ACTIVATION arbre. Read-only. No ACT.

    tree_id and source_row_id are kept separate so future batches where
    ROW_ID != TREE_ID do not accidentally inherit the batch-1 equality.
    """
    src_row = source_row_id if source_row_id is not None else tree_id
    return {
        "source_row_id":        str(src_row),
        "source_pack":          "MMONDE_OS_TRAD_34_ARBRES",
        "source_provenance":    "SOURCE_PROVENANCE_DOCUMENTED",
        "source_reference":     _BATCH1_SOURCE_REF,
        "compilation_status":   "DOCUMENTED_TREE_ACTIVATION_COMPILED",
        "activation_dimension": tree_id - 1,
        "readonly":             True,
        "emits_act":            False,
        "can_decide":           False,
        "authority":            "NON_SOVEREIGN",
        "memory_write":         False,
        "graphiti_write":       False,
        "neo4j_write":          False,
    }


_TREES: list[dict] = [
    {"id": 1,  "name": "ARBRE_01__Arbre_de_l_Humain",          "domain": "I_FONDAMENTAUX"},
    {"id": 2,  "name": "ARBRE_02__Arbre_de_la_Conscience",      "domain": "I_FONDAMENTAUX"},
    {"id": 3,  "name": "ARBRE_03__Arbre_de_la_Perception",      "domain": "I_FONDAMENTAUX"},
    {"id": 4,  "name": "ARBRE_04__Arbre_du_Sens",               "domain": "I_FONDAMENTAUX",  **_prov(tree_id=4,  source_row_id=4)},
    {"id": 5,  "name": "ARBRE_05__Arbre_de_l_Identite",         "domain": "I_FONDAMENTAUX",  **_prov(tree_id=5,  source_row_id=5)},
    {"id": 6,  "name": "ARBRE_06__Arbre_de_la_Comprehension",   "domain": "COGNITION",        **_prov(tree_id=6,  source_row_id=6)},
    {"id": 7,  "name": "ARBRE_07__Arbre_de_l_Organisation",     "domain": "COGNITION",        **_prov(tree_id=7,  source_row_id=7)},
    {"id": 8,  "name": "ARBRE_08__Arbre_de_la_Pensee",          "domain": "COGNITION",        **_prov(tree_id=8,  source_row_id=8)},
    {"id": 9,  "name": "ARBRE_09__Arbre_de_l_Intelligence",     "domain": "COGNITION"},
    {"id": 10, "name": "ARBRE_10__Arbre_du_Langage",            "domain": "COGNITION"},
    {"id": 11, "name": "ARBRE_11__Arbre_de_la_Science",         "domain": "EPISTEMICS"},
    {"id": 12, "name": "ARBRE_12__Arbre_de_la_Technique",       "domain": "EPISTEMICS",       **_prov(tree_id=12, source_row_id=12)},
    {"id": 13, "name": "ARBRE_13__Arbre_de_l_Art",              "domain": "EPISTEMICS",       **_prov(tree_id=13, source_row_id=13)},
    {"id": 14, "name": "ARBRE_14__Arbre_de_la_Philosophie",     "domain": "EPISTEMICS",       **_prov(tree_id=14, source_row_id=14)},
    {"id": 15, "name": "ARBRE_15__Arbre_de_la_Spiritualite",    "domain": "EPISTEMICS",       **_prov(tree_id=15, source_row_id=15)},
    {"id": 16, "name": "ARBRE_16__Arbre_de_la_Relation",        "domain": "SOCIAL",           **_prov(tree_id=16, source_row_id=16)},
    {"id": 17, "name": "ARBRE_17__Arbre_du_Collectif",          "domain": "SOCIAL",          **_prov(tree_id=17, source_row_id=17)},
    {"id": 18, "name": "ARBRE_18__Arbre_de_la_Transmission",    "domain": "SOCIAL",          **_prov(tree_id=18, source_row_id=18)},
    {"id": 19, "name": "ARBRE_19__Arbre_de_la_Culture",         "domain": "SOCIAL"},
    {"id": 20, "name": "ARBRE_20__Arbre_de_l_Action",           "domain": "PLANNING"},
    {"id": 21, "name": "ARBRE_21__Arbre_de_la_Creation",        "domain": "PLANNING"},
    {"id": 22, "name": "ARBRE_22__Arbre_de_la_Transformation",  "domain": "PLANNING",        **_prov(tree_id=22, source_row_id=22)},
    {"id": 23, "name": "ARBRE_23__Arbre_du_Temps",              "domain": "TEMPORAL"},
    {"id": 24, "name": "ARBRE_24__Arbre_de_la_Memoire",         "domain": "TEMPORAL"},
    {"id": 25, "name": "ARBRE_25__Arbre_de_l_Histoire",         "domain": "TEMPORAL"},
    {"id": 26, "name": "ARBRE_26__Arbre_de_la_Coherence",       "domain": "GOVERNANCE"},
    {"id": 27, "name": "ARBRE_27__Arbre_de_la_Verite",          "domain": "GOVERNANCE"},
    {"id": 28, "name": "ARBRE_28__Arbre_de_la_Valeur",          "domain": "GOVERNANCE"},
    {"id": 29, "name": "ARBRE_29__Arbre_de_la_Finalite",        "domain": "GOVERNANCE",      **_prov(tree_id=29, source_row_id=29)},
    {"id": 30, "name": "ARBRE_30__Arbre_Cognitif_Global",       "domain": "META"},
    {"id": 31, "name": "ARBRE_31__Arbre_des_Flux",              "domain": "INFRASTRUCTURE"},
    {"id": 32, "name": "ARBRE_32__Arbre_des_Connexions",        "domain": "INFRASTRUCTURE",  **_prov(tree_id=32, source_row_id=32)},
    {"id": 33, "name": "ARBRE_33__Arbre_de_l_Optimisation",     "domain": "INFRASTRUCTURE"},
    {"id": 34, "name": "ARBRE_34__Arbre_de_la_Stabilite",       "domain": "INFRASTRUCTURE",  **_prov(tree_id=34, source_row_id=34)},
]


@dataclass
class TreeEntry:
    id: int
    name: str
    domain: str
    # Semantic compilation provenance — batch 1: ROW_IDs 4-8, 12-16
    # Fields are None / False for arbres not yet compiled.
    source_row_id: str | None = None
    source_pack: str | None = None
    source_provenance: str | None = None
    source_reference: str | None = None
    compilation_status: str | None = None
    activation_dimension: int | None = None
    readonly: bool = True
    emits_act: bool = False
    can_decide: bool = False
    authority: str = "NON_SOVEREIGN"
    memory_write: bool = False
    graphiti_write: bool = False
    neo4j_write: bool = False

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "name": self.name, "domain": self.domain}
        if self.compilation_status is not None:
            d.update({
                "source_row_id":       self.source_row_id,
                "source_pack":         self.source_pack,
                "source_provenance":   self.source_provenance,
                "source_reference":    self.source_reference,
                "compilation_status":  self.compilation_status,
                "activation_dimension": self.activation_dimension,
                "readonly":            self.readonly,
                "emits_act":           self.emits_act,
                "can_decide":          self.can_decide,
                "authority":           self.authority,
                "memory_write":        self.memory_write,
                "graphiti_write":      self.graphiti_write,
                "neo4j_write":         self.neo4j_write,
            })
        return d


def get_all_trees() -> list[TreeEntry]:
    return [TreeEntry(**t) for t in _TREES]


def get_tree_by_id(tree_id: int) -> TreeEntry | None:
    for t in _TREES:
        if t["id"] == tree_id:
            return TreeEntry(**t)
    return None


def get_trees_by_domain(domain: str) -> list[TreeEntry]:
    return [TreeEntry(**t) for t in _TREES if t["domain"] == domain]


def get_tree_provenance(tree_id: int) -> TreeEntry | None:
    """Return TreeEntry with provenance metadata for a compiled arbre, or None.

    Read-only. Does not modify the registry. Does not emit ACT.
    Does not write to memory, Graphiti, or Neo4j.
    Returns None for arbres not yet compiled (compilation_status is None).
    """
    entry = get_tree_by_id(tree_id)
    if entry is None or entry.compilation_status is None:
        return None
    return entry
