from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_admin
from app.core.response import ok
from app.services import fntv_schema_adapter

router = APIRouter(prefix="/api/favorites", tags=["favorites"], dependencies=[Depends(get_current_admin)])


@router.get("")
def list_favorites(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1),
    keyword: str | None = None,
):
    return ok(fntv_schema_adapter.favorites_page(page=page, page_size=page_size, keyword=keyword))
