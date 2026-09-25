"""Offline, reproducible four-metric A/B retrieval evaluation.

These are transparent proxy metrics, not Ragas scores. They let the project be
audited without consuming an LLM API quota; generation is verified separately.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.task4_chunking_indexing import embed_texts
from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search
from src.task7_reranking import rerank_rrf

EVAL_DIR = ROOT / "group_project/evaluation"


def cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    denominator = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return max(0.0, min(1.0, numerator / denominator)) if denominator else 0.0


def expected_files(value: str) -> set[str]:
    return {part.strip() for part in value.split(";") if part.strip()}


def source_name(item: dict) -> str:
    source = str(item.get("metadata", {}).get("source", "")).replace("\\", "/")
    return source.rsplit("/", 1)[-1]


def evaluate_case(case: dict, config: str) -> dict:
    started = time.perf_counter()
    dense = semantic_search(case["question"], top_k=10)
    if config == "dense":
        results = dense[:5]
    else:
        sparse = lexical_search(case["question"], top_k=10)
        results = rerank_rrf([dense, sparse], top_k=5)
    latency_ms = (time.perf_counter() - started) * 1000

    expected = expected_files(case["expected_context"])
    names = [source_name(item) for item in results]
    relevance = [name in expected for name in names]
    first_rank = next((index for index, relevant in enumerate(relevance, 1) if relevant), None)

    texts = [case["question"], case["expected_answer"], *[item["content"] for item in results]]
    vectors = embed_texts(texts)
    question_vector, reference_vector, *context_vectors = vectors
    support = max((cosine(reference_vector, vector) for vector in context_vectors), default=0.0)
    return {
        "question": case["question"],
        "expected_context": sorted(expected),
        "retrieved_sources": names,
        "metrics": {
            "faithfulness_proxy": support,
            "answer_relevance_proxy": cosine(question_vector, reference_vector),
            "context_recall": float(any(relevance)),
            "context_precision": sum(relevance) / len(results) if results else 0.0,
        },
        "reciprocal_rank": 1.0 / first_rank if first_rank else 0.0,
        "retrieval_ms": latency_ms,
    }


def main() -> None:
    golden = json.loads((EVAL_DIR / "golden_dataset.json").read_text(encoding="utf-8"))
    # Exclude one-time model loading from both configuration latency means.
    semantic_search("khởi động mô hình đánh giá", top_k=1)
    payload = {
        "method": "offline_semantic_proxy",
        "definitions": {
            "faithfulness_proxy": "maximum BGE-M3 cosine similarity between the reference answer and a retrieved chunk",
            "answer_relevance_proxy": "BGE-M3 cosine similarity between question and reference answer",
            "context_recall": "1 when at least one expected source file appears in top-5, otherwise 0",
            "context_precision": "fraction of top-5 chunks whose source file is expected",
            "reciprocal_rank": "1/rank of the first expected source file",
        },
        "results": {},
        "summary": {},
    }
    for config in ("dense", "hybrid_rrf"):
        rows = []
        for index, case in enumerate(golden, 1):
            rows.append(evaluate_case(case, config))
            print(f"{config}: {index}/{len(golden)}", flush=True)
        payload["results"][config] = rows
        metric_names = rows[0]["metrics"]
        payload["summary"][config] = {
            **{
                name: statistics.fmean(row["metrics"][name] for row in rows)
                for name in metric_names
            },
            "mrr": statistics.fmean(row["reciprocal_rank"] for row in rows),
            "mean_retrieval_ms": statistics.fmean(row["retrieval_ms"] for row in rows),
        }
    output = EVAL_DIR / "offline_evaluation_results.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
