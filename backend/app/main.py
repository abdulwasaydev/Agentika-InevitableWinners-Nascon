"""Veritas HTTP API. One bounded worker processes persisted jobs."""

import asyncio
import os
from collections import deque
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, update

from .db import database_ready, database_url, make_engine, session_factory
from .models import AuditEvent, Claim, ClaimDependency, HumanReview, SuppliedDocument, VerificationJob, utcnow
from .presentation import claim_detail, claim_summary, job_out, lineage_edge, review_out
from .schemas import (
    ClaimDetail, ErrorOut, HealthOut, JobOut, JobStatus, LineageOut, ReviewQueueOut,
    ReviewRequest, ReviewResult, VerificationRequest, VerifyAccepted,
)
from .services.pipeline import process_job
from .services.policy import PolicyClaim, apply_review, release_action


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def _process_next(factory) -> bool:
    with factory() as session:
        job_id = session.scalar(select(VerificationJob.id).where(VerificationJob.status == JobStatus.queued).order_by(VerificationJob.created_at).limit(1))
    if job_id is None:
        return False
    process_job(factory, job_id, max_claims=max(1, min(20, int(os.getenv("MAX_CLAIMS", "5")))))
    return True


async def _worker(factory, wake: asyncio.Event) -> None:
    while True:
        try:
            worked = await asyncio.to_thread(_process_next, factory)
        except Exception:
            # A transient database outage must not terminate the only worker.
            worked = False
        if worked:
            continue
        wake.clear()
        try:
            await asyncio.wait_for(wake.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass


@asynccontextmanager
async def lifespan(application: FastAPI):
    try:
        engine = make_engine()
    except ValueError:
        engine = None
    ready = database_ready(engine)
    application.state.engine = engine
    application.state.factory = session_factory(engine) if ready else None
    application.state.wake = asyncio.Event()
    application.state.worker = None
    if ready:
        with application.state.factory() as session:
            session.execute(update(VerificationJob).where(VerificationJob.status == JobStatus.running).values(
                status=JobStatus.interrupted, error_code="WORKER_RESTARTED",
                overall_action="hold_for_review", updated_at=utcnow(),
            ))
            session.commit()
        application.state.worker = asyncio.create_task(_worker(application.state.factory, application.state.wake))
    try:
        yield
    finally:
        if application.state.worker is not None:
            application.state.worker.cancel()
            try:
                await application.state.worker
            except asyncio.CancelledError:
                pass
        if engine is not None:
            engine.dispose()


app = FastAPI(title="Veritas API", version="0.1.0", description="Evidence-backed AI claim verification with human review", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message})


def _factory(request: Request):
    factory = getattr(request.app.state, "factory", None)
    if factory is None:
        raise AppError(503, "DATABASE_UNAVAILABLE", "Configure PostgreSQL and apply the reviewed migration, then restart the API")
    return factory


def _recalculate_job(session, job: VerificationJob) -> None:
    claims = list(session.scalars(select(Claim).where(Claim.job_id == job.id)))
    job.overall_action = release_action(job.policy, [
        PolicyClaim(claim.effective_status, claim.material, claim.high_risk)
        for claim in claims
    ])
    job.updated_at = utcnow()


