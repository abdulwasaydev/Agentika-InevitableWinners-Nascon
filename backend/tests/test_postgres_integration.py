"""Optional durable flow. Runs only against an explicitly isolated local PostgreSQL DB."""

import os
import time
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.main import app
from app.models import AuditEvent, VerificationJob, utcnow


def _local_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not configured")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+psycopg" or parsed.host not in {"localhost", "127.0.0.1", "::1"} or parsed.database != "veritas_test":
        pytest.skip("Only a dedicated local PostgreSQL veritas_test database is allowed")
    return url


def _completed(client: TestClient, job_id: str) -> dict:
    for _ in range(100):
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"completed", "failed", "interrupted"}:
            return job
        time.sleep(0.05)
    pytest.fail("worker did not complete within five seconds")


def test_seeded_job_review_audit_and_restart(monkeypatch):
    url = _local_url()
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DEMO_MODE", "true")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")

    with TestClient(app) as client:
        response = client.post("/api/v1/verify", json={
            "mode": "guardian", "policy": "strict",
            "text": "The fictional Aster Archive opened in 2018.",
        })
        assert response.status_code == 202
        job = _completed(client, response.json()["job_id"])
        assert job["status"] == "completed"
        assert job["overall_action"] == "hold_for_review"
        claim_id = job["claims"][0]["id"]
        child_response = client.post("/api/v1/verify", json={
            "mode": "guardian", "policy": "strict",
            "text": "The fictional Aster Archive opened in 2020.",
            "parent_claim_ids": [claim_id],
        })
        assert child_response.status_code == 202
        child = _completed(client, child_response.json()["job_id"])
        assert child["claims"][0]["provisional_status"] == "supported"
        assert child["claims"][0]["effective_status"] == "pending_review"
        assert child["overall_action"] == "hold_for_review"
        lineage = client.get(f"/api/v1/claims/{child['claims'][0]['id']}/lineage").json()
        assert lineage["edges"][0]["parent_claim_id"] == claim_id
        queue = client.get("/api/v1/reviews?status=pending").json()["items"]
        assert any(item["id"] == claim_id for item in queue)
        review = client.post(f"/api/v1/claims/{claim_id}/reviews", json={
            "decision": "approve", "reviewer_id": "local-test", "rationale": "Accept the disputed finding",
        })
        assert review.status_code == 200
        assert review.json()["overall_action"] == "hold_for_review"
        correction = client.post(f"/api/v1/claims/{claim_id}/reviews", json={
            "decision": "correct", "reviewer_id": "local-test",
            "rationale": "Propose the documented year", "corrected_text": "The fictional Aster Archive opened in 2020.",
        })
        assert correction.status_code == 200
        detail = correction.json()["claim"]
        assert detail["text"] == "The fictional Aster Archive opened in 2018."
        assert detail["corrected_text"] == "The fictional Aster Archive opened in 2020."
        assert len(detail["reviews"]) == 2
        assert correction.json()["overall_action"] == "hold_for_review"
        assert client.get(f"/api/v1/jobs/{child['id']}").json()["overall_action"] == "hold_for_review"

    engine = create_engine(url)
    interrupted_id = uuid4()
    with Session(engine) as session:
        events = session.query(AuditEvent).filter(AuditEvent.entity_id == UUID(claim_id)).all()
        assert sum(event.action == "human_review" for event in events) == 2
        session.add(VerificationJob(
            id=interrupted_id, mode="guardian", policy="strict", origin="local_test",
            input_text="A test claim.", parent_claim_ids=[], status="running",
            created_at=utcnow(), updated_at=utcnow(),
        ))
        session.commit()
    engine.dispose()
    with TestClient(app) as client:
        restarted = client.get(f"/api/v1/jobs/{interrupted_id}").json()
        assert restarted["status"] == "interrupted"
        assert restarted["overall_action"] == "hold_for_review"
