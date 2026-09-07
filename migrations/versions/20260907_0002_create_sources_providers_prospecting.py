"""Create sources, providers, and prospecting records.

Revision ID: 20260907_0002
Revises: 20260905_0001
Create Date: 2026-09-07 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260907_0002"
down_revision: str | None = "20260905_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create reusable sources, providers, and contextual prospecting records."""
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "providers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("contact_name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "prospecting_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purchase_need_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"]),
        sa.ForeignKeyConstraint(["purchase_need_id"], ["purchase_needs.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prospecting_records_provider_id", "prospecting_records", ["provider_id"])
    op.create_index(
        "ix_prospecting_records_purchase_need_id", "prospecting_records", ["purchase_need_id"]
    )
    op.create_index("ix_prospecting_records_source_id", "prospecting_records", ["source_id"])


def downgrade() -> None:
    """Remove prospecting records, providers, and sources."""
    op.drop_index("ix_prospecting_records_source_id", table_name="prospecting_records")
    op.drop_index("ix_prospecting_records_purchase_need_id", table_name="prospecting_records")
    op.drop_index("ix_prospecting_records_provider_id", table_name="prospecting_records")
    op.drop_table("prospecting_records")
    op.drop_table("providers")
    op.drop_table("sources")
