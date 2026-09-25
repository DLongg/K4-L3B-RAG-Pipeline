"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _ocr_scanned_pdf(path: Path) -> str:
    """Render and OCR a scanned PDF when MarkItDown finds no text layer."""
    try:
        import fitz
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as error:
        raise RuntimeError(
            "PDF scan detected but OCR is unavailable. Install with "
            "python -m pip install pymupdf rapidocr-onnxruntime."
        ) from error

    engine = RapidOCR()
    pages = []
    with fitz.open(path) as document:
        for page in document:
            image = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            result, _ = engine(image.tobytes("png"))
            lines = [item[1].strip() for item in (result or []) if item[1].strip()]
            if lines:
                pages.append("\n".join(lines))
    return "\n\n".join(pages).strip()


def convert_legal_docs() -> None:
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkItDown()
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() in {".pdf", ".doc", ".docx"}:
            result = converter.convert(str(path))
            content = (result.text_content or "").strip()
            if not content:
                content = _ocr_scanned_pdf(path)
            output_path = output_dir / f"{path.stem}.md"
            if content:
                output_path.write_text(content + "\n", encoding="utf-8")
            elif output_path.exists() and output_path.stat().st_size == 0:
                output_path.unlink()


def convert_news_articles() -> None:
    import json

    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        title = str(data.get("title", "")).strip()
        url = str(data.get("url", "")).strip()
        crawled = str(data.get("date_crawled", "")).strip()
        content = str(data.get("content_markdown", "")).strip()
        if not all((title, url, crawled, content)):
            continue
        header = (
            f"# {title}\n\n"
            f"**Source:** {url}\n\n"
            f"**Crawled:** {crawled}\n\n---\n\n"
        )
        (output_dir / f"{path.stem}.md").write_text(
            header + content + "\n", encoding="utf-8"
        )


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
