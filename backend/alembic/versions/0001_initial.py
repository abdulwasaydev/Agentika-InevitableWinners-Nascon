"""Initial durable verification schema.

Revision ID: 0001_initial
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "verification_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("policy", sa.String(20), nullable=False),
        sa.Column("origin", sa.String(80), nullable=False),
        sa.Column("parent_claim_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("overall_action", sa.String(30)),
        sa.Column("error_code", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_verification_jobs_status", "verification_jobs", ["status"])
    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("verification_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer()),
        sa.Column("end_offset", sa.Integer()),
        sa.Column("checkability", sa.String(30), nullable=False),
        sa.Column("provisional_status", sa.String(30), nullable=False),
        sa.Column("effective_status", sa.String(30), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("corrected_text", sa.Text()),
        sa.Column("material", sa.Boolean(), nullable=False),
        sa.Column("high_risk", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_claims_job_id", "claims", ["job_id"])
    op.create_index("ix_claims_effective_status", "claims", ["effective_status"])
    op.create_index("ix_claims_needs_review", "claims", ["needs_review"])
    op.create_index("ix_claim_job_status", "claims", ["job_id", "effective_status"])
    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("claim_id", sa.Uuid(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stance", sa.String(20), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("provenance", sa.String(40), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("document_id", sa.String(200)),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("validity_status", sa.String(30), nullable=False),
    )
    op.create_index("ix_evidence_claim_id", "evidence", ["claim_id"])
    op.create_table(
        "agent_assessments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("claim_id", sa.Uuid(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("position", sa.String(30), nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_assessments_claim_id", "agent_assessments", ["claim_id"])
    op.create_table(
        "human_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("claim_id", sa.Uuid(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("reviewer_id", sa.String(120), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("corrected_text", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_human_reviews_claim_id", "human_reviews", ["claim_id"])
    op.create_table(
        "claim_dependencies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("parent_claim_id", sa.Uuid(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("child_claim_id", sa.Uuid(), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("parent_claim_id", "child_claim_id", name="uq_claim_dependency"),
    )
    op.create_index("ix_claim_dependencies_parent_claim_id", "claim_dependencies", ["parent_claim_id"])
    op.create_index("ix_claim_dependencies_child_claim_id", "claim_dependencies", ["child_claim_id"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("claim_dependencies")
    op.drop_table("human_reviews")
    op.drop_table("agent_assessments")
    op.drop_table("evidence")
    op.drop_table("claims")
    op.drop_table("verification_jobs")
