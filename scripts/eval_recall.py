"""
Recall@k harness against the golden set.
Run with API server up: python scripts/eval_recall.py
Outputs a table to stdout and a timestamped JSON to eval/results/.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

API_URL = "http://localhost:8000/api/v1/query"
GOLDEN_SET = Path(__file__).parent.parent / "eval" / "golden_set.json"
RESULTS_DIR = Path(__file__).parent.parent / "eval" / "results"
K_VALUES = [1, 3, 5]
MAX_K = max(K_VALUES)


def get_top_sources(query: str, top_k: int) -> list[str]:
    resp = httpx.post(API_URL, json={"query": query, "top_k": top_k}, timeout=30.0)
    resp.raise_for_status()
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[len("data: "):])
            if payload.get("type") == "chunks":
                return [c["metadata"].get("source", "?") for c in payload["chunks"]]
    return []


def main():
    cases = json.loads(GOLDEN_SET.read_text())
    per_case = []

    for case in cases:
        sources = get_top_sources(case["query"], MAX_K)
        hits = {k: case["expected_source"] in sources[:k] for k in K_VALUES}
        per_case.append({**case, "retrieved_sources": sources, "hits": hits})

    print(f"{'query':<55} {'expected':<20} {'@1':<4} {'@3':<4} {'@5':<4}")
    for c in per_case:
        h = c["hits"]
        print(f"{c['query'][:53]:<55} {c['expected_source']:<20} "
              f"{'Y' if h[1] else 'N':<4} {'Y' if h[3] else 'N':<4} {'Y' if h[5] else 'N':<4}")

    n = len(per_case)
    summary = {k: sum(c["hits"][k] for c in per_case) / n for k in K_VALUES}
    print("\nrecall@k:")
    for k in K_VALUES:
        print(f"  recall@{k}: {sum(c['hits'][k] for c in per_case)}/{n} ({summary[k]:.2f})")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"recall_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "cases": per_case,
    }, indent=2))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
