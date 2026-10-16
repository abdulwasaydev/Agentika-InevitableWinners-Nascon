"""PostgreSQL persistence model for jobs, evidence, reviews and lineage."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class VerificationJob(Base):
    __tablename__ = "verification_jobs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    mode: Mapped[str] = mapped_column(String(20))
    input_text: Mapped[str] = mapped_column(Text)
    policy: Mapped[str] = mapped_column(String(20))
    origin: Mapped[str] = mapped_column(String(80))
    parent_claim_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), index=True)
    overall_action: Mapped[str | None] = mapped_column(String(30), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    claims: Mapped[list["Claim"]] = relationship(back_populates="job", cascade="all, delete-orphan", order_by="Claim.start_offset")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("verification_jobs.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checkability: Mapped[str] = mapped_column(String(30))
    provisional_status: Mapped[str] = mapped_column(String(30))
    effective_status: Mapped[str] = mapped_column(String(30), index=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    material: Mapped[bool] = mapped_column(Boolean, default=True)
    high_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    job: Mapped[VerificationJob] = relationship(back_populates="claims")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    assessments: Mapped[list["AgentAssessment"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    reviews: Mapped[list["HumanReview"]] = relationship(back_populates="claim", cascade="all, delete-orphan", order_by="HumanReview.created_at")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    stance: Mapped[str] = mapped_column(String(20))
    source_type: Mapped[str] = mapped_column(String(40))
    provenance: Mapped[str] = mapped_column(String(40))
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    title: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str] = mapped_column(Text)
    source_text: Mapped[str] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validity_status: Mapped[str] = mapped_column(String(30))
    claim: Mapped[Claim] = relationship(back_populates="evidence")


class AgentAssessment(Base):
    __tablename__ = "agent_assessments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    position: Mapped[str] = mapped_column(String(30))
    reasoning_summary: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    claim: Mapped[Claim] = relationship(back_populates="assessments")


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(40))
    reviewer_id: Mapped[str] = mapped_column(String(120))
    rationale: Mapped[str] = mapped_column(Text)
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    claim: Mapped[Claim] = relationship(back_populates="reviews")


class ClaimDependency(Base):
    __tablename__ = "claim_dependencies"
    __table_args__ = (UniqueConstraint("parent_claim_id", "child_claim_id", name="uq_claim_dependency"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    parent_claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    child_claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    relationship: Mapped[str] = mapped_column(String(40), default="derived_from")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    action: Mapped[str] = mapped_column(String(80))
    actor: Mapped[str] = mapped_column(String(120))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


Index("ix_claim_job_status", Claim.job_id, Claim.effective_status)
