"""Veritas HTTP API. Route schemas are exported as the shared contract."""

from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, status

from .schemas import (
    ClaimDetail, ErrorOut, HealthOut, JobOut, LineageOut, ReviewQueueOut,
    ReviewRequest, ReviewResult, VerificationRequest, VerifyAccepted,
)

app = FastAPI(title="Veritas API", version="0.1.0", description="Evidence-backed AI claim verification with human review")


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="setup_required", database_configured=False, database_ready=False)


@app.post("/api/v1/verify", status_code=status.HTTP_202_ACCEPTED, response_model=VerifyAccepted, responses={503: {"model": ErrorOut}})
def verify(request: VerificationRequest) -> VerifyAccepted:
    raise HTTPException(503, detail="Database and worker are not configured")


@app.get("/api/v1/jobs/{job_id}", response_model=JobOut, responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def get_job(job_id: UUID) -> JobOut:
    raise HTTPException(503, detail="Database is not configured")


@app.get("/api/v1/claims/{claim_id}", response_model=ClaimDetail, responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def get_claim(claim_id: UUID) -> ClaimDetail:
    raise HTTPException(503, detail="Database is not configured")


@app.get("/api/v1/reviews", response_model=ReviewQueueOut, responses={503: {"model": ErrorOut}})
def get_reviews(status: str = Query(default="pending", pattern="^(pending|all)$")) -> ReviewQueueOut:
    raise HTTPException(503, detail="Database is not configured")


@app.post("/api/v1/claims/{claim_id}/reviews", response_model=ReviewResult, responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def submit_review(claim_id: UUID, request: ReviewRequest) -> ReviewResult:
    raise HTTPException(503, detail="Database is not configured")


@app.get("/api/v1/claims/{claim_id}/lineage", response_model=LineageOut, responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def get_lineage(claim_id: UUID) -> LineageOut:
    raise HTTPException(503, detail="Database is not configured")
