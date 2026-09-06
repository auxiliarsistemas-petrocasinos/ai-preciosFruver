"""Endpoints técnicos de disponibilidad."""

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Confirma que el proceso web está disponible.

    No verifica dependencias externas ni el esquema de datos: la estrategia de
    acceso a PostgreSQL y migraciones aún no ha sido definida.
    """
    return {"status": "ok"}
