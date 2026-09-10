"""Login y logout HTML para la autenticación local."""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.middleware import (
    SESSION_COOKIE_NAME,
    delete_session_cookie,
    set_session_cookie,
)
from app.auth.security import login_origin_is_valid, safe_next_path, validate_authenticated_csrf
from app.auth.services import (
    authenticate_user,
    cleanup_expired_sessions,
    create_user_session,
    find_user_session,
    revoke_session,
)
from app.core.config import settings
from app.db.session import get_session

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


def _login_response(
    request: Request,
    *,
    username: str = "",
    next_path: str = "/",
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"username": username, "next": next_path, "error": error},
        status_code=status_code,
    )


@router.get("/login", response_class=HTMLResponse)
def login_form(
    request: Request,
    next: str = "/",
    db: Session = Depends(get_session),
) -> Response:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if raw_token and find_user_session(db, raw_token) is not None:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response = _login_response(request, next_path=safe_next_path(next))
    if raw_token:
        delete_session_cookie(response)
    return response


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    db: Session = Depends(get_session),
) -> Response:
    if not login_origin_is_valid(request, settings.app_origin):
        return HTMLResponse("Solicitud de login no permitida.", status_code=403)

    async with request.form(max_files=0, max_fields=3, max_part_size=16 * 1024) as form:
        username_value = form.get("username", "")
        password_value = form.get("password", "")
        next_value = form.get("next", "/")
        username = username_value if isinstance(username_value, str) else ""
        password = password_value if isinstance(password_value, str) else ""
        next_path = safe_next_path(next_value if isinstance(next_value, str) else "/")

    user = authenticate_user(db, username, password)
    if user is None:
        response = _login_response(
            request,
            username=username,
            next_path=next_path,
            error="Usuario o contraseña incorrectos",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        presented_token = request.cookies.get(SESSION_COOKIE_NAME)
        if presented_token and find_user_session(db, presented_token) is None:
            delete_session_cookie(response)
        return response

    revoke_session(db, request.cookies.get(SESSION_COOKIE_NAME))
    cleanup_expired_sessions(db)
    _, raw_token = create_user_session(db, user, settings.session_lifetime_seconds)
    response = RedirectResponse(next_path, status_code=status.HTTP_303_SEE_OTHER)
    set_session_cookie(response, raw_token)
    return response


@router.post("/logout")
def logout(
    request: Request,
    csrf_token: str = Form("", alias="_csrf_token"),
    db: Session = Depends(get_session),
) -> Response:
    validate_authenticated_csrf(request, csrf_token)
    revoke_session(db, request.cookies.get(SESSION_COOKIE_NAME))
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    delete_session_cookie(response)
    return response
