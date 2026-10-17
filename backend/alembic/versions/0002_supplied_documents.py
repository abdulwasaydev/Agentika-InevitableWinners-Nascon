"""Persist bounded source documents separately from advertised claims.

Revision ID: 0002_supplied_documents
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_supplied_documents"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplied_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("verification_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("version", sa.String(80)),
        sa.Column("effective_date", sa.String(80)),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint("job_id", "document_id", name="uq_supplied_document_job_id"),
    )
    op.create_index("ix_supplied_documents_job_id", "supplied_documents", ["job_id"])
    op.execute("ALTER TABLE supplied_documents ENABLE ROW LEVEL SECURITY")
    for role in ("anon", "authenticated"):
        op.execute(f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
        REVOKE ALL ON TABLE supplied_documents FROM {role};
    END IF;
END $$
""")


def downgrade() -> None:
    op.drop_table("supplied_documents")
