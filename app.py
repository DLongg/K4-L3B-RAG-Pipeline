import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="RAG Tư Vấn Du Lịch Việt Nam",
    page_icon="🇻🇳",
    layout="wide",
)

# Khởi tạo session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar cấu hình và thông tin
with st.sidebar:
    st.title("🇻🇳 Du Lịch Việt Nam RAG")
    st.caption("Hệ thống hỏi đáp & tư vấn quy định, chính sách và cẩm nang du lịch.")

    st.markdown("---")
    st.subheader("⚙️ Cấu hình truy xuất")
    top_k = st.slider("Số chunks truy xuất (top_k)", min_value=3, max_value=10, value=5, step=1)

    if st.button("🗑️ Xóa lịch sử trò chuyện", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.subheader("💡 Câu hỏi gợi ý")
    sample_queries = [
        "Điều kiện kinh doanh dịch vụ lữ hành quốc tế gồm những gì?",
        "Thủ tục xin cấp visa điện tử (E-visa) vào Việt Nam?",
        "Quyền và nghĩa vụ của khách du lịch được quy định thế nào?",
        "Mức xử phạt hành vi không niêm yết giá hàng hóa dịch vụ du lịch?",
    ]
    for sq in sample_queries:
        if st.button(sq, key=f"btn_{sq}", use_container_width=True):
            st.session_state["preset_query"] = sq
            st.rerun()

    st.markdown("---")
    st.caption("🔹 Pipeline: ChromaDB (Dense) + BM25 (Sparse) + Reciprocal Rank Fusion (RRF)")


st.title("🏛️ Trợ Lý AI Tư Vấn Du Lịch Việt Nam")
st.markdown(
    "Hệ thống RAG hỗ trợ tra cứu các văn bản pháp luật (Luật Du lịch, Nghị định 168/2017/NĐ-CP, "
    "Quyết định 509/QĐ-TTg) và cẩm nang, tin tức du lịch chính thống."
)

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            retrieval_method = msg.get("retrieval_source", "hybrid").upper()
            with st.expander(f"📚 Xem {len(msg['sources'])} nguồn tài liệu trích dẫn [{retrieval_method}]"):
                for i, src in enumerate(msg["sources"], 1):
                    meta = src.get("metadata", {})
                    title = meta.get("title", "Tài liệu")
                    source = meta.get("source", "Nguồn")
                    doc_type = meta.get("doc_type", "Chung")
                    url = meta.get("url")
                    score = src.get("score", 0.0)

                    st.markdown(f"**[{i}] {title}** ({doc_type.upper()}) — *Score:* `{score:.4f}`")
                    st.caption(f"📁 Tệp nguồn: `{source}`" + (f" | 🔗 [Liên kết nguồn]({url})" if url else ""))
                    st.text(src.get("content", "").strip())
                    st.markdown("---")

# Xử lý input từ chat hoặc từ câu hỏi gợi ý
user_input = st.chat_input("Nhập câu hỏi về luật, quy định hoặc địa điểm du lịch...")
preset_query = st.session_state.pop("preset_query", None)
query = preset_query or user_input

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm tài liệu và sinh câu trả lời có trích dẫn..."):
            result = generate_with_citation(query, top_k=top_k)
            answer = result.get("answer", "")
            sources = result.get("sources", [])
            retrieval_source = result.get("retrieval_source", "none")

        st.markdown(answer)

        if sources:
            with st.expander(f"📚 Xem {len(sources)} nguồn tài liệu trích dẫn [{retrieval_source.upper()}]"):
                for i, src in enumerate(sources, 1):
                    meta = src.get("metadata", {})
                    title = meta.get("title", "Tài liệu")
                    source = meta.get("source", "Nguồn")
                    doc_type = meta.get("doc_type", "Chung")
                    url = meta.get("url")
                    score = src.get("score", 0.0)

                    st.markdown(f"**[{i}] {title}** ({doc_type.upper()}) — *Score:* `{score:.4f}`")
                    st.caption(f"📁 Tệp nguồn: `{source}`" + (f" | 🔗 [Liên kết nguồn]({url})" if url else ""))
                    st.text(src.get("content", "").strip())
                    st.markdown("---")

    # Lưu tin nhắn vào session state
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
    })
