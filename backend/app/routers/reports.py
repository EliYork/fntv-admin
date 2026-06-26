from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_admin
from app.core.response import ok

router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(get_current_admin)])


@router.get("/{report_name}")
def report_placeholder(report_name: str):
    return ok({"name": report_name, "items": []})

