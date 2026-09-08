"""Create evidence items table.

Revision ID: 20260908_0004
Revises: 20260908_0003
Create Date: 2026-09-08 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0004"
down_revision: str | None = "20260908_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create URL evidence associated with exactly one supported target."""
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prospecting_record_id", sa.Integer(), nullable=True),
        sa.Column("commercial_offer_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("captured_on", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "((prospecting_record_id IS NOT NULL AND commercial_offer_id IS NULL) "
            "OR (prospecting_record_id IS NULL AND commercial_offer_id IS NOT NULL))",
            name="ck_evidence_items_exactly_one_target",
        ),
        sa.ForeignKeyConstraint(["commercial_offer_id"], ["commercial_offers.id"]),
        sa.ForeignKeyConstraint(["prospecting_record_id"], ["prospecting_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evidence_items_commercial_offer_id",
        "evidence_items",
        ["commercial_offer_id"],
    )
    op.create_index(
        "ix_evidence_items_prospecting_record_id",
        "evidence_items",
        ["prospecting_record_id"],
    )


def downgrade() -> None:
    """Remove evidence items."""
    op.drop_index("ix_evidence_items_prospecting_record_id", table_name="evidence_items")
    op.drop_index("ix_evidence_items_commercial_offer_id", table_name="evidence_items")
    op.drop_table("evidence_items")
