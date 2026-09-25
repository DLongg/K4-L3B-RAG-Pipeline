"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm: Du lịch Việt Nam.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Tài liệu đã thu thập trong data/landing/legal/:
    - Luat-Du-lich-so-092017QH14.pdf: Luật Du lịch số 09/2017/QH14 (Quốc hội)
    - 168.signed.pdf: Nghị định 168/2017/NĐ-CP hướng dẫn thi hành Luật Du lịch (Chính phủ)
    - 509-ttg.signed.pdf: Quyết định 509/QĐ-TTg phê duyệt Quy hoạch hệ thống du lịch 2021-2030 (Thủ tướng)
"""

from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

# Danh sách nguồn tài liệu pháp luật về Du lịch Việt Nam
LEGAL_SOURCES = {
    "Luat-Du-lich-so-092017QH14.pdf": {
        "title": "Luật Du lịch số 09/2017/QH14",
        "source": "Cổng thông tin Quốc hội / Bộ Văn hóa Thể thao và Du lịch",
    },
    "168.signed.pdf": {
        "title": "Nghị định 168/2017/NĐ-CP quy định chi tiết một số điều của Luật Du lịch",
        "source": "Cổng thông tin điện tử Chính phủ",
    },
    "509-ttg.signed.pdf": {
        "title": "Quyết định 509/QĐ-TTg phê duyệt Quy hoạch hệ thống du lịch 2021-2030",
        "source": "Cổng thông tin điện tử Chính phủ",
    },
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Xác nhận và kiểm tra tối thiểu 3 tài liệu pháp luật PDF/DOCX trong data/landing/legal/."""
    setup_directory()
    found_files = [
        f for f in DATA_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in {".pdf", ".doc", ".docx"}
    ]

    print(f"Found {len(found_files)} legal documents in {DATA_DIR}:")
    for file_path in found_files:
        info = LEGAL_SOURCES.get(file_path.name, {"title": file_path.stem})
        size_kb = file_path.stat().st_size / 1024
        print(f" - [{file_path.name}] ({size_kb:.1f} KB): {info['title']}")

    if len(found_files) < 3:
        raise RuntimeError(f"Cần tối thiểu 3 tài liệu, hiện có {len(found_files)}")
    print("Verification completed: Tối thiểu 3 tài liệu pháp luật hợp lệ.")


if __name__ == "__main__":
    setup_directory()
    download_documents()
