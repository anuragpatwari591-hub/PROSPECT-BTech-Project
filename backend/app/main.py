"""FastAPI application factory: routers, CORS, security headers, and safe error handling."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.deps import APIError
from app.api.routes import meta, projects
from app.core.config import get_settings
from app.services.github_client import GitHubError

log = logging.getLogger("prospect")


def _error(status: int, code: str, message: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, **extra}})


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)
    app = FastAPI(title="PROSPECT API", version=__version__,
                  description="Predictive Software Project Risk Analysis and Decision Support System. "
                              "Risk scores are rule-based heuristics; ML outputs are experimental.")

    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
                       allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if not request.url.path.startswith(("/docs", "/redoc")):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(APIError)
    async def api_error(_: Request, exc: APIError):
        return _error(exc.status_code, exc.code, exc.message, **exc.extra)

    @app.exception_handler(GitHubError)
    async def github_error(_: Request, exc: GitHubError):
        return _error(exc.status_code, exc.code, exc.message, **exc.extra)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return _error(422, "VALIDATION_ERROR", "Request validation failed.", details=details)

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error")  # full trace goes to server logs only, never to the client
        return _error(500, "INTERNAL_ERROR", "An unexpected error occurred.")

    app.include_router(meta.router)
    app.include_router(projects.router)
    return app


app = create_app()
