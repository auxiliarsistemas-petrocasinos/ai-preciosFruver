"""Creación de sesiones síncronas de SQLAlchemy."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


@lru_cache
def get_engine() -> Engine:
    """Devuelve el motor configurado para la base de datos de la aplicación."""
    if not settings.database_url:
        msg = "DATABASE_URL debe estar configurada para usar la persistencia."
        raise RuntimeError(msg)
    return create_engine(settings.database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Devuelve la fábrica de sesiones síncronas."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """Entrega y cierra una sesión por solicitud web."""
    with get_session_factory()() as session:
        yield session
