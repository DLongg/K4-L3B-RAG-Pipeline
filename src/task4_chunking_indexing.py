"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DIM = 1024

COLLECTION_NAME = "rag_documents"

_MODEL_CACHE = None


def get_embedding_model():
    """Lazy load SentenceTransformer model."""
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        from sentence_transformers import SentenceTransformer
        _MODEL_CACHE = SentenceTransformer(EMBEDDING_MODEL)
    return _MODEL_CACHE


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Dispatch embedding theo EMBEDDING_PROVIDER trong .env."""
    if not texts:
        return []
    provider = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").lower()

    if provider == "sentence_transformers":
        model = get_embedding_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
    elif provider == "gemini":
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
        result = client.models.embed_content(
            model=model_name,
            contents=texts,
        )
        return [e.values for e in result.embeddings]
    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        response = client.embeddings.create(
            input=texts,
            model=model_name,
        )
        return [item.embedding for item in response.data]
    else:
        model = get_embedding_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for path in STANDARDIZED_DIR.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        title = path.stem
        url = None
        doc_type = "legal" if "legal" in path.parts else "news"

        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith("# ") and title == path.stem:
                title = line_str.replace("# ", "").strip()
            elif line_str.startswith("**Source:**"):
                url_part = line_str.replace("**Source:**", "").strip()
                if url_part:
                    url = url_part

        documents.append({
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": content,
            "metadata": {
                "source": path.name,
                "title": title,
                "doc_type": doc_type,
                "url": url,
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for document in documents:
        split_texts = splitter.split_text(document["content"])
        for index, text in enumerate(split_texts):
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {
                    **document["metadata"],
                    "chunk_index": index,
                },
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    if not chunks:
        return []
    vectors = embed_texts([chunk["content"] for chunk in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    return chunks


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    collection = get_collection()
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=[chunk["metadata"] for chunk in chunks],
    )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
