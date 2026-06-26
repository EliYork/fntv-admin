from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_admin
from app.core.response import ok

router = APIRouter(prefix="/api/tasks", tags=["tasks"], dependencies=[Depends(get_current_admin)])


@router.get("")
def list_tasks():
    return ok({"items": [], "page": 1, "page_size": 20, "total": 0, "pages": 0})


@router.get("/{task_id}")
def task_detail(task_id: int):
    return ok({"id": task_id})


@router.post("/{task_name}")
def run_task(task_name: str):
    return ok({"task": task_name, "status": "queued"})

