from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.deps import get_current_admin
from app.core.response import ok
from app.services import fntv_adapter

router = APIRouter(prefix="/api/history", tags=["history"], dependencies=[Depends(get_current_admin)])


@router.get("")
def list_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1),
    user_guid: str | None = None,
    keyword: str | None = None,
    media_type: str | None = None,
    watched: bool | None = None,
    resolution: str | None = None,
    progress_min: int | None = None,
    progress_max: int | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
):
    filters = {
        "user_guid": user_guid,
        "keyword": keyword,
        "media_type": media_type,
        "watched": watched,
        "resolution": resolution,
        "progress_min": progress_min,
        "progress_max": progress_max,
        "start_time": start_time,
        "end_time": end_time,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    return ok(fntv_adapter.history_page(page, page_size, filters))


@router.get("/export")
def export_history(
    user_guid: str | None = None,
    keyword: str | None = None,
    media_type: str | None = None,
    watched: bool | None = None,
    resolution: str | None = None,
    progress_min: int | None = None,
    progress_max: int | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
):
    filters = {
        "user_guid": user_guid,
        "keyword": keyword,
        "media_type": media_type,
        "watched": watched,
        "resolution": resolution,
        "progress_min": progress_min,
        "progress_max": progress_max,
        "start_time": start_time,
        "end_time": end_time,
    }
    csv_text = fntv_adapter.history_csv(filters)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="fntv-history.csv"'},
    )


@router.get("/{record_id}")
def history_detail(record_id: str):
    return ok(fntv_adapter.history_detail(record_id) or {})
