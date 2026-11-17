"""Standardized error responses and application exceptions."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("snack_overflow.errors")


class AppError(Exception):
    """
    Custom application exception producing standardized error envelopes.
    Constructor signature: (status_code, code, message).
    """

    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "BAD_REQUEST",
        message: str = "A business error occurred.",
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


AppException = AppError


class NotFoundError(AppError):
    """Resource not found exception (404)."""

    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, code=code, message=message)


class UnauthorizedError(AppError):
    """Authentication required or invalid credentials (401)."""

    def __init__(self, message: str = "Unauthorized", code: str = "UNAUTHORIZED") -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, code=code, message=message)


class ForbiddenError(AppError):
    """Insufficient permissions (403)."""

    def __init__(self, message: str = "Forbidden", code: str = "FORBIDDEN") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, code=code, message=message)


class ConflictError(AppError):
    """Resource conflict or duplicate constraint violation (409)."""

    def __init__(self, message: str = "Conflict", code: str = "CONFLICT") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, code=code, message=message)


class InsufficientStockError(AppError):
    """Stock consumption exceeds available pantry quantity (400)."""

    def __init__(self, message: str = "Insufficient stock available", code: str = "INSUFFICIENT_STOCK") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, code=code, message=message)


class DatabaseError(AppError):
    """Database connectivity or query failure (503)."""

    def __init__(self, message: str = "Database service unavailable", code: str = "DATABASE_UNAVAILABLE") -> None:
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, code=code, message=message)


def format_error_response(
    code: str,
    message: str,
    details: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Enforce strict {"error": {"code": "...", "message": "..."}} envelope.
    'details' is included on validation errors if provided.
    """
    error_payload: Dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if details is not None:
        error_payload["details"] = details
    return {"error": error_payload}


def register_error_handlers(app: FastAPI) -> None:
    """Attach standardized exception handlers to the FastAPI application."""

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(code=exc.code, message=exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        details: List[Dict[str, Any]] = []

        for err in errors:
            loc = [str(x) for x in err.get("loc", []) if str(x) not in ("body", "query", "path", "header")]
            field_name = ".".join(loc) if loc else str(err.get("loc", ["body"])[-1])
            details.append({
                "field": field_name,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            })

        summary = f"Field '{details[0]['field']}': {details[0]['message']}" if details else "Validation failed."
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=format_error_response(
                code="VALIDATION_ERROR",
                message=summary,
                details=details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        status_to_code = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            500: "INTERNAL_SERVER_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }
        code = status_to_code.get(exc.status_code, f"HTTP_{exc.status_code}")
        message = str(exc.detail) if exc.detail else "An HTTP error occurred."
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(code=code, message=message),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=format_error_response(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred.",
            ),
        )
