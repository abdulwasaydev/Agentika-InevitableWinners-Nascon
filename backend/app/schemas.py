"""The canonical public API contract. Export OpenAPI from these models."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    interrupted = "interrupted"


class ClaimStatus(StrEnum):
    supported = "supported"
    disputed = "disputed"
    insufficient_evidence = "insufficient_evidence"
    pending_review = "pending_review"
    not_checkable = "not_checkable"


class ReleaseAction(StrEnum):
    pass_ = "pass"
    annotate = "annotate"
    hold_for_review = "hold_for_review"


class ReviewDecision(StrEnum):
    approve = "approve"
    dispute = "dispute"
    insufficient = "insufficient"
    request_more_evidence = "request_more_evidence"
    correct = "correct"


class SuppliedDocumentIn(BaseModel):
    document_id: Annotated[str, Field(min_length=1, max_length=120)]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    version: Annotated[str | None, Field(max_length=80)] = None
    effective_date: Annotated[str | None, Field(max_length=80)] = None
    text: Annotated[str, Field(min_length=1, max_length=12000)]

    @model_validator(mode="after")
    def nonblank_fields(self):
        if not all((self.document_id.strip(), self.title.strip(), self.text.strip())):
            raise ValueError("document ID, title and text must contain non-whitespace characters")
        return self


class SuppliedDocumentOut(SuppliedDocumentIn):
    pass


class VerificationRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=8000)]
    mode: Annotated[str, Field(pattern="^(guardian|claim_court)$")] = "claim_court"
    policy: Annotated[str, Field(pattern="^(strict|balanced)$")] = "strict"
    origin: Annotated[str, Field(min_length=1, max_length=80)] = "user_input"
    parent_claim_ids: list[UUID] = Field(default_factory=list, max_length=20)
    documents: list[SuppliedDocumentIn] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def nonblank_text(self):
        if not self.text.strip():
            raise ValueError("text must contain non-whitespace characters")
        if len({doc.document_id for doc in self.documents}) != len(self.documents):
            raise ValueError("document IDs must be unique within a submission")
        if sum(len(doc.text) for doc in self.documents) > 24000:
            raise ValueError("combined document text exceeds 24000 characters")
        return self


class VerifyAccepted(BaseModel):
    job_id: UUID
    status: JobStatus
    poll_url: str


class EvidenceOut(BaseModel):
    id: UUID
    stance: str
    source_type: str
    provenance: str
    url: str | None = None
    document_id: str | None = None
    title: str
    excerpt: str
    retrieved_at: datetime
    published_at: datetime | None = None
    validity_status: str


class AssessmentOut(BaseModel):
    id: UUID
    role: str
    position: str
    reasoning_summary: str
    evidence_ids: list[UUID]
    limitations: str | None = None
    created_at: datetime


class ReviewOut(BaseModel):
    id: UUID
    claim_id: UUID
    decision: ReviewDecision
    reviewer_id: str
    rationale: str
    corrected_text: str | None = None
    created_at: datetime


class ClaimSummary(BaseModel):
    id: UUID
    job_id: UUID
    text: str
    start_offset: int | None = None
    end_offset: int | None = None
    checkability: str
    provisional_status: ClaimStatus
    effective_status: ClaimStatus
    needs_review: bool
    reason_codes: list[str]
    support_evidence_ids: list[UUID]
    challenge_evidence_ids: list[UUID]
    corrected_text: str | None = None


class ClaimDetail(ClaimSummary):
    evidence: list[EvidenceOut]
    assessments: list[AssessmentOut]
    reviews: list[ReviewOut]
    parent_claim_ids: list[UUID]


class JobOut(BaseModel):
    id: UUID
    status: JobStatus
    mode: str
    policy: str
    origin: str
    input_text: str
    documents: list[SuppliedDocumentOut] = Field(default_factory=list)
    overall_action: ReleaseAction | None = None
    claims: list[ClaimSummary]
    created_at: datetime
    updated_at: datetime
    error_code: str | None = None


class ReviewQueueOut(BaseModel):
    items: list[ClaimSummary]


class ReviewResult(BaseModel):
    review: ReviewOut
    claim: ClaimDetail
    overall_action: ReleaseAction


class ReviewRequest(BaseModel):
    decision: ReviewDecision
    reviewer_id: Annotated[str, Field(min_length=1, max_length=120)]
    rationale: Annotated[str, Field(min_length=3, max_length=2000)]
    corrected_text: Annotated[str | None, Field(max_length=8000)] = None

    @model_validator(mode="after")
    def correction_requires_text(self):
        if self.decision == ReviewDecision.correct and not self.corrected_text:
            raise ValueError("corrected_text is required for a correction")
        if self.decision != ReviewDecision.correct and self.corrected_text:
            raise ValueError("corrected_text is only allowed for a correction")
        return self


class LineageEdge(BaseModel):
    parent_claim_id: UUID
    child_claim_id: UUID
    relationship: str


class LineageOut(BaseModel):
    claim_id: UUID
    edges: list[LineageEdge]


class HealthOut(BaseModel):
    status: str
    database_configured: bool
    database_ready: bool


class ErrorOut(BaseModel):
    code: str
    message: str
