"""One error format for the whole API:

    {"success": false, "error": {"code": "...", "message": "...", "details": ...}}
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class AppError(Exception):
    """Raise this from services/routes; the handler below turns it into JSON."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers
        super().__init__(message)


def error_body(code: str, message: str, details: object | None = None) -> dict:
    return {"success": False, "error": {"code": code, "message": message, "details": details}}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, exc.details),
        headers=exc.headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for err in exc.errors():
        field = ".".join(str(part) for part in err["loc"] if part not in ("body", "query", "path"))
        message = str(err["msg"]).removeprefix("Value error, ")
        details.append({"field": field, "message": message})
    return JSONResponse(
        status_code=422,
        content=error_body("VALIDATION_ERROR", "Some fields are invalid.", details),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(codes.get(exc.status_code, "HTTP_ERROR"), str(exc.detail)),
        headers=getattr(exc, "headers", None),
    )


async def database_error_handler(request: Request, exc: PyMongoError) -> JSONResponse:
    logger.exception("Database error")  # full detail goes to the server log only
    return JSONResponse(
        status_code=503,
        content=error_body("DATABASE_ERROR", "A database error occurred. Please try again later."),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content=error_body("INTERNAL_ERROR", "Something went wrong. Please try again later."),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(PyMongoError, database_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
