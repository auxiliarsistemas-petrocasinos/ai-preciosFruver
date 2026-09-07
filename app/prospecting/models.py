"""Modelo persistente del registro contextual de prospección."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.providers.models import Provider
    from app.purchase_needs.models import PurchaseNeed
    from app.sources.models import Source


class ProspectingRecord(Base):
    """Consulta de una fuente asociada al contexto de una necesidad de compra."""

    __tablename__ = "prospecting_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_need_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_needs.id"), nullable=False, index=True
    )
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("providers.id"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    purchase_need: Mapped["PurchaseNeed"] = relationship(back_populates="prospecting_records")
    source: Mapped["Source"] = relationship(back_populates="prospecting_records")
    provider: Mapped["Provider | None"] = relationship(back_populates="prospecting_records")
