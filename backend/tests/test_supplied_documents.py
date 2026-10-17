"""Exercise the HTTP persistence path in an isolated disposable test database.

Production still requires reviewed PostgreSQL migrations; this is not a fallback.
"""

from fastapi.testclient import TestClient
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models import Base
from app.services.pipeline import process_job


def test_two_supplied_documents_stay_linked_to_one_promise(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    documents = [
        {"document_id": "TERMS-v1", "title": "Terms", "version": "v1", "effective_date": "2026-10-01", "text": "Members may cancel at any time."},
        {"document_id": "FAQ-v2", "title": "FAQ", "version": "v2", "effective_date": "2026-10-02", "text": "Access continues through the paid month."},
    ]
    with TestClient(app) as client:
        app.state.factory = factory
        accepted = client.post("/api/v1/verify", json={"text": "Cancel anytime; access continues through the paid month.", "documents": documents})
        assert accepted.status_code == 202
        job_id = accepted.json()["job_id"]
        process_job(factory, UUID(job_id))
        result = client.get(f"/api/v1/jobs/{job_id}")
        assert result.status_code == 200
        data = result.json()
        assert data["status"] == "completed"
        assert data["overall_action"] == "hold_for_review"
        assert data["claims"][0]["text"] == "Cancel anytime; access continues through the paid month."
        assert len(data["claims"]) == 1
        assert data["documents"] == sorted(documents, key=lambda d: d["document_id"])
        duplicate = client.post("/api/v1/verify", json={"text": "A promise", "documents": [documents[0], documents[0]]})
        assert duplicate.status_code == 422
        oversized = client.post("/api/v1/verify", json={"text": "A promise", "documents": [{**documents[0], "text": "x" * 12001}]})
        assert oversized.status_code == 422
    engine.dispose()
