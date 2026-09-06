"""Modelo persistente de necesidades de compra."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PurchaseNeed(Base):
    """Necesidad de compra registrada para investigación posterior."""

    __tablename__ = "purchase_needs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    variety: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_standard: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(Text, nullable=False)
    required_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    destination_city: Mapped[str] = mapped_column(Text, nullable=False)
    destination_location: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
