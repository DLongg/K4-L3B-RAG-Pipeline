"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

from rank_bm25 import BM25Okapi


CORPUS: list[dict] = []
_BM25_INDEX = None
_INDEXED_CORPUS_LEN = 0


def load_corpus() -> list[dict]:
    """Tải corpus từ standardized documents nếu CORPUS chưa có."""
    global CORPUS
    if not CORPUS:
        try:
            from .task4_chunking_indexing import load_documents, chunk_documents
            docs = load_documents()
            CORPUS = chunk_documents(docs)
        except Exception:
            CORPUS = []
    return CORPUS


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    global _BM25_INDEX, _INDEXED_CORPUS_LEN
    if not corpus:
        return None
    tokenized = [item["content"].lower().split() for item in corpus]
    _BM25_INDEX = BM25Okapi(tokenized)
    _INDEXED_CORPUS_LEN = len(corpus)
    return _BM25_INDEX


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    global _BM25_INDEX, _INDEXED_CORPUS_LEN
    corpus = CORPUS if CORPUS else load_corpus()
    if not corpus or not query.strip() or top_k <= 0:
        return []

    if _BM25_INDEX is None or _INDEXED_CORPUS_LEN != len(corpus):
        bm25 = build_bm25_index(corpus)
    else:
        bm25 = _BM25_INDEX

    if bm25 is None:
        return []

    tokens = query.lower().split()
    scores = bm25.get_scores(tokens)

    scored_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )

    results = []
    for idx in scored_indices[:top_k]:
        item = corpus[idx]
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": float(scores[idx]),
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })

    return results


if __name__ == "__main__":
    for res in lexical_search("test query", top_k=3):
        print(res)
