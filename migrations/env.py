"""Configuración de Alembic para el esquema de la aplicación."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.commercial_offers import models as commercial_offer_models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.evidence import models as evidence_models  # noqa: F401
from app.prospecting import models as prospecting_models  # noqa: F401
from app.providers import models as provider_models  # noqa: F401
from app.purchase_needs import models  # noqa: F401
from app.sources import models as source_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

if not settings.database_url:
    msg = "DATABASE_URL debe estar configurada para ejecutar migraciones."
    raise RuntimeError(msg)

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecuta migraciones sin crear una conexión."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones con una conexión síncrona."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
