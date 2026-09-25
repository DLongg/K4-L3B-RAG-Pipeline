"""
Task 9 — Retrieval pipeline hoàn chỉnh.

Luồng xử lý:
    1. Chạy semantic_search và lexical_search.
    2. Fuse hai danh sách bằng RRF đúng một lần.
    3. Lấy best cosine score gốc từ dense results.
    4. Nếu score dưới threshold, thử PageIndex fallback.
    5. Nếu fallback lỗi, trả hybrid results thay vì crash.

Không so sánh threshold với RRF score vì hai thang đo khác nhau.
"""

import argparse
import json
import os
import logging
import math
from dotenv import load_dotenv

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank_rrf
from .task8_pageindex_vectorless import pageindex_search

load_dotenv()

_ENV_THRESHOLD = os.getenv("SCORE_THRESHOLD")
try:
    SCORE_THRESHOLD = float(_ENV_THRESHOLD) if _ENV_THRESHOLD and _ENV_THRESHOLD.strip() else 0.3
    if not math.isfinite(SCORE_THRESHOLD) or not -1 <= SCORE_THRESHOLD <= 1:
        raise ValueError("Invalid cosine threshold")
except ValueError:
    SCORE_THRESHOLD = 0.3
    logging.getLogger(__name__).warning("Invalid SCORE_THRESHOLD; using uncalibrated default 0.3")
DEFAULT_TOP_K = 5


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
) -> list[dict]:
    """Trả về hybrid hoặc pageindex SearchResult."""
    if not query.strip() or top_k <= 0:
        return []

    # 1. Chạy semantic_search và lexical_search
    dense = _safe_search(semantic_search, query, top_k * 2)
    sparse = _safe_search(lexical_search, query, top_k * 2) if use_reranking else []

    # 2. Fuse hai danh sách bằng RRF đúng một lần
    hybrid = (
        rerank_rrf([dense, sparse], top_k=top_k)
        if use_reranking
        else dense[:top_k]
    )

    # 3. Lấy best cosine score gốc từ dense results
    best_dense_score = max((item["score"] for item in dense), default=-1.0)

    # 4. Nếu score dưới threshold, thử PageIndex fallback
    if not dense or best_dense_score < score_threshold:
        try:
            fallback = pageindex_search(query, top_k=top_k)
            if fallback:
                return fallback[:top_k]
        except Exception:
            pass

    # 5. Mặc định trả về kết quả hybrid
    return hybrid[:top_k]


def _safe_search(search, query, top_k):
    try:
        return search(query, top_k=top_k)
    except Exception as error:
        logging.getLogger(__name__).warning("%s unavailable (%s)", search.__name__, type(error).__name__)
        return []


def calibrate_threshold(samples: list[dict]) -> dict:
    """Choose threshold by balanced accuracy on labelled raw dense scores.

    in_domain=True means score should pass; False means fallback should run.
    This measures routing, not answer quality. Use a separate held-out set.
    """
    if not samples or {item["in_domain"] for item in samples} != {True, False}:
        raise ValueError("Calibration requires both in-domain and out-of-domain samples")
    scores = sorted({float(item["score"]) for item in samples})
    if any(not math.isfinite(score) or not -1 <= score <= 1 for score in scores):
        raise ValueError("Expected finite cosine scores in [-1, 1]")
    candidates = sorted({-1.0, 1.0, *scores, *[(a + b) / 2 for a, b in zip(scores, scores[1:])]})
    rows = []
    positives = sum(item["in_domain"] for item in samples)
    negatives = len(samples) - positives
    for threshold in candidates:
        tp = sum(item["in_domain"] and item["score"] >= threshold for item in samples)
        tn = sum(not item["in_domain"] and item["score"] < threshold for item in samples)
        rows.append({"threshold": threshold, "balanced_accuracy": (tp / positives + tn / negatives) / 2,
                     "in_domain_pass_rate": tp / positives, "out_of_domain_fallback_rate": tn / negatives})
    best = max(rows, key=lambda row: (row["balanced_accuracy"], row["out_of_domain_fallback_rate"], -row["threshold"]))
    return {"selected": best, "sample_count": len(samples), "sweep": rows}


def calibrate_queries(cases: list[dict]) -> dict:
    """Run dense retrieval once per labelled query, then sweep thresholds."""
    samples = []
    for case in cases:
        query = case.get("query", "")
        label = case.get("in_domain")
        if not query.strip() or not isinstance(label, bool):
            raise ValueError("Each calibration case needs query and boolean in_domain")
        dense = semantic_search(query, top_k=1)
        score = dense[0]["score"] if dense else -1.0
        samples.append({"query": query, "in_domain": label, "score": score})
    result = calibrate_threshold(samples)
    result["samples"] = samples
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibrate", type=str, help="JSON file of query/in_domain cases")
    args = parser.parse_args()
    if args.calibrate:
        with open(args.calibrate, encoding="utf-8") as handle:
            print(json.dumps(calibrate_queries(json.load(handle)), ensure_ascii=False, indent=2))
    else:
        for result in retrieve("test query", top_k=3):
            print(result)
