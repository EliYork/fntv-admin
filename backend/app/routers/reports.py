from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_admin
from app.core.response import ok
from app.services import report_service

router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(get_current_admin)])


@router.get("/overview")
def overview():
    return ok(report_service.overview())


@router.get("/play-trend")
def play_trend(days: str = Query(default="30")):
    return ok(report_service.play_trend(days=days))


@router.get("/hourly-distribution")
def hourly_distribution(days: str = Query(default="30")):
    return ok(report_service.hourly_distribution(days=days))


@router.get("/top-users")
def top_users(days: str = Query(default="30"), limit: int = Query(default=10, ge=1)):
    return ok(report_service.top_users(days=days, limit=limit))


@router.get("/top-media")
def top_media(days: str = Query(default="30"), limit: int = Query(default=10, ge=1), mode: str = Query(default="episode")):
    return ok(report_service.top_media(days=days, limit=limit, mode=mode))


@router.get("/media-type-distribution")
def media_type_distribution():
    return ok(report_service.media_type_distribution())


@router.get("/resolution-distribution")
def resolution_distribution(days: str = Query(default="30")):
    return ok(report_service.resolution_distribution(days=days))
