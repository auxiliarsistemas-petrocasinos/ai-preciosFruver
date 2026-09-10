"""Validaciones HTTP compartidas por autenticación y CSRF."""

from hmac import compare_digest
from urllib.parse import unquote, urlsplit

from fastapi import HTTPException, Request, status


def safe_next_path(value: str | None) -> str:
    """Acepta solo destinos internos absolutos y evita variantes codificadas."""
    if not value:
        return "/"
    decoded = value
    for _ in range(5):
        next_decoded = unquote(decoded)
        if next_decoded == decoded:
            break
        decoded = next_decoded
    else:
        return "/"
    if (
        not decoded.startswith("/")
        or decoded.startswith("//")
        or "\\" in decoded
        or any(ord(character) < 32 or ord(character) == 127 for character in decoded)
    ):
        return "/"
    parsed = urlsplit(decoded)
    if parsed.scheme or parsed.netloc or parsed.path == "/login":
        return "/"
    return decoded


def login_origin_is_valid(request: Request, app_origin: str) -> bool:
    """Valida Origin o, cuando no existe, el origin exacto de Referer."""
    origin = request.headers.get("origin")
    if origin is not None:
        return compare_digest(origin, app_origin)
    referer = request.headers.get("referer")
    if referer is None:
        return False
    try:
        parsed = urlsplit(referer)
        if parsed.username is not None or parsed.password is not None:
            return False
        referer_origin = f"{parsed.scheme}://{parsed.netloc}"
    except ValueError:
        return False
    return compare_digest(referer_origin, app_origin)


def validate_authenticated_csrf(request: Request, supplied_token: str) -> None:
    """Exige el synchronizer token de la sesión autenticada."""
    user_session = getattr(request.state, "current_session", None)
    if (
        user_session is None
        or not supplied_token
        or not compare_digest(supplied_token, user_session.csrf_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token CSRF ausente o inválido.",
        )
