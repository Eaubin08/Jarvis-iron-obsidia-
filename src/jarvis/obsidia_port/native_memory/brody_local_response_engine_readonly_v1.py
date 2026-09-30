import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


BOUNDARY_FALSE_KEYS = [
    "memory_decision",
    "allowed_to_decide",
    "emits_act",
    "kernel_binding",
    "x108_runtime_binding",
    "x108_merge",
    "kernel_mutation",
    "x108_mutation",
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value, max_chars=1800):
    if not value:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:max_chars]


def compact(value, max_chars=420):
    text = clean_text(value, max_chars=max_chars)
    return text


def load_json(path_value):
    path = Path(path_value)
    if not path.exists():
        raise RuntimeError(f"MISSING_HYDRATED_PACKET_JSON={path_value}")
    return json.loads(path.read_text(encoding="utf-8"))


def extract_packet(obj):
    if isinstance(obj, dict):
        for key in ["hydrated_packet", "packet", "context_packet_source", "source_packet"]:
            nested = obj.get(key)
            if isinstance(nested, dict) and nested.get("context_packet"):
                return nested

        if obj.get("context_packet"):
            return obj

    raise RuntimeError("NO_CONTEXT_PACKET_FOUND")


def validate_boundary(obj, packet):
    for source in [obj, packet]:
        if not isinstance(source, dict):
            continue

        for key in BOUNDARY_FALSE_KEYS:
            if key in source and source.get(key) is not False:
                raise RuntimeError(f"BOUNDARY_VIOLATION_{key}={source.get(key)}")

        if source.get("decision_authority") and source.get("decision_authority") != "KX108_ONLY":
            raise RuntimeError(f"BAD_DECISION_AUTHORITY={source.get('decision_authority')}")

    return True


def item_material(item):
    candidates = [
        "hydrated_excerpt",
        "hydrated_text",
        "material",
        "content_excerpt",
        "local_excerpt",
        "excerpt",
        "body",
        "text",
        "summary",
        "preview",
    ]

    for key in candidates:
        value = item.get(key)
        if value:
            return clean_text(value)

    return ""


def normalize_items(packet, max_items):
    raw_items = packet.get("context_packet", {}).get("items", []) or []
    selected = []

    for item in raw_items[:max_items]:
        material = item_material(item)
        selected.append({
            "rank": item.get("rank"),
            "id": item.get("id"),
            "title": item.get("title"),
            "path": item.get("path") or "",
            "tags": item.get("tags") or [],
            "score": item.get("score"),
            "source_ref": item.get("source_ref") or item.get("path") or item.get("title") or item.get("id"),
            "material": material,
            "has_material": bool(material),
        })

    return selected


def tag_map(items):
    counts = {}
    for item in items:
        for tag in item.get("tags") or []:
            tag = str(tag).strip()
            if tag:
                counts[tag] = counts.get(tag, 0) + 1

    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def build_response(obj, max_items=6):
    packet = extract_packet(obj)
    validate_boundary(obj, packet)

    query = packet.get("query") or obj.get("query") or ""
    selected = normalize_items(packet, max_items=max_items)

    material_items = [x for x in selected if x.get("has_material")]
    material_count = len(material_items)
    sources_cited = all(bool(x.get("source_ref")) for x in selected)
    tags = tag_map(selected)

    if selected and material_count == 0:
        quality = "LOW_MATERIAL"
    elif material_count < max(1, len(selected) // 2):
        quality = "PARTIAL_MATERIAL"
    else:
        quality = "USABLE_MATERIAL"

    lines = []
    lines.append("# BRODY LOCAL RESPONSE ENGINE — READONLY")
    lines.append("")
    lines.append(f"- query: {query}")
    lines.append("- role: LOCAL_RESPONSE_ENGINE")
    lines.append("- memory_role: GUIDE_CONTEXT_NAVIGATION_ONLY")
    lines.append("- decision_authority: KX108_ONLY")
    lines.append("- emits_act: false")
    lines.append("- kernel_mutation: false")
    lines.append("- x108_runtime_binding: false")
    lines.append(f"- material_quality: {quality}")
    lines.append("")
    lines.append("## Réponse locale structurée")
    lines.append("")
    lines.append(
        "Brody transforme le packet hydraté en réponse locale structurée. "
        "Cette sortie reste documentaire : elle oriente, cite les sources disponibles, "
        "ne décide pas, ne déclenche rien, et ne modifie pas X108."
    )
    lines.append("")

    lines.append("## Lecture active")
    lines.append("")
    if material_items:
        for item in material_items[:max_items]:
            lines.append(f"### {item.get('rank')}. {item.get('title')}")
            lines.append(f"- score: {item.get('score')}")
            lines.append(f"- source_ref: {item.get('source_ref')}")
            lines.append(f"- tags: {', '.join(item.get('tags') or [])}")
            lines.append("")
            lines.append(compact(item.get("material"), max_chars=700))
            lines.append("")
    else:
        lines.append("Aucun extrait local hydraté exploitable dans ce packet. Réponse limitée aux métadonnées et aux références.")
        lines.append("")

    lines.append("## Carte tags")
    lines.append("")
    if tags:
        for tag, count in list(tags.items())[:16]:
            lines.append(f"- {tag}: {count}")
    else:
        lines.append("- aucun tag exploitable")
    lines.append("")

    lines.append("## Sources")
    lines.append("")
    for item in selected:
        lines.append(f"- {item.get('title')} :: {item.get('source_ref')}")
    lines.append("")

    lines.append("## Boundary")
    lines.append("")
    lines.append("Memory is guide/context/navigation only. Brody consumes hydrated context. KX108 remains sole decision authority.")

    return {
        "status": "BRODY_LOCAL_RESPONSE_ENGINE_READONLY_PASS",
        "created_at": now_iso(),
        "query": query,
        "input_status": obj.get("status"),
        "packet_status": packet.get("status"),
        "results_count": len(selected),
        "items_with_material": material_count,
        "material_quality": quality,
        "sources_cited": sources_cited,
        "response_md": "\n".join(lines),
        "selected_items": selected,
        "tag_counts": tags,
        "readonly": True,
        "memory_role": "GUIDE_CONTEXT_NAVIGATION_ONLY",
        "memory_decision": False,
        "allowed_to_decide": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
        "kernel_mutation": False,
        "x108_runtime_binding": False,
        "x108_merge": False,
        "neo4j_role": "LIVE_GRAPH_MEMORY_SURFACE_ONLY",
        "brody_role": "LOCAL_RESPONSE_ENGINE",
        "ui": False,
        "scope": "BRODY_LOCAL_RESPONSE_ENGINE_READONLY_ONLY",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hydrated-packet-json", required=True)
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    parser.add_argument("--max-items", type=int, default=6)
    args = parser.parse_args()

    obj = load_json(args.hydrated_packet_json)
    response = build_response(obj, max_items=args.max_items)

    if args.out_json:
        out = Path(args.out_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.out_md:
        out = Path(args.out_md)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(response["response_md"], encoding="utf-8")

    print(json.dumps(response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
