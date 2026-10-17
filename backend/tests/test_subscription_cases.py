"""The shared fictional inputs traverse the actual HTTP and service pipeline.

This test uses a disposable SQLAlchemy database; it is not a PostgreSQL or
Supabase persistence claim.
"""

import json
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models import Base
from app.services.pipeline import process_job


CASES = json.loads((Path(__file__).resolve().parents[2] / "frontend" / "src" / "fixtures" / "subscription_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case_id,expected,action", [
    ("holds-up", "consistent", "pass"),
    ("exception", "qualified", "hold_for_review"),
    ("unresolved", "insufficient_evidence", "hold_for_review"),
])
def test_fictional_case_follows_real_api_pipeline(case_id, expected, action, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    example = next(case for case in CASES if case["id"] == case_id)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with TestClient(app) as client:
        app.state.factory = factory
        accepted = client.post("/api/v1/verify", json={"text": example["advertisement"], "documents": example["documents"], "policy": "strict"})
        assert accepted.status_code == 202
        job_id = accepted.json()["job_id"]
        process_job(factory, UUID(job_id))
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        assert job["status"] == "completed"
        assert job["input_text"] == example["advertisement"]
        assert len(job["documents"]) == 2
        assert job["overall_action"] == action
        assert len(job["claims"]) == 1
        assert job["claims"][0]["comparison_result"] == expected
        detail = client.get(f"/api/v1/claims/{job['claims'][0]['id']}").json()
        by_id = {document["document_id"]: document for document in example["documents"]}
        assert all(item["excerpt"] in by_id[item["document_id"]]["text"] for item in detail["evidence"])
        assert all(item["validity_status"] == "valid" for item in detail["evidence"])
        if case_id == "exception":
            assert any("never been used" in item["excerpt"] and item["stance"] == "challenge" for item in detail["evidence"])
        if case_id == "unresolved":
            assert any("refund" in question for question in detail["unresolved_questions"])
            assert "not proof of deception" in detail["comparison_explanation"]
    engine.dispose()


def test_review_history_and_guardian_hold_survive_app_lifespan(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    example = next(case for case in CASES if case["id"] == "exception")
    with TestClient(app) as client:
        app.state.factory = factory
        accepted = client.post("/api/v1/verify", json={"text": example["advertisement"], "documents": example["documents"], "mode": "guardian", "policy": "strict"})
        assert accepted.status_code == 202
        job_id = accepted.json()["job_id"]
        process_job(factory, UUID(job_id))
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        assert job["overall_action"] == "hold_for_review"
        claim_id = job["claims"][0]["id"]
        approved = client.post(f"/api/v1/claims/{claim_id}/reviews", json={
            "decision": "approve", "reviewer_id": "demo-reviewer", "rationale": "The usage condition still narrows the promise.",
        })
        assert approved.status_code == 200
        assert approved.json()["overall_action"] == "hold_for_review"
        assert approved.json()["claim"]["needs_review"] is True
        corrected = client.post(f"/api/v1/claims/{claim_id}/reviews", json={
            "decision": "correct", "reviewer_id": "demo-reviewer", "rationale": "Display the condition explicitly.",
            "corrected_text": "A full refund within 30 days only if the service was unused.",
        })
        assert corrected.status_code == 200
        assert corrected.json()["claim"]["text"] == example["advertisement"]
        assert corrected.json()["claim"]["corrected_text"] != example["advertisement"]
        assert corrected.json()["overall_action"] == "hold_for_review"
        assert corrected.json()["claim"]["provisional_status"] == "pending_review"
        assert len(corrected.json()["claim"]["reviews"]) == 2
        assert all(review["reviewer_id"] == "demo-reviewer" and review["rationale"] and review["created_at"] for review in corrected.json()["claim"]["reviews"])
    with TestClient(app) as client:
        app.state.factory = factory
        persisted = client.get(f"/api/v1/claims/{claim_id}").json()
        assert persisted["comparison_result"] == "qualified"
        assert len(persisted["reviews"]) == 2
        assert client.get(f"/api/v1/jobs/{job_id}").json()["overall_action"] == "hold_for_review"
    engine.dispose()


def test_insufficient_review_does_not_release_refund_claim(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    example = next(case for case in CASES if case["id"] == "unresolved")
    with TestClient(app) as client:
        app.state.factory = factory
        accepted = client.post("/api/v1/verify", json={"text": example["advertisement"], "documents": example["documents"], "mode": "guardian", "policy": "strict"})
        job_id = accepted.json()["job_id"]
        process_job(factory, UUID(job_id))
        claim_id = client.get(f"/api/v1/jobs/{job_id}").json()["claims"][0]["id"]
        reviewed = client.post(f"/api/v1/claims/{claim_id}/reviews", json={
            "decision": "insufficient", "reviewer_id": "demo-reviewer", "rationale": "Refund eligibility is missing from supplied terms.",
        })
        assert reviewed.status_code == 200
        assert reviewed.json()["claim"]["effective_status"] == "insufficient_evidence"
        assert reviewed.json()["claim"]["comparison_result"] == "insufficient_evidence"
        assert reviewed.json()["overall_action"] == "hold_for_review"
        assert client.get(f"/api/v1/jobs/{job_id}").json()["overall_action"] == "hold_for_review"
    engine.dispose()
