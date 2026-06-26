from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_admin
from app.core.response import ok
from app.utils.pagination import normalize_page

router = APIRouter(prefix="/api/logs", tags=["logs"], dependencies=[Depends(get_current_admin)])


@router.get("")
def list_logs(page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1)):
    page_num, clean_page_size, _ = normalize_page(page, page_size)
    return ok({"items": [], "page": page_num, "page_size": clean_page_size, "total": 0, "pages": 0})


@router.get("/download")
def download_logs():
    return ok({"message": "log download placeholder"})


@router.delete("/cleanup")
def cleanup_logs():
    return ok({"message": "log cleanup placeholder"})
