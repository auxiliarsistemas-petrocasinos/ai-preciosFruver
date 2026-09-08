"""Modelo persistente de ofertas comerciales."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.prospecting.models import ProspectingRecord


class CommercialOffer(Base):
    """Información comercial encontrada para una prospección con proveedor."""

    __tablename__ = "commercial_offers"
    __table_args__ = (
        CheckConstraint("price_amount > 0", name="ck_commercial_offers_price_amount_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospecting_record_id: Mapped[int] = mapped_column(
        ForeignKey("prospecting_records.id"), nullable=False, index=True
    )
    price_amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    price_unit: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    obtained_on: Mapped[date] = mapped_column(Date, nullable=False)
    offered_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    prospecting_record: Mapped["ProspectingRecord"] = relationship(
        back_populates="commercial_offers"
    )
