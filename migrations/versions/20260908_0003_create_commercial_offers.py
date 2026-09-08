"""Create commercial offers table.

Revision ID: 20260908_0003
Revises: 20260907_0002
Create Date: 2026-09-08 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0003"
down_revision: str | None = "20260907_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create offers captured for prospecting records with providers."""
    op.create_table(
        "commercial_offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prospecting_record_id", sa.Integer(), nullable=False),
        sa.Column("price_amount", sa.Numeric(), nullable=False),
        sa.Column("price_unit", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("obtained_on", sa.Date(), nullable=False),
        sa.Column("offered_description", sa.Text(), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("price_amount > 0", name="ck_commercial_offers_price_amount_positive"),
        sa.ForeignKeyConstraint(["prospecting_record_id"], ["prospecting_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_offers_prospecting_record_id",
        "commercial_offers",
        ["prospecting_record_id"],
    )


def downgrade() -> None:
    """Remove commercial offers."""
    op.drop_index("ix_commercial_offers_prospecting_record_id", table_name="commercial_offers")
    op.drop_table("commercial_offers")
