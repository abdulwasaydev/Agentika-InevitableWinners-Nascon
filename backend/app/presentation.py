"""Map persisted records to the public API without exposing raw source text."""

from .models import Claim, ClaimDependency, HumanReview, VerificationJob
from .schemas import (
    AssessmentOut, ClaimDetail, ClaimSummary, EvidenceOut, JobOut,
    LineageEdge, ReviewOut, SuppliedDocumentOut,
)


def claim_summary(claim: Claim) -> ClaimSummary:
    return ClaimSummary(
        id=claim.id, job_id=claim.job_id, text=claim.text,
        start_offset=claim.start_offset, end_offset=claim.end_offset,
        checkability=claim.checkability,
        provisional_status=claim.provisional_status,
        effective_status=claim.effective_status,
        needs_review=claim.needs_review, reason_codes=claim.reason_codes,
        comparison_result=claim.comparison_result,
        comparison_explanation=claim.comparison_explanation,
        unresolved_questions=claim.unresolved_questions,
        support_evidence_ids=[e.id for e in claim.evidence if e.stance == "support" and e.validity_status == "valid"],
        challenge_evidence_ids=[e.id for e in claim.evidence if e.stance == "challenge" and e.validity_status == "valid"],
        corrected_text=claim.corrected_text,
    )


def review_out(review: HumanReview) -> ReviewOut:
    return ReviewOut(
        id=review.id, claim_id=review.claim_id, decision=review.decision,
        reviewer_id=review.reviewer_id, rationale=review.rationale,
        corrected_text=review.corrected_text, created_at=review.created_at,
    )


def claim_detail(claim: Claim, parent_claim_ids: list) -> ClaimDetail:
    base = claim_summary(claim).model_dump()
    return ClaimDetail(
        **base,
        evidence=[EvidenceOut(
            id=e.id, stance=e.stance, source_type=e.source_type,
            provenance=e.provenance, url=e.url, document_id=e.document_id,
            title=e.title, excerpt=e.excerpt, retrieved_at=e.retrieved_at,
            published_at=e.published_at, validity_status=e.validity_status,
        ) for e in claim.evidence],
        assessments=[AssessmentOut(
            id=a.id, role=a.role, position=a.position,
            reasoning_summary=a.reasoning_summary,
            evidence_ids=a.evidence_ids, limitations=a.limitations,
            created_at=a.created_at,
        ) for a in claim.assessments],
        reviews=[review_out(r) for r in claim.reviews],
        parent_claim_ids=parent_claim_ids,
    )


def job_out(job: VerificationJob) -> JobOut:
    return JobOut(
        id=job.id, status=job.status, mode=job.mode, policy=job.policy,
        origin=job.origin, input_text=job.input_text,
        documents=[SuppliedDocumentOut(
            document_id=d.document_id, title=d.title, version=d.version,
            effective_date=d.effective_date, text=d.text,
        ) for d in job.documents],
        overall_action=job.overall_action,
        claims=[claim_summary(c) for c in job.claims],
        created_at=job.created_at, updated_at=job.updated_at,
        error_code=job.error_code,
    )


def lineage_edge(edge: ClaimDependency) -> LineageEdge:
    return LineageEdge(
        parent_claim_id=edge.parent_claim_id,
        child_claim_id=edge.child_claim_id,
        relationship=edge.relationship,
    )
