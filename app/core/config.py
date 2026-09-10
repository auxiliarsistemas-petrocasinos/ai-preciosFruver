"""Configuración de la aplicación a partir de variables de entorno."""

from dataclasses import dataclass
from os import getenv
from urllib.parse import urlsplit


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _positive_int(name: str, value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un entero positivo.") from exc
    if parsed <= 0:
        raise ValueError(f"{name} debe ser un entero positivo.")
    return parsed


def _validate_auth_origin(app_origin: str, secure_cookie: bool) -> str:
    try:
        parsed = urlsplit(app_origin)
        parsed.port
    except ValueError as exc:
        raise ValueError("APP_ORIGIN debe ser un origen HTTP o HTTPS válido.") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or app_origin != f"{parsed.scheme}://{parsed.netloc}"
    ):
        raise ValueError("APP_ORIGIN debe contener solo un origen HTTP o HTTPS canónico.")
    if secure_cookie and parsed.scheme != "https":
        raise ValueError("SESSION_COOKIE_SECURE=true requiere APP_ORIGIN con HTTPS.")
    if not secure_cookie and (
        parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError(
            "SESSION_COOKIE_SECURE=false solo se admite con APP_ORIGIN HTTP en loopback."
        )
    return app_origin


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    app_env: str
    debug: bool
    database_url: str
    evidence_storage_path: str
    app_origin: str
    session_lifetime_seconds: int
    session_cookie_secure: bool

    @classmethod
    def from_environment(cls) -> "Settings":
        session_cookie_secure = _as_bool(getenv("SESSION_COOKIE_SECURE", "false"))
        app_origin = _validate_auth_origin(
            getenv("APP_ORIGIN", "http://127.0.0.1:8000"), session_cookie_secure
        )
        return cls(
            app_name=getenv("APP_NAME", "ai-preciosFruver"),
            app_env=getenv("APP_ENV", "development"),
            debug=_as_bool(getenv("DEBUG", "false")),
            database_url=getenv("DATABASE_URL", ""),
            evidence_storage_path=getenv(
                "EVIDENCE_STORAGE_PATH", "/var/lib/ai-precios-fruver/evidence"
            ),
            app_origin=app_origin,
            session_lifetime_seconds=_positive_int(
                "SESSION_LIFETIME_SECONDS", getenv("SESSION_LIFETIME_SECONDS", "28800")
            ),
            session_cookie_secure=session_cookie_secure,
        )


settings = Settings.from_environment()
