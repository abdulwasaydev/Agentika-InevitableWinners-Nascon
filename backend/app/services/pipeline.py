"""One bounded, persistent verification job through actual services."""

import os
import hashlib
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..models import AgentAssessment, AuditEvent, Claim, ClaimDependency, Evidence, VerificationJob, utcnow
from ..schemas import ClaimStatus, JobStatus
from ..providers.live import ProviderFailure, live_extract
from .extraction import ClaimLimitExceeded, ExtractedClaim, extract_claims
from .policy import PolicyClaim, release_action
from .comparison import compare_promise
from .official_policy import (
    POLICY_ORIGIN, PASTED_POLICY_ORIGIN, PolicySnapshot, PolicySourceUnavailable,
    compare_official_policy, compare_policy_text,
)
from .verification import verify_one_claim


def demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "true").strip().lower() in {"1", "true", "yes"}


def process_job(factory: sessionmaker[Session], job_id: UUID, *, max_claims: int = 5) -> None:
    with factory() as session:
        job = session.get(VerificationJob, job_id)
        if job is None or job.status != JobStatus.queued:
            return
        job.status = JobStatus.running
        job.updated_at = utcnow()
        session.commit()

    try:
        with factory() as session:
            job = session.get(VerificationJob, job_id)
            assert job is not None
            extracted = (
                [ExtractedClaim(job.input_text, 0, len(job.input_text), "checkable", False)]
                if job.documents or job.origin in {POLICY_ORIGIN, PASTED_POLICY_ORIGIN} else
                extract_claims(job.input_text, max_claims=max_claims) if demo_mode() else
                live_extract(job.input_text, max_claims=max_claims)
            )
            parent_ids = [UUID(value) for value in job.parent_claim_ids]
            parents = list(session.scalars(select(Claim).where(Claim.id.in_(parent_ids)))) if parent_ids else []
            unresolved_parent = any(p.effective_status != ClaimStatus.supported for p in parents)
            policy_claims: list[PolicyClaim] = []

            for item in extracted:
                if job.origin == POLICY_ORIGIN:
                    comparison = compare_official_policy(item.text)
                elif job.origin == PASTED_POLICY_ORIGIN:
                    if len(job.documents) != 1:
                        raise PolicySourceUnavailable("Pasted policy document is missing")
                    policy_text = job.documents[0].text
                    snapshot = PolicySnapshot(policy_text, hashlib.sha256(policy_text.encode("utf-8")).hexdigest(), job.created_at)
                    comparison = compare_policy_text(item.text, snapshot, verified_source=False)
                else:
                    comparison = compare_promise(item.text, job.documents) if job.documents else None
                verification = None if comparison else verify_one_claim(
                    item, use_demo=demo_mode(), unresolved_parent=unresolved_parent,
                )
                candidates = comparison.evidence if comparison else verification.evidence
                support = comparison.support if comparison else verification.support
                challenge = comparison.challenge if comparison else verification.challenge
                finding = comparison.finding if comparison else verification.finding
                claim = Claim(
                    id=uuid4(), job_id=job.id, text=item.text,
                    start_offset=item.start_offset, end_offset=item.end_offset,
                    checkability=item.checkability,
                    provisional_status=finding.provisional_status,
                    effective_status=finding.effective_status,
                    needs_review=finding.needs_review,
                    reason_codes=finding.reason_codes,
                    comparison_result=comparison.result if comparison else None,
                    comparison_explanation=comparison.explanation if comparison else None,
                    unresolved_questions=comparison.unresolved_questions if comparison else [],
                    material=item.checkability == "checkable", high_risk=item.high_risk,
                )
                session.add(claim)
                for candidate in candidates:
                    session.add(Evidence(
                        id=candidate.id, claim_id=claim.id, stance=candidate.stance,
                        source_type=candidate.source_type, provenance=candidate.provenance,
                        url=candidate.url, document_id=candidate.document_id,
                        title=candidate.title, excerpt=candidate.excerpt,
                        source_text=candidate.source_text, retrieved_at=candidate.retrieved_at,
                        published_at=candidate.published_at, validity_status=candidate.validity_status,
                    ))
                for draft in (support, challenge):
                    session.add(AgentAssessment(
                        id=uuid4(), claim_id=claim.id, role=draft.role,
                        position=draft.position, reasoning_summary=draft.reasoning_summary,
                        evidence_ids=[str(c.evidence_id) for c in draft.citations],
                        limitations=draft.limitations,
                    ))
                for parent in parents:
                    session.add(ClaimDependency(
                        id=uuid4(), parent_claim_id=parent.id, child_claim_id=claim.id,
                        relationship="derived_from",
                    ))
                policy_claims.append(PolicyClaim(finding.effective_status, claim.material, claim.high_risk))

            job.overall_action = release_action(job.policy, policy_claims)
            job.status = JobStatus.completed
            job.updated_at = utcnow()
            session.add(AuditEvent(
                id=uuid4(), entity_type="job", entity_id=job.id,
                action="verification_completed", actor="worker",
                metadata_json={"claim_count": len(extracted), "demo_mode": demo_mode() and job.origin not in {POLICY_ORIGIN, PASTED_POLICY_ORIGIN}},
            ))
            session.commit()
    except Exception as exc:
        with factory() as session:
            job = session.get(VerificationJob, job_id)
            if job is not None:
                job.status = JobStatus.failed
                job.error_code = ("SOURCE_UNAVAILABLE" if isinstance(exc, PolicySourceUnavailable)
                                  else "CLAIM_LIMIT_EXCEEDED" if isinstance(exc, ClaimLimitExceeded)
                                  else "PROVIDER_ERROR" if isinstance(exc, ProviderFailure)
                                  else "PROCESSING_ERROR")
                job.overall_action = "hold_for_review"
                job.updated_at = utcnow()
                session.commit()
