"""FastAPI application factory for NetTriage AI."""

import logging

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from nettriage.api.errors import APIError
from nettriage.api.routes.batches import router as batches_router
from nettriage.api.routes.classify import router as classify_router
from nettriage.api.routes.health import router as health_router
from nettriage.api.routes.tickets import router as tickets_router
from nettriage.api.routes.ui import router as ui_router
from nettriage.core.config import get_settings
from nettriage.core.logging import configure_logging

logger = logging.getLogger(__name__)


def _api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch every :class:`APIError` and return the standard error shape."""
    if not isinstance(exc, APIError):
        raise exc
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": exc.code.value,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    configure_logging(settings)

    logger.info("Starting application", extra={"environment": settings.environment})

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(ui_router)
    app.include_router(classify_router)
    app.include_router(batches_router)
    app.include_router(tickets_router)
    app.include_router(health_router)
    app.add_exception_handler(APIError, _api_error_handler)
    return app


app = create_app()
