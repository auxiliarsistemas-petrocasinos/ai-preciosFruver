import asyncio

from app.api.routes.health import health_check
from app.main import app


def test_health_check_returns_ok() -> None:
    assert asyncio.run(health_check()) == {"status": "ok"}


def test_health_check_is_registered() -> None:
    assert "/health" in app.openapi()["paths"]