def _reevaluate_descendants(session, parent_id: UUID) -> None:
    # A reviewed ancestor can change the release decision several jobs downstream.
    # Every descendant needs a fresh decision; inherited support is never automatic.
    pending = deque([parent_id])
    visited = {parent_id}
    affected_jobs = set()
    descendants = []
    while pending:
        current_parent_id = pending.popleft()
        children = list(session.scalars(
            select(Claim).join(ClaimDependency, ClaimDependency.child_claim_id == Claim.id)
            .where(ClaimDependency.parent_claim_id == current_parent_id)
        ))
        for child in children:
            if child.id in visited:
                continue
            visited.add(child.id)
            pending.append(child.id)
            descendants.append((child, current_parent_id))
    for child, _ in descendants:
        child.effective_status = "pending_review"
        child.needs_review = True
        affected_jobs.add(child.job_id)
    session.flush()
    for child, direct_parent_id in descendants:
        parent_ids = list(session.scalars(select(ClaimDependency.parent_claim_id).where(ClaimDependency.child_claim_id == child.id)))
        parents = list(session.scalars(select(Claim).where(Claim.id.in_(parent_ids))))
        reasons = list(child.reason_codes)
        if any(parent.effective_status != "supported" for parent in parents):
            if "UNRESOLVED_PARENT" not in reasons:
                reasons.append("UNRESOLVED_PARENT")
            reasons = [code for code in reasons if code != "PARENT_RESOLVED_RECHECK_REQUIRED"]
        else:
            reasons = [code for code in reasons if code != "UNRESOLVED_PARENT"]
            if "PARENT_RESOLVED_RECHECK_REQUIRED" not in reasons:
                reasons.append("PARENT_RESOLVED_RECHECK_REQUIRED")
        child.reason_codes = reasons
        session.add(AuditEvent(
            id=uuid4(), entity_type="claim", entity_id=child.id,
            action="lineage_reevaluated", actor="policy",
            metadata_json={"parent_claim_id": str(direct_parent_id), "status": "pending_review"},
        ))
    for job_id in affected_jobs:
        child_job = session.get(VerificationJob, job_id, with_for_update=True)
        _recalculate_job(session, child_job)


@app.get("/health", response_model=HealthOut)
def health(request: Request) -> HealthOut:
    configured = bool(database_url())
    ready = bool(getattr(request.app.state, "factory", None))
    return HealthOut(status="ok" if ready else "setup_required", database_configured=configured, database_ready=ready)


@app.post("/api/v1/verify", status_code=status.HTTP_202_ACCEPTED, response_model=VerifyAccepted, responses={503: {"model": ErrorOut}})
async def verify(request: VerificationRequest, http_request: Request) -> VerifyAccepted:
    factory = _factory(http_request)
    if len(request.text) > int(os.getenv("MAX_INPUT_CHARS", "8000")):
        raise AppError(422, "INPUT_TOO_LONG", "Text exceeds the configured input limit")
    with factory() as session:
        max_pending = max(1, int(os.getenv("MAX_PENDING_JOBS", "8")))
        pending = session.scalar(select(func.count()).select_from(VerificationJob).where(VerificationJob.status == JobStatus.queued))
        if pending >= max_pending:
            raise AppError(503, "WORKER_QUEUE_FULL", "Too many verification jobs are waiting")
        if request.parent_claim_ids:
            existing = set(session.scalars(select(Claim.id).where(Claim.id.in_(request.parent_claim_ids))))
            if existing != set(request.parent_claim_ids):
                raise AppError(422, "UNKNOWN_PARENT_CLAIM", "Every parent_claim_id must refer to a persisted claim")
        job = VerificationJob(
            id=uuid4(), mode=request.mode, policy=request.policy, origin=request.origin,
            input_text=request.text, parent_claim_ids=[str(x) for x in request.parent_claim_ids],
            status=JobStatus.queued, created_at=utcnow(), updated_at=utcnow(),
        )
        session.add(job)
        for document in request.documents:
            session.add(SuppliedDocument(
                id=uuid4(), job_id=job.id, document_id=document.document_id,
                title=document.title, version=document.version,
                effective_date=document.effective_date, text=document.text,
            ))
        session.commit()
    http_request.app.state.wake.set()
    return VerifyAccepted(job_id=job.id, status=JobStatus.queued, poll_url=f"/api/v1/jobs/{job.id}")


