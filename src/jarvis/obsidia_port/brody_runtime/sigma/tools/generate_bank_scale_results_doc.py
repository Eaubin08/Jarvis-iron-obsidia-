import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ART = ROOT / "artifacts" / "p2_bank_scale"
DOC = ROOT / "docs" / "P2_BANK_SCALE_RESULTS.md"
TIERS = [1000, 10000, 100000]


def find_summary(size: int):
    if not ART.exists():
        return None
    matches = sorted(
        ART.glob(f"{size}_cases_*_workers/bank_scale_summary.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def fmt_dist(d: dict, keys: list[str]) -> str:
    return " / ".join(f"{k}={d.get(k, 0)}" for k in keys)


def load_rows():
    rows = []
    missing = []
    for size in TIERS:
        summary_path = find_summary(size)
        if summary_path is None:
            missing.append(size)
            continue
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        workers_match = re.search(rf"{size}_cases_(\d+)_workers", summary_path.as_posix())
        workers = int(workers_match.group(1)) if workers_match else data.get("workers", "?")
        rows.append(
            {
                "size": size,
                "workers": workers,
                "total_cases": data.get("total_cases", 0),
                "failed_cases": data.get("failed_cases", 0),
                "family_counts": data.get("family_counts", {}),
                "gate_counts": data.get("gate_counts", {}),
                "gap_counts": data.get("gap_counts", {}),
                "total_elapsed_s": data.get("total_elapsed_s", 0.0),
                "mean_elapsed_ms": data.get("mean_elapsed_ms", 0.0),
                "throughput_cases_per_s": data.get("throughput_cases_per_s", 0.0),
                "summary_path": rel(summary_path),
                "report_path": rel(Path(data.get("report_json", ""))) if data.get("report_json") else "",
                "csv_path": rel(Path(data.get("report_csv", ""))) if data.get("report_csv") else "",
            }
        )
    rows.sort(key=lambda r: r["size"])
    return rows, missing


def build_markdown(rows, missing):
    lines = []
    lines.append("# P2 Bank Scale Results")
    lines.append("")
    lines.append("## Status")
    lines.append("")
    lines.append("Generated from local scale artifact summaries when available.")
    lines.append("")
    if rows:
        lines.append(f"Available tiers: {', '.join(str(r['size']) for r in rows)}")
    else:
        lines.append("Available tiers: none")
    if missing:
        lines.append(f"Missing tiers: {', '.join(str(x) for x in missing)}")
    else:
        lines.append("Missing tiers: none")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Tier | Cases | Workers | Failed | Family distribution | Gate distribution | Gap distribution | Total elapsed (s) | Mean elapsed (ms) | Throughput (cases/s) | Summary |")
    lines.append("|---|---:|---:|---:|---|---|---|---:|---:|---:|---|")
    for r in rows:
        lines.append(
            "| {size} | {total_cases} | {workers} | {failed_cases} | {family} | {gates} | {gaps} | {total:.3f} | {mean:.3f} | {tp:.3f} | `{summary}` |".format(
                size=r["size"],
                total_cases=r["total_cases"],
                workers=r["workers"],
                failed_cases=r["failed_cases"],
                family=fmt_dist(r["family_counts"], ["allow", "hold", "block"]),
                gates=fmt_dist(r["gate_counts"], ["ALLOW", "HOLD", "BLOCK", "ERROR"]),
                gaps=fmt_dist(r["gap_counts"], ["MATCH", "HARDER_THAN_BUSINESS", "SOFTER_THAN_BUSINESS", "UNKNOWN"]),
                total=float(r["total_elapsed_s"]),
                mean=float(r["mean_elapsed_ms"]),
                tp=float(r["throughput_cases_per_s"]),
                summary=r["summary_path"],
            )
        )
    lines.append("")
    lines.append("## Reading rule")
    lines.append("")
    lines.append("- 1k = public validation tier")
    lines.append("- 10k = local auto-validation tier")
    lines.append("- 100k = execution/stress tier")
    lines.append("")
    lines.append("## Artifact pointers")
    lines.append("")
    for r in rows:
        lines.append(f"- {r['size']} → summary: `{r['summary_path']}`")
        if r["report_path"]:
            lines.append(f"  - report_json: `{r['report_path']}`")
        if r["csv_path"]:
            lines.append(f"  - report_csv: `{r['csv_path']}`")
    lines.append("")
    return "\n".join(lines) + "\n"


def main():
    rows, missing = load_rows()
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(build_markdown(rows, missing), encoding="utf-8")
    print(json.dumps({
        "doc": rel(DOC),
        "tiers_found": [r["size"] for r in rows],
        "missing_tiers": missing,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
