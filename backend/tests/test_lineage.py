"""Test policy propagation in an isolated SQLAlchemy unit database.

Production still requires PostgreSQL; this test never configures an API database.
"""

from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.main import _reevaluate_descendants
from app.models import AuditEvent, Base, Claim, ClaimDependency, VerificationJob


def test_ancestor_review_reholds_every_downstream_job():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        claims = []
        jobs = []
        for index in range(3):
            job = VerificationJob(
                id=uuid4(), mode="guardian", policy="strict", origin="test",
                input_text=f"Claim {index}", parent_claim_ids=[],
                status="completed", overall_action="pass",
            )
            claim = Claim(
                id=uuid4(), job_id=job.id, text=f"Claim {index}",
                checkability="checkable", provisional_status="supported",
                effective_status="supported", reason_codes=[], needs_review=False,
                material=True, high_risk=False,
            )
            session.add_all([job, claim])
            jobs.append(job)
            claims.append(claim)
        for parent, child in zip(claims, claims[1:]):
            session.add(ClaimDependency(id=uuid4(), parent_claim_id=parent.id, child_claim_id=child.id))
        # The shortcut edge makes traversal order unsafe if reasons are set too early.
        session.add(ClaimDependency(id=uuid4(), parent_claim_id=claims[0].id, child_claim_id=claims[2].id))
        session.flush()

        claims[0].effective_status = "disputed"
        _reevaluate_descendants(session, claims[0].id)
        session.flush()
        assert [claim.effective_status for claim in claims] == ["disputed", "pending_review", "pending_review"]
        assert [job.overall_action for job in jobs] == ["pass", "hold_for_review", "hold_for_review"]
        assert all("UNRESOLVED_PARENT" in claim.reason_codes for claim in claims[1:])
        assert len(list(session.scalars(select(AuditEvent).where(AuditEvent.action == "lineage_reevaluated")))) == 2

        claims[0].effective_status = "supported"
        _reevaluate_descendants(session, claims[0].id)
        session.flush()
        assert claims[1].effective_status == "pending_review"
        assert "PARENT_RESOLVED_RECHECK_REQUIRED" in claims[1].reason_codes
        assert "UNRESOLVED_PARENT" in claims[2].reason_codes
        assert jobs[1].overall_action == "hold_for_review"
    engine.dispose()
