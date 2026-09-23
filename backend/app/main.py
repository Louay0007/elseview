import json
import logging
import time
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.auth.delivery import deliver_local
from app.auth.router import router as auth_router
from app.auth.service import AuthService
from app.common.errors import DomainError
from app.config import Settings, load_settings
from app.db import Database

logger = logging.getLogger("elseview")


class SafeFormatter(logging.Formatter):
    """Allowlisted event fields only; arbitrary messages/exception bodies are never emitted."""

    def format(self, record):
        return json.dumps(
            {
                "level": record.levelname,
                "event": getattr(record, "event", "application_event"),
                "request_id": getattr(record, "request_id", None),
                "status": getattr(record, "status", None),
                "duration_ms": getattr(record, "duration_ms", None),
            }
        )


def error_response(code: str, message: str, request_id: str, status: int):
    return JSONResponse(
        {"error": {"code": code, "message": message}, "request_id": request_id},
        status_code=status,
    )


class RequestBoundary:
    """Bound bodies before routing; do not trust Content-Length or log request content."""

    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            request_id = str(UUID(headers.get(b"x-request-id", b"").decode("ascii")))
        except (ValueError, UnicodeError):
            request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = False
        status = 500
        began = time.monotonic()

        async def safe_send(message):
            nonlocal started, status
            if message["type"] == "http.response.start":
                started = True
                status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", request_id.encode()),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ]
            await send(message)

        async def reject(code, text, number):
            await error_response(code, text, request_id, number)(scope, receive, safe_send)

        try:
            length = headers.get(b"content-length")
            if length is not None and (not length.isdigit()):
                return await reject("INVALID_CONTENT_LENGTH", "Invalid content length.", 400)
            if length is not None and int(length) > self.limit:
                return await reject("PAYLOAD_TOO_LARGE", "Request body is too large.", 413)
            chunks, total = [], 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > self.limit:
                    return await reject("PAYLOAD_TOO_LARGE", "Request body is too large.", 413)
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
                return await receive()

            await self.app(scope, replay, safe_send)
        except Exception:
            if not started:
                await reject("INTERNAL_ERROR", "An internal error occurred.", 500)
        finally:
            logger.info(
                "request",
                extra={
                    "event": "http_request",
                    "request_id": request_id,
                    "status": status,
                    "duration_ms": round((time.monotonic() - began) * 1000, 2),
                },
            )


def create_app(settings: Settings | None = None) -> FastAPI:
    try:
        settings = settings or load_settings()
    except Exception:
        raise RuntimeError(
            "Invalid application configuration; check documented settings."
        ) from None
    database = Database(settings)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(SafeFormatter())
        logger.addHandler(handler)
    logger.setLevel(settings.log_level)
    logger.propagate = False

    @asynccontextmanager
    async def lifespan(app):
        app.state.started = True
        runner = None
        try:
            if settings.job_runner_enabled:
                from app.jobs.runner import JobRunner

                runner = JobRunner(database, settings)
                app.state.job_runner = runner
                await runner.start()
            yield
        finally:
            if runner is not None:
                await runner.stop()
            app.state.cache.close()
            app.state.rate_limiter.close()
            database.close()
            app.state.started = False

    app = FastAPI(
        title="Elseview",
        description="See what you’re missing.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.database = database
    app.state.started = False
    from app.common.cache import Cache, RateLimiter

    app.state.cache = Cache(settings)
    app.state.rate_limiter = RateLimiter(settings)
    app.state.auth = AuthService(
        database, settings, lambda email, purpose, raw: deliver_local(settings, email, purpose, raw)
    )
    app.include_router(auth_router)
    from app.jobs.router import router as jobs_router

    app.include_router(jobs_router)

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        return error_response(exc.code, exc.message, request.state.request_id, exc.status)

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError):
        return error_response("VALIDATION_ERROR", "Invalid request.", request.state.request_id, 422)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        codes = {
            404: ("NOT_FOUND", "Resource not found."),
            405: ("METHOD_NOT_ALLOWED", "Method not allowed."),
        }
        code, message = codes.get(
            exc.status_code, ("REQUEST_ERROR", "Request could not be completed.")
        )
        return error_response(code, message, request.state.request_id, exc.status_code)

    @app.get("/api/v1/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/api/v1/health/ready")
    def ready(request: Request):
        if not database.check_ready():
            return error_response(
                "NOT_READY", "Service is not ready.", request.state.request_id, 503
            )
        return {"status": "ready"}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-CSRF-Token",
            "Idempotency-Key",
        ],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestBoundary, limit=settings.max_request_bytes)
    return app
