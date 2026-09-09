"""Add persistent file representation to evidence.

Revision ID: 20260909_0005
Revises: 20260908_0004
Create Date: 2026-09-09 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_0005"
down_revision: str | None = "20260908_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the mutually exclusive persistent-file representation."""
    op.alter_column("evidence_items", "url", existing_type=sa.Text(), nullable=True)
    op.add_column("evidence_items", sa.Column("storage_key", sa.Text(), nullable=True))
    op.add_column("evidence_items", sa.Column("original_filename", sa.Text(), nullable=True))
    op.add_column("evidence_items", sa.Column("media_type", sa.Text(), nullable=True))
    op.add_column("evidence_items", sa.Column("file_size", sa.BigInteger(), nullable=True))
    op.create_unique_constraint("uq_evidence_items_storage_key", "evidence_items", ["storage_key"])
    op.create_check_constraint(
        "ck_evidence_items_exactly_one_representation",
        "evidence_items",
        "((url IS NOT NULL AND storage_key IS NULL AND original_filename IS NULL "
        "AND media_type IS NULL AND file_size IS NULL) OR "
        "(url IS NULL AND storage_key IS NOT NULL AND original_filename IS NOT NULL "
        "AND media_type IS NOT NULL AND file_size IS NOT NULL AND file_size > 0))",
    )


def downgrade() -> None:
    """Refuse data loss when file evidence exists, then restore URL-only evidence."""
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM evidence_items WHERE storage_key IS NOT NULL
                ) THEN
                    RAISE EXCEPTION
                        'Cannot downgrade 20260909_0005 while file evidence exists; '
                        'remove or migrate those rows explicitly first.';
                END IF;
            END
            $$;
            """
        )
    )
    op.drop_constraint(
        "ck_evidence_items_exactly_one_representation", "evidence_items", type_="check"
    )
    op.drop_constraint("uq_evidence_items_storage_key", "evidence_items", type_="unique")
    op.drop_column("evidence_items", "file_size")
    op.drop_column("evidence_items", "media_type")
    op.drop_column("evidence_items", "original_filename")
    op.drop_column("evidence_items", "storage_key")
    op.alter_column("evidence_items", "url", existing_type=sa.Text(), nullable=False)
