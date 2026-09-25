"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    if not ranked_lists or top_k <= 0:
        return []

    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            if item_id not in items:
                items[item_id] = item

    ranked_ids = sorted(scores, key=lambda i: scores[i], reverse=True)
    results = []
    for item_id in ranked_ids[:top_k]:
        result = items[item_id].copy()
        result["score"] = float(scores[item_id])
        result["retrieval_method"] = "hybrid"
        results.append(result)

    return results


if __name__ == "__main__":
    sample_dense = [{"id": "doc1", "content": "A", "score": 0.9, "metadata": {}, "retrieval_method": "dense"}]
    sample_bm25 = [{"id": "doc1", "content": "A", "score": 5.0, "metadata": {}, "retrieval_method": "bm25"}]
    print(rerank_rrf([sample_dense, sample_bm25], top_k=1))
