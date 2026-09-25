"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os
from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "")

SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên gia tư vấn thông tin và quy định du lịch Việt Nam.
Hãy trả lời câu hỏi của người dùng DỰA HOÀN TOÀN vào các tài liệu được cung cấp trong Context.
Mỗi luận điểm hoặc thông tin trả lời bắt buộc phải trích dẫn rõ nguồn tương ứng (Ví dụ: [Document 1], hoặc tên văn bản/điều luật).
Nếu thông tin trong Context không đủ để trả lời chính xác hoặc câu hỏi nằm ngoài phạm vi tài liệu, bạn HÃY TỪ CHỐI bằng câu: "Tôi không thể xác minh thông tin này từ nguồn hiện có." và tuyệt đối không tự bịa đặt thông tin."""

SAFE_REFUSAL_MESSAGE = "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context (giải quyết Lost-in-the-middle)."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "Tài liệu")
        source = metadata.get("source", "Nguồn")
        parts.append(
            f"[Document {index} | Title: {title} | Source: {source}]\n{chunk.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    provider = os.getenv("LLM_PROVIDER", LLM_PROVIDER).lower()
    model_name = os.getenv("LLM_MODEL", LLM_MODEL)

    if provider == "gemini":
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        target_model = model_name or "gemini-2.5-flash"
        response = client.models.generate_content(
            model=target_model,
            contents=f"{system_prompt}\n\n{user_message}",
        )
        return response.text or ""

    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        target_model = model_name or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
        )
        return response.choices[0].message.content or ""

    elif provider == "anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        target_model = model_name or "claude-3-5-haiku-20241022"
        response = client.messages.create(
            model=target_model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=1024,
            temperature=TEMPERATURE,
        )
        return response.content[0].text or ""

    else:
        # Fallback to gemini if available
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{system_prompt}\n\n{user_message}",
        )
        return response.text or ""


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    if not query.strip() or top_k <= 0:
        return {
            "answer": SAFE_REFUSAL_MESSAGE,
            "sources": [],
            "retrieval_source": "none",
        }

    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return {
            "answer": SAFE_REFUSAL_MESSAGE,
            "sources": [],
            "retrieval_source": "none",
        }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
        if not answer or not answer.strip():
            answer = SAFE_REFUSAL_MESSAGE
    except Exception as error:
        print(f"LLM generation warning: {error}")
        answer = SAFE_REFUSAL_MESSAGE

    method = chunks[0].get("retrieval_method", "hybrid")
    retrieval_source = "pageindex" if method == "pageindex" else "hybrid"

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    print(generate_with_citation("Thủ tục xin cấp thẻ hướng dẫn viên du lịch gồm những gì?"))
