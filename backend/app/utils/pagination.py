from __future__ import annotations

from app.core.config import settings


def normalize_page(page: int = 1, page_size: int | None = None) -> tuple[int, int, int]:
    clean_page = max(1, page)
    clean_page_size = min(200, max(1, page_size or settings.default_page_size))
    offset = (clean_page - 1) * clean_page_size
    return clean_page, clean_page_size, offset

