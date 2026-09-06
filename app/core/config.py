"""Configuración de la aplicación a partir de variables de entorno."""

from dataclasses import dataclass
from os import getenv


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    app_env: str
    debug: bool
    database_url: str
    evidence_storage_path: str

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            app_name=getenv("APP_NAME", "ai-preciosFruver"),
            app_env=getenv("APP_ENV", "development"),
            debug=_as_bool(getenv("DEBUG", "false")),
            database_url=getenv("DATABASE_URL", ""),
            evidence_storage_path=getenv(
                "EVIDENCE_STORAGE_PATH", "/var/lib/ai-precios-fruver/evidence"
            ),
        )


settings = Settings.from_environment()
