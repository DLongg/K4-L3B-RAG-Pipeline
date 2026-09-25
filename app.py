"""Streamlit UI for the Vietnam tourism RAG pipeline."""

from __future__ import annotations

import os
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import SAFE_REFUSAL_MESSAGE, generate_with_citation
from src.task9_retrieval_pipeline import SCORE_THRESHOLD


load_dotenv()

st.set_page_config(
    page_title="RAG Tư Vấn Du Lịch Việt Nam",
    page_icon="🇻🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px; padding-top: 1.5rem;}
    [data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.22); border-radius: 12px;
        padding: .7rem 1rem; background: rgba(128,128,128,.04);
    }
    .pipeline-box {
        border-left: 4px solid #1f77b4; padding: .7rem 1rem;
        background: rgba(31,119,180,.07); border-radius: 6px; margin: .4rem 0 1rem;
    }
    .method-note {font-size: .88rem; color: #6b7280;}
    </style>
    """,
    unsafe_allow_html=True,
)


def env_text(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    return value or default


def route_label(route: str) -> str:
    return {
        "hybrid": "Hybrid: Dense + BM25 + RRF",
        "pageindex": "PageIndex vectorless fallback",
        "none": "Không có nguồn phù hợp",
    }.get(route, route.upper())


def score_label(source: dict) -> tuple[str, str]:
    method = source.get("retrieval_method", "hybrid")
    if method == "hybrid":
        return "RRF score", "Điểm hợp nhất thứ hạng; không phải xác suất đúng."
    if method == "pageindex":
        return "PageIndex rank score", "Điểm xếp hạng node tài liệu của fallback."
    if method == "dense":
        return "Cosine similarity", "Độ tương đồng ngữ nghĩa của BGE-M3."
    return "BM25 score", "Mức khớp từ khóa của BM25."


def render_pipeline_trace(message: dict) -> None:
    route = message.get("retrieval_source", "none")
    elapsed = message.get("elapsed_seconds")
    used_top_k = message.get("top_k")
    sources = message.get("sources", [])

    columns = st.columns(4)
    columns[0].metric("Tuyến truy xuất", "HYBRID" if route == "hybrid" else route.upper())
    columns[1].metric("Nguồn sử dụng", len(sources))
    columns[2].metric("Thời gian", f"{elapsed:.2f}s" if elapsed is not None else "—")
    columns[3].metric("Top-k", used_top_k or len(sources) or "—")

    with st.expander("🔎 Chi tiết cách hệ thống tìm kiếm", expanded=False):
        st.markdown(
            f"""
            **Kết quả đã đi theo:** `{route_label(route)}`

            1. **Dense semantic search** — BGE-M3 biến câu hỏi thành vector 1024 chiều và tìm
               các chunk gần nhất trong ChromaDB theo cosine similarity.
            2. **BM25 lexical search** — tìm thêm các đoạn khớp từ khóa, tên văn bản, số hiệu,
               địa danh và thuật ngữ pháp lý.
            3. **RRF fusion** — hợp nhất hai bảng xếp hạng bằng Reciprocal Rank Fusion (`k=60`).
               RRF được gọi đúng một lần.
            4. **Fallback decision** — so raw dense cosine với threshold `{SCORE_THRESHOLD:.2f}`.
               Nếu thấp hơn ngưỡng, pipeline thử PageIndex vectorless. Khi PageIndex không khả
               dụng, hệ thống giữ kết quả hybrid thay vì làm ứng dụng lỗi.
            5. **Generation** — reorder context, gọi `{env_text('LLM_PROVIDER', 'gemini')}` /
               `{env_text('LLM_MODEL', 'chưa cấu hình')}` và kiểm tra nhãn `[Document N]`.
            """
        )


def render_sources(message: dict) -> None:
    sources = message.get("sources", [])
    if not sources:
        return
    route = message.get("retrieval_source", "hybrid").upper()
    with st.expander(
        f"📚 Xem {len(sources)} nguồn tài liệu trích dẫn [{route}]",
        expanded=False,
    ):
        st.caption(
            "Số Document bên dưới khớp trực tiếp với citation trong câu trả lời. "
            "Điểm của các phương pháp khác nhau không nên so sánh trực tiếp."
        )
        for index, source_item in enumerate(sources, 1):
            metadata = source_item.get("metadata", {})
            title = metadata.get("title", "Tài liệu")
            source_path = metadata.get("source", "Nguồn không xác định")
            doc_type = metadata.get("doc_type", "chung")
            chunk_index = metadata.get("chunk_index", "—")
            page_index = metadata.get("page_index")
            url = metadata.get("url")
            method = source_item.get("retrieval_method", "hybrid")
            score = float(source_item.get("score", 0.0))
            label, explanation = score_label(source_item)

            st.markdown(f"### [Document {index}] {title}")
            info = st.columns([1.1, 1.1, 1.3, 1.1])
            info[0].markdown(f"**Loại**  \n`{str(doc_type).upper()}`")
            info[1].markdown(f"**Phương pháp**  \n`{str(method).upper()}`")
            info[2].markdown(f"**{label}**  \n`{score:.6f}`")
            position = f"Trang {page_index}" if page_index is not None else f"Chunk {chunk_index}"
            info[3].markdown(f"**Vị trí**  \n`{position}`")
            st.caption(f"{explanation} · Tệp: `{Path(str(source_path)).name}`")
            if url:
                st.markdown(f"[Mở liên kết nguồn]({url})")
            with st.expander(f"Xem nội dung chunk của Document {index}"):
                st.text(source_item.get("content", "").strip())
            if index < len(sources):
                st.divider()


def render_assistant_message(message: dict) -> None:
    answer = message.get("content", "")
    if answer == SAFE_REFUSAL_MESSAGE:
        st.warning(answer, icon="⚠️")
        st.caption("Pipeline không tìm được nguồn đủ tin cậy hoặc provider tạm thời không khả dụng.")
    else:
        st.markdown(answer)
    render_pipeline_trace(message)
    render_sources(message)


if "messages" not in st.session_state:
    st.session_state.messages = []

pageindex_ready = bool(os.getenv("PAGEINDEX_API_KEY", "").strip())
embedding_model = env_text("EMBEDDING_MODEL", "BAAI/bge-m3")
llm_provider = env_text("LLM_PROVIDER", "gemini")
llm_model = env_text("LLM_MODEL", "chưa cấu hình")

with st.sidebar:
    st.title("🇻🇳 Vietnam Tourism RAG")
    st.caption("Tra cứu luật, chính sách và cẩm nang du lịch có dẫn nguồn.")

    st.subheader("Cấu hình phiên hỏi đáp")
    top_k = st.slider(
        "Số chunk đưa vào LLM",
        min_value=3,
        max_value=10,
        value=5,
        step=1,
        help="Tăng top-k giúp có thêm ngữ cảnh nhưng làm prompt dài hơn.",
    )
    st.text_input("Chế độ retrieval", value="Hybrid + RRF", disabled=True)
    st.caption("Dense BGE-M3 + BM25, hợp nhất bằng RRF.")

    st.subheader("Trạng thái hệ thống")
    st.write("✅ ChromaDB + BGE-M3 local")
    st.write("✅ BM25 + RRF local")
    st.write(f"{'✅' if pageindex_ready else '⚪'} PageIndex fallback " + ("đã cấu hình" if pageindex_ready else "chưa có API key"))
    st.write(f"✅ LLM: {llm_provider} / {llm_model}")
    st.caption(f"Embedding: `{embedding_model}`")
    st.caption(f"Fallback threshold: `{SCORE_THRESHOLD:.2f}`")

    st.subheader("Dữ liệu đang dùng")
    data_cols = st.columns(3)
    data_cols[0].metric("Legal", "3")
    data_cols[1].metric("News", "7")
    data_cols[2].metric("Chunks", "558")

    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    with st.expander("Luồng xử lý đầy đủ"):
        st.code(
            "Question\n"
            "  ├─ Dense (BGE-M3 + Chroma)\n"
            "  ├─ Sparse (BM25)\n"
            "  └─ RRF fusion\n"
            "       ├─ cosine < threshold → PageIndex\n"
            "       └─ otherwise → Hybrid top-k\n"
            "             ↓\n"
            "       Reorder + LLM + Citation",
            language="text",
        )

st.title("🏛️ Trợ lý RAG Du lịch Việt Nam")
st.markdown(
    "Hỏi về **Luật Du lịch**, **Nghị định 168/2017/NĐ-CP**, **Quyết định 509/QĐ-TTg**, "
    "E-visa, quyền của khách du lịch và các điểm đến. Câu trả lời chỉ được chấp nhận khi "
    "có citation `[Document N]` hợp lệ."
)

with st.expander("💡 Chọn câu hỏi demo", expanded=not st.session_state.messages):
    sample_queries = [
        ("Pháp luật", "Thẻ hướng dẫn viên du lịch quốc tế có thời hạn bao lâu?"),
        ("Nhập cảnh", "Thủ tục xin cấp visa điện tử E-visa vào Việt Nam gồm những gì?"),
        ("Quyền lợi", "Khách du lịch có những quyền và nghĩa vụ gì?"),
        ("Điểm đến", "Hà Nội có những địa điểm du lịch nào đáng chú ý?"),
        ("Ngoài miền", "Cách cấu hình máy chủ Kubernetes production?"),
    ]
    prompt_columns = st.columns(2)
    for index, (category, sample) in enumerate(sample_queries):
        if prompt_columns[index % 2].button(
            f"{category}: {sample}", key=f"sample_{index}", use_container_width=True
        ):
            st.session_state["preset_query"] = sample
            st.rerun()

if not st.session_state.messages:
    st.info(
        "Hãy chọn một câu hỏi demo hoặc nhập câu hỏi bên dưới. Mở phần “Chi tiết cách hệ thống "
        "tìm kiếm” sau câu trả lời để xem tuyến Dense/BM25/RRF/PageIndex.",
        icon="ℹ️",
    )

for stored_message in st.session_state.messages:
    with st.chat_message(stored_message["role"]):
        if stored_message["role"] == "assistant":
            render_assistant_message(stored_message)
        else:
            st.markdown(stored_message["content"])

typed_query = st.chat_input("Nhập câu hỏi về luật, thủ tục hoặc điểm đến du lịch Việt Nam...")
preset_query = st.session_state.pop("preset_query", None)
query = preset_query or typed_query

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        started = time.perf_counter()
        with st.spinner("Dense và BM25 đang tìm kiếm, sau đó RRF hợp nhất kết quả..."):
            result = generate_with_citation(query, top_k=top_k)
        elapsed_seconds = time.perf_counter() - started
        assistant_message = {
            "role": "assistant",
            "content": result.get("answer", SAFE_REFUSAL_MESSAGE),
            "sources": result.get("sources", []),
            "retrieval_source": result.get("retrieval_source", "none"),
            "elapsed_seconds": elapsed_seconds,
            "top_k": top_k,
        }
        render_assistant_message(assistant_message)

    st.session_state.messages.append(assistant_message)
