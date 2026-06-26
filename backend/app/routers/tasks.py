from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_admin
from app.core.response import ok
from app.utils.pagination import normalize_page

router = APIRouter(prefix="/api/tasks", tags=["tasks"], dependencies=[Depends(get_current_admin)])


@router.get("")
def list_tasks(page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1)):
    page_num, clean_page_size, _ = normalize_page(page, page_size)
    return ok({"items": [], "page": page_num, "page_size": clean_page_size, "total": 0, "pages": 0})


@router.get("/{task_id}")
def task_detail(task_id: int):
    return ok({"id": task_id})


@router.post("/{task_name}")
def run_task(task_name: str):
    return ok({"task": task_name, "status": "queued"})