@app.get("/api/v1/jobs/{job_id}", response_model=JobOut, responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def get_job(job_id: UUID, request: Request) -> JobOut:
    with _factory(request)() as session:
        job = session.get(VerificationJob, job_id)
        if job is None:
            raise AppError(404, "JOB_NOT_FOUND", "Unknown job ID")
        return job_out(job)


@app.get("/api/v1/claims/{claim_id}", response_model=ClaimDetail, responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def get_claim(claim_id: UUID, request: Request) -> ClaimDetail:
    with _factory(request)() as session:
        claim = session.get(Claim, claim_id)
        if claim is None:
            raise AppError(404, "CLAIM_NOT_FOUND", "Unknown claim ID")
        parents = list(session.scalars(select(ClaimDependency.parent_claim_id).where(ClaimDependency.child_claim_id == claim_id)))
        return claim_detail(claim, parents)


@app.get("/api/v1/reviews", response_model=ReviewQueueOut, responses={503: {"model": ErrorOut}})
def get_reviews(request: Request, status: str = Query(default="pending", pattern="^(pending|all)$")) -> ReviewQueueOut:
    with _factory(request)() as session:
        query = select(Claim).order_by(Claim.job_id, Claim.start_offset).limit(100)
        if status == "pending":
            query = query.where(Claim.needs_review.is_(True))
        return ReviewQueueOut(items=[claim_summary(c) for c in session.scalars(query)])


@app.post("/api/v1/claims/{claim_id}/reviews", response_model=ReviewResult, responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def submit_review(claim_id: UUID, payload: ReviewRequest, request: Request) -> ReviewResult:
    with _factory(request)() as session:
        claim = session.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
        if claim is None:
            raise AppError(404, "CLAIM_NOT_FOUND", "Unknown claim ID")
        job = session.get(VerificationJob, claim.job_id, with_for_update=True)
        if job.status != JobStatus.completed:
            raise AppError(409, "JOB_NOT_COMPLETED", "Reviews require a completed verification job")
        if claim.checkability == "not_checkable":
            raise AppError(409, "NOT_CHECKABLE", "A non-checkable item has no finding to review")
        effective, needs_review = apply_review(claim.provisional_status, payload.decision)
        if payload.decision == "approve" and "UNRESOLVED_PARENT" in claim.reason_codes:
            effective, needs_review = "pending_review", True
        claim.effective_status = effective
        claim.needs_review = needs_review
        if payload.corrected_text is not None:
            claim.corrected_text = payload.corrected_text
        review = HumanReview(
            id=uuid4(), claim_id=claim.id, decision=payload.decision,
            reviewer_id=payload.reviewer_id, rationale=payload.rationale,
            corrected_text=payload.corrected_text, created_at=utcnow(),
        )
        session.add(review)
        session.add(AuditEvent(
            id=uuid4(), entity_type="claim", entity_id=claim.id,
            action="human_review", actor=payload.reviewer_id,
            metadata_json={"decision": payload.decision, "review_id": str(review.id)},
        ))
        session.flush()
        _recalculate_job(session, job)
        _reevaluate_descendants(session, claim.id)
        session.commit()
        session.expire(claim, ["reviews"])
        parents = list(session.scalars(select(ClaimDependency.parent_claim_id).where(ClaimDependency.child_claim_id == claim_id)))
        return ReviewResult(review=review_out(review), claim=claim_detail(claim, parents), overall_action=job.overall_action)


@app.get("/api/v1/claims/{claim_id}/lineage", response_model=LineageOut, responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def get_lineage(claim_id: UUID, request: Request) -> LineageOut:
    with _factory(request)() as session:
        if session.get(Claim, claim_id) is None:
            raise AppError(404, "CLAIM_NOT_FOUND", "Unknown claim ID")
        edges = list(session.scalars(select(ClaimDependency).where(
            (ClaimDependency.parent_claim_id == claim_id) | (ClaimDependency.child_claim_id == claim_id)
        )))
        return LineageOut(claim_id=claim_id, edges=[lineage_edge(edge) for edge in edges])
