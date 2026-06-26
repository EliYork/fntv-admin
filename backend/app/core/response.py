from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return {"success": True, "data": data if data is not None else {}, "message": message}


def fail(code: str, message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


def page(items: list[Any], page_num: int, page_size: int, total: int) -> dict[str, Any]:
    pages = 0 if total == 0 else (total + page_size - 1) // page_size
    return ok({"items": items, "page": page_num, "page_size": page_size, "total": total, "pages": pages})

