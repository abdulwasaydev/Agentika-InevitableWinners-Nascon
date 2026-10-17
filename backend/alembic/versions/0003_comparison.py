"""Store document comparison separately from claim status and Guardian action.

Revision ID: 0003_comparison
Revises: 0002_supplied_documents
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_comparison"
down_revision = "0002_supplied_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("claims", sa.Column("comparison_result", sa.String(30)))
    op.add_column("claims", sa.Column("comparison_explanation", sa.Text()))
    op.add_column("claims", sa.Column("unresolved_questions", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("claims", "unresolved_questions")
    op.drop_column("claims", "comparison_explanation")
    op.drop_column("claims", "comparison_result")
