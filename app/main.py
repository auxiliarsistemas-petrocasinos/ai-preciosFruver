"""Punto de entrada de la aplicación FastAPI."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.health import router as health_router
from app.core.config import settings
from app.evidence.upload_limit import EvidenceUploadBodyLimitMiddleware
from app.web.routes.commercial_offers import router as commercial_offers_router
from app.web.routes.evidence import router as evidence_router
from app.web.routes.home import router as web_router
from app.web.routes.providers import router as providers_router
from app.web.routes.purchase_needs import router as purchase_needs_router
from app.web.routes.sources import router as sources_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.state.evidence_storage_path = Path(settings.evidence_storage_path)
    app.add_middleware(EvidenceUploadBodyLimitMiddleware)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(health_router)
    app.include_router(web_router)
    app.include_router(purchase_needs_router)
    app.include_router(commercial_offers_router)
    app.include_router(evidence_router)
    app.include_router(sources_router)
    app.include_router(providers_router)
    return app


app = create_app()
