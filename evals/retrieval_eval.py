"""Offline retrieval evaluation for the OKF knowledge search.

Measures whether the documents an answer needs are actually retrieved, which
is the main factual-quality lever in a retrieval-grounded assistant: the model
cannot ground an answer in a document it never sees. No model or network calls.

Usage, from the backend repository root:
    python -m evals.retrieval_eval            # summary + failing cases
    python -m evals.retrieval_eval --verbose  # every case with its ranking
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from app.ai.okf import retrieve_with_sources

CASES_PATH = Path(__file__).with_name("retrieval_cases.json")


@dataclass(frozen=True)
class CaseResult:
    id: str
    style: str
    hit: bool
    rank: int | None  # 1-based rank of the first expected document
    retrieved: tuple[str, ...]


def run(k: int | None = None) -> tuple[list[CaseResult], dict[str, float]]:
    spec = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    k = k or spec["k"]
    results: list[CaseResult] = []
    for case in spec["cases"]:
        sources = retrieve_with_sources(case["query"], case.get("topic", "general"), limit=k)
        retrieved = tuple(source["path"] for source in sources.sources)
        ranks = [index + 1 for index, path in enumerate(retrieved) if path in case["expected"]]
        results.append(CaseResult(case["id"], case.get("style", "direct"), bool(ranks), ranks[0] if ranks else None, retrieved))

    def recall(items: list[CaseResult]) -> float:
        return round(sum(item.hit for item in items) / len(items), 3) if items else 0.0

    def mrr(items: list[CaseResult]) -> float:
        return round(sum(1 / item.rank for item in items if item.rank) / len(items), 3) if items else 0.0

    direct = [item for item in results if item.style == "direct"]
    paraphrase = [item for item in results if item.style == "paraphrase"]
    metrics = {
        "k": k,
        "cases": len(results),
        f"recall@{k}": recall(results),
        "mrr": mrr(results),
        f"recall@{k}_direct": recall(direct),
        f"recall@{k}_paraphrase": recall(paraphrase),
    }
    return results, metrics


def main() -> None:
    verbose = "--verbose" in sys.argv
    results, metrics = run()
    print(json.dumps(metrics, indent=2))
    for item in results:
        if verbose or not item.hit:
            mark = "PASS" if item.hit else "MISS"
            print(f"{mark} [{item.style}] {item.id}: rank={item.rank} retrieved={list(item.retrieved)}")


if __name__ == "__main__":
    main()
