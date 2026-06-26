from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.response import fail

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        return fail(exc.code, exc.message, exc.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException):
        code = "UNAUTHORIZED" if exc.status_code == 401 else "HTTP_ERROR"
        message = str(exc.detail) if exc.detail else "请求失败"
        return fail(code, message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        logger.info("request validation failed: %s", exc.errors())
        return fail("VALIDATION_ERROR", "请求参数不合法", 422)

    @app.exception_handler(Exception)
    async def unknown_error_handler(_: Request, exc: Exception):
        logger.exception("unhandled server error: %s", exc.__class__.__name__)
        return fail("INTERNAL_ERROR", "服务器内部错误", 500)

