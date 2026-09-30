from __future__ import annotations

import json
from pathlib import Path


ARTIFACT_ROOT = Path("artifacts") / "p2_bank_replay"
DOC_PATH = Path("docs") / "P2_BANK_REPLAY_RESULTS.md"
TIERS = [1000, 10000, 100000]
WORKERS = 6


def load_summary(tier: int) -> dict | None:
    path = ARTIFACT_ROOT / f"{tier}_cases_{WORKERS}_workers" / "bank_replay_summary.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    found = []
    missing = []
    rows = []

    for tier in TIERS:
        summary = load_summary(tier)
        if summary is None:
            missing.append(tier)
            continue

        found.append(tier)
        rows.append(
            "| {tier} | {cases} | {workers} | {failed} | {family} | {first_gate} | {second_gate} | {stable} | {gate_match} | {verdict_match} | {reason_match} | {hash_match} | {unsafe} | {softer} | {elapsed:.3f} | {mean:.3f} | {throughput:.3f} | `{summary_path}` |".format(
                tier=tier,
                cases=summary["total_cases"],
                workers=summary["workers"],
                failed=summary["failed_cases"],
                family=" / ".join(f"{k}={v}" for k, v in sorted(summary["family_counts"].items())),
                first_gate=" / ".join(f"{k}={v}" for k, v in sorted(summary["first_gate_counts"].items())),
                second_gate=" / ".join(f"{k}={v}" for k, v in sorted(summary["second_gate_counts"].items())),
                stable=summary["replay_stable_count"],
                gate_match=summary["replay_gate_match_count"],
                verdict_match=summary["replay_verdict_match_count"],
                reason_match=summary["replay_reason_match_count"],
                hash_match=summary["replay_hash_match_count"],
                unsafe=summary["unsafe_allow_count"],
                softer=summary["softer_drift_count"],
                elapsed=summary["total_elapsed_s"],
                mean=summary["mean_elapsed_ms"],
                throughput=summary["throughput_cases_per_s"],
                summary_path=str((ARTIFACT_ROOT / f"{tier}_cases_{WORKERS}_workers" / "bank_replay_summary.json").as_posix()),
            )
        )

    text = "\n".join(
        [
            "# P2 BANK REPLAY RESULTS",
            "",
            "## Status",
            "",
            "Generated from local replay artifact summaries when available.",
            "",
            f"Available tiers: {', '.join(map(str, found)) if found else 'none'}",
            f"Missing tiers: {', '.join(map(str, missing)) if missing else 'none'}",
            "",
            "## Table",
            "",
            "| Tier | Cases | Workers | Failed | Family distribution | First gate distribution | Second gate distribution | Replay stable | Gate match | Verdict match | Reason match | Hash match | Unsafe allow | Softer drift | Total elapsed (s) | Mean elapsed (ms) | Throughput (cases/s) | Summary |",
            "|---|---:|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
            *rows,
            "",
        ]
    )

    DOC_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"doc": str(DOC_PATH), "tiers_found": found, "missing_tiers": missing}, ensure_ascii=False))


if __name__ == "__main__":
    main()