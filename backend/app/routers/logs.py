from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_admin
from app.core.response import ok

router = APIRouter(prefix="/api/logs", tags=["logs"], dependencies=[Depends(get_current_admin)])


@router.get("")
def list_logs():
    return ok({"items": [], "page": 1, "page_size": 20, "total": 0, "pages": 0})


@router.get("/download")
def download_logs():
    return ok({"message": "log download placeholder"})


@router.delete("/cleanup")
def cleanup_logs():
    return ok({"message": "log cleanup placeholder"})

