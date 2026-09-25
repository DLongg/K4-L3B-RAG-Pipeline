"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if not query.strip() or top_k <= 0:
        return []

    collection = get_collection()
    query_vector = embed_texts([query])[0]

    response = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    if not response or not response.get("ids") or not response["ids"][0]:
        return []

    results = []
    ids = response["ids"][0]
    documents = response.get("documents", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]

    for item_id, content, metadata, distance in zip(ids, documents, metadatas, distances):
        score = float(max(0.0, min(1.0, 1.0 - distance)))
        cleaned_meta = dict(metadata) if metadata else {}
        if cleaned_meta.get("url") == "":
            cleaned_meta["url"] = None
        results.append({
            "id": item_id,
            "content": content,
            "score": score,
            "metadata": cleaned_meta,
            "retrieval_method": "dense",
        })

    sorted_results = sorted(results, key=lambda item: item["score"], reverse=True)
    return sorted_results[:top_k]


if __name__ == "__main__":
    for res in semantic_search("test query", top_k=3):
        print(res)
