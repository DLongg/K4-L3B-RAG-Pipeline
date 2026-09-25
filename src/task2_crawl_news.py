"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
    
-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

from crawl4ai import AsyncWebCrawler


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://thuvienphapluat.vn/phap-luat/dieu-kien-thu-tuc-kinh-doanh-dich-vu-du-lich-hien-nay-duoc-phap-luat-quy-dinh-nhu-the-nao-cac-van-d-845113-7468.html",
    "https://inncare.vn/cam-nang-khach-san/dieu-kien-kinh-doanh-dich-vu-luu-tru-du-lich-2026-cap-nhat-moi-nhat-theo-luat-du-lich/",
    "https://luatvietnam.vn/hanh-chinh/thu-tuc-xin-e-visa-nhap-canh-viet-nam-570-96842-article.html",
    "https://luatminhkhue.vn/quyen-va-nghia-vu-cua-khach-du-lich-theo-quy-dinh-phap-luat-hien-nay.aspx",
    "https://www.vioit.vn/chinh-sach-phat-trien-du-lich-theo-huong-ben-vung-tai-viet-nam.html",
    "https://pbgdpl.camau.gov.vn/quy-dinh-moi-trong-xu-phat-vi-pham-hanh-chinh-linh-vuc-du-lich.7639",
    "https://hanoidep.vn/di-du-lich-o-viet-nam/",
    "https://vinpearl.com/vi/40-dia-diem-du-lich-viet-nam-noi-tieng-nhat-dinh-nen-den-mot-lan",
]


async def crawl_article(url: str, crawler: AsyncWebCrawler | None = None) -> dict:
    """Crawl một URL và trả về dict chứa metadata + nội dung markdown."""
    if crawler is None:
        async with AsyncWebCrawler() as local_crawler:
            return await _do_crawl(local_crawler, url)
    return await _do_crawl(crawler, url)


async def _do_crawl(crawler: AsyncWebCrawler, url: str) -> dict:
    result = await crawler.arun(url=url)
    if hasattr(result, "success") and not result.success:
        error = getattr(result, "error_message", None) or "unknown crawl error"
        raise RuntimeError(f"Crawl failed: {error}")
    title = (result.metadata or {}).get("title") or (result.metadata or {}).get("og:title")
    if not title or not str(title).strip():
        # Fallback title derived from URL slug
        title = url.rstrip("/").split("/")[-1].replace("_", " ").replace("-", " ")

    content = result.markdown or ""
    if not str(content).strip() and hasattr(result, "cleaned_html") and result.cleaned_html:
        content = result.cleaned_html

    return {
        "url": url,
        "title": str(title).strip(),
        "date_crawled": datetime.now().isoformat(),
        "content_markdown": str(content).strip(),
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    async with AsyncWebCrawler() as crawler:
        for index, url in enumerate(ARTICLE_URLS, 1):
            try:
                article = await crawl_article(url, crawler=crawler)
                output = DATA_DIR / f"article_{index:02d}.json"
                output.write_text(
                    json.dumps(article, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                print(f"Saved: {output.name} ({len(article['content_markdown'])} chars)")
            except Exception as error:
                print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())

