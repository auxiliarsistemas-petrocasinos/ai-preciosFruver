"""Middleware fail-closed para proteger toda ruta no incluida expresamente."""

from collections.abc import Callable
from urllib.parse import urlencode

from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool
from starlette.responses import RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.auth.services import detached_identity
from app.core.config import settings
from app.db.session import get_session_factory

SESSION_COOKIE_NAME = "ai_pf_session"


def _is_public(scope: Scope) -> bool:
    method = scope.get("method", "")
    path = scope.get("path", "")
    if path == "/login" and method in {"GET", "POST"}:
        return True
    if path == "/health" and method == "GET":
        return True
    return method in {"GET", "HEAD"} and (path == "/static" or path.startswith("/static/"))


def delete_session_cookie(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


def set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        raw_token,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


def _load_identity(factory: sessionmaker[Session], raw_token: str) -> tuple[object, object] | None:
    with factory() as db:
        return detached_identity(db, raw_token)


class AuthenticationMiddleware:
    """Resuelve una cookie opaca antes de entregar rutas protegidas a FastAPI."""

    def __init__(
        self,
        app: ASGIApp,
        session_factory_provider: Callable[[], sessionmaker[Session]] = get_session_factory,
    ) -> None:
        self.app = app
        self.session_factory_provider = session_factory_provider

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        state["current_user"] = None
        state["current_session"] = None
        if _is_public(scope):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_cookie = headers.get(b"cookie", b"").decode("latin-1")
        raw_token = None
        for item in raw_cookie.split(";"):
            name, separator, value = item.strip().partition("=")
            if separator and name == SESSION_COOKIE_NAME:
                raw_token = value
                break

        identity = None
        if raw_token:
            app = scope.get("app")
            factory = getattr(getattr(app, "state", None), "auth_session_factory", None)
            if factory is None:
                factory = self.session_factory_provider()
            identity = await run_in_threadpool(_load_identity, factory, raw_token)

        if identity is None:
            if headers.get(b"hx-request", b"").lower() == b"true":
                response = Response(status_code=204, headers={"HX-Redirect": "/login"})
            else:
                location = "/login"
                if scope.get("method") == "GET":
                    path = scope.get("path", "/")
                    query = scope.get("query_string", b"").decode("latin-1")
                    destination = f"{path}?{query}" if query else path
                    location = f"/login?{urlencode({'next': destination})}"
                response = RedirectResponse(location, status_code=303)
            if raw_token:
                delete_session_cookie(response)
            await response(scope, receive, send)
            return

        state["current_user"], state["current_session"] = identity
        await self.app(scope, receive, send)
