"""Create purchase needs table.

Revision ID: 20260905_0001
Revises:
Create Date: 2026-09-05 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260905_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the table that records purchase needs."""
    op.create_table(
        "purchase_needs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=False),
        sa.Column("variety", sa.Text(), nullable=True),
        sa.Column("quality_standard", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(), nullable=False),
        sa.Column("unit_of_measure", sa.Text(), nullable=False),
        sa.Column("required_delivery_date", sa.Date(), nullable=False),
        sa.Column("destination_city", sa.Text(), nullable=False),
        sa.Column("destination_location", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Remove the purchase needs table."""
    op.drop_table("purchase_needs")
