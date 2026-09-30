from __future__ import annotations

from typing import Any


CAPABILITY_MARKERS = (
    "fonction",
    "fonctionnal",
    "capacite",
    "capacite",
    "tu sais faire quoi",
    "tu peux faire quoi",
    "aide",
    "help",
    "presente toi",
    "presente toi",
    "qui es tu",
    "qui es-tu",
)


def is_brody_capabilities_query(text: str | None) -> bool:
    q = (text or "").strip().lower()
    if not q:
        return False
    return any(marker in q for marker in CAPABILITY_MARKERS)


def build_brody_capabilities_response(text: str | None = None) -> dict[str, Any]:
    answer = (
        "Je suis Brody, interface consultative d'Obsidia X-108. "
        "Je fonctionne en lecture seule : je peux lire, structurer, expliquer, projeter et auditer des signaux, "
        "mais je ne decide pas, je n'ecris pas en memoire et je n'emets aucun ACT.\n\n"
        "Mes fonctions principales :\n"
        "1. Lire une demande utilisateur et produire une reponse consultative.\n"
        "2. Interroger les surfaces memoire readonly quand l'index reconnait une ancre.\n"
        "3. Travailler avec les ancres X108, memoire, arbres, preuves, operateur, gencoin, P/T, audit.\n"
        "4. Fournir une projection OS Reverse readonly quand le pipeline enrichi est actif.\n"
        "5. Exposer les frontieres de securite : readonly, no ACT, no verdict, no write, KX108_ONLY.\n"
        "6. Aider l'operateur a inspecter une trace, comprendre une preuve, lire un paquet, ou preparer l'etape sure suivante.\n\n"
        "Limites : je suis advisory only. L'autorite de decision reste X-108. "
        "Je ne peux pas autoriser une action, muter le kernel, ecrire dans la memoire ou promouvoir une commande humaine."
    )

    return {
        "final_answer": answer,
        "response": answer,
        "source": "BRODY_CAPABILITIES_INTENT",
        "voice_source": "BRODY_CAPABILITIES_INTENT",
        "voice_src": "BRODY_CAPABILITIES_INTENT",
        "decision_authority": "KX108_ONLY",
        "readonly": True,
        "advisory_only": True,
        "emits_act": False,
        "emits_verdict": False,
        "memory_write": False,
        "kernel_mutation": "NONE",
        "x108_mutation": "NONE",
        "classification": "BRODY_CAPABILITIES",
        "original_message": text or "",
    }
