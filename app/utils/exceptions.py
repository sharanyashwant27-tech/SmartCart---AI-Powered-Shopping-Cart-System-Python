"""Custom application exceptions and HTTP error handlers."""

from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):
    """Base application exception with HTTP status and detail."""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "app_error",
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        self.detail = detail
        self.status_code = status_code
        self.code = code
        self.extra = extra or {}
        super().__init__(detail)


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(detail, status.HTTP_404_NOT_FOUND, "not_found", **kwargs)


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Not authenticated", **kwargs: Any) -> None:
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED, "unauthorized", **kwargs)


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Insufficient permissions", **kwargs: Any) -> None:
        super().__init__(detail, status.HTTP_403_FORBIDDEN, "forbidden", **kwargs)


class ConflictError(AppException):
    def __init__(self, detail: str = "Conflict", **kwargs: Any) -> None:
        super().__init__(detail, status.HTTP_409_CONFLICT, "conflict", **kwargs)


class ValidationAppError(AppException):
    def __init__(self, detail: str = "Validation error", **kwargs: Any) -> None:
        super().__init__(
            detail, status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error", **kwargs
        )


class PaymentError(AppException):
    def __init__(self, detail: str = "Payment failed", **kwargs: Any) -> None:
        super().__init__(detail, status.HTTP_402_PAYMENT_REQUIRED, "payment_error", **kwargs)


def _error_body(
    detail: Any,
    code: str,
    status_code: int,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "success": False,
        "error": {"code": code, "detail": detail, "status_code": status_code},
    }
    if extra:
        body["error"]["extra"] = extra
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.detail, exc.code, exc.status_code, exc.extra),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.detail, "http_error", exc.status_code),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                "Request validation failed",
                "validation_error",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"errors": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "Internal server error",
                "internal_error",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                {"message": str(exc)} if get_settings_debug() else None,
            ),
        )


def get_settings_debug() -> bool:
    from app.config import get_settings

    return get_settings().debug
