"""Modelo persistente de referencias de evidencia."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.commercial_offers.models import CommercialOffer
    from app.prospecting.models import ProspectingRecord


class Evidence(Base):
    """Referencia URL que sustenta una prospección o una oferta comercial."""

    __tablename__ = "evidence_items"
    __table_args__ = (
        CheckConstraint(
            "((prospecting_record_id IS NOT NULL AND commercial_offer_id IS NULL) "
            "OR (prospecting_record_id IS NULL AND commercial_offer_id IS NOT NULL))",
            name="ck_evidence_items_exactly_one_target",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospecting_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("prospecting_records.id"), nullable=True, index=True
    )
    commercial_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("commercial_offers.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    captured_on: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    prospecting_record: Mapped["ProspectingRecord | None"] = relationship(
        back_populates="evidence_items"
    )
    commercial_offer: Mapped["CommercialOffer | None"] = relationship(
        back_populates="evidence_items"
    )
