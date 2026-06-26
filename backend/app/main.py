from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.errors import register_exception_handlers
from app.core.logging import setup_logging
from app.routers import auth, dashboard, history, logs, media, reports, settings, system, tasks, users
from app.services.system_service import startup_check

setup_logging()

app = FastAPI(title="fntv-admin", version="0.1.0")
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    startup_check()


app.include_router(system.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(history.router)
app.include_router(users.router)
app.include_router(media.router)
app.include_router(reports.router)
app.include_router(tasks.router)
app.include_router(logs.router)
app.include_router(settings.router)

static_dir = Path(__file__).parent / "static"
assets_dir = static_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
def frontend_index():
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"success": True, "data": {"message": "frontend build not found"}, "message": "ok"}


@app.get("/{path:path}")
def frontend_fallback(path: str):
    if path.startswith("api/"):
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "接口不存在"}}
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"success": True, "data": {"message": "frontend build not found"}, "message": "ok"}
